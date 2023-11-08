# a lambda handler that presings a s3 url for the conito user folder in a os environ bucket
import boto3
import os
import uuid
import json
from botocore.config import Config

def handler(event, context):

    config = Config(signature_version='s3v4')
    s3 = boto3.client('s3', config=config)
    # get the user email from the event cognito
    username = event['requestContext']['authorizer']['claims']['cognito:username']
    # create the path for the user folder
    path = f"input/{username}"
    # add a uuid to the file .jpg
    path += f"/{str(uuid.uuid4())}.jpg"
    # prepresign the url to path
    presigned_url = s3.generate_presigned_url(
        'put_object', 
        Params={'Bucket': os.environ['BUCKET'], 'Key': path}, 
        ExpiresIn=3600)
    
    #presign the url using boto generate_presigned_post.
    #this is a more secure way to do it.
    # presigned_url = s3.generate_presigned_post( 
    #     Bucket=os.environ['BUCKET'],
    #     Key=path,
    #     ExpiresIn=3600)
        
    return {
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': os.environ['CORS_ORIGIN'] if 'CORS_ORIGIN' in os.environ else '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
        'statusCode': 200,
        'body': json.dumps({'presigned_url':presigned_url})
    }