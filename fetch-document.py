import json
import boto3
import logging
import re
from decimal import Decimal

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS Clients
textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')

# Replace with your actual table name
TABLE_NAME = 'EPRA-tb'
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print(json.dumps(event))
    try:
        # Loop through every message in the SQS batch
        for record in event['Records']:
            sqs_body = json.loads(record['body'])
            sns_message = json.loads(sqs_body['Message'])
            
            job_id = sns_message['JobId']
            status = sns_message['Status']
            s3_file = sns_message['DocumentLocation']['S3ObjectName']
            
            logger.info(f"Processing Job: {job_id} for {s3_file} (Status: {status})")

            if status == 'SUCCEEDED':
                all_blocks = []
                next_token = None
                
                while True:
                    params = {'JobId': job_id}
                    if next_token:
                        params['NextToken'] = next_token
                    
                    response = textract.get_document_analysis(**params)
                    all_blocks.extend(response['Blocks'])
                    
                    next_token = response.get('NextToken')
                    if not next_token:
                        break

                logger.info(f"Retrieved a total of {len(all_blocks)} blocks.")
                
                extracted_towns = parse_textract_blocks(all_blocks)
                
                if extracted_towns:
                    save_to_dynamo_batch(extracted_towns, job_id)
                else:
                    logger.error(f"No fuel price table found for Job: {job_id}")

    except Exception as e:
        logger.error(f"Fatal Lambda Error: {str(e)}")
        raise e 

    return {'statusCode': 200, 'body': 'Table data processed and saved.'}

def parse_textract_blocks(blocks):
    block_map = {b['Id']: b for b in blocks}
    effective_date = "Unknown Period"
    town_results = []
    
    # Find the date string
    for b in blocks:
        if b['BlockType'] == 'LINE' and 'March 2026' in b.get('Text', ''):
            effective_date = b['Text']
            break

    tables = [b for b in blocks if b['BlockType'] == 'TABLE']
    for table_block in tables:
        rows = {}
        is_target_table = False
        
        for rel in table_block.get('Relationships', []):
            if rel['Type'] == 'CHILD':
                for cell_id in rel['Ids']:
                    cell = block_map[cell_id]
                    
                    # --- THE FIX: Only process if it is a CELL ---
                    if cell['BlockType'] != 'CELL':
                        continue
                    
                    r, c = cell['RowIndex'], cell['ColumnIndex']
                    
                    # Get Text for this cell
                    text = ""
                    if 'Relationships' in cell:
                        for child_id in cell['Relationships'][0]['Ids']:
                            text += block_map[child_id].get('Text', '') + " "
                    
                    val = text.strip()
                    
                    # Check if this table contains our data
                    if any(x in val.upper() for x in ["MOMBASA", "TOWNS", "SUPER PETROL"]):
                        is_target_table = True
                    
                    if r not in rows: rows[r] = {}
                    rows[r][c] = val

        if is_target_table:
            for r_idx, cols in rows.items():
                town_name = cols.get(2, "")
                # Ensure it's a data row (check if column 3 has a price)
                if town_name and any(char.isdigit() for char in cols.get(3, "")):
                    if town_name.upper() != "TOWNS":
                        town_results.append({
                            'Town': town_name,
                            'Petrol': cols.get(3),
                            'Diesel': cols.get(4),
                            'Kerosene': cols.get(5),
                            'EffectiveDate': effective_date
                        })
    return town_results
def save_to_dynamo_batch(data_list, job_id):
    """Saves multiple items safely by checking for empty price strings."""
    with table.batch_writer() as batch:
        for entry in data_list:
            try:
                
                p_raw = re.sub(r'[^\d.]', '', entry.get('Petrol', ''))
                d_raw = re.sub(r'[^\d.]', '', entry.get('Diesel', ''))
                k_raw = re.sub(r'[^\d.]', '', entry.get('Kerosene', ''))

                petrol_val = Decimal(p_raw) if p_raw else Decimal('0')
                diesel_val = Decimal(d_raw) if d_raw else Decimal('0')
                kero_val = Decimal(k_raw) if k_raw else Decimal('0')

                batch.put_item(
                    Item={
                        'Towns': entry['Town'],
                        'EffectiveDate': entry['EffectiveDate'],
                        'PetrolPrice': petrol_val,
                        'DieselPrice': diesel_val,
                        'KerosenePrice': kero_val,
                        'JobId': job_id
                    }
                )
            except Exception as e:
                logger.error(f"Failed to save item for {entry.get('Town')}: {str(e)}")
