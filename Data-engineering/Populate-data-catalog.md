Populating the Data Catalog | Lambda, Athena, Glue, S3

- create a database in the aws glue data catalog
- create and run aws glue crawler in the data catalog
- use amazon athena to query data in the table
- rerun the crawler to update the data catalog table

To build a data catalog population solution using **AWS Lambda**, **Amazon Athena**, **AWS Glue**, and **Amazon S3** with AWS CDK, you can follow this pattern. The following AWS services will be used:

1. **S3**: Stores the raw data.
2. **AWS Glue Crawler**: Automatically crawls the S3 bucket to detect the schema and populate the AWS Glue Data Catalog.
3. **AWS Glue Data Catalog**: Catalogs the metadata of the data stored in S3.
4. **Lambda**: Triggers the Glue Crawler and manages other operations.
5. **Athena**: Queries the data stored in S3 via the AWS Glue Data Catalog.
6. **CloudWatch Events (EventBridge)**: Optionally schedule the crawler to update the Glue Data Catalog table periodically.

### Steps:
1. Create an S3 bucket to store the raw data.
2. Create a Glue Database in the Glue Data Catalog.
3. Create and configure a Glue Crawler to crawl the S3 bucket and populate the Glue Data Catalog.
4. Use Amazon Athena to query the data from the cataloged tables.
5. Optionally, rerun the crawler periodically using Lambda or EventBridge.

### Solution Architecture:
- **S3 Bucket**: Stores raw data in CSV or Parquet format.
- **AWS Glue Crawler**: Automatically detects data schemas and updates the Glue Data Catalog.
- **Lambda**: Triggers the Glue Crawler and manages the rerun process.
- **Athena**: Queries data cataloged by Glue.

Here’s the AWS CDK code in Python to implement this solution:

### Directory Structure:

```bash
.
├── lambda
│   └── trigger_crawler.py  # Lambda function to trigger the Glue Crawler
└── app.py                 # CDK Python application
```

### `app.py` (CDK Application)

```python
from aws_cdk import (
    core,
    aws_s3 as s3,
    aws_iam as iam,
    aws_glue as glue,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_athena as athena,
)

class DataCatalogStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create an S3 bucket to store the raw data
        data_bucket = s3.Bucket(self, "DataBucket",
                                versioned=True,
                                removal_policy=core.RemovalPolicy.DESTROY)
        
        # Create AWS Glue Database
        glue_database = glue.Database(self, "GlueDatabase",
                                      database_name="data_catalog_db")

        # Create Glue Crawler Role
        glue_crawler_role = iam.Role(self, "GlueCrawlerRole",
                                     assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
                                     managed_policies=[
                                         iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")
                                     ])

        # Grant Glue Role permission to access S3 bucket
        data_bucket.grant_read(glue_crawler_role)

        # Create Glue Crawler
        glue_crawler = glue.CfnCrawler(self, "GlueCrawler",
                                       role=glue_crawler_role.role_arn,
                                       database_name=glue_database.database_name,
                                       targets={
                                           "s3Targets": [{
                                               "path": data_bucket.bucket_arn
                                           }]
                                       },
                                       table_prefix="catalog_",
                                       recrawl_policy={"recrawlBehavior": "CRAWL_EVERYTHING"},
                                       schema_change_policy={"updateBehavior": "UPDATE_IN_DATABASE", "deleteBehavior": "LOG"})

        # Create Lambda function to trigger Glue Crawler
        trigger_crawler_lambda = _lambda.Function(self, "TriggerCrawlerLambda",
                                                  runtime=_lambda.Runtime.PYTHON_3_8,
                                                  handler="trigger_crawler.handler",
                                                  code=_lambda.Code.from_asset("lambda"),
                                                  environment={
                                                      "CRAWLER_NAME": glue_crawler.ref
                                                  })

        # Grant Lambda permissions to start Glue Crawler
        trigger_crawler_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["glue:StartCrawler"],
            resources=[glue_crawler.attr_arn]
        ))

        # Setup EventBridge Rule to trigger the Lambda function on a schedule
        event_rule = events.Rule(self, "TriggerCrawlerEventRule",
                                 schedule=events.Schedule.rate(core.Duration.days(1)))
        event_rule.add_target(targets.LambdaFunction(trigger_crawler_lambda))

        # Athena Workgroup (optional for Athena queries)
        athena_workgroup = athena.CfnWorkGroup(self, "AthenaWorkgroup",
                                               name="data_catalog_workgroup",
                                               state="ENABLED",
                                               work_group_configuration={
                                                   "resultConfiguration": {
                                                       "outputLocation": f"s3://{data_bucket.bucket_name}/athena-results/"
                                                   }
                                               })

        # Output values for ease of reference
        core.CfnOutput(self, "DataBucket", value=data_bucket.bucket_name)
        core.CfnOutput(self, "GlueCrawlerName", value=glue_crawler.ref)
        core.CfnOutput(self, "AthenaWorkgroup", value=athena_workgroup.name)


app = core.App()
DataCatalogStack(app, "DataCatalogStack")
app.synth()
```

### Lambda Function (`trigger_crawler.py`)

This Lambda function triggers the Glue Crawler when invoked.

```python
import os
import boto3

def handler(event, context):
    glue = boto3.client('glue')
    crawler_name = os.getenv('CRAWLER_NAME')
    
    try:
        response = glue.start_crawler(Name=crawler_name)
        print(f"Started Glue Crawler: {crawler_name}")
        return response
    except Exception as e:
        print(f"Error starting Glue Crawler: {str(e)}")
        raise e
```

### Steps Explanation:

1. **Amazon S3**: An S3 bucket is created to store the raw data. When new files are uploaded, they can be crawled by AWS Glue.
   
2. **AWS Glue Crawler**:
   - A Glue Crawler is created to detect the schema of the files in the S3 bucket and populate the Glue Data Catalog with the metadata.
   - The crawler is scheduled to run daily using **EventBridge** to update the Glue Data Catalog as new files are added to S3.

3. **AWS Glue Data Catalog**:
   - The Glue Crawler creates tables in the Glue Data Catalog that reflect the structure of the data in S3.

4. **Amazon Athena**:
   - Athena is configured with a workgroup to allow querying the data from S3 using SQL.

5. **AWS Lambda**:
   - The Lambda function triggers the Glue Crawler whenever it's invoked. You can also manually trigger the crawler from the AWS Glue console if needed.

6. **CloudWatch Events (EventBridge)**:
   - EventBridge is used to trigger the Lambda function to start the Glue Crawler on a daily schedule, ensuring the Glue Data Catalog is always up-to-date with the latest data.

### Summary:
- **S3**: Stores raw data.
- **AWS Glue Crawler**: Automatically scans the data in S3 and updates the Glue Data Catalog.
- **AWS Glue Data Catalog**: Stores metadata about the S3 data.
- **Athena**: Allows querying the data cataloged by Glue using SQL.
- **Lambda**: Triggers the Glue Crawler, ensuring the Data Catalog is updated when needed.
