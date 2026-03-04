import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

textract = boto3.client('textract')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    print("###EVENT###, {event}")

    for record in event['Records']:
        try:
            # The SNS message with job information
            sns_message = json.loads(record['Sns']['Message'])
            # Accessing the keys for getting Textract results
            job_id = sns_message['JobId']
            status = sns_message['Status'] 

            if status == 'SUCCEEDED':
                # Proceed to get the document text detection results
                response = textract.get_document_text_detection(JobId=job_id)

                # Collect extracted text
                detected_text = []
                for item in response.get('Blocks', []):
                    if item['BlockType'] == 'LINE':
                        detected_text.append(item['Text'])

