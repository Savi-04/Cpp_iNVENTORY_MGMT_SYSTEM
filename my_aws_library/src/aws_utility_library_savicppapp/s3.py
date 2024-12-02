import boto3
import os
import uuid
from datetime import datetime
from django.utils.text import slugify

def upload_to_s3(file, bucket_name, object_name_prefix, region_name):
    """
    Upload a file to S3 with a unique name and return its URL.
    :param file: File object to upload.
    :param bucket_name: Name of the S3 bucket.
    :param object_name_prefix: Prefix for the S3 object key
    :param region_name: AWS region for the S3 bucket.
    :return: S3 file URL or None if the upload fails.
    """
    try:
        # Generate a unique object name
        file_name, file_extension = os.path.splitext(file.name)
        unique_name = f"{slugify(file_name)}_{uuid.uuid4().hex}_{int(datetime.now().timestamp())}{file_extension}"
        object_name = f"{object_name_prefix}{unique_name}"

        # Uploading the file to S3
        s3_client = boto3.client('s3', region_name=region_name)
        s3_client.upload_fileobj(file, bucket_name, object_name)

        # Generating the S3 URL
        s3_url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{object_name}"
        return s3_url
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        return None
