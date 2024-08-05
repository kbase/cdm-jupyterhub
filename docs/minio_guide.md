
# MinIO Guide

This guide provides an overview of using MinIO with the `mc` (MinIO Client) tool and a sample Python script for 
interacting with MinIO.

## Prerequisites

1. Establish a tunnel to connect to the MinIO server:

    ```bash
    ssh -f -N -L 9002:ci07:9002 <ac.anl_username>@login1.berkeley.kbase.us 
    ssh -f -N -L 9003:ci07:9003 <ac.anl_username>@login1.berkeley.kbase.us 
    ```

   `<ac.anl_username>`: Your username for SSH access. Contact the KBase System Admin team if you do not have access.

## Using MinIO UI
Open a web browser and navigate to the following URL:

```
http://localhost:9003
```

Please note that UI access requires a MinIO username and password. The access key and secret key will not work for 
UI access. Please contact the KBase System Admin team for the username and password.

## Using MinIO Client (`mc`)

### Installation

Download and install the MinIO Client (`mc`) from the [MinIO official website](https://min.io/download?license=agpl&platform=macos).

### Configuration

1. Add MinIO server to the `mc` configuration:

    ```bash
    mc alias set cdm-minio http://localhost:9002
    ```
    It will prompt you to enter the access key and secret key. Please contact the KBase System Admin team for the 
    access key and secret key.

2. Verify the configuration and connection:

    ```bash
    mc ls cdm-minio
    ```
   

### Basic Commands

* List all buckets:

    ```bash
    mc ls cdm-minio
    ```

* Upload a file:

    ```bash
    mc cp <local_file_path> cdm-minio/<bucket_name>
    ```
* Upload a directory:

    ```bash
    mc cp --recursive <local_directory_path> cdm-minio/<bucket_name>
    ```
    
* Download a file:

    ```bash
    mc cp cdm-minio/<bucket_name>/<file_name> <local_file_path>
    ```
  
* Download a directory:

    ```bash
    mc cp --recursive cdm-minio/<bucket_name> <local_directory_path>
    ```
  
## Using MinIO with Python

The following Python script demonstrates how to interact with MinIO using the `boto3` library.

Ensure you have the `boto3` library installed:

```bash
pip install boto3
```

### Sample Python Script
```python
from pathlib import Path

import boto3

# MinIO configuration
endpoint_url = 'http://localhost:9002'
access_key = 'MINIOACCESSKEY'
secret_key = 'MINIOSECRETKEY'

# Create S3 client
s3 = boto3.client('s3', 
                  endpoint_url=endpoint_url, 
                  aws_access_key_id=access_key, 
                  aws_secret_access_key=secret_key)

def upload_to_s3(
        upload_file: Path,
        s3_key: str,
        s3: boto3.client,
        bucket: str):
    """
    Upload the specified file to the specified S3 bucket.

    :param upload_file: path of the file to upload
    :param s3_key: key of the file in the S3 bucket
    :param s3: boto3 client for S3
    :param bucket: name of the S3 bucket
    """
    try:
        # Skip uploading if the file already exists in the bucket
        s3.head_object(Bucket=bucket, Key=s3_key)
    except s3.exceptions.ClientError:
        s3.upload_file(str(upload_file), bucket, s3_key)
```

## Additional Resources
* [MinIO Client (mc) Official Guide](https://min.io/docs/minio/linux/reference/minio-mc.html?ref=docs)
* [MinIO Python SDK](https://docs.min.io/docs/python-client-quickstart-guide.html)
* [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#using-boto3)