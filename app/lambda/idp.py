# boto json os
import boto3
import json
import os
import urllib



# a handler for lambda
def handler(event, context):
    # get bucket name and key from the event 
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    # do url decode for key
    key = urllib.parse.unquote_plus(key)
    # get the file from s3
    s3 = boto3.client('s3')
    # call textract to get all the text from the pdf
    textract = boto3.client('textract')
    response = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': bucket,
                'Name': key}})
    # create a new key that removes a prefix from the path
    output_key = key.replace('input/', 'output/')
    # replace the file extention with .json
    output_key = output_key.replace('.pdf', '.json')
    output_key = output_key.replace('.jpg', '.json')
    # put the json file in the output prefix with the response extracted text
    print(output_key)
    print(s3.put_object(Body=json.dumps(response), Bucket=bucket, Key=output_key,ContentType="application/json"))
    return {
        'statusCode': 200,
        'body': json.dumps(output_key)
        
    }
