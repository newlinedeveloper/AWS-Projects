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
