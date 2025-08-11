from datetime import datetime

from constructs import Construct
from aws_cdk import (
    Stack,
    Duration,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_event_sources,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_s3 as s3
)

class isbnProcessorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # =============================
        # S3 Bucket
        # =============================

        # 1. Create a LifeCycle rule for isbn-images S3 bucket
        s3_lifecycle_rule = s3. \
            LifecycleRule(
                expiration=Duration.days(14)
            )
        
        # 2. Create isbn-images S3 Bucket
        images_bucket = s3. \
            Bucket(
                self,
                id='CDKImagesBucket',
                bucket_name=f'isbn-images-{datetime.now().strftime('%Y%m%d')}', # Use the current date as a bucket suffix
                lifecycle_rules=[s3_lifecycle_rule]
            )

        
        # =============================
        # API Gateway
        # =============================

        # 1. Create role and grant s3:PutObject to the REST API, only for the isbn-images bucket
        rest_api_role = iam.\
            Role(
                self,
                id='CDKApiGatewayRole',
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
                                'application/json': '{"message": "Invalid request: check Content-Type and filename query string"}'
                            }
                        )
                    ]
                )
            )

        # 3. Create API Gateway REST API with CloudWatch logging options
        rest_api = apigateway. \
            RestApi(
                self,
                id='CDKApiGatewayRestApi',
                rest_api_name='upload-isbn',
                binary_media_types=['image/jpeg', 'image/png'],
                cloud_watch_role=True,
                deploy_options=apigateway.StageOptions(
                    logging_level=apigateway.MethodLoggingLevel.INFO,
                    data_trace_enabled=True
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