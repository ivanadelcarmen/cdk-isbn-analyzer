import urllib.request
import urllib.error
import json

from typing import Any

def fetch_book_data(isbn: str) -> dict[str,Any]:
    """
    Make a GET request to the 'volumes' endpoint of the Google Books API
    to get the details of the desired ISBN as a JSON object.

    Args:
        isbn: String of the ISBN-10 or ISBN-13 number without non-numerical characters (e.g., 9789876290500).
    
    Returns:
        dict[str,Any]: The parsed JSON object returned from the API.
    """
    try:
        URL = 'https://www.googleapis.com/books/v1/volumes?q=isbn'
        
        with urllib.request.urlopen(URL + ':' + isbn) as req:
            response = json.loads(req.read().decode())
        response['code'] = 200
        return response
    except (urllib.error.HTTPError, urllib.error.URLError) as err:
        return {
            'code': err.code if err.code else -1,
            'reason': err.reason
        }


def structure_book_data(isbn: str) -> dict[str,Any]:
    """
    Structure the data retrieved from the Google Books API into a JSON, NoSQL 
    format that contains relevant fields.

    Args:
        isbn: String of the ISBN-10 or ISBN-13 number without non-numerical characters (e.g., 9789876290500).
    
    Returns:
        dict[str,Any]: A JSON object which contains the formatted and structured data returned
                       from the API. In case the API outputs no matched books, a JSON object is 
                       returned with an exception value of 1 and the ISBN number, opposed to the 
                       value 0 of successfully parsed results.
    """
    book_data = fetch_book_data(isbn)

    # If there are matching results, select the first volume found
    if book_data['totalItems'] != 0:
        book_data = book_data['items'][0]
        volume_data = book_data['volumeInfo']
        isbn_data = sorted(book_data['volumeInfo']['industryIdentifiers'], key=lambda x: x['type']) # ISBN 10, ISBN 13 in order

        publisher = volume_data['publisher'] if 'publisher' in volume_data.keys() else 'N/A'
        title = f'{volume_data['title']}: {volume_data['subtitle']}' \
                if 'subtitle' in volume_data.keys() else volume_data['title']

        formatted_data = {
            'isbn': isbn_data[1]['identifier'], # By default, ISBN-13 is taken as the ID
            'authors': volume_data['authors'],
            'title': title,
            'categories': volume_data['categories'],
            'page_count': volume_data['pageCount'],
            'language': volume_data['language'].upper(),
            'publisher': publisher,
            'published_year': int(volume_data['publishedDate'][:4]),
            'exception': 0
        }

        return formatted_data

    # Proceed to build an exception object or message in case there are no matching results
    if isbn.isdigit() and (len(isbn) == 10 or len(isbn) == 13):
        return {
            'isbn': isbn,
            'exception': 1
        }
    else:
        raise Exception(f'The selected value does not match ISBN-10 or ISBN-13 formats.', isbn)