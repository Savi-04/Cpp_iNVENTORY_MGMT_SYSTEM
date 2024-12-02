from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect
import json
from django.http import Http404,JsonResponse
from .forms import ProductForm, OrderForm
from aws_utility_library_savicppapp import *
# from .dbpart.dynamodb import DynamoDBTable
# from .dbpart.sqs_sns import send_sns_notification,fetch_sqs_messages,delete_sqs_message
# from .dbpart.s3 import upload_to_s3
# from .dbpart.lambda_utility import trigger_lambda
from allauth.account.views import SignupView
from .models import UserProfile
import matplotlib
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import uuid 
import os

matplotlib.use("Agg")
# adding variable name to identify the table to be used.
products_table = DynamoDBTable(table_name=os.environ['PRODUCTS_DYNAMODB_TABLE_NAME'])
orders_table = DynamoDBTable(table_name=os.environ['ORDERS_DYNAMODB_TABLE_NAME'])

class CustomSignupView(SignupView):
    def form_valid(self, form):
        response = super().form_valid(form)
        phone = self.request.POST.get('phone')
        address = self.request.POST.get('address')

        UserProfile.objects.create(
            user=self.user, 
            phone=phone,
            address=address
        )

        return response
    
class Index(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/mainpage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fetch orders and products for the dashboard
        orders = orders_table.get_all_items()
        products = [order["product_name"] for order in orders]
        quantities = [order["quantity"] for order in orders]

        # Generate pie chart
        plt.figure(figsize=(6, 6))
        plt.pie(quantities, labels=products, autopct="%1.1f%%", startangle=140)
        plt.title("Order Distribution by Product")
        pie_chart = self.save_plot_to_base64()

        # Generate bar chart
        plt.figure(figsize=(8, 5))
        plt.bar(products, quantities, color="skyblue")
        plt.title("Total Quantities Ordered by Product")
        plt.xlabel("Products")
        plt.ylabel("Quantities")
        bar_graph = self.save_plot_to_base64()

        # Add chart data to context
        context["pie_chart"] = pie_chart
        context["bar_graph"] = bar_graph
        context['profile_count'] = UserProfile.objects.count()
        context['order_count'] = len(orders_table.get_all_items())
        context['product_count'] = len(products_table.get_all_items())

        # Fetch notifications from SQS
        #context['notifications'] = fetch_sqs_messages(sqs_queue_url=os.environ['PRODUCTS_SQS_QUEUE_URL'])
        context['notifications'] = []
        messages = fetch_sqs_messages(sqs_queue_url=os.environ['PRODUCTS_SQS_QUEUE_URL'])
        for msg in messages:
           try:
                # Parse the message body as JSON
                body = json.loads(msg["body"])
                context["notifications"].append({
                    "message": body.get("Message", "Unknown message"),
                    "timestamp": body.get("Timestamp", "Unknown timestamp"),
                    "receipt_handle": msg["receipt_handle"]
                })
           except json.JSONDecodeError:
                # If parsing fails, fallback to raw body
                context["notifications"].append({
                    "message": msg["Body"],
                    "timestamp": "Unknown timestamp",
                    "receipt_handle": msg["receipt_handle"]
                })

        return context

      
        

      

    def post(self, request, *args, **kwargs):
        """
        Handle 'Mark as Read' action by deleting a notification from SQS.
        """
        receipt_handle = request.POST.get("receipt_handle")

        if receipt_handle:
            success = delete_sqs_message(sqs_queue_url=os.environ['PRODUCTS_SQS_QUEUE_URL'], receipt_handle=receipt_handle)
            if success:
                return redirect('dashboard')
        
        return redirect('dashboard')

    def save_plot_to_base64(self):
        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        buffer.close()
        plt.close('all')
        return image_base64

    def test_func(self):
        return self.request.user.is_superuser

class Products(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/myproducts.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        """
        Fetch the necessary context data for the products page.
        """
        context = super().get_context_data(**kwargs)
        context['profile_count'] = UserProfile.objects.count()
        context['order_count'] = len(orders_table.get_all_items())
        context['product_count'] = len(products_table.get_all_items())
        context['products'] = products_table.get_all_items()
        context['form'] = ProductForm()
        return context

    def post(self, request, *args, **kwargs):
        """
        Handle product addition while checking if the product already exists.
        """
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            # Extract data from the form
            product_name = form.cleaned_data['product_name'].strip().lower()
            category = form.cleaned_data['category']
            stock_quantity = form.cleaned_data['stock_quantity']
            image = form.cleaned_data['image']

            # Fetch all existing products from the database
            products = products_table.get_all_items()

            # Check for case-insensitive match of product name
            product_exists = any(
                p['name'].strip().lower() == product_name for p in products if 'name' in p
            )

            if product_exists:
                # If product exists, add an error to the context and stop the operation
                # context = self.get_context_data(**kwargs)
                # context['form'] = form
                # context['error'] = f"The product '{form.cleaned_data['product_name']}' already exists."
                messages.error(request, f"The product '{form.cleaned_data['product_name']}' already exists.")
                return redirect('products')
                

            # Proceed to add the product if it doesn't exist
            bucket_name = os.environ['PRODUCTS_S3_BUCKET_NAME']  
            region_name = os.environ['AWS_REGION']
            object_name_prefix = "products/"  # Folder structure in S3

            # Upload image to S3
            image_url = upload_to_s3(image, bucket_name, object_name_prefix, region_name)

            if not image_url:
                context = self.get_context_data(**kwargs)
                context['form'] = form
                context['error'] = "Image upload failed."
                return self.render_to_response(context)

            # Add product to DynamoDB
            product_id = str(uuid.uuid4())
            product_data = {
                'product_id': product_id,  
                'name': form.cleaned_data['product_name'],
                'category': category,
                'quantity': stock_quantity,
                'image_url': image_url,
            }
            products_table.put_item(product_data)
            messages.success(request, f"Product '{form.cleaned_data['product_name']}' added successfully!")
            return redirect('products')
        else:
            # If the form is invalid, re-render the page with errors
            context = self.get_context_data(**kwargs)
            context['form'] = form
            messages.error(request, "Form submission failed. Please correct the errors.")
            return self.render_to_response(context)


class EditProducts(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/edit_products.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_id = self.kwargs.get('product_id')
        product = products_table.get_item(key={'product_id': product_id})
        if not product:
            raise Http404("Product not found.")

        # Pre-fill the form with existing product details
        context['form'] = ProductForm(initial={
            'product_name': product.get('name'),
            'category': product.get('category'),
            'stock_quantity': product.get('quantity'),
        })
        context['product_id'] = product_id
        context['existing_image_url'] = product.get('image_url')  # Pass existing image URL to template
        return context

    def post(self, request, *args, **kwargs):
        form = ProductForm(request.POST, request.FILES)
        product_id = self.kwargs.get('product_id')
        if form.is_valid():
            data = form.cleaned_data
            image = request.FILES.get("image")

            # Prepare Lambda payload for update
            payload = {
                "operation": "update",
                "table_name": os.environ['PRODUCTS_DYNAMODB_TABLE_NAME'],
                "item_id": product_id,
                "update_data": {
                    "name": data["product_name"],
                    "category": data["category"],
                    "quantity": data["stock_quantity"],
                },
            }

            if image:
                # Upload new image to S3
                bucket_name = os.environ['PRODUCTS_S3_BUCKET_NAME']
                object_key = f"products/{product_id}.jpg"  # Use product_id for consistent naming
                image_url = upload_to_s3(image, bucket_name, object_key, os.environ['AWS_REGION'])
                if not image_url:
                    messages.error(request, "Failed to upload the image. Please try again.")
                    return redirect('edit_product', product_id=product_id)

                # Add the new image URL to the payload
                payload["update_data"]["image_url"] = image_url

            # Trigger Lambda function
            response = trigger_lambda(
                lambda_name="manage_product_operations",  # Replace with your Lambda function name
                payload=payload,
                region_name=os.environ['AWS_REGION']
            )

            # Handle Lambda response
            if response.get("status") == "success":
                messages.success(request, "Product updated successfully!")
                return redirect('products')
            else:
                messages.error(request, response.get("message", "Failed to update the product."))
        else:
            messages.error(request, "Form submission failed. Please correct the errors.")
        return redirect('edit_product', product_id=product_id)

class DeleteProduct(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "dashboard/delete_product.html"

    def test_func(self):
        return self.request.user.is_superuser

    def post(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_id')
        if not product_id:
            messages.error(request, "Product ID is missing.")
            return redirect('products')

        # Prepare the payload for Lambda
        payload = {
            "operation": "delete",
            "table_name": os.environ['PRODUCTS_DYNAMODB_TABLE_NAME'],
            "item_id": product_id,
            "bucket_name": os.environ['PRODUCTS_S3_BUCKET_NAME'],
            "object_key": f"products/{product_id}.jpg",  # Adjust based on your S3 key structure
        }

        try:
            # Trigger the Lambda function
            response = trigger_lambda(
                lambda_name="manage_product_operations",  # Replace with your Lambda function name
                payload=payload,
                region_name=os.environ['AWS_REGION']
            )

            # Handle Lambda response
            if response.get("status") == "success":
                messages.success(request, "Product deleted successfully.")
            else:
                error_message = response.get("message", "Failed to delete product.")
                messages.error(request, error_message)

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

        return redirect('products')

class Staff(LoginRequiredMixin,UserPassesTestMixin,TemplateView):
     template_name='dashboard/staff.html'
     def test_func(self):
        return self.request.user.is_superuser
     def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profiles'] = UserProfile.objects.all()
        return context

class Orders(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/orders.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        """
        Fetch context data for the orders dashboard.
        Includes counts for profiles, orders, products, and the list of orders.
        """
        context = super().get_context_data(**kwargs)
        context['profile_count'] = UserProfile.objects.count()
        context['order_count'] = len(orders_table.get_all_items())
        context['product_count'] = len(products_table.get_all_items())
        context['orders'] = orders_table.get_all_items()
        return context

    def post(self, request, *args, **kwargs):
        """
        Handle 'Approve' or 'Reject' logic for an order.
        """
        order_id = request.POST.get("order_id")
        action = request.POST.get("action")  # 'approve' or 'reject'

        if not order_id:
            return JsonResponse({"status": "error", "message": "Order ID is missing."})
        if action not in ["approve", "reject"]:
            return JsonResponse({"status": "error", "message": f"Invalid action: {action}"})

        try:
            # Fetch the order details
            order = orders_table.get_item(key={"order_id": order_id})
            if not order:
                return JsonResponse({"status": "error", "message": "Order not found."})

            if action == "approve":
                return self._approve_order(order)

            elif action == "reject":
                return self._reject_order(order_id)

        except Exception as e:
            print(f"Error processing order action: {e}")
            return JsonResponse({"status": "error", "message": str(e)})

    def _approve_order(self, order):
        """
        Approve an order if sufficient stock is available.
        Updates the order status and reduces stock.
        """
        product_id = order.get("product_id")
        requested_quantity = order.get("quantity")

        if not product_id:
            return JsonResponse({
                "status": "error",
                "message": "Product ID is missing from the order."
            })

        # Fetch the product details using product_id
        product = products_table.get_item(key={"product_id": product_id})
        if not product:
            return JsonResponse({
                "status": "error",
                "message": f"Product with ID '{product_id}' not found in inventory."
            })

        available_quantity = product.get("quantity", 0)

        if requested_quantity > available_quantity:
            return JsonResponse({"status": "error", "message": "Low stocks."})

        # Update the order status to Approved
        orders_table.update_item(
            key={"order_id": order["order_id"]},
            update_expression="SET #status = :approved",
            expression_values={":approved": "Approved"},
            expression_names={"#status": "status"}
        )

        # Reduce stock for the product
        products_table.update_item(
            key={"product_id": product_id},
            update_expression="SET quantity = quantity - :requested",
            expression_values={":requested": requested_quantity},
        )

        return redirect('orders')

    def _reject_order(self, order_id):
        """
        Reject an order by updating its status.
        """
        orders_table.update_item(
            key={"order_id": order_id},
            update_expression="SET #status = :rejected",
            expression_values={":rejected": "Rejected"},
            expression_names={"#status": "status"}
        )
        return JsonResponse({"status": "success", "message": "Order rejected."})

class OrderRequest(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/order_request.html'

    def get_context_data(self, **kwargs):
        """
        Fetch products and orders to populate the order request page.
        """
        context = super().get_context_data(**kwargs)

        # Fetch products and pass them to the form
        products = products_table.get_all_items()
        context['products'] = products  # Pass for rendering in the template
        context['form'] = OrderForm(products_table=products_table)

        # Fetch orders placed by the logged-in user
        user_email = self.request.user.email
        user_orders = orders_table.get_all_items()
        context['orders'] = [
            order for order in user_orders if order.get('ordered_by') == user_email
        ]
        return context

    def post(self, request, *args, **kwargs):
        """
        Handle order creation, including `product_id` and `product_name`.
        """
        form = OrderForm(request.POST, products_table=products_table)
        if form.is_valid():
            # Extract product_id and retrieve product details
            product_id = form.cleaned_data.get('product_name')  # product_id is selected
            products = products_table.get_all_items()
            product = next((p for p in products if p['product_id'] == product_id), None)

            if not product:
                return JsonResponse({"status": "error", "message": "Product not found."})

            product_name = product['name']
            quantity = form.cleaned_data['quantity']
            category = form.cleaned_data['category']

            # Add a new order to DynamoDB
            order_id = str(uuid.uuid4())
            order_data = {
                'order_id': order_id,
                'product_id': product_id,
                'product_name': product_name,
                'quantity': quantity,
                'category': category,
                'ordered_by': request.user.email,
                'status': 'Pending',  # Default status
            }
            orders_table.put_item(order_data)

            # Send a notification to SNS
            sns_topic_arn = os.environ['PRODUCTS_SNS_TOPIC_ARN']
            message = (
                f"New order placed by {request.user.email}\n"
                f"Product: {product_name}\n"
                f"Quantity: {quantity}\n"
                f"Category: {category}"
            )
            send_sns_notification(message=message, sns_topic_arn=sns_topic_arn)

            return redirect('order_request')

        # If form is invalid, re-render the page with errors
        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)

class RedirectView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect('dashboard')  
        else:
            return redirect('order_request')  