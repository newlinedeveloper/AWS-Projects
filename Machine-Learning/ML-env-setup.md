Set Up an ML Environment | AMAZON SAGEMAKER, LAMBDA, S3
- Deploy an AI/ML learning environment
- Familiarise yourself with the sagemaker studio IDE
- Walkthrough a sample ML project

Here's a Python AWS CDK code that sets up an AI/ML learning environment using **Amazon SageMaker**, **Lambda**, and **S3**. The architecture will do the following:

- **Deploy an AI/ML environment** using SageMaker Studio, which is an integrated development environment (IDE) for machine learning.
- Create a **SageMaker Notebook** instance as part of the SageMaker Studio environment to run your ML workflows.
- Use **S3** for storing datasets and model artifacts.
- Configure **Lambda** to automate some tasks related to the ML workflow, such as triggering model training or preprocessing data.

### Architecture:
1. **S3 Bucket** for storing data and model artifacts.
2. **SageMaker Studio** environment to run your ML notebooks.
3. **Lambda Function** to automate specific tasks like data preprocessing or model training.
4. **IAM roles** for giving necessary permissions to SageMaker and Lambda.

### CDK Stack:

```python
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_sagemaker as sagemaker,
    Duration,
    RemovalPolicy
)
from constructs import Construct

class SageMakerMLStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create an S3 bucket for datasets and model artifacts
        s3_bucket = s3.Bucket(self, "MLDataBucket",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Create IAM role for SageMaker Studio
        sagemaker_role = iam.Role(self, "SageMakerExecutionRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSageMakerFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
            ]
        )

        # SageMaker Studio Domain
        sagemaker_domain = sagemaker.CfnDomain(self, "SageMakerStudioDomain",
            auth_mode="IAM",  # Using IAM for authentication
            default_user_settings={
                "executionRole": sagemaker_role.role_arn,
                "securityGroups": []  # Add any security group details if necessary
            },
            domain_name="MLStudioDomain"
        )

        # SageMaker Notebook Instance
        notebook_instance = sagemaker.CfnNotebookInstance(self, "SageMakerNotebook",
            instance_type="ml.t3.medium",
            role_arn=sagemaker_role.role_arn,
            direct_internet_access="Enabled",
            notebook_instance_name="MLNotebookInstance"
        )

        # Lambda function to automate tasks like data preprocessing
        ml_lambda_function = _lambda.Function(self, "MLPreprocessingLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="preprocessing.handler",
            code=_lambda.Code.from_asset("lambda"),  # Directory where lambda code is stored
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                'S3_BUCKET': s3_bucket.bucket_name
            }
        )

        # Grant the Lambda function permissions to read/write from S3 and interact with SageMaker
        s3_bucket.grant_read_write(ml_lambda_function)

        ml_lambda_function.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "sagemaker:CreateTrainingJob",
                "sagemaker:DescribeTrainingJob",
                "sagemaker:StartNotebookInstance",
                "sagemaker:StopNotebookInstance"
            ],
            resources=["*"]
        ))

        # Outputs
        self.add_outputs(s3_bucket, sagemaker_domain, notebook_instance, ml_lambda_function)

    def add_outputs(self, s3_bucket, sagemaker_domain, notebook_instance, ml_lambda_function):
        from aws_cdk import CfnOutput
        CfnOutput(self, "S3BucketName", value=s3_bucket.bucket_name)
        CfnOutput(self, "SageMakerDomainId", value=sagemaker_domain.attr_domain_id)
        CfnOutput(self, "NotebookInstanceName", value=notebook_instance.notebook_instance_name)
        CfnOutput(self, "LambdaFunctionArn", value=ml_lambda_function.function_arn)
```

### Breakdown of the CDK Code:

1. **S3 Bucket**:
   - Used to store datasets and model artifacts.
   - The Lambda function and SageMaker Notebook instance will have read/write access to this bucket.

2. **SageMaker Role**:
   - An IAM role that allows the SageMaker notebook instance to access resources, including S3.
   - This role has full SageMaker and S3 access for flexibility in ML workflows.

3. **SageMaker Studio Domain**:
   - Sets up a **SageMaker Studio** domain where the SageMaker IDE will run.
   - The domain will include users who can access the ML environment using IAM for authentication.

4. **SageMaker Notebook Instance**:
   - The notebook instance allows you to run your Jupyter notebooks for training ML models, experimenting with datasets, and building models.
   - It’s an **on-demand** resource, which can be started or stopped as needed.

5. **Lambda Function**:
   - Automates data preprocessing tasks. For example, you can invoke this Lambda function to clean up datasets before passing them to SageMaker training jobs.
   - The Lambda function has the necessary permissions to create SageMaker training jobs and interact with SageMaker APIs.

6. **Permissions**:
   - The Lambda function is granted access to interact with SageMaker services and also read/write to the S3 bucket.
   - The SageMaker Studio notebook instance has a role that gives it full access to SageMaker and S3.

### Lambda Function Code (optional, stored in `lambda/preprocessing.py`):

```python
import boto3
import os

s3_client = boto3.client('s3')
sagemaker_client = boto3.client('sagemaker')

def handler(event, context):
    # Your data preprocessing logic here
    # For example, this code could download a dataset, clean it, and re-upload it to S3
    bucket = os.environ['S3_BUCKET']
    print(f"Preprocessing dataset from S3 bucket: {bucket}")

    # Simulating some task like dataset cleaning or feature extraction
    # Once preprocessed, you can trigger a SageMaker Training job or other actions

    return {
        'statusCode': 200,
        'body': 'Dataset preprocessed and ready for training'
    }
```

### Features in the CDK Stack:

- **Amazon SageMaker Studio**: A domain and notebook instance are created to provide you with an ML environment where you can develop, train, and evaluate models.
- **S3 Bucket**: Stores datasets and model artifacts.
- **Lambda Function**: Automates tasks like data preprocessing and can trigger further actions like training jobs.
- **IAM Roles**: Permissions are granted for SageMaker and Lambda to access S3 and perform necessary ML tasks.

### Deployment Steps:

1. Save the Lambda function code in a folder called `lambda`.
2. Deploy the CDK stack:

```bash
cdk deploy
```

This will set up an ML environment with the required resources (S3, Lambda, SageMaker Studio) automatically.

### SageMaker Studio Walkthrough:

Once the stack is deployed:
1. You can access SageMaker Studio from the AWS Management Console, under **SageMaker > Studio**.
2. Start the notebook instance, and you can upload a sample dataset to the S3 bucket.
3. Walk through a sample ML project such as training a simple machine learning model (e.g., using scikit-learn or TensorFlow).
