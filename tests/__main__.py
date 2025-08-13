import json
import os
import urllib.error

import unittest
from unittest.mock import patch, MagicMock

from src.scripts.utils import fetch_book_data, structure_book_data
from src.scripts.handler import lambda_handler

class TestFetchBookData(unittest.TestCase):
    @patch('src.scripts.utils.urllib.request.urlopen')
    def test_valid_request(self, mock_request_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({'title': 'Example'}).encode()

        mock_request_urlopen.return_value.__enter__.return_value = mock_response

        isbn = '9789876290500'
        result = fetch_book_data(isbn)
        self.assertEqual(result['code'], 200)
        self.assertEqual(result['title'], 'Example')

        # Check that the function also calls the right concatenated URL
        mock_request_urlopen.assert_called_once_with(
            f'https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}'
        )
    
    @patch('src.scripts.utils.urllib.request.urlopen')
    def test_http_error(self, mock_request_urlopen):
        http_err = urllib.error.HTTPError(
            url='api.example.com', code=404, msg='Not found', hdrs=None, fp=None
        )
        mock_request_urlopen.side_effect = http_err

        result = fetch_book_data('9789876290500')
        self.assertEqual(result['code'], 404)
        self.assertEqual(result['reason'], 'Not found')

    @patch('src.scripts.utils.urllib.request.urlopen')
    def test_url_error(self, mock_request_urlopen):
        url_err = urllib.error.URLError(
            reason='Connection failed', filename=None
        )
        mock_request_urlopen.side_effect = url_err

        result = fetch_book_data('9789876290500')
        self.assertEqual(result['reason'], 'Connection failed')


class TestStructureBookData(unittest.TestCase):
    @patch('src.scripts.utils.fetch_book_data')
    def test_matching_object(self, mock_fetch_book_data):
        mock_res = {
            'totalItems': 1,
            'items': [
                {
                    'volumeInfo': {
                        'industryIdentifiers': [
                            'mock_item',
                            {'identifier': '9789876290500'}
                        ],
                        'authors': ['Michel Foucault'],
                        'title': 'Las palabras y las cosas',
                        'subtitle': 'una arqueología de las ciencias humanas',
                        'categories': ['Civilization'],
                        'pageCount': 398,
                        'language': 'es',
                        'publishedDate': '2011-03-20'
                    }
                }
            ]
        }
        mock_fetch_book_data.return_value = mock_res

        res_example = {
            'isbn': '9789876290500',
            'authors': ['Michel Foucault'],
            'title': 'Las palabras y las cosas: una arqueología de las ciencias humanas',
            'categories': ['Civilization'],
            'page_count': 398,
            'language': 'ES',
            'publisher': 'N/A',
            'year': 2011,
            'exception': 0
        }

        # Use mock value '1' as argument
        self.assertEqual(structure_book_data('1'), res_example)

    @patch('src.scripts.utils.fetch_book_data')
    def test_empty_object(self, mock_fetch_book_data):
        mock_res = {'totalItems': 0}
        mock_fetch_book_data.return_value = mock_res
        
        isbn_13 = '9742544919120'
        isbn_10 = '9744537984'
        res_example = {
            'exception': 1
        }

        # The arguments for each case must be the same as the ISBN numbers in the variable example
        res_example['isbn'] = isbn_13
        self.assertEqual(structure_book_data(isbn_13), res_example)

        res_example['isbn'] = isbn_10
        self.assertEqual(structure_book_data(isbn_10), res_example) 

    @patch('src.scripts.utils.fetch_book_data')
    def test_invalid_values(self, mock_fetch_book_data):
        mock_fetch_book_data.return_value = {'totalItems': 0}

        # Numeric value with length unequal to 10 or 13
        with self.assertRaises(ValueError) as assert_error:
            structure_book_data('123456')
        self.assertEqual(assert_error.exception.args[1], '123456')
        
        # Alphabetic value with length 13
        with self.assertRaises(ValueError) as assert_error:
            structure_book_data('abcdefghijklm')
        self.assertEqual(assert_error.exception.args[1], 'abcdefghijklm')


class TestLambdaHandler(unittest.TestCase):
    @patch('src.scripts.handler.load_to_db')
    @patch("src.scripts.handler.structure_book_data")
    @patch("src.scripts.handler.boto3.client")
    def test_lambda_handler_success(self, mock_boto, mock_structure, mock_load_db):
        bucket_name = 'my-bucket'
        file_name = 'test.jpg'
        timestamp = '2025-01-01'

        raw_isbn = '978-12345-67890'
        clean_isbn = '9781234567890'

        table_name = 'table-example'

        s3_event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': bucket_name},
                        'object': {'key': file_name}
                    },
                    'eventTime': timestamp
                }
            ]
        }

        # Mock Rekognition output
        mock_rekognition = MagicMock()
        mock_rekognition.detect_text.return_value = {
            'TextDetections': [
                {'DetectedText': raw_isbn}
            ]
        }
        mock_boto.return_value = mock_rekognition

        # Mock structure_book_data() reduced output
        mock_structure.return_value = {
            'isbn': '9781234567890',
            'exception': 0
        }

        # Call lambda_handler() with env variables and the fake S3 event
        with patch.dict(os.environ, {'TABLE_NAME': table_name}):
            lambda_handler(s3_event, None)

        # Assert resulting values for each resource
        mock_rekognition.detect_text.assert_called_once_with(
            Image={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': file_name
                }
            }
        )
        mock_structure.assert_called_once_with(clean_isbn)
        mock_load_db.assert_called_once_with(
            {
                'isbn': clean_isbn,
                'exception': 0,
                'timestamp': timestamp
            },
            table_name
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)