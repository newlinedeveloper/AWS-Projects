Daily batch extraction - RDS, Athena, Glue, S3


Here’s a Python AWS CDK code that sets up a **Daily Batch Extraction Service** using **Amazon RDS**, **AWS Glue**, **Amazon S3**, and **Amazon Athena**. The service uses AWS Glue to extract data from RDS using a JDBC connection, processes it with a Spark script, and stores the data in S3. Athena queries can then be run on the extracted data.

### Flow Overview:
1. **Amazon RDS**: A database from which data will be extracted.
2. **AWS Glue**: A Glue job (created using Glue Studio) extracts data from the RDS database, processes it, and saves it in an S3 bucket.
3. **Amazon S3**: Stores the extracted and processed data.
4. **Amazon Athena**: Queries the data stored in S3.

### AWS Components:
1. **RDS**: A relational database storing the data.
2. **Glue JDBC Connection**: Connects Glue to the RDS instance.
3. **Glue Studio**: Used to create a Spark script to process data.
4. **S3**: Stores the extracted data in a data lake.
5. **Athena**: Queries the data stored in S3.

### CDK Code

```python
from aws_cdk import (
    core,
    aws_rds as rds,
    aws_s3 as s3,
    aws_glue as glue,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_athena as athena,
)

class DailyBatchExtractionService(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create VPC for RDS and Glue
        vpc = ec2.Vpc(self, "RDSVpc", max_azs=2)

        # Create S3 bucket to store extracted data
        data_bucket = s3.Bucket(self, "DataBucket", 
                                removal_policy=core.RemovalPolicy.DESTROY)

        # Create RDS instance (PostgreSQL in this case)
        rds_instance = rds.DatabaseInstance(self, "RDSInstance",
                                            engine=rds.DatabaseInstanceEngine.POSTGRES,
                                            vpc=vpc,
                                            allocated_storage=100,
                                            database_name="mydatabase",
                                            credentials=rds.Credentials.from_generated_secret("admin"),
                                            removal_policy=core.RemovalPolicy.DESTROY,
                                            deletion_protection=False)

        # Create IAM Role for Glue
        glue_role = iam.Role(self, "GlueServiceRole",
                             assumed_by=iam.ServicePrincipal("glue.amazonaws.com"))

        # Attach necessary policies for Glue to access S3, RDS, and Athena
        glue_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "s3:*",
                "rds:*",
                "athena:*",
                "glue:*",
                "logs:*"
            ],
            resources=["*"]
        ))

        # Create AWS Glue Database
        glue_db = glue.CfnDatabase(self, "GlueDatabase",
                                   catalog_id=core.Aws.ACCOUNT_ID,
                                   database_input=glue.CfnDatabase.DatabaseInputProperty(
                                       name="extracted_data_db"
                                   ))

        # Create Glue JDBC Connection to RDS
        glue_jdbc_connection = glue.CfnConnection(self, "GlueJDBCConnection",
                                                  catalog_id=core.Aws.ACCOUNT_ID,
                                                  connection_input=glue.CfnConnection.ConnectionInputProperty(
                                                      connection_type="JDBC",
                                                      connection_properties={
                                                          "JDBC_CONNECTION_URL": f"jdbc:postgresql://{rds_instance.db_instance_endpoint_address}:{rds_instance.db_instance_endpoint_port}/{rds_instance.instance_identifier}",
                                                          "USERNAME": "admin",
                                                          "PASSWORD": rds_instance.secret.secret_value.to_string()
                                                      },
                                                      name="rds-jdbc-connection",
                                                      physical_connection_requirements=glue.CfnConnection.PhysicalConnectionRequirementsProperty(
                                                          subnet_id=vpc.private_subnets[0].subnet_id,
                                                          availability_zone=vpc.availability_zones[0],
                                                          security_group_id_list=[rds_instance.connections.security_groups[0].security_group_id]
                                                      )
                                                  ))

        # Glue Job Script in S3 (processing RDS data)
        glue_script_location = "s3://my-glue-scripts/rds-to-s3-spark-script.py"

        # Create Glue Job to extract data from RDS and store it in S3
        glue_job = glue.CfnJob(self, "GlueJob",
                               role=glue_role.role_arn,
                               command=glue.CfnJob.JobCommandProperty(
                                   name="glueetl",
                                   script_location=glue_script_location
                               ),
                               glue_version="2.0",
                               max_capacity=5,
                               worker_type="G.1X",
                               number_of_workers=2,
                               connections=glue.CfnJob.ConnectionsListProperty(
                                   connections=[glue_jdbc_connection.ref]
                               ))

        # Create Athena workgroup
        athena_workgroup = athena.CfnWorkGroup(self, "AthenaWorkGroup",
                                               name="AthenaQueryGroup",
                                               work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                                                   result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                                                       output_location=f"s3://{data_bucket.bucket_name}/athena-results/"
                                                   )
                                               ))

        # Create Athena named query for querying the data in S3
        athena_query = athena.CfnNamedQuery(self, "AthenaQuery",
                                            database="extracted_data_db",
                                            query_string=f"SELECT * FROM {glue_db.database_input.name}",
                                            name="QueryExtractedData",
                                            work_group=athena_workgroup.name)

        # Output S3 bucket and RDS endpoint details
        core.CfnOutput(self, "DataBucketName", value=data_bucket.bucket_name)
        core.CfnOutput(self, "RDSEndpoint", value=rds_instance.db_instance_endpoint_address)
        core.CfnOutput(self, "AthenaWorkgroup", value=athena_workgroup.name)

app = core.App()
DailyBatchExtractionService(app, "DailyBatchExtractionService")
app.synth()
```

