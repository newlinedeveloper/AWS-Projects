import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_de_cdk.aws_de_cdk_stack import AwsDeCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_de_cdk/aws_de_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsDeCdkStack(app, "aws-de-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
