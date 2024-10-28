Here’s a Python AWS CDK code that sets up a **Document Indexing and Search Service** using **Amazon S3**, **AWS Glue**, and **Amazon OpenSearch Service**. This solution ingests data into OpenSearch using AWS Glue and provides functionality for indexing and searching documents via OpenSearch.

### Flow Overview:
1. **S3 Bucket**: Documents (e.g., text, PDFs, or CSVs) are uploaded to an S3 bucket.
2. **AWS Glue**: A Glue job ingests and processes data from S3 and sends it to Amazon OpenSearch for indexing.
3. **Amazon OpenSearch Service**: It is used for document indexing and search.

### AWS Components:
1. **S3**: To store the raw documents.
2. **Glue Job**: To ingest, process, and send data to OpenSearch.
3. **OpenSearch**: To index and search the documents.

### CDK Code

```python
from aws_cdk import (
    core,
    aws_s3 as s3,
    aws_glue as glue,
    aws_iam as iam,
    aws_opensearchservice as opensearch,
    aws_ec2 as ec2
)

class DocumentIndexingAndSearchService(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create S3 Bucket for document storage
        document_bucket = s3.Bucket(self, "DocumentBucket", 
                                    removal_policy=core.RemovalPolicy.DESTROY)

        # Create VPC for OpenSearch
        vpc = ec2.Vpc(self, "OpenSearchVpc", max_azs=2)

        # Create OpenSearch Domain (Amazon OpenSearch Service)
        opensearch_domain = opensearch.Domain(self, "OpenSearchDomain",
                                              version=opensearch.EngineVersion.OPENSEARCH_1_0,
                                              vpc=vpc,
                                              vpc_subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)],
                                              capacity={
                                                  "master_nodes": 2,
                                                  "master_node_instance_type": "t3.medium.search",
                                                  "data_nodes": 2,
                                                  "data_node_instance_type": "t3.medium.search"
                                              },
                                              fine_grained_access_control={
                                                  "master_user_name": "admin"
                                              },
                                              enforce_https=True,
                                              node_to_node_encryption=True,
                                              encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True),
                                              removal_policy=core.RemovalPolicy.DESTROY)

        # Create IAM Role for AWS Glue Job
        glue_role = iam.Role(self, "GlueServiceRole",
                             assumed_by=iam.ServicePrincipal("glue.amazonaws.com"))

        glue_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "es:ESHttpPut",
                "es:ESHttpPost",
                "es:ESHttpGet"
            ],
            resources=[
                document_bucket.bucket_arn,
                f"{document_bucket.bucket_arn}/*",
                f"{opensearch_domain.domain_arn}/*"
            ]
        ))

        # Create AWS Glue Database
        glue_db = glue.CfnDatabase(self, "GlueDatabase", catalog_id=core.Aws.ACCOUNT_ID,
                                   database_input=glue.CfnDatabase.DatabaseInputProperty(
                                       name="documents_db"
                                   ))

        # Glue job script location in S3 (for data ingestion into OpenSearch)
        glue_script_location = "s3://my-glue-scripts/opensearch-ingestion-script.py"

        # Create Glue Job to process data and ingest into OpenSearch
        glue_job = glue.CfnJob(self, "GlueJob",
                               role=glue_role.role_arn,
                               command=glue.CfnJob.JobCommandProperty(
                                   name="glueetl",
                                   script_location=glue_script_location
                               ),
                               glue_version="2.0",
                               max_capacity=10,
                               worker_type="G.1X",
                               number_of_workers=2)

        # Output the S3 bucket name and OpenSearch endpoint
        core.CfnOutput(self, "DocumentBucketName", value=document_bucket.bucket_name)
        core.CfnOutput(self, "OpenSearchDomainEndpoint", value=opensearch_domain.domain_endpoint)

app = core.App()
DocumentIndexingAndSearchService(app, "DocumentIndexingAndSearchService")
app.synth()
```

### Key Components in CDK Code

1. **S3 Bucket**:
   - A bucket is created to store the raw documents.
   
2. **Amazon OpenSearch Service**:
   - An OpenSearch domain is created within a VPC. This domain will be used for indexing and searching documents.
   - Security is enforced with HTTPS, encryption-at-rest, and node-to-node encryption.

3. **AWS Glue**:
   - The Glue job ingests data from the S3 bucket, processes it, and sends the data to OpenSearch.
   - The Glue job script that performs the ingestion and transformation should be uploaded to an S3 bucket (the `glue_script_location` in this code is a placeholder).

4. **IAM Role**:
   - The Glue job is given permissions to interact with S3 and OpenSearch.

5. **Outputs**:
   - Outputs the S3 bucket name and OpenSearch domain endpoint, which can be used to upload documents and perform search operations.

---

### AWS Glue Job Script (`opensearch-ingestion-script.py`)

Below is a sample Glue job script (`opensearch-ingestion-script.py`) to ingest data from S3 into OpenSearch:

```python
import boto3
import json
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
import requests

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Fetch arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 's3_bucket', 'opensearch_endpoint'])

s3 = boto3.client('s3')
bucket_name = args['s3_bucket']
opensearch_endpoint = args['opensearch_endpoint']

# Read data from S3
raw_data = glueContext.create_dynamic_frame.from_catalog(database="documents_db", table_name="documents_table")

# Flatten and convert data to JSON (for indexing)
json_data = raw_data.toDF().toJSON().map(lambda j: json.loads(j)).collect()

# Send data to OpenSearch for indexing
headers = {'Content-Type': 'application/json'}
for record in json_data:
    doc_id = record['id']  # Assuming each document has an 'id' field
    url = f"{opensearch_endpoint}/documents/_doc/{doc_id}"
    requests.put(url, headers=headers, data=json.dumps(record))

job.commit()
```

---

### Explanation of Components:

1. **S3**: 
   - The S3 bucket serves as the data lake where raw documents are uploaded.

2. **OpenSearch**: 
   - OpenSearch provides a scalable search engine for indexing and searching documents. The documents are indexed by Glue, and users can query them using OpenSearch APIs.

3. **Glue Job**:
   - The AWS Glue job reads the documents from S3, processes them (e.g., flattens data, converts to JSON), and sends them to OpenSearch for indexing.
   
4. **VPC**:
   - The OpenSearch service is placed in a VPC for security, and the Glue job interacts with it via HTTPS.

---

### Final Steps:

1. **Deploy the CDK Stack**: Deploy the CDK stack to provision the S3 bucket, Glue job, and OpenSearch domain.
   
2. **Upload Documents to S3**: Users upload documents to the S3 bucket. This could be triggered by S3 events (optional) to run the Glue job automatically.

3. **Run Glue Job**: Manually or automatically trigger the Glue job to process and index the documents into OpenSearch.

4. **Search via OpenSearch**: Once documents are indexed in OpenSearch, you can query them using OpenSearch APIs.

5. **Monitor the System**: Use Amazon CloudWatch for logging and monitoring the Glue job and OpenSearch service.

--- 

This solution provides a scalable and serverless architecture for document indexing and search using AWS-managed services.
