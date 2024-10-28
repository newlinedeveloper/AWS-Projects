Here’s a Python AWS CDK code that covers the use case of moving data from **S3 to Amazon Redshift**, building a cloud data warehouse with the following functionalities:

1. **AWS Glue Job** to flatten the data.
2. **Amazon Redshift Spectrum** to query the flattened data stored in S3.
3. **Materialized View** in Amazon Redshift to query the data efficiently.

### Flow Overview:
1. **S3 Bucket**: The raw data is uploaded to an S3 bucket.
2. **AWS Glue Job**: Flattens the raw data and writes the transformed data back to another S3 bucket.
3. **Amazon Redshift Spectrum**: Queries the transformed data stored in S3 using an external table.
4. **Materialized View**: Created in Amazon Redshift to improve query performance by caching the results.

### Steps in the CDK Code:
- **S3 Buckets** for raw data and transformed data.
- **AWS Glue Job** to transform and flatten data.
- **Amazon Redshift** with **Redshift Spectrum** to query data in S3.
- **Materialized View** in Redshift to speed up the querying of the flattened data.

### CDK Code

```python
from aws_cdk import (
    core,
    aws_s3 as s3,
    aws_iam as iam,
    aws_glue as glue,
    aws_redshift as redshift,
    aws_ec2 as ec2
)

class S3ToRedshiftDataWarehouseStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create S3 buckets for raw and transformed data
        raw_data_bucket = s3.Bucket(self, "RawDataBucket", removal_policy=core.RemovalPolicy.DESTROY)
        transformed_data_bucket = s3.Bucket(self, "TransformedDataBucket", removal_policy=core.RemovalPolicy.DESTROY)

        # Create an IAM role for AWS Glue with S3 read/write access
        glue_role = iam.Role(self, "GlueJobRole",
                             assumed_by=iam.ServicePrincipal("glue.amazonaws.com"))
        glue_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            resources=[raw_data_bucket.bucket_arn, f"{raw_data_bucket.bucket_arn}/*",
                       transformed_data_bucket.bucket_arn, f"{transformed_data_bucket.bucket_arn}/*"]
        ))

        # Create AWS Glue database to store metadata
        glue_db = glue.CfnDatabase(self, "GlueDatabase", catalog_id=core.Aws.ACCOUNT_ID,
                                   database_input=glue.CfnDatabase.DatabaseInputProperty(
                                       name="my_glue_database"
                                   ))

        # Glue job script location in S3 (for flattening the data)
        glue_script_location = "s3://my-glue-scripts/flatten-script.py"  # This is the script location
        
        # Create Glue Job
        glue_job = glue.CfnJob(self, "GlueJob",
                               name="FlattenDataJob",
                               role=glue_role.role_arn,
                               command=glue.CfnJob.JobCommandProperty(
                                   name="glueetl",
                                   script_location=glue_script_location
                               ),
                               default_arguments={
                                   "--job-language": "python",
                                   "--extra-py-files": "s3://my-libraries/pandas.zip"
                               },
                               glue_version="2.0",
                               max_capacity=10,
                               worker_type="G.1X",
                               number_of_workers=5)

        # Create Redshift cluster with Spectrum enabled
        vpc = ec2.Vpc(self, "RedshiftVpc")
        
        redshift_cluster = redshift.Cluster(self, "RedshiftCluster",
                                            master_user=redshift.Login(master_username="admin"),
                                            vpc=vpc,
                                            removal_policy=core.RemovalPolicy.DESTROY,
                                            default_database_name="dev",
                                            publicly_accessible=True)

        # S3 bucket for Redshift Spectrum
        spectrum_bucket = s3.Bucket(self, "SpectrumBucket", removal_policy=core.RemovalPolicy.DESTROY)

        # IAM Role for Redshift to access Spectrum and S3
        redshift_spectrum_role = iam.Role(self, "RedshiftSpectrumRole",
                                          assumed_by=iam.ServicePrincipal("redshift.amazonaws.com"))
        redshift_spectrum_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:ListBucket"],
            resources=[spectrum_bucket.bucket_arn, f"{spectrum_bucket.bucket_arn}/*"]
        ))

        # Grant Redshift permission to use the role
        redshift_cluster.grant_role(redshift_spectrum_role)

        # Create Redshift Spectrum External Schema (done via SQL after cluster is created)
        external_schema_ddl = f"""
        CREATE EXTERNAL SCHEMA spectrum_schema
        FROM DATA CATALOG
        DATABASE 'my_glue_database'
        IAM_ROLE '{redshift_spectrum_role.role_arn}'
        CREATE EXTERNAL DATABASE IF NOT EXISTS;
        """

        # Athena table query to create external table in Redshift Spectrum
        external_table_ddl = f"""
        CREATE EXTERNAL TABLE spectrum_schema.transformed_table (
            id int,
            name string,
            age int,
            country string
        )
        ROW FORMAT DELIMITED
        FIELDS TERMINATED BY ','
        STORED AS TEXTFILE
        LOCATION 's3://{transformed_data_bucket.bucket_name}/transformed/';
        """

        # Materialized View
        materialized_view_ddl = """
        CREATE MATERIALIZED VIEW mv_transformed_data AS
        SELECT id, name, age, country
        FROM spectrum_schema.transformed_table;
        """

        # Output resources and values for reference
        core.CfnOutput(self, "RawDataBucketName", value=raw_data_bucket.bucket_name)
        core.CfnOutput(self, "TransformedDataBucketName", value=transformed_data_bucket.bucket_name)
        core.CfnOutput(self, "RedshiftClusterEndpoint", value=redshift_cluster.cluster_endpoint.hostname)

app = core.App()
S3ToRedshiftDataWarehouseStack(app, "S3ToRedshiftDataWarehouseStack")
app.synth()
```

