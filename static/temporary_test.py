from aws_library import S3Manager

s3_manager = S3Manager(bucket_name='inventory-images')
image_url = s3_manager.upload_file(file_path='local_path/image.jpg', object_name='products/image.jpg')
print(f"Image uploaded successfully: {image_url}")