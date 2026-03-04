import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
textract = boto3.client('textract')
sns = boto3.client('sns')

topic_arn = os.environ ['TEXTRACT_NOTIFICATION_TOPIC'] 
textract_role = os.environ['TEXTRACT_ROLE_ARN']

def lambda_handler(event, context):
    print(f"****EVENT****: {event}")
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        try:
            try: 
                s3.head_object(Bucket=bucket, Key=key)
                print(f"Object {key} verification succesful in {bucket}")
            except Exception as e:
                print(f"Object verification failed: {str{e}}")
                raise Exception(e)

            response = textract.start_document_text_detection(
                DocumentLocation = {
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                },
                NotificationChannel={
                    'SNSTopicArn': topic_arn,
                    'RoleArn': textract_role
                }
            )

            logger.info(f"File {key} is sent to Textraxt.")

        except Exception as e:
            logger.error(f"Error processing file {key} from bucket {bucket}: {str(e)}")
            continue
    
    return {
        'statusCode': 200,
        'body': 'Textract processing initialized Succesfully !!!'
    }