### Key Components in CDK Code

1. **VPC**: 
   - The VPC is created to host the RDS instance and Glue connections.
   
2. **S3 Bucket**: 
   - A bucket is created to store the extracted data after the Glue job processes it.

3. **RDS**:
   - An RDS instance is created (PostgreSQL in this example) to store data that will be extracted.

4. **AWS Glue JDBC Connection**:
   - A JDBC connection is created to connect Glue to the RDS instance.

5. **Glue Job**:
   - A Glue job script is specified (stored in S3) that performs data extraction from the RDS instance and stores the processed data in the S3 bucket.
   - The script is expected to be written using Glue Studio.

6. **Athena**:
   - Athena is used to query the processed data stored in S3.
   - A workgroup is created for Athena queries, and an example query is defined using the Glue database created earlier.

### Glue Job Script (`rds-to-s3-spark-script.py`)

Here is a simple Glue job script that connects to RDS via JDBC, extracts the data, and stores it in the S3 bucket:

```python
import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from awsglue.transforms import *

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Parameters
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'rds_jdbc_url', 'username', 'password', 's3_output_path'])
jdbc_url = args['rds_jdbc_url']
username = args['username']
password = args['password']
s3_output_path = args['s3_output_path']

# Read from RDS (PostgreSQL) table
df = spark.read.format("jdbc").option("url", jdbc_url) \
    .option("dbtable", "public.my_table") \
    .option("user", username) \
    .option("password", password) \
    .load()

# Convert Spark DataFrame to Glue DynamicFrame
dynamic_frame = DynamicFrame.fromDF(df, glueContext, "dynamic_frame")

# Write the data to S3 in parquet format
s3_sink = glueContext.getSink(path=s3_output_path, connection_type="s3", format="parquet")
s3_sink.writeFrame(dynamic_frame)

job.commit()
```

### Athena Query Example

In Athena, after the data is written to S3, you can query the data using SQL. Example:

```sql
SELECT * FROM mydatabase.my_table;
```

This SQL query will pull data from the files stored in S3, allowing users to run analytical queries on the processed data.

---

### Explanation of Components:

1. **S3**: 
   - The S3 bucket acts as the destination where extracted and processed data from RDS is stored.

2. **RDS**: 
   - Amazon RDS is used as the relational database where the original data is stored.

3. **AWS Glue**: 
   - AWS Glue provides an ETL service. In this case, it is used to extract the data from RDS, process it with a Spark script (run in Glue Studio), and store the processed data in the S3 bucket.

4. **Athena**: 
   - Athena is used to run

 SQL queries on the data stored in S3 without needing a database server, offering an efficient way to analyze the extracted data.

This CDK stack can be deployed in your AWS environment to implement the daily batch extraction pipeline.
