import boto3
import logging

# Read the list of existing buckets
def list_buckets():
    try:
        s3 = boto3.client('s3')
        response = s3.list_buckets()
        if response:
            for bucket in response['Buckets']:
                print(f'Bucket: {bucket["Name"]}')

    except Exception as e:
        logging.error(e)
        return False
    return True

# Upload a file to S3
def upload_to_s3(file_path, bucket_name, object_name):
    try:
        s3 = boto3.client('s3')
        s3.upload_file(file_path, bucket_name, object_name)
    except Exception as e:
        logging.error(e)
        return False
    return True

# Delete file from S3
def delete_from_s3(bucket, key_name):
    s3 = boto3.client('s3')
    try:
        s3.delete_object(Bucket=bucket, Key=key_name)
    except Exception as e:
        logging.error(e)
        return False
    return True

