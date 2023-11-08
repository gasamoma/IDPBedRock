# json os boto
import boto3
import json
import os
import botocore


# a function that calls aws translate to covnert spanish into english
def translate_text(text, lang="en"):
    # get the translate client
    translate = boto3.client('translate')
    # translate the text
    if lang=='en':
        source='en'
        dest='es'
    else:
        source='es'
        dest='en'
        
    translation = translate.translate_text(
        Text=text,
        SourceLanguageCode=source,
        TargetLanguageCode=dest
    )
    # return the translation
    return translation

# a function that assumes another role
def assume_role(role_arn, session_name):
    # get the sts client
    sts = boto3.client('sts')
    # assume the role
    assumed_role_object = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )
    # get the credentials
    credentials = assumed_role_object['Credentials']
    # return the credentials
    return credentials
# a function that sings auth v4 httplib requests without using boto3
def sign_request(credentials, method, url, body):
    # get the http client
    http = boto3.client('http')
    # get the headers
    headers = {'content-type': 'application/json'}
    # get the url
    url = url.replace("https://", "http://")
    # get the body
    body = body.encode('utf-8')
    # get the method
    method = method.upper()
    # get the signed request
    signed_request = http.request_presign(
        method=method,
        url=url,
        headers=headers,
        body=body,
        auth_scheme='AWS4-HMAC-SHA256',
        expires_in=3600,
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
    # return the signed request
    return signed_request


def get_bedrock_client():
    region = 'us-east-1'
    # assume another role in another account by os environment variables
    assume_role_arn = os.environ['ASSUME_ROLE_ARN'] if 'ASSUME_ROLE_ARN' in os.environ else None
    assume_role_session_name = os.environ['ASSUME_ROLE_SESSION_NAME'] if 'ASSUME_ROLE_SESSION_NAME' in os.environ else None
    # if assume role arn is not none
    if assume_role_arn is not None:
        credentials = assume_role(assume_role_arn, assume_role_session_name)
        return boto3.client(
            'bedrock-runtime', 
            region_name=region,
            aws_access_key_id=credentials['AccessKeyId'], 
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'])
    else:
        return boto3.client(
            'bedrock-runtime', 
            region_name=region)


# a function that calls the bedrock invoke model api depending on the model id
def invoke_model(input_data):
    # get the model id from the environment variables default it to ai21.j2-jumbo-instruct
    modelId = os.environ['MODEL_ID'] if 'MODEL_ID' in os.environ else 'ai21.j2-jumbo-instruct'
    
    # get the bedrock client
    bedrock = get_bedrock_client()
    # get the input data
    input_data = json.dumps(input_data)
    # if model id has ai21 in the string content
    if modelId.split(".")[0]== "ai21":
        body = json.dumps({
            "prompt": input_data , 
            "maxTokens":200,
            "temperature":0.7,
            "topP":1,
            "stopSequences": [],
            "countPenalty":{"scale":0},
            "presencePenalty":{"scale":0},
            "frequencyPenalty":{"scale":0}
        })
        accept = 'application/json'
        contentType = 'application/json'
        response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
    else:
        # translate the input_data into english
        input_data = translate_text(input_data, lang="es")
        body = json.dumps({"inputText": input_data['TranslatedText'] })
        accept = 'application/json'
        contentType = 'application/json'
        response_b = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
        # {\"inputText\": \"story of two dogs\"}
        response_body = json.loads(response_b.get('body').read())
        # modify the response and translate it back to spanish
        response = response_body.get('results')[0].get('outputText')
        response = translate_text(response, lang='en')['TranslatedText']
        
    # return the response
    return response

# a lambda handler called by the api gateway post no proxy
def handler(event, context):
    
    print(boto3.__version__)
    print(botocore.__version__)
    # get the request body from the event
    body = json.loads(event['body'])
    endpoint_region = os.environ['ENDPOINT_REGION'] if 'ENDPOINT_REGION' in os.environ else 'us-west-2'
    bedrock = get_bedrock_client()
    # get the cognito username from the event identity
    username = event['requestContext']['authorizer']['claims']['cognito:username']
    
    # get the key from the body
    key = body['key']
    # get the query from the body if exists
    query = body['query'] if 'query' in body else None
    # if query is none 
    if query is None:
        query = "Cuanto salario gana la persona de la que se habla en el siguiente texto: "
    # check if key contains username
    if key.find(username) == -1:
        # the user is not autorized to get this content
        return {
            'statusCode': 401,
            'body': json.dumps('Unauthorized')
            }
    # else extract the contents of the bucket that is a json file
    else:
        # get the bucketname from the os
        bucketname = os.environ['BUCKET_NAME']
        # get the s3 file with the key
        s3 = boto3.resource('s3')
        obj = s3.Object(bucketname, key)
        # get the contents of the file
        contents = obj.get()['Body'].read().decode('utf-8')
        # the content is a response from detect_document_text
        response = json.loads(contents)
        ## TODO try to send the raw refined response of textract instead of joining it 
        
        # join all the detected text if exists into one string
        text = ""
        for item in response['Blocks']:
            if item['BlockType'] == "LINE":
                text += item['Text'] + " "
            elif item['BlockType'] == "PAGE":
                text += "\n"
            elif item['BlockType'] == "WORD":
                text += item['Text'] + " "
        
        # documentation https://preview.documentation.bedrock.aws.dev/Documentation/BedrockUserGuide.pdf"{\"prompt\":\"
        body = query + text
        print(body)
        response = invoke_model(body)
        response_body = bytes.decode(response['body'].read())
        load_body = json.loads(response_body)
        # return all the results
        return {
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': os.environ['CORS_ORIGIN'] if 'CORS_ORIGIN' in os.environ else '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
            'statusCode': 200,
            'body': json.dumps(load_body.get('completions')[0].get('data').get('text'))
            }
