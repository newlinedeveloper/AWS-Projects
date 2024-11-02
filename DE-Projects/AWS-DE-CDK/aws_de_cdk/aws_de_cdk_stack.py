from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3_notifications as s3n,
    aws_events as events,
    aws_events_targets as targets,
    aws_athena as athena,
    aws_glue as glue,
    Duration,
    RemovalPolicy,
    CfnOutput
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

        pandas_layer = _lambda.LayerVersion.from_layer_version_arn(self, "PandasLayer",
            layer_version_arn="arn:aws:lambda:us-east-2:336392948345:layer:AWSSDKPandas-Python39:25"
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
            layers=[pandas_layer]
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

        # IAM policy for Lambda to access Athena and Glue
        process_csv_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "glue:*",
                "athena:*",
                "s3:*"
            ],
            resources=["*"]
        ))

        # Athena WorkGroup
        athena_workgroup = athena.CfnWorkGroup(self, "AthenaWorkGroup",
                                               name="csv-to-parquet-workgroup",
                                               work_group_configuration={
                                                   "resultConfiguration": {
                                                       "outputLocation": f"s3://{staging_bucket.bucket_name}/athena-results/"
                                                   }
                                               })

        # Glue Database
        glue_db = glue.CfnDatabase(self, "GlueDatabase",
                                   catalog_id=self.account,
                                   database_input={
                                       "name": "staging_data_db"
                                   })

        # Glue Table for the Parquet files in the staging bucket
        glue_table = glue.CfnTable(self, "GlueTable",
            catalog_id=self.account,
            database_name="staging_data_db",
            table_input={
                "name": "staging_data_table",
                "storageDescriptor": {
                    "columns": [
                        {"name": "Year", "type": "int"},
                        {"name": "Industry_aggregation_NZSIOC", "type": "string"},
                        {"name": "Industry_code_NZSIOC", "type": "string"},
                        {"name": "Industry_name_NZSIOC", "type": "string"},
                        {"name": "Units", "type": "string"},
                        {"name": "Variable_code", "type": "string"},
                        {"name": "Variable_name", "type": "string"},
                        {"name": "Variable_category", "type": "string"},
                        {"name": "Value", "type": "string"},
                        {"name": "Industry_code_ANZSIC06", "type": "string"}
                    ],
                    "location": f"s3://{staging_bucket.bucket_name}/",
                    "inputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    "outputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    "serdeInfo": {
                        "serializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
                    }
                },
                "tableType": "EXTERNAL_TABLE"
            }
        )

        # Ensure Glue Table is created after the Glue Database
        glue_table.add_dependency(glue_db)


        # Outputs
        CfnOutput(self, "RawBucketName", value=raw_bucket.bucket_name)
        CfnOutput(self, "StagingBucketName", value=staging_bucket.bucket_name)
        CfnOutput(self, "LambdaFunctionArn", value=process_csv_lambda.function_arn)
        CfnOutput(self, "AthenaWorkGroupName", value=athena_workgroup.name)

    
