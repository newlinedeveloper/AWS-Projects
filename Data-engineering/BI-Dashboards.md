Business Intelligence Dashboards | QuickSight, Athena, Glue, S3

Here's how you can set up an AWS CDK (Python) stack to build a Business Intelligence (BI) architecture using QuickSight, Athena, Glue, and S3. The stack will:
1. Create an S3 bucket to store data.
2. Use Glue to catalog the data.
3. Use Athena to query the data from S3 and make it accessible for QuickSight.
4. Create a QuickSight dataset that visualizes the Athena query results.
5. Publish a QuickSight dashboard.

### Steps Overview:
1. **S3 Bucket**: Store raw data.
2. **Glue**: Create a Glue database and catalog the data.
3. **Athena**: Query the cataloged data.
4. **QuickSight**: Use the Athena data source for visualization.

### AWS CDK Python Code

First, install the necessary CDK dependencies:

```bash
pip install aws-cdk-lib aws-cdk.aws-s3 aws-cdk.aws-glue aws-cdk.aws-athena aws-cdk.aws-quicksight aws-cdk.aws-iam
```

Then, create your CDK stack as follows:

### CDK Stack: `BusinessIntelligenceStack`

```python
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    aws_glue as glue,
    aws_athena as athena,
    CfnOutput,
    Duration,
    RemovalPolicy
)
from constructs import Construct

class BusinessIntelligenceStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create S3 Bucket to store raw data
        data_bucket = s3.Bucket(self, "DataBucket",
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create a Glue Database
        glue_database = glue.CfnDatabase(self, "GlueDatabase",
                                         catalog_id=self.account,
                                         database_input={
                                             "name": "bi_data_lake"
                                         })

        # Create Glue Table (for Athena queries)
        glue_table = glue.CfnTable(self, "GlueTable",
                                   catalog_id=self.account,
                                   database_name=glue_database.ref,
                                   table_input={
                                       "name": "bi_data_table",
                                       "storageDescriptor": {
                                           "columns": [
                                               {"name": "EmployeeID", "type": "int"},
                                               {"name": "Name", "type": "string"},
                                               {"name": "Department", "type": "string"},
                                               {"name": "Salary", "type": "int"}
                                           ],
                                           "location": f"s3://{data_bucket.bucket_name}/",
                                           "inputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                                           "outputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                                           "serdeInfo": {
                                               "serializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
                                           }
                                       },
                                       "tableType": "EXTERNAL_TABLE"
                                   })

        # Athena WorkGroup
        athena_workgroup = athena.CfnWorkGroup(self, "AthenaWorkGroup",
                                               name="BIWorkGroup",
                                               work_group_configuration={
                                                   "resultConfiguration": {
                                                       "outputLocation": data_bucket.s3_url_for_object()
                                                   }
                                               })

        # IAM Role for QuickSight
        quicksight_role = iam.Role(self, "QuickSightServiceRole",
                                   assumed_by=iam.ServicePrincipal("quicksight.amazonaws.com"),
                                   managed_policies=[
                                       iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess"),
                                       iam.ManagedPolicy.from_aws_managed_policy_name("AWSQuicksightAthenaAccess"),
                                       iam.ManagedPolicy.from_aws_managed_policy_name("AWSGlueConsoleFullAccess")
                                   ])

        # Outputs for future references
        CfnOutput(self, "DataBucket", value=data_bucket.bucket_name)
        CfnOutput(self, "GlueDatabase", value=glue_database.ref)
        CfnOutput(self, "AthenaWorkGroup", value=athena_workgroup.name)
        CfnOutput(self, "QuickSightRoleArn", value=quicksight_role.role_arn)

```

### Explanation:

1. **S3 Bucket**:
   - `data_bucket`: This bucket is created to store raw data which will later be cataloged and queried.

2. **Glue Database and Table**:
   - A Glue database (`bi_data_lake`) is created to store metadata about the raw data. 
   - A Glue table (`bi_data_table`) catalogs the data in the S3 bucket, making it available for querying via Athena.

3. **Athena Workgroup**:
   - The Athena workgroup (`BIWorkGroup`) is configured with an output location (the same S3 bucket) where query results will be stored.

4. **QuickSight Role**:
   - An IAM role (`quicksight_role`) is created to allow QuickSight to access the Glue catalog, Athena, and the S3 bucket. This role assumes permissions to allow QuickSight to interact with these resources.

### Step-by-Step Guide:

#### 1. Deploy the Stack
Run the following commands to deploy the stack:

```bash
cdk bootstrap
cdk deploy
```

#### 2. Glue Crawler (Optional)
You can add a Glue Crawler that regularly scans your S3 bucket and updates the Glue catalog.

#### 3. Setup QuickSight:
1. **Sign into AWS QuickSight**.
2. **Manage QuickSight Permissions**:
   - Use the **IAM Role** output (`QuickSightRoleArn`) to grant QuickSight access to the S3 bucket and Athena.
3. **Create Data Source** in QuickSight:
   - Create a new data source using Athena.
   - Point it to the `bi_data_lake` Glue database and the `bi_data_table`.

4. **Visualize Data**:
   - Create a QuickSight dataset using Athena's query results.
   - Build and publish your dashboard.

#### Example Athena Query for the Data:

Once the Athena workgroup and Glue table are set up, you can query the data with a SQL query like:

```sql
SELECT * FROM bi_data_lake.bi_data_table LIMIT 10;
```

#### Sample Dashboard in QuickSight:

- You can create visualizations based on the Athena query results. For example:
  - A **Bar Chart** to show total salary by department.
  - A **Pie Chart** to show the percentage distribution of employees across departments.

### Conclusion:

This CDK stack sets up the foundation for a business intelligence architecture on AWS. It uses S3 for data storage, Glue for cataloging, Athena for querying, and QuickSight for data visualization. You can extend this further by adding more data to the S3 bucket and refining your QuickSight dashboards to gain deeper insights from the data.
