Event-Driven ETL Automation | Lambda, Step Functions, SNS, Glue

- configure lambda function to automatically start step function workflow
- create step functions workflow to co-ordinate data analytics pipeline

Here's a Python AWS CDK application for creating an **Event-Driven ETL Automation** system using **AWS Lambda**, **Step Functions**, **SNS**, and **AWS Glue**. This architecture allows you to trigger a Step Functions workflow using Lambda, which then orchestrates the entire ETL process using Glue.

### Scenario Overview:
1. **Lambda Function**: The Lambda function triggers a Step Functions workflow when an event (e.g., new data in an S3 bucket) occurs.
2. **Step Functions**: Coordinates the different stages of the ETL pipeline by orchestrating the Glue job(s).
3. **SNS**: Used for notifications or to publish status updates.
4. **AWS Glue**: Executes the ETL job to transform and load data.
5. **S3**: Optionally stores raw data and processed data.

### Directory Structure:
```bash
.
├── app.py  # Main CDK application
└── lambda
    └── trigger_step_function.py  # Lambda function to trigger Step Functions
```

### `app.py` (CDK Application)

```python
from aws_cdk import (
    core,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_sns as sns,
    aws_iam as iam,
    aws_glue as glue,
    aws_events as events,
    aws_events_targets as targets
)

class EventDrivenETLStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create an S3 bucket to store raw data
        raw_data_bucket = s3.Bucket(self, "RawDataBucket",
                                    versioned=True,
                                    removal_policy=core.RemovalPolicy.DESTROY)

        # Create an SNS Topic for status notifications
        sns_topic = sns.Topic(self, "ETLStatusTopic")

        # Create Glue ETL Job (requires Glue script and resources)
        glue_job = glue.CfnJob(self, "GlueETLJob",
                               name="etl-job",
                               role="AWSGlueServiceRole",  # Assumed IAM role for Glue
                               command={
                                   "name": "glueetl",
                                   "scriptLocation": "s3://path-to-your-script/script.py",
                                   "pythonVersion": "3"
                               },
                               default_arguments={
                                   "--TempDir": "s3://path-to-temp-dir/",
                                   "--job-bookmark-option": "job-bookmark-enable"
                               },
                               max_retries=2,
                               max_capacity=5.0)

        # Lambda function to trigger Step Functions workflow
        trigger_lambda = _lambda.Function(self, "TriggerStepFunctionLambda",
                                          runtime=_lambda.Runtime.PYTHON_3_8,
                                          handler="trigger_step_function.handler",
                                          code=_lambda.Code.from_asset("lambda"),
                                          environment={
                                              "STEP_FUNCTION_ARN": "arn:aws:states:region:account:stateMachine:your-state-machine"
                                          })

        # Grant Lambda permissions to invoke Step Functions
        trigger_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["states:StartExecution"],
            resources=["*"]
        ))

        # Step Functions Workflow Definition
        start_glue_job = tasks.GlueStartJobRun(self, "StartGlueJob",
                                               glue_job_name=glue_job.ref)

        publish_sns = tasks.SnsPublish(self, "NotifySNS",
                                       topic=sns_topic,
                                       message=sfn.TaskInput.from_text("ETL Job completed!"))

        # Create Step Functions State Machine
        state_machine = sfn.StateMachine(self, "ETLStateMachine",
                                         definition=start_glue_job.next(publish_sns),
                                         timeout=core.Duration.minutes(30))

        # Grant Lambda permission to trigger Step Functions
        state_machine.grant_start_execution(trigger_lambda)

        # Trigger Step Functions workflow using EventBridge (optional: based on S3 event or any other event)
        event_rule = events.Rule(self, "TriggerStepFunctionRule",
                                 event_pattern={
                                     "source": ["aws.s3"],
                                     "detail": {
                                         "eventName": ["ObjectCreated:Put"]
                                     }
                                 })

        event_rule.add_target(targets.LambdaFunction(trigger_lambda))

        # Outputs
        core.CfnOutput(self, "RawDataBucket", value=raw_data_bucket.bucket_name)
        core.CfnOutput(self, "StepFunctionArn", value=state_machine.state_machine_arn)
        core.CfnOutput(self, "SnsTopicArn", value=sns_topic.topic_arn)

app = core.App()
EventDrivenETLStack(app, "EventDrivenETLStack")
app.synth()
```

### Lambda Function (`trigger_step_function.py`)

The Lambda function that triggers the Step Functions workflow:

```python
import os
import json
import boto3

def handler(event, context):
    step_function_arn = os.environ.get('STEP_FUNCTION_ARN')
    
    # Initialize Step Functions client
    client = boto3.client('stepfunctions')
    
    # Start the Step Function execution
    response = client.start_execution(
        stateMachineArn=step_function_arn,
        input=json.dumps(event)
    )
    
    print(f"Started Step Function execution: {response['executionArn']}")
    
    return response
```

### Step Functions Workflow
The Step Functions workflow consists of:
1. **Start Glue Job**: The Glue job is started to process and transform the data.
2. **SNS Publish**: Sends a notification to an SNS topic once the Glue job completes.

### AWS Glue Job
In this example, AWS Glue is configured to run a Spark script to perform the actual ETL job. The Glue job is configured to run with the following properties:
- **Python version 3**.
- **Temporary directory** in S3 for storing intermediate results.
- **Job Bookmark** to allow Glue to remember the progress of previous jobs.

### Permissions and IAM Roles
- The **Lambda function** needs permissions to start Step Functions workflows (`states:StartExecution`).
- The **Step Functions state machine** needs permissions to start Glue jobs and publish messages to SNS.
- The **Glue job** needs an IAM role (`AWSGlueServiceRole`) with permissions to access S3, write logs, and perform other required operations.

### Summary:
This CDK stack builds an event-driven ETL automation service that leverages:
- **AWS Lambda** to trigger the Step Functions workflow.
- **Step Functions** to orchestrate the Glue ETL process.
- **SNS** for notifications.
- **Glue** to execute the ETL job.
- **S3** to store raw and processed data.
