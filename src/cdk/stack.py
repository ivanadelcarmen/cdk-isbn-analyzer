from pathlib import Path
from configparser import ConfigParser

from constructs import Construct
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_logs as logs
)

config_file = Path(__file__).parent.parent / 'config.conf'
parser = ConfigParser()
parser.read(config_file)

TRANSITION_DAYS = parser.getint('lifecycleRules', 'transitionDays')
EXPIRATION_DAYS = parser.getint('lifecycleRules', 'expirationDays')

if TRANSITION_DAYS > 0 and EXPIRATION_DAYS > TRANSITION_DAYS:
    transition_state = [
        s3.Transition(
            storage_class=s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
            transition_after=Duration.days(TRANSITION_DAYS)
        )
    ]
else:
    transition_state = None

REMOVAL_POLICY = parser.get('storagePolicies', 'removalPolicy').strip().upper()

if REMOVAL_POLICY == 'DESTROY':
    configured_removal = RemovalPolicy.DESTROY
elif REMOVAL_POLICY == 'RETAIN':
    configured_removal = RemovalPolicy.RETAIN
else:
    raise ValueError(f'Invalid removal policy: {REMOVAL_POLICY}')

class isbnProcessorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # =============================
        # S3 Bucket
        # =============================

        # 1. Create a LifeCycle Rule for the S3 bucket
        s3_lifecycle_rule = s3. \
            LifecycleRule(
                expiration=Duration.days(EXPIRATION_DAYS),
                transitions=transition_state
            )
        
        # 2. Create S3 Bucket
        images_bucket = s3. \
            Bucket(
                self,
                id='ImagesBucket',
                bucket_name='isbn-processor-images',
                lifecycle_rules=[s3_lifecycle_rule],
                removal_policy=configured_removal
            )
        
        # =============================
        # API Gateway
        # =============================

        # 1. Create role and grant PUT access to the REST API, only for the created bucket
        rest_api_role = iam.\
            Role(
                self,
                id='GatewayS3Role',
                role_name='APIGatewayS3Role',
                assumed_by=iam.ServicePrincipal('apigateway.amazonaws.com')
            )
        images_bucket.grant_put(rest_api_role)
        
        # 2. S3 integration
        s3_integration = apigateway. \
            AwsIntegration(
                service='s3',
                integration_http_method='PUT',
                path=f'{images_bucket.bucket_name}/{{object}}',
                options=apigateway.IntegrationOptions(
                    credentials_role=rest_api_role,
                    request_parameters={
                        'integration.request.header.Content-Type': 'method.request.header.Content-Type',
                        'integration.request.path.object': 'method.request.querystring.filename'
                    },
                    integration_responses=[
                        apigateway.IntegrationResponse(
                            status_code='200',
                            selection_pattern='2..',
                            response_parameters={
                                'method.response.header.Content-Type': 'integration.response.header.Content-Type'
                            },
                            response_templates={
                                'application/json': '{"message": "Image successfully loaded"}'
                            }
                        ),
                        apigateway.IntegrationResponse(
                            status_code='400',
                            selection_pattern='4..',
                            response_templates={
                                'application/json': '{"message": "Invalid request: check Content-Type or filename query string"}'
                            }
                        )
                    ]
                )
            )

        # 3. Create API Gateway REST API with CloudWatch options
        rest_api = apigateway. \
            RestApi(
                self,
                id='GatewayS3RestAPI',
                rest_api_name='upload-isbn',
                binary_media_types=['image/jpeg', 'image/png'], # Expect binary inputs for the allowed formats
                cloud_watch_role=True,
                cloud_watch_role_removal_policy=RemovalPolicy.DESTROY,
                deploy_options=apigateway.StageOptions(
                    stage_name='v1'
                )
            )
        images_endpoint = rest_api.root.add_resource('images')

        # 4. Add S3 integration and specify + validate request parameters
        images_endpoint.add_method(
            'PUT',
            integration=s3_integration,
            request_parameters={
                'method.request.header.Content-Type': True,
                'method.request.querystring.filename': True
            },
            request_validator=apigateway.RequestValidator(
                self,
                id='CDKRestApiRequestValidator',
                rest_api=rest_api,
                validate_request_parameters=True
            ),
            method_responses=[
                apigateway.MethodResponse(
                    status_code='200',
                    response_parameters={
                        'method.response.header.Content-Type': True
                    }
                ),
                apigateway.MethodResponse(
                    status_code='400'
                )
            ]
        )

        # =============================
        # DynamoDB Table
        # =============================
        
        # 1. Create the DynamoDB Table with provisioned settings
        isbn_events_table = dynamodb. \
            Table(
                self,
                id='EventsTable',
                table_name='isbn_events',
                billing_mode=dynamodb.BillingMode.PROVISIONED,
                read_capacity=1,
                write_capacity=4,
                partition_key=dynamodb.Attribute(
                    name='isbn',
                    type=dynamodb.AttributeType.STRING
                ),
                sort_key=dynamodb.Attribute(
                    name='timestamp',
                    type=dynamodb.AttributeType.STRING
                ),
                removal_policy=configured_removal
            )

        # =============================
        # Lambda Function
        # =============================
        
        # 1. Create inline policies
        bucket_lambda_policy = iam. \
            PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=['s3:GetObject'],
                        resources=[f'{images_bucket.bucket_arn}/*']
                    )
                ]
            )
        
        rekognition_lambda_policy = iam. \
            PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=['rekognition:DetectText'],
                        resources=['*']
                    )
                ]
            )
        
        dynamodb_lambda_policy = iam. \
            PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=['dynamodb:PutItem'],
                        resources=[isbn_events_table.table_arn]
                    )
                ]
            )
        
        # 2. Create custom Lambda execution role with managed and custom policies
        lambda_exec_role = iam. \
            Role(
                self,
                id='LambdaExecutionRole',
                role_name='LambdaISBNProcessorRole',
                assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
                managed_policies=[
                    # Attach basic Lambda execution managed policies
                    iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')
                ],
                inline_policies={
                    'LambdaS3BucketGetPolicy': bucket_lambda_policy,
                    'LambdaRekognitionAccessPolicy': rekognition_lambda_policy,
                    'LambdaDynamoDBTableAccessPolicy': dynamodb_lambda_policy
                }
            )

        # 3. Create Lambda event source from S3
        s3_event_source = lambda_event_sources. \
            S3EventSource(
                bucket=images_bucket,
                events=[s3.EventType.OBJECT_CREATED_PUT]
            )
        
        # 4. Create Lambda function with logging options and add event source
        lambda_processor = lambda_. \
            Function(
                self,
                id='LambdaFunction',
                function_name='isbn_processor',
                runtime=lambda_.Runtime.PYTHON_3_12,
                code=lambda_.Code.from_asset('scripts'),
                handler='handler.lambda_handler',
                role=lambda_exec_role,
                timeout=Duration.seconds(8),
                environment={
                    'TABLE_NAME': isbn_events_table.table_name # Required environment variable for loading data
                },
                log_group=logs.LogGroup(
                    self,
                    id='LambdaLogGroup',
                    retention=logs.RetentionDays.ONE_WEEK,
                    removal_policy=RemovalPolicy.DESTROY
                )
            )
        lambda_processor.add_event_source(s3_event_source)