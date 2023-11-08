# a lambda handler
import boto3
import os
import json

def lambda_handler(event, context):
    # get the cognito username from the event identity
    username = event['requestContext']['authorizer']['claims']['cognito:username']
    # username = "gasamoma"
    # prefix output/ with username
    username = "output/" + username
    bucketname = os.environ['BUCKET_NAME']
    # get the file keys from username prefix from the s3 bucket
    s3 = boto3.client('s3')
    response = s3.list_objects_v2(Bucket=bucketname, Prefix=username)
    # get all the keys into a list 
    keys = [{'s3Key':item['Key'],"name": item['Key'].split("/")[-1] } for item in response['Contents'][1:]]
    # return only the object keys 
    
    return {
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': os.environ['CORS_ORIGIN'] if 'CORS_ORIGIN' in os.environ else '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
        'statusCode': 200,
        'body': json.dumps(keys)
        }