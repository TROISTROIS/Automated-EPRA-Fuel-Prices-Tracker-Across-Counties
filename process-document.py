import json
import boto3
import urllib.parse
import logging 

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
textract = boto3.client('textract')

def lambda_handler(event, context):
    print(json.dumps(event))

    # Retrieve the bucket and the file
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    try:
        # Object metadata for validation
        response = s3.get_object(Bucket=bucket, Key=key)
        content_type = response['ContentType']
        logger.info(f"CONTENT TYPE: {content_type}")

        # Start Asynchronous Analysis
        textract_response = textract.start_document_analysis(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            FeatureTypes=['TABLES'],
            NotificationChannel={
                'SNSTopicArn': 'arn:aws:sns:us-east-1:966392475043:AmazonTextractSNSTopic',
                'RoleArn': 'arn:aws:iam::966392475043:role/TextractIAMRoleforSNS'
            }

        )

        job_id = textract_response['JobId']
        logger.info(f"Started analysis Job: {job_id} for file {key}")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Asynchronous Table Extraction Started', 'JobId': job_id})
        }

    except Exception as e:
        logger.error(f"Error processing {key}: {str(e)}")
        raise e