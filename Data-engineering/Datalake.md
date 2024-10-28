## Datalake

To implement the scenario where an S3 bucket (`raw-bucket`) triggers a Lambda function upon CSV file upload, processes the file to convert it into Parquet format, and stores the processed file in another S3 bucket (`staging-bucket`), you can follow these steps using AWS CDK with Python.

### **Steps:**

1. Create two S3 buckets (`raw-bucket` and `staging-bucket`).
2. Create a Lambda function that gets triggered when a file is uploaded to the `raw-bucket`.
3. The Lambda function processes the CSV file and converts it into Parquet format.
4. Store the Parquet file in the `staging-bucket`.

Below is the AWS CDK Python code to achieve this:

### **1. Install Required Packages**
Make sure to install the necessary CDK libraries before proceeding:
```bash
pip install aws-cdk-lib constructs
```

### **2. AWS CDK Python Code**

```python
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3_notifications as s3n,
    aws_events as events,
    aws_events_targets as targets,
    Duration
)
from constructs import Construct

class S3ToLambdaToParquetStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create the raw bucket
        raw_bucket = s3.Bucket(self, "RawBucket", 
            versioned=True,
            removal_policy=s3.RemovalPolicy.DESTROY
        )

        # Create the staging bucket
        staging_bucket = s3.Bucket(self, "StagingBucket", 
            versioned=True,
            removal_policy=s3.RemovalPolicy.DESTROY
        )

        # Create a Lambda function that will process the CSV and convert to Parquet
        process_csv_lambda = _lambda.Function(self, "ProcessCsvLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="process_csv.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                'STAGING_BUCKET_NAME': staging_bucket.bucket_name
            }
        )

        # Grant the Lambda function read/write permissions on the S3 buckets
        raw_bucket.grant_read(process_csv_lambda)
        staging_bucket.grant_write(process_csv_lambda)

        # Add S3 bucket notification to trigger the Lambda function on CSV file upload
        raw_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(process_csv_lambda),
            s3.NotificationKeyFilter(suffix='.csv')  # Only trigger for CSV files
        )

        # Output the bucket names
        self.output_bucket_names(raw_bucket, staging_bucket)

    def output_bucket_names(self, raw_bucket: s3.Bucket, staging_bucket: s3.Bucket) -> None:
        from aws_cdk import CfnOutput

        # Output Raw Bucket Name
        CfnOutput(self, "RawBucketName", value=raw_bucket.bucket_name)

        # Output Staging Bucket Name
        CfnOutput(self, "StagingBucketName", value=staging_bucket.bucket_name)

```

### **3. Lambda Code (Python) - `lambda/process_csv.py`**

This Lambda function gets triggered when a CSV file is uploaded, processes it, converts the CSV file to Parquet, and uploads it to the staging bucket.

```python
import os
import boto3
import pandas as pd
from pyarrow import csv, parquet

s3_client = boto3.client('s3')
staging_bucket = os.environ['STAGING_BUCKET_NAME']

def handler(event, context):
    for record in event['Records']:
        raw_bucket = record['s3']['bucket']['name']
        csv_file_key = record['s3']['object']['key']

        # Download CSV file from raw bucket
        local_csv_file = '/tmp/' + csv_file_key.split('/')[-1]
        s3_client.download_file(raw_bucket, csv_file_key, local_csv_file)

        # Convert CSV to Parquet
        parquet_file_key = csv_file_key.replace('.csv', '.parquet')
        local_parquet_file = '/tmp/' + parquet_file_key.split('/')[-1]
        
        # Use Pandas or PyArrow for conversion
        csv_data = pd.read_csv(local_csv_file)
        table = csv_data.to_parquet(local_parquet_file)

        # Upload Parquet file to the staging bucket
        s3_client.upload_file(local_parquet_file, staging_bucket, parquet_file_key)

        print(f"Processed {csv_file_key} and uploaded {parquet_file_key} to {staging_bucket}")

```

### **4. Deploy the CDK Stack**

Make sure the Lambda function dependencies (like `pandas` and `pyarrow`) are included in a Lambda layer or bundled with the function if they are too large. You can do this using Docker or AWS Lambda Layers.

1. **Initialize CDK Project**: If you haven't already initialized your CDK project, run:
   ```bash
   cdk init app --language python
   ```

2. **Deploy the Stack**:
   ```bash
   cdk deploy
   ```

### **Summary of Components**

1. **Buckets**:
   - `raw-bucket`: Receives CSV files.
   - `staging-bucket`: Stores the processed Parquet files.

2. **Lambda Function**:
   - This function reads the CSV file from the `raw-bucket`, converts it into Parquet, and writes it to the `staging-bucket`.

3. **S3 Event Notification**:
   - Configured on `raw-bucket` to trigger the Lambda function when a new CSV file is uploaded.

This setup should allow you to automatically process CSV files and store the result in Parquet format in the staging bucket.
