from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_s3 as s3,
    aws_lambda as _lambda,
    # cognito
    aws_cognito as _cognito,
    aws_s3_notifications as s3_notify,
    aws_iam as iam,
    # cloudfront
    aws_cloudfront as _cf,
    CfnOutput,
    aws_cloudfront_origins as origins,
    aws_apigateway as apigateway,
    Duration,
    aws_lambda_python_alpha as python,
    RemovalPolicy,
    aws_s3_deployment as s3deploy,
    # aws_sqs as sqs,
)
import os
from constructs import Construct
import os
from constructs import Construct

class IdpStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # an s3 bucket with a name read from a environment variable
        # get the bucket name from an evironment variable
        bucket_name = os.environ.get("BUCKET_NAME", "idp-demo-bucket-proxy")
        if not bucket_name:
            raise ValueError("BUCKET_NAME environment variable is not set")
        
        # create the bucket
        s3_bucket = s3.Bucket(
            self, bucket_name,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED
            )
        
        lambda_function = python.PythonFunction(self, "IdpLambdaFunction",
            entry="app/lambda",
            index="idp.py",
            handler="handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            environment={
                "BUCKET_NAME": s3_bucket.bucket_name
            },
            timeout=Duration.seconds(120),
            layers=[
                python.PythonLayerVersion(self, "IdpLambdaFunction_layer",
                    entry="lib/python",
                    compatible_runtimes=[_lambda.Runtime.PYTHON_3_9]
                )
            ]
        )
        
        get_user_files_lambda = python.PythonFunction(self, "GetUserFilesLambdaFunction",
            entry="app/lambda",
            index="get_user_files.py",
            handler="lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            environment={
                "BUCKET_NAME": s3_bucket.bucket_name
            },
            timeout=Duration.seconds(120),
            layers=[
                python.PythonLayerVersion(self, "GetUserFilesLambdaFunction_layer",
                    entry="lib/python",
                    compatible_runtimes=[_lambda.Runtime.PYTHON_3_9]
                )
            ]
        )
        # an S3 OBJECT_CREATED event in the s3_bucket input prefix that triggers the lambda_function
        notification = s3_notify.LambdaDestination(lambda_function)
        # permisions to the lambda to use the s3_bucket
        s3_bucket.grant_read_write(lambda_function)
        
        get_user_files_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:ListBucket"],
                resources=[s3_bucket.bucket_arn,s3_bucket.bucket_arn + "/*"]))
                
        s3_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED, 
            notification, 
            s3.NotificationKeyFilter(prefix="input/"))        
        # give permisions to the lambda function to call amazon textract and Amazon bedrock
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "textract:StartDocumentTextDetection", 
                    "textract:GetDocumentTextDetection", 
                    "textract:GetDocumentAnalysis", 
                    "textract:GetDocumentTextDetection",
                    "textract:DetectDocumentText",
                    "bedrock:*"],
                    resources=["*"]))
                    
        
        # a lambda function called query_bedrock
        query_bedrock = python.PythonFunction(self, "QueryBedrock",
            entry="app/lambda",
            index="query_bedrock.py",  
            handler="handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            environment={
                "BUCKET_NAME": s3_bucket.bucket_name,
                "PREFIX": "output/",
                "MODEL_ID": "ai21.j2-ultra-v1",
                #"ASSUME_ROLE_ARN":"arn:aws:iam::479225850607:role/CallBedrockAPI-fromLambda",
                #"ASSUME_ROLE_SESSION_NAME":"bedrock_session"
                },
            timeout=Duration.seconds(120),
            layers=[
                python.PythonLayerVersion(self, "bedrock",
                    entry="lib/python",
                    compatible_runtimes=[_lambda.Runtime.PYTHON_3_9]
                )
            ]
        )
        
        api_back_get = python.PythonFunction(self, "ApiBackendGet",
            entry="app/lambda",
            index="api_get.py",
            handler="handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            environment={
                    "BUCKET": s3_bucket.bucket_name,
                },
            timeout=Duration.seconds(120),
            layers=[
                python.PythonLayerVersion(self, "api_layer_get",
                    entry="lib/python",
                    compatible_runtimes=[_lambda.Runtime.PYTHON_3_9]
                )
            ]
        )
        # add permisions to api_back_get to presing urls from s3 to put
        s3_bucket.grant_put(api_back_get,objects_key_pattern="input/*")
        # add permisions to api_back_get to presing urls from s3 to write
        s3_bucket.grant_write(api_back_get,objects_key_pattern="input/*")
        s3_bucket.grant_read(api_back_get,objects_key_pattern="input/*")

        # add permisions to the query_bedrock lambda function to read files from s3 to the output prefix
        s3_bucket.grant_read(query_bedrock,objects_key_pattern="output/*")
        
        # add permisions to the query_bedrock lambda function to use Amazon bedrock
        query_bedrock.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:*"],
                resources=["*"]))
        # add permisions to the query_bedrock lambda function to assume this role arn:aws:iam::479225850607:role/CallBedrockAPI-fromLambda
        query_bedrock.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                resources=["arn:aws:iam::479225850607:role/CallBedrockAPI-fromLambda"]))
        # add translate:TranslateText permission to query_bedrock
        query_bedrock.add_to_role_policy(
            iam.PolicyStatement(
                actions=["translate:TranslateText"],
                resources=["*"]))
            
        s3_website_bucket = s3.Bucket(
            self, "IdpWebsite")
        
        s3deploy.BucketDeployment(self, "DeployWebsite",
            sources=[s3deploy.Source.asset("./web/")],
            destination_bucket=s3_website_bucket
        )
        
        # create an origin access identity
        oin = _cf.OriginAccessIdentity(
            self, "IdpBr-demoOriginAccessIdentity",
            comment="IdpBr-demoOriginAccessIdentity")
        # give permisions to the origin_access_identity to access the s3_website_bucket
        s3_website_bucket.grant_read(oin)
        # a cloudfront distribution for the s3_website_bucket
        cloudfront_website = _cf.Distribution(
            self,
            "IdpCloudFront",
            default_behavior=_cf.BehaviorOptions(
                allowed_methods=_cf.AllowedMethods.ALLOW_ALL,
                origin=origins.S3Origin(
                    s3_website_bucket,
                    origin_access_identity=oin)))
        ## Cognito
        user_pool = _cognito.UserPool(
            self, "IdpUserPoolBR",
            user_pool_name="IdpUserPoolBR",
            self_sign_up_enabled=True,
            # removal policy destroy
            removal_policy=RemovalPolicy.DESTROY,
            # add email as a standard attribute
            standard_attributes=_cognito.StandardAttributes(
                email=_cognito.StandardAttribute(
                    required=True,
                    mutable=False)),
            user_verification=_cognito.UserVerificationConfig(
                email_subject="Verify your email for our awesome app!",
                email_body="Thanks for signing up to our awesome app! Your verification code is {####}",
                email_style=_cognito.VerificationEmailStyle.CODE,
                sms_message="Thanks for signing up to our awesome app! Your verification code is {####}"
            ),
            sign_in_aliases=_cognito.SignInAliases(
                email=True,
                phone=False,
                username=False))
        
        redirect_uri="https://"+cloudfront_website.distribution_domain_name+"/index.html"
        
        domain = user_pool.add_domain("CognitoDomain",
            cognito_domain=_cognito.CognitoDomainOptions(
                domain_prefix="idp-br-domain-demo"
            )
        )
        client = user_pool.add_client("app-client",
            o_auth=_cognito.OAuthSettings(
                flows=_cognito.OAuthFlows(
                    implicit_code_grant=True
                ),
                # the cloudfront distribution root url
                callback_urls=[redirect_uri]
            ),
            auth_flows=_cognito.AuthFlow(
                user_password=True,
                user_srp=True
            )
        )
        sign_in_url = domain.sign_in_url(client,
            redirect_uri=redirect_uri
        )
        autorizer=apigateway.CognitoUserPoolsAuthorizer(
                self, "IdpBrAuthorizer",
                cognito_user_pools=[user_pool])
        # give permisions to the cloudfront to use the s3_website
        #s3_website.grant_read(cloudfront)
        
        # an API gateway that with cors for the cloudfront
        api_gateway = apigateway.RestApi(
            self, "IdpApiGateway",
            rest_api_name="IdpApiGateway",
            description="This is the Idp API Gateway",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_methods=["*"],
                # TODO allow the cloufront distribution
                allow_origins=["*"],
                allow_headers=["*"])
                )
        # a method for the api that calls the bedrock lambda function
        query_bedrock_integration = apigateway.LambdaIntegration(query_bedrock,
                request_templates={"application/json": '{ "statusCode": "200" }'})
        api_backend_get_integration = apigateway.LambdaIntegration( api_back_get,
                request_templates={"application/json": '{ "statusCode": "200" }'})
        get_user_files_integration = apigateway.LambdaIntegration(get_user_files_lambda,
                request_templates={"application/json": '{ "statusCode": "200" }'})
        
        api_backend_resource = api_gateway.root.add_resource("api_backend")
        get_user_files_resource = api_gateway.root.add_resource("get_user_files")
        
        api_backend_resource.add_method(
            "POST", query_bedrock_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=autorizer)
        
        method_get_user_files = get_user_files_resource.add_method(
            "POST", get_user_files_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=autorizer)
        method_api_backend_get = api_backend_resource.add_method(
            "GET", api_backend_get_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=autorizer)
            
        
        s3_bucket.add_cors_rule(allowed_origins=["*"],# TODO Only allow cloudfront_website
            allowed_methods=[s3.HttpMethods.PUT],
            allowed_headers=['*'])
        
        # CfnOutput the iam role of the query bedrock function
        CfnOutput(self, "QueryBedrockRole", value=query_bedrock.role.role_arn)
        
        CfnOutput(self, "CFUrl", value=redirect_uri)
        
        CfnOutput(self, "UserPoolLoginUrl", value=sign_in_url)