import json
import urllib.error

import unittest
from unittest.mock import patch, MagicMock

from src.scripts.utils import fetch_book_data, structure_book_data

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
        json_res = {
            'totalItems': 1,
            'items': [
                {
                    'volumeInfo': {
                        'industryIdentifiers': [
                            'mockItem',
                            {
                                'identifier': '9789876290500'
                            }
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
        mock_fetch_book_data.return_value = json_res

        res_example = {
            'isbn': '9789876290500',
            'authors': ['Michel Foucault'],
            'title': 'Las palabras y las cosas: una arqueología de las ciencias humanas',
            'categories': ['Civilization'],
            'page_count': 398,
            'language': 'ES',
            'publisher': 'N/A',
            'published_year': 2011,
            'exception': 0
        }

        # Use mock value '1' as argument
        self.assertEqual(structure_book_data('1'), res_example)

    @patch('src.scripts.utils.fetch_book_data')
    def test_empty_object(self, mock_fetch_book_data):
        json_res = {'totalItems': 0}
        mock_fetch_book_data.return_value = json_res
        
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


if __name__ == '__main__':
    unittest.main(verbosity=2)