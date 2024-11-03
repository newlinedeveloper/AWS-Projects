Securing the Data Lake | Lake Formation, Athena, Glue

To secure a data lake using AWS Lake Formation, Athena, and Glue with the following features:
1. **Create an AWS Glue Crawler to ingest data**.
2. **Create restrictions for IAM users with Lake Formation**.
3. **Test restrictions by querying as IAM users**.

Here's how you can achieve this using AWS CDK (Python):

### Steps Overview:
1. **Create S3 Buckets**: For raw and transformed data.
2. **Glue Crawler**: Create a Glue Crawler to crawl the data in the raw bucket.
3. **Lake Formation Setup**: Use Lake Formation to manage access control for the Glue data catalog and S3 data.
4. **IAM Role and User Restrictions**: Define roles and policies for restricted access via Lake Formation.
5. **Athena Workgroup**: Set up an Athena workgroup for querying.

### CDK Code

First, install the necessary CDK dependencies:

```bash
pip install aws-cdk-lib aws-cdk.aws-glue aws-cdk.aws-s3 aws-cdk.aws-iam aws-cdk.aws-athena aws-cdk.aws-lakeformation
```

### CDK Stack: `SecureDataLakeStack`

```python
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_glue as glue,
    aws_iam as iam,
    aws_lakeformation as lakeformation,
    aws_athena as athena,
    CfnOutput,
    RemovalPolicy,
    Duration,
)
from constructs import Construct

class SecureDataLakeStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create the S3 Bucket for raw data
        raw_bucket = s3.Bucket(self, "RawDataBucket", 
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Create the S3 Bucket for transformed data
        transformed_bucket = s3.Bucket(self, "TransformedDataBucket", 
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create a Glue Database
        glue_database = glue.CfnDatabase(self, "GlueDatabase",
                                         catalog_id=self.account,
                                         database_input={
                                             "name": "data_lake_db"
                                         })

        # Create a Glue Crawler to ingest data from raw S3 bucket
        glue_crawler_role = iam.Role(self, "GlueCrawlerRole",
                                     assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
                                     managed_policies=[
                                         iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")
                                     ])

        raw_bucket.grant_read(glue_crawler_role)

        glue_crawler = glue.CfnCrawler(self, "GlueCrawler",
                                       role=glue_crawler_role.role_arn,
                                       database_name=glue_database.ref,
                                       targets={
                                           "s3Targets": [{"path": raw_bucket.bucket_arn}]
                                       },
                                       table_prefix="raw_data_")

        # Create Lake Formation Permissions for IAM users
        lake_admin_role = lakeformation.CfnPermissions(self, "LakeFormationAdminRole",
                                                       data_lake_principal={
                                                           "dataLakePrincipalIdentifier": glue_crawler_role.role_arn
                                                       },
                                                       resource={
                                                           "catalog": {}
                                                       },
                                                       permissions=["ALL"])

        # Create IAM User for restricted access
        restricted_user = iam.User(self, "RestrictedIAMUser")

        # Lake Formation permissions for restricted IAM user
        restricted_user_role = lakeformation.CfnPermissions(self, "RestrictedUserPermissions",
                                                            data_lake_principal={
                                                                "dataLakePrincipalIdentifier": restricted_user.user_arn
                                                            },
                                                            resource={
                                                                "database": {
                                                                    "catalogId": self.account,
                                                                    "name": glue_database.ref
                                                                }
                                                            },
                                                            permissions=["SELECT"])

        # Create an Athena Workgroup
        athena_workgroup = athena.CfnWorkGroup(self, "AthenaWorkGroup",
                                               name="DataLakeWorkGroup",
                                               work_group_configuration={
                                                   "resultConfiguration": {
                                                       "outputLocation": transformed_bucket.s3_url_for_object()
                                                   }
                                               })

        # Athena query output location
        CfnOutput(self, "AthenaQueryOutputLocation", value=transformed_bucket.bucket_name)

        # Outputs
        CfnOutput(self, "RawBucketName", value=raw_bucket.bucket_name)
        CfnOutput(self, "GlueDatabaseName", value=glue_database.ref)
        CfnOutput(self, "RestrictedIAMUser", value=restricted_user.user_name)
        CfnOutput(self, "GlueCrawlerName", value=glue_crawler.ref)

```

### Explanation:

1. **S3 Buckets**:
   - `raw_bucket`: Stores raw data.
   - `transformed_bucket`: Stores data after processing or querying via Athena.

2. **Glue Crawler**:
   - A Glue Crawler is created with a role (`glue_crawler_role`) that has read access to the raw S3 bucket. It ingests data into a Glue database (`data_lake_db`).

3. **Lake Formation Setup**:
   - Lake Formation permissions are created to manage access to the Glue catalog and S3 data. 
   - A **Lake Formation Admin** role is defined to allow the Glue Crawler to manage data in Lake Formation.
   - A **restricted IAM user** is created, who has SELECT permissions on the Glue database via Lake Formation (`restricted_user_role`).

4. **IAM Policies**:
   - The **restricted IAM user** has limited access to the Glue database through Lake Formation, allowing SELECT queries only.

5. **Athena Workgroup**:
   - The Athena workgroup is created to allow querying of data stored in the data lake. The results are stored in the `transformed_bucket`.

### Testing the Restrictions:

1. **Run the Glue Crawler** to crawl the data in the `raw_bucket` and ingest it into the Glue database.
   ```bash
   aws glue start-crawler --name <crawler-name>
   ```

2. **Login as the restricted IAM user** and attempt to query the data in the Glue database using Athena:
   - The restricted user should only be able to run SELECT queries on the Glue database through Athena because of the restricted permissions.

3. **Test Queries**:
   Run a query in Athena using the restricted IAM user:
   ```sql
   SELECT * FROM data_lake_db.raw_data_table LIMIT 10;
   ```

### Conclusion:
- This CDK code sets up a basic AWS Data Lake architecture using Glue, Athena, and Lake Formation.
- It ensures secure access to the data with Lake Formation by restricting access for certain IAM users and providing read permissions only.
