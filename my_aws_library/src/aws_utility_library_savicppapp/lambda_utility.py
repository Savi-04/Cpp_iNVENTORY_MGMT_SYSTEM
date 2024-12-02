import boto3
import json
import os

def trigger_lambda(lambda_name, payload, region_name=None):
    """
    Trigger an AWS Lambda function with the given payload.
    :param lambda_name: Name of the Lambda function.
    :param payload: Dictionary payload to pass to the Lambda.
    :param region_name: AWS region where the Lambda function resides.
    :return: Response from the Lambda invocation.
    """
    try:
        # Use provided region_name or fallback to environment variable
        region = region_name or os.environ.get('AWS_REGION', 'us-east-1')
        lambda_client = boto3.client('lambda', region_name=region)
        response = lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType='RequestResponse',  # Wait for the function to complete
            Payload=json.dumps(payload)
        )
        response_payload = response['Payload'].read().decode('utf-8')
        return json.loads(response_payload)
    except Exception as e:
        return {"status": "error", "message": f"Failed to trigger Lambda: {e}"}