### Key Components in CDK Code:

1. **S3 Buckets**:
   - `raw_data_bucket`: Used to upload raw data files.
   - `transformed_data_bucket`: Stores transformed (flattened) data after the Glue job processes it.

2. **IAM Role**:
   - Provides permissions for AWS Glue and Redshift to access S3 buckets.

3. **AWS Glue Job**:
   - The Glue job is responsible for flattening and transforming the data. The Glue job script location is stored in S3 (`glue_script_location`).
   
   - The script processes raw data, flattens it, and writes the transformed data back to the `transformed_data_bucket`.

4. **Redshift Cluster with Spectrum**:
   - Redshift is deployed inside a VPC and is publicly accessible.
   - Redshift Spectrum is enabled to query the transformed data directly from S3.
   - **IAM Role** is created for Redshift to interact with S3 using Spectrum.

5. **Redshift Spectrum External Schema**:
   - A schema is created to allow Redshift to access external tables in the Glue Data Catalog using **Redshift Spectrum**.

6. **Materialized View**:
   - A materialized view is created to optimize query performance by caching the result of the query.

### AWS Glue Job Python Script:

In your S3 bucket (`my-glue-scripts`), create a Python script (`flatten-script.py`) that handles flattening the data:

```python
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

# Initialize Glue context
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Read raw data from S3
raw_data = glueContext.create_dynamic_frame.from_catalog(database="my_glue_database", table_name="raw_table")

# Flatten the data (modify based on actual structure)
flattened_data = raw_data.repartition(1)

# Write flattened data to S3 in CSV format
glueContext.write_dynamic_frame.from_options(
    frame=flattened_data,
    connection_type="s3",
    connection_options={"path": "s3://my-transformed-data-bucket/transformed/"},
    format="csv"
)

job.commit()
```

### Key Concepts:

1. **AWS Glue**:
   - The Glue job flattens the raw data from S3 and stores it in a transformed state back in S3.

2. **Redshift Spectrum**:
   - Spectrum is used to query external tables stored in S3 without loading data into Redshift.
   - This allows querying large datasets in S3 efficiently using standard SQL.

3. **Materialized Views**:
   - Materialized views store the results of a query in a persistent state, improving the performance of repetitive queries by avoiding full scans.

4. **Athena Glue Catalog**:
   - The external table created by Athena (Redshift Spectrum) uses the Glue Catalog as a source of metadata for the S3 data.

### Final Steps:

- Once the CDK stack is deployed, you can manually run SQL commands (from Redshift or using a SQL client) to create the **External Schema**, **External Table**, and **Materialized View**.
- Run
