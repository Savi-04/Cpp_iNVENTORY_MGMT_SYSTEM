import boto3
from botocore.exceptions import BotoCoreError, ClientError
import os
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

class DynamoDBTable:
    def __init__(self, table_name):
        self.table = dynamodb.Table(table_name)

    def get_all_items(self):
        """Fetching all products/orders from the table."""
        try:
            response = self.table.scan()
            return response.get('Items', [])
        except (BotoCoreError, ClientError) as e:
            print(f"Error fetching all items: {e}")
            return []

    def get_item(self, key):
        """Fetching a single product by its key."""
        try:
            response = self.table.get_item(Key=key)
            return response.get('Item')
        except (BotoCoreError, ClientError) as e:
            print(f"Error fetching item with key {key}: {e}")
            return None

    def put_item(self, item):
        """Add a new product/order to the table."""
        try:
            self.table.put_item(Item=item)
        except (BotoCoreError, ClientError) as e:
            print(f"Error adding item: {e}")

    def update_item(self, key, update_expression, expression_values, expression_names=None):
    
       try:
        # Prepare parameters for update_item
        params = {
            "Key": key,
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": expression_values,
        }
        if expression_names:
            params["ExpressionAttributeNames"] = expression_names

        # Perform the update
        self.table.update_item(**params)
       except (BotoCoreError, ClientError) as e:
        print(f"Error updating item with key {key}: {e}")


    def delete_item(self, key):
        """Delete a product by its key."""
        try:
            self.table.delete_item(Key=key)
        except (BotoCoreError, ClientError) as e:
            print(f"Error deleting item with key {key}: {e}")
