import boto3
from botocore.exceptions import BotoCoreError, ClientError


def send_sns_notification(message, sns_topic_arn, region_name="us-east-1"):
    """
    Send a notification to an SNS Topic.
    :param message: The message to send.
    :param sns_topic_arn: The ARN of the SNS Topic.
    :param region_name: AWS region name.
    :return: True if the notification was sent successfully, False otherwise.
    """
    try:
        sns_client = boto3.client('sns', region_name=region_name)
        sns_client.publish(TopicArn=sns_topic_arn, Message=message)
        return True
    except (BotoCoreError, ClientError) as e:
        print(f"Error sending SNS notification: {e}")
        return False


def fetch_sqs_messages(sqs_queue_url, region_name="us-east-1"):
    """
    Fetch messages from an SQS Queue along with their ReceiptHandles.
    :param sqs_queue_url: The URL of the SQS Queue.
    :param region_name: AWS region name.
    :return: A list of messages with their body and ReceiptHandle.
    """
    try:
        sqs_client = boto3.client('sqs', region_name=region_name)
        response = sqs_client.receive_message(
            QueueUrl=sqs_queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=1
        )
        messages = []
        if "Messages" in response:
            for msg in response["Messages"]:
                messages.append({
                    "body": msg["Body"],
                    "receipt_handle": msg["ReceiptHandle"]
                })
        return messages
    except (BotoCoreError, ClientError) as e:
        print(f"Error fetching SQS messages: {e}")
        return []


def delete_sqs_message(sqs_queue_url, receipt_handle, region_name="us-east-1"):
    """
    Delete a specific message from an SQS Queue using its ReceiptHandle.
    :param sqs_queue_url: The URL of the SQS Queue.
    :param receipt_handle: The ReceiptHandle of the message to delete.
    :param region_name: AWS region name.
    :return: True if the message was deleted successfully, False otherwise.
    """
    try:
        sqs_client = boto3.client('sqs', region_name=region_name)
        sqs_client.delete_message(
            QueueUrl=sqs_queue_url,
            ReceiptHandle=receipt_handle
        )
        return True
    except (BotoCoreError, ClientError) as e:
        print(f"Error deleting SQS message: {e}")
        return False
