import boto3
import json
import base64

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda handler for editing (updating) and deleting items in DynamoDB and S3.
    """
    try:
        # Extract common parameters
        operation = event.get("operation")
        table_name = event.get("table_name")
        bucket_name = event.get("bucket_name")  # Optional for S3 operations

        if not operation or not table_name:
            return {"status": "error", "message": "Missing required parameters: operation or table_name."}

        table = dynamodb.Table(table_name)

        if operation == "update":
            return handle_update(event, table, bucket_name)
        elif operation == "delete":
            return handle_delete(event, table, bucket_name)
        else:
            return {"status": "error", "message": f"Unsupported operation: {operation}"}

    except Exception as e:
        return {"status": "error", "message": f"Lambda handler failed: {str(e)}"}

# Helper function: Update operation
def handle_update(event, table, bucket_name):
    item_id = event.get("item_id")  # Use product_id or order_id
    update_data = event.get("update_data")
    object_key = event.get("object_key")  # For S3
    new_image_file = event.get("new_image_file")  # Base64-encoded image for S3

    if not item_id or not update_data:
        return {"status": "error", "message": "Missing required parameters: item_id or update_data."}

    try:
        # Fetch the existing item
        existing_item = table.get_item(Key={"product_id": item_id}).get("Item")
        if not existing_item:
            return {"status": "error", "message": "Item not found for update operation."}

        # Handle image replacement if applicable
        if new_image_file and bucket_name and object_key:
            # Delete old image
            current_image_url = existing_item.get("image_url")
            if current_image_url:
                old_object_key = current_image_url.split(f"{bucket_name}/")[-1]
                s3_client.delete_object(Bucket=bucket_name, Key=old_object_key)

            # Upload new image
            image_data = base64.b64decode(new_image_file)
            s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=image_data)
            update_data["image_url"] = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"

        # Update item in DynamoDB
        update_expression = "SET " + ", ".join([f"{k} = :{k}" for k in update_data.keys()])
        expression_values = {f":{k}": v for k, v in update_data.items()}

        table.update_item(
            Key={"product_id": item_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )

        return {"status": "success", "message": "Item updated successfully."}

    except Exception as e:
        return {"status": "error", "message": f"Failed to update item: {str(e)}"}

# Helper function: Delete operation
def handle_delete(event, table, bucket_name):
    item_id = event.get("item_id")  # Use product_id or order_id

    if not item_id:
        return {"status": "error", "message": "Missing item_id for delete operation."}

    try:
        # Fetch the item
        item = table.get_item(Key={"product_id": item_id}).get("Item")
        if not item:
            return {"status": "error", "message": "Item not found for delete operation."}

        # Delete image from S3 if applicable
        if bucket_name:
            current_image_url = item.get("image_url")
            if current_image_url:
                object_key = current_image_url.split(f"{bucket_name}/")[-1]
                s3_client.delete_object(Bucket=bucket_name, Key=object_key)

        # Delete item from DynamoDB
        table.delete_item(Key={"product_id": item_id})

        return {"status": "success", "message": "Item and associated image deleted successfully."}

    except Exception as e:
        return {"status": "error", "message": f"Failed to delete item: {str(e)}"}
