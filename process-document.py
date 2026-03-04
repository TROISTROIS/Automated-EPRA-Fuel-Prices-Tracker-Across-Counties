import boto3
import os
import logging
import urllib.parse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
textract = boto3.client('textract')

topic_arn = os.environ['TEXTRACT_NOTIFICATION_TOPIC'] 
textract_role = os.environ['TEXTRACT_ROLE_ARN']

def lambda_handler(event, context):
    logger.info(f"****EVENT****: {event}")
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        # Use unquote_plus to handle spaces and special characters in filenames
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])

        try:
            # 1. Start Document Analysis (Specifically for Tables)
            response = textract.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                },
                FeatureTypes=['TABLES'], # Identifies the rows/columns
                NotificationChannel={
                    'SNSTopicArn': topic_arn,
                    'RoleArn': textract_role
                },
                
                # Unique identifier to track this job in logs
                ClientRequestToken=key.replace('/', '-') 
            )

            job_id = response['JobId']
            logger.info(f"Started Table Analysis JobId: {job_id} for file: {key}")

        except Exception as e:
            logger.error(f"Error starting Textract for {key}: {str(e)}")
            continue
    
    return {
        'statusCode': 200,
        'body': 'Asynchronous Table Extraction Started'
    }