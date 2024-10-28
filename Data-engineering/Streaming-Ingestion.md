Streaming ingestion service - Kinesis Firehose, Lambda, Athena
- Use kinesis Data firehose to ingest data to amazon s3
- Call amazon Athena to query data using python SDK

Here's a Python AWS CDK code to set up a **Streaming Ingestion Service** using **Amazon Kinesis Data Firehose**, **AWS Lambda**, **Amazon S3**, and **Amazon Athena**. This service ingests streaming data using Kinesis Data Firehose, processes it using Lambda, stores the data in an S3 bucket, and allows querying the data using Athena through a Python SDK.

### Components:
1. **Amazon Kinesis Data Firehose**: To stream and ingest data into S3.
2. **AWS Lambda**: To process the streamed data.
3. **Amazon S3**: To store the ingested data.
4. **Amazon Athena**: To query the data stored in S3.

### CDK Code:

```python
from aws_cdk import (
    core,
    aws_kinesisfirehose as firehose,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_logs as logs,
    aws_athena as athena
)

class StreamingIngestionService(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create an S3 bucket to store Firehose data
        data_bucket = s3.Bucket(self, "DataIngestionBucket",
                                removal_policy=core.RemovalPolicy.DESTROY)

        # Create an S3 bucket for Athena query results
        athena_results_bucket = s3.Bucket(self, "AthenaResultsBucket",
                                          removal_policy=core.RemovalPolicy.DESTROY)

        # Create an IAM Role for Lambda function with permissions to write to S3
        lambda_role = iam.Role(self, "LambdaExecutionRole",
                               assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"))
        
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:*", "logs:*"],
            resources=["*"]
        ))

        # Lambda function that will process data (firehose to Lambda integration)
        data_processing_lambda = _lambda.Function(self, "DataProcessingLambda",
                                                  runtime=_lambda.Runtime.PYTHON_3_8,
                                                  handler="lambda_function.handler",
                                                  code=_lambda.Code.from_asset("lambda"),
                                                  role=lambda_role)

        # Create a Kinesis Data Firehose Delivery Stream
        firehose_delivery_stream = firehose.CfnDeliveryStream(self, "FirehoseToS3",
                                                              s3_destination_configuration=firehose.CfnDeliveryStream.S3DestinationConfigurationProperty(
                                                                  bucket_arn=data_bucket.bucket_arn,
                                                                  role_arn=lambda_role.role_arn,
                                                                  prefix="data/",
                                                                  buffering_hints=firehose.CfnDeliveryStream.BufferingHintsProperty(
                                                                      size_in_m_bs=5,
                                                                      interval_in_seconds=300
                                                                  ),
                                                                  compression_format="GZIP"
                                                              ))

        # Grant permissions for Firehose to write to the S3 bucket
        data_bucket.grant_put(firehose_delivery_stream)
        
        # Create an Athena workgroup
        athena_workgroup = athena.CfnWorkGroup(self, "AthenaWorkGroup",
                                               name="StreamingAthenaWorkGroup",
                                               work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                                                   result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                                                       output_location=f"s3://{athena_results_bucket.bucket_name}/"
                                                   )
                                               ))

        # Output S3 bucket name and Athena workgroup details
        core.CfnOutput(self, "DataBucketName", value=data_bucket.bucket_name)
        core.CfnOutput(self, "AthenaWorkgroupName", value=athena_workgroup.name)

app = core.App()
StreamingIngestionService(app, "StreamingIngestionService")
app.synth()
```

### Explanation of the Components:

1. **S3 Buckets**:
   - **DataIngestionBucket**: This S3 bucket is used to store the data ingested by Kinesis Data Firehose.
   - **AthenaResultsBucket**: This S3 bucket stores the query results from Athena.

2. **IAM Role**:
   - The Lambda function is provided with an execution role that gives it permissions to access S3 and write logs.

3. **Lambda Function**:
   - A Lambda function is triggered when data is ingested via Kinesis Data Firehose. The Lambda function can be used to process the data (transform, enrich, filter, etc.) before saving it to the S3 bucket.

4. **Kinesis Data Firehose**:
   - Kinesis Data Firehose is configured to receive streaming data and deliver it to the S3 bucket. The data is stored in the bucket with a GZIP compression format and the buffering hints allow the data to be processed in 5 MB chunks or every 300 seconds (whichever happens first).

5. **Athena Workgroup**:
   - A workgroup is created in Athena for querying the ingested data. The query results will be stored in the AthenaResultsBucket.

---

### Lambda Function Code

Here's an example of a simple **Lambda function** (`lambda_function.py`) that processes the incoming Kinesis Firehose data:

```python
import json

def handler(event, context):
    # Log the event received
    print(f"Received event: {json.dumps(event)}")

    # Example of data transformation (can be customized)
    for record in event['records']:
        payload = record['data']
        # Process the data
        print(f"Processing payload: {payload}")

    return {
        'records': event['records']
    }
```

---

### Querying Data using Athena (with Python SDK)

You can use the **Boto3** Python SDK to query data in Athena. Here’s an example of how to submit a query using the Python SDK:

```python
import boto3

# Athena client
client = boto3.client('athena')

def run_athena_query(query, database, output_bucket):
    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database},
        ResultConfiguration={
            'OutputLocation': f's3://{output_bucket}/results/'
        }
    )
    return response['QueryExecutionId']

def get_query_results(query_execution_id):
    # Fetch query results
    response = client.get_query_results(QueryExecutionId=query_execution_id)
    return response

# Define the SQL query to run
query = "SELECT * FROM my_table LIMIT 10;"

# Run the query
query_execution_id = run_athena_query(query, database='my_database', output_bucket='my-athena-results-bucket')

# Fetch and print the results
results = get_query_results(query_execution_id)
print(results)
```

### CDK Output

Once the stack is deployed, CDK will output the **S3 Bucket Name** (where the Firehose will deliver data) and the **Athena Workgroup Name**.

### Additional Considerations:

1. **Kinesis Data Firehose Buffering**:
   - The buffering hints in the Firehose configuration (5 MB or 300 seconds) ensure that the data is ingested efficiently into the S3 bucket.

2. **Compression**:
   - Data is compressed using GZIP to optimize storage in S3.

3. **Data Transformation**:
   - The Lambda function can be customized to process the data before it is stored in S3. This could include tasks like filtering, formatting, or enriching the data.

4. **Athena**:
   - Athena is used to run SQL queries on the data stored in S3. It can query the raw data in S3 without needing to load it into a separate database.

This CDK stack can be deployed in your AWS environment to implement a streaming ingestion pipeline using Kinesis Firehose, Lambda, and Athena.
