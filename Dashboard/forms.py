from django import forms

class ProductForm(forms.Form):
    product_name = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product name'}),
        label="Product Name"
    )
    stock_quantity = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter stock quantity'}),
        label="Stock Quantity"
    )
    category = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product category'}),
        label="Category"
    )
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label="Product Image"
    )


class OrderForm(forms.Form):
    product_name = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Product Name"
    )
    product_id = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    quantity = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter quantity'}),
        label="Quantity"
    )
    category = forms.CharField(
        required=True,
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter product category'}),
        label="Category"
    )

    def __init__(self, *args, **kwargs):
        products_table = kwargs.pop('products_table', None)  # Pass the products_table dynamically
        super().__init__(*args, **kwargs)

        if products_table:
            products = products_table.get_all_items()
            print("Fetched products for dropdown:", products)  # Debug log

            # Use the correct key ('name' instead of 'product_name')
            product_choices = [
                (product['product_id'], product['name'])  # Match keys in DynamoDB
                for product in products
                if 'product_id' in product and 'name' in product
            ]

            print("Filtered product choices:", product_choices)  # Debug log

            # Set choices for the product_name field
            self.fields['product_name'].choices = product_choices