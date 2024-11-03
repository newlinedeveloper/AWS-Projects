Image and Video Analysis | AMAZON REKOGNITION, LAMBDA, S3

- use Amazon Rekognition to detect objects (labels) in an image
- Configure a lambda function to be invoked by an S3 event

Below is a Python AWS CDK code for an architecture that integrates **Amazon Rekognition**, **Lambda**, and **S3** to detect objects in an image. The architecture will do the following:

- An S3 bucket will store the images.
- A Lambda function will be triggered when a new image is uploaded to the S3 bucket.
- The Lambda function will use **Amazon Rekognition** to detect objects (labels) in the image and log the detected labels.

### Steps:
1. Create an S3 bucket to store images.
2. Set up an S3 event notification to trigger a Lambda function when a new image is uploaded.
3. Inside the Lambda function, invoke Amazon Rekognition to detect objects (labels) in the uploaded image.

### CDK Code:

```python
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3_notifications as s3n,
    aws_lambda_event_sources as event_sources,
    aws_rekognition as rekognition,
    Duration,
    RemovalPolicy
)
from constructs import Construct
import os

class ImageRekognitionStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create the S3 bucket where images will be uploaded
        image_bucket = s3.Bucket(self, "ImageBucket",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,  # Cleanup bucket on stack deletion
            auto_delete_objects=True  # Automatically delete objects on bucket removal
        )

        # Lambda function for processing uploaded images and invoking Rekognition
        rekognition_lambda = _lambda.Function(self, "RekognitionLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="rekognition_lambda.handler",
            code=_lambda.Code.from_asset("lambda"),  # Directory where the lambda code is stored
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                'IMAGE_BUCKET': image_bucket.bucket_name
            }
        )

        # Grant the Lambda function permissions to use Rekognition and access the S3 bucket
        image_bucket.grant_read(rekognition_lambda)

        rekognition_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["rekognition:DetectLabels"],
            resources=["*"]  # Rekognition API requires a global ARN
        ))

        # Add S3 event notification to trigger the Lambda function on image uploads
        image_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(rekognition_lambda),
            s3.NotificationKeyFilter(suffix='.jpg')  # Only trigger for JPG images (you can extend to .png etc.)
        )

        # Outputs
        self.add_outputs(image_bucket, rekognition_lambda)

    def add_outputs(self, image_bucket, rekognition_lambda):
        from aws_cdk import CfnOutput
        CfnOutput(self, "ImageBucketName", value=image_bucket.bucket_name)
        CfnOutput(self, "LambdaFunctionArn", value=rekognition_lambda.function_arn)


```

### Lambda Function Code (`lambda/rekognition_lambda.py`):

```python
import json
import boto3
import os

s3_client = boto3.client('s3')
rekognition_client = boto3.client('rekognition')

def handler(event, context):
    # Extract bucket name and object key from the S3 event
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']
        
        # Call Rekognition to detect labels in the image
        response = rekognition_client.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': object_key
                }
            },
            MaxLabels=10,  # Limit to 10 labels
            MinConfidence=75  # Minimum confidence for a label to be returned
        )
        
        # Log detected labels
        print(f"Detected labels for {object_key}:")
        for label in response['Labels']:
            print(f"{label['Name']} - Confidence: {label['Confidence']}%")
        
        # Return response
        return {
            'statusCode': 200,
            'body': json.dumps('Rekognition labels detected')
        }
```

### CDK Stack Breakdown:

1. **S3 Bucket (`image_bucket`)**: 
   - Stores the images that you want to analyze.
   - Triggers the Lambda function when a new image is uploaded (specifically images with `.jpg` extension).

2. **Lambda Function (`rekognition_lambda`)**:
   - The Lambda function is triggered when a new image is uploaded to the S3 bucket.
   - It uses Amazon Rekognition to analyze the image and detect labels.
   - The function has the necessary IAM permissions to read from the S3 bucket and invoke Rekognition.

3. **S3 Event Notification**:
   - The S3 bucket triggers the Lambda function when a new image with the `.jpg` suffix is uploaded.

4. **Permissions**:
   - The Lambda function is granted permissions to use Rekognition (`rekognition:DetectLabels`) and to read from the S3 bucket.

### Deployment:

1. Save the Lambda function code (`rekognition_lambda.py`) in a folder named `lambda`.
2. Deploy the CDK stack using:

```bash
cdk deploy
```

This will provision all the required AWS resources: S3 bucket, Lambda function, and the IAM roles and permissions necessary for Rekognition and S3 access.

### Testing:

1. Upload an image (e.g., `test.jpg`) to the S3 bucket created by the stack.
2. The Lambda function will be triggered, and you can check the logs in CloudWatch to see the detected labels.

### Next Steps:

- Extend the architecture to support other image formats (e.g., `.png`).
- You can store the detected labels in a DynamoDB table or send them to an SNS topic for further processing.
