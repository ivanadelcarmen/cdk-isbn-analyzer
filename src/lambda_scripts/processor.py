import re
import os
import logging

import boto3
from botocore.exceptions import ClientError
from utils import structure_book_data

logger = logging.getLogger(__name__) # Set up logging

def load_to_db(object, table_name):
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        response = table.put_item(Item=object)

        logger.info('Object loaded to DynamoDB table %s: %s', table_name, response)

    except ClientError as err:
        logger.error('CLIENT ERROR %s', err.response['Error']['Code'])
        err_message = f'Could not upload the object to DynamoDB. {err.response['Error']['Message']}'
        logger.exception('MESSAGE %s', err_message)


def lambda_handler(event, context):
    try:
        rekognition = boto3.client('rekognition')
        
        event_date = event['Records'][0]['eventTime'][:10]
        event_time = event['Records'][0]['eventTime'][11:19]

        image = {
            'S3Object': {
                    'Bucket': event['Records'][0]['s3']['bucket']['name'],
                    'Name': event['Records'][0]['s3']['object']['key']
                }
        }
        response = rekognition.detect_text(Image=image)
        
        # Join together all the detected digits in the first line
        first_line = response['TextDetections'][0]['DetectedText']
        isbn = ''.join(re.findall(r'\d', first_line))
        
        # Build the JSON object with ISBN data along with timestamp information from the S3 event
        book_data = structure_book_data(isbn)
        book_data['date'] = event_date
        book_data['time'] = event_time

        # Log the parsed data and load it into the DynamoDB table
        logger.info("Parsed data: %s", book_data)
        load_to_db(book_data, os.getenv('TABLE_NAME'))
        
    except ClientError as err:
        logger.error('CLIENT ERROR %s', err.response['Error']['Code'])
        err_message = f'Could not analyze image. {err.response['Error']['Message']}'
        logger.exception('MESSAGE %s', err_message)
        
    except Exception as err:
        logger.exception('UNEXPECTED ERROR OCCURED')