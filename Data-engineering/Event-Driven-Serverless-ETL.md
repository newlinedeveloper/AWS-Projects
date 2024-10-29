Event-Driven Serverless ETL | Redshift, Glue, S3

- create an AWS Glue connection to amazon redshift
- use AWS Glue studio to create an ETL Job
- Query the data through amazon redshift query editor


To create a Python AWS CDK application for **Event-Driven Serverless ETL** using **Lambda**, **Amazon Redshift**, **AWS Glue**, and **S3**, here’s a solution. This ETL pipeline consists of:

1. **AWS Glue** to extract, transform, and load (ETL) data from **S3** into **Amazon Redshift**.
2. **AWS Lambda** to trigger the ETL job when new data is uploaded to S3.
3. **Amazon Redshift** as the data warehouse to store and query the transformed data.

### Solution Overview:
- **S3**: A bucket for storing raw data files.
- **AWS Glue**: An ETL job to transform and load data from S3 to Redshift.
- **Amazon Redshift**: A cluster to store and query the transformed data.
- **Lambda**: A trigger function that starts the Glue ETL job when new files are uploaded to S3.

### Steps:
1. **Create an S3 bucket** for raw data.
2. **Create a Glue connection** to Amazon Redshift.
3. **Create a Glue job** to extract data from S3, transform it, and load it into Redshift.
4. **Trigger Glue job** using a Lambda function on S3 events.
5. **Query the data** through Amazon Redshift Query Editor.

Here’s the Python AWS CDK application:

### Directory Structure:

```bash
.
├── lambda
│   └── trigger_glue.py  # Lambda function that triggers the Glue job
└── app.py               # CDK Python application
```

### app.py (CDK Application)

```python
from aws_cdk import (
    core,
    aws_s3 as s3,
    aws_glue as glue,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3_notifications as s3_notifications,
    aws_redshift as redshift,
    aws_events as events,
    aws_events_targets as targets,
)

class EventDrivenETL(core.Stack):
    
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create an S3 bucket for raw data
        raw_data_bucket = s3.Bucket(self, "RawDataBucket",
                                    versioned=True,
                                    removal_policy=core.RemovalPolicy.DESTROY)

        # Create Amazon Redshift Cluster
        redshift_cluster = redshift.Cluster(self, "RedshiftCluster",
                                            master_user=redshift.Login(master_username="admin"),
                                            vpc=core.Vpc(self, "RedshiftVpc"),
                                            default_database_name="etl_db")

        # Glue connection to Redshift
        glue_connection = glue.CfnConnection(self, "RedshiftGlueConnection",
                                             catalog_id=self.account,
                                             connection_input={
                                                 "Name": "redshift_connection",
                                                 "ConnectionType": "JDBC",
                                                 "ConnectionProperties": {
                                                     "JDBC_CONNECTION_URL": redshift_cluster.cluster_endpoint.socket_address,
                                                     "USERNAME": "admin",
                                                     "PASSWORD": redshift_cluster.secret.secret_value.to_string()
                                                 }
                                             })

        # Create Glue Database
        glue_database = glue.Database(self, "GlueETLDatabase",
                                      database_name="etl_db")

        # Create Glue Role
        glue_role = iam.Role(self, "GlueServiceRole",
                             assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
                             managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")])

        # Create Glue ETL Job
        glue_job = glue.CfnJob(self, "ETLGlueJob",
                               name="s3_to_redshift_etl",
                               role=glue_role.role_arn,
                               command={
                                   "name": "glueetl",
                                   "scriptLocation": "s3://path-to-glue-script/glue_etl_script.py",
                                   "pythonVersion": "3"
                               },
                               connections={"connections": ["redshift_connection"]},
                               default_arguments={
                                   "--enable-continuous-cloudwatch-log": "true",
                                   "--extra-py-files": "s3://path-to-extra-py-files/",
                                   "--TempDir": f"s3://{raw_data_bucket.bucket_name}/temp/",
                                   "--job-bookmark-option": "job-bookmark-enable"
                               },
                               glue_version="2.0",
                               max_capacity=2)

        # Create Lambda Function to trigger Glue Job
        trigger_lambda = _lambda.Function(self, "TriggerGlueJobLambda",
                                          runtime=_lambda.Runtime.PYTHON_3_8,
                                          handler="trigger_glue.handler",
                                          code=_lambda.Code.from_asset("lambda"),
                                          environment={
                                              "GLUE_JOB_NAME": glue_job.name
                                          })

        # Grant Lambda permissions to start Glue job
        trigger_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["glue:StartJobRun"],
            resources=[glue_job.attr_name]
        ))

        # Add S3 event notification to trigger Lambda when a new CSV file is uploaded
        notification = s3_notifications.LambdaDestination(trigger_lambda)
        raw_data_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, notification, s3.NotificationKeyFilter(suffix=".csv"))

        # Output bucket and Redshift details
        core.CfnOutput(self, "RawDataBucketName", value=raw_data_bucket.bucket_name)
        core.CfnOutput(self, "RedshiftClusterEndpoint", value=redshift_cluster.cluster_endpoint.hostname)
        core.CfnOutput(self, "RedshiftClusterDatabase", value=redshift_cluster.default_database_name)


app = core.App()
EventDrivenETL(app, "EventDrivenETLStack")
app.synth()
```

### Lambda Function (trigger_glue.py)

```python
import os
import boto3

def handler(event, context):
    glue = boto3.client('glue')
    glue_job_name = os.getenv('GLUE_JOB_NAME')

    response = glue.start_job_run(JobName=glue_job_name)
    print(f"Started Glue Job: {glue_job_name}")
    return response
```

### Glue ETL Script (glue_etl_script.py)

This Glue ETL script will extract the data from the raw S3 bucket, transform it, and load it into Amazon Redshift.

```python
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Load data from S3
datasource = glueContext.create_dynamic_frame.from_catalog(database="etl_db", table_name="s3_raw_data_table")

# Apply transformations (e.g., flatten, clean, etc.)
transformed_data = ApplyMapping.apply(frame=datasource, mappings=[
    ("column1", "string", "column1", "string"),
    ("column2", "int", "column2", "int"),
])

# Write transformed data to Redshift
glueContext.write_dynamic_frame.from_jdbc_conf(
    frame=transformed_data,
    catalog_connection="redshift_connection",
    connection_options={
        "dbtable": "etl_target_table",
        "database": "etl_db"
    },
    redshift_tmp_dir="s3://raw_data_bucket/temp/"
)

job.commit()
```

### Steps Explanation:

1. **Amazon S3**: An S3 bucket stores the raw CSV files. When a file is uploaded, it triggers a Lambda function.
2. **AWS Lambda**: This function starts an AWS Glue job upon receiving an S3 event notification.
3. **AWS Glue**:
   - A Glue job connects to Amazon Redshift via a JDBC connection.
   - The ETL process extracts data from S3, transforms it (e.g., data cleaning or enrichment), and loads it into Redshift.
4. **Amazon Redshift**: The transformed data is stored in a Redshift table, and you can query it via the Redshift Query Editor.
5. **JDBC Connection**: A Glue connection to Amazon Redshift allows the ETL job to load the transformed data into the Redshift database.

### Summary:
- **S3**: Ingests raw data (CSV files).
- **Lambda**: Detects new file uploads and starts the Glue job.
- **Glue**: Transforms and loads data from S3 into Redshift.
- **Amazon Redshift**: Stores and queries the transformed data.

This solution provides an event-driven ETL pipeline where new files in S3 automatically trigger the data processing and loading into Redshift.
