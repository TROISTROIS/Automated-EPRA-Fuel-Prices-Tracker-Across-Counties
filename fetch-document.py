import json
import boto3
import logging
import re
import os
from decimal import Decimal


logger = logging.getLogger()
logger.setLevel(logging.INFO)

textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')

table_name = os.environ ['DYNAMODB_TABLE']
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    logger.info(f"Event: {json.dumps(event)}")
    try:
        for record in event['Records']:
            sqs_body = json.loads(record['body'])
            sns_message = json.loads(sqs_body['Message'])
            
            job_id = sns_message.get('JobId')
            status = sns_message.get('Status')
            
            if not job_id:
                logger.error("JobId not found in SNS message")
                continue

            logger.info(f"Processing Job: {job_id} (Status: {status})")

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

                logger.info(f"Retrieved {len(all_blocks)} blocks.")
                extracted_data = parse_textract_blocks(all_blocks)
                
                if extracted_data:
                    save_to_dynamo_batch(extracted_data, job_id)
                else:
                    logger.warning(f"No fuel price data extracted for Job: {job_id}")

    except Exception as e:
        logger.error(f"Fatal Lambda Error: {str(e)}")
        raise e 

    return {'statusCode': 200, 'body': 'Processing complete.'}

def parse_textract_blocks(blocks):
    block_map = {b['Id']: b for b in blocks}
    effective_date = "Unknown Period"
    town_results = []
    
    # Try to find the effective date usually in a LINE block
    for b in blocks:
        # Looking for date pattern March 2026
        if b['BlockType'] == 'LINE':
            text = b.get('Text', '')
            if any(month in text for month in ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']):
                effective_date = text
                break

    tables = [b for b in blocks if b['BlockType'] == 'TABLE']
    for table_block in tables:
        rows = {}
        is_target_table = False
        
        for rel in table_block.get('Relationships', []):
            if rel['Type'] == 'CHILD':
                for cell_id in rel['Ids']:
                    cell = block_map[cell_id]
                    if cell['BlockType'] != 'CELL':
                        continue
                    
                    r, c = cell['RowIndex'], cell['ColumnIndex']
                    
                    # Extract text from cell
                    text = ""
                    if 'Relationships' in cell:
                        for child_id in cell['Relationships'][0]['Ids']:
                            text += block_map[child_id].get('Text', '') + " "
                    
                    val = text.strip()
                    
                    # Detect if this is the fuel price table
                    if any(x in val.upper() for x in ["MOMBASA", "SUPER PETROL", "DIESEL", "KEROSENE"]):
                        is_target_table = True
                    
                    if r not in rows: rows[r] = {}
                    rows[r][c] = val

        if is_target_table:
            for r_idx, cols in rows.items():
                town_name = cols.get(2, "") 
                # Check for validity: town name exists and price column has at least one digit
                if town_name and any(char.isdigit() for char in cols.get(3, "")):
                    if town_name.upper() not in ["TOWNS", "TOWN"]:
                        town_results.append({
                            'Town': town_name,
                            'Petrol': cols.get(3),
                            'Diesel': cols.get(4),
                            'Kerosene': cols.get(5),
                            'EffectiveDate': effective_date
                        })
    return town_results

def save_to_dynamo_batch(data_list, job_id):
    with table.batch_writer() as batch:
        for entry in data_list:
            try:
                # Clean numeric values
                p_raw = re.sub(r'[^\d.]', '', entry.get('Petrol', ''))
                d_raw = re.sub(r'[^\d.]', '', entry.get('Diesel', ''))
                k_raw = re.sub(r'[^\d.]', '', entry.get('Kerosene', ''))

                petrol_val = Decimal(p_raw) if p_raw else Decimal('0')
                diesel_val = Decimal(d_raw) if d_raw else Decimal('0')
                kero_val = Decimal(k_raw) if k_raw else Decimal('0')

                batch.put_item(
                    Item={
                        'Town': entry['Town'], 
                        'EffectiveDate': entry['EffectiveDate'],
                        'PetrolPrice': petrol_val,
                        'DieselPrice': diesel_val,
                        'KerosenePrice': kero_val,
                        'JobId': job_id
                    }
                )
            except Exception as e:
                logger.error(f"Failed to save item for {entry.get('Town')}: {str(e)}")
