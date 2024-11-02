from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3_notifications as s3n,
    aws_events as events,
    aws_events_targets as targets,
    Duration,
    RemovalPolicy
)
from constructs import Construct

class AwsDeCdkStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create the raw bucket
        raw_bucket = s3.Bucket(self, "RawBucket", 
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create the staging bucket
        staging_bucket = s3.Bucket(self, "StagingBucket", 
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        pandas_layer = _lambda.LayerVersion(self, "PandasLayer",
            code=_lambda.Code.from_asset("lambda_layer/pandas_layer.zip")
        )

        pyarrow_layer = _lambda.LayerVersion(self, "PyarrowLayer",
            code=_lambda.Code.from_asset("lambda_layer/pyarrow_layer.zip")
        )

        # Create a Lambda function that will process the CSV and convert to Parquet
        process_csv_lambda = _lambda.Function(self, "ProcessCsvLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="process_csv.handler",
            code=_lambda.Code.from_asset("lambda"),  # Directory, not the file
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                'STAGING_BUCKET_NAME': staging_bucket.bucket_name
            },
            layers=[pandas_layer, pyarrow_layer]
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
