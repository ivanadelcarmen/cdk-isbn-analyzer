import unittest

# Import utils.py functions
from src.scripts.utils import fetch_book_data, structure_book_data

class fetchBookDataSuite(unittest.TestCase):
    def test_correct_requests(self):
        # The last one is a non-existent ISBN-10 but nonetheless queryable
        isbns = ['9789876290500', '9780393089059', '9786071608154', '9780262510875', '9789538945']
        for isbn in isbns:
            self.assertEqual(fetch_book_data(isbn)['code'], 200)

    def test_correct_books(self):
        isbns_ids = {
            '9789876290500': '8vTsQgAACAAJ',
            '9780393089059': '11GNEAAAQBAJ',
            '9786071608154': 'eDwRNAEACAAJ',
            '9780262510875': 'iL34DwAAQBAJ'
        }
        for item in isbns_ids.items():
            fetched_id = fetch_book_data(item[0])['items'][0]['id']
            self.assertEqual(fetched_id, item[1])

    def test_incorrect_requests(self):
        self.assertNotEqual(fetch_book_data('1'*100000)['code'], 200)
        self.assertNotEqual(fetch_book_data('&q')['code'], 200)


class structureBookDataSuite(unittest.TestCase):
    def test_matching_results(self):
        book_one = {
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
        self.assertEqual(structure_book_data('9789876290500'), book_one)

        book_two = {
            'isbn': '9780393089059',
            'authors': ['Homer'],
            'title': 'The Odyssey',
            'categories': ['Poetry'],
            'page_count': 0, # N/A
            'language': 'EN',
            'publisher': 'National Geographic Books',
            'published_year': 2017,
            'exception': 0
        }
        self.assertEqual(structure_book_data('9780393089059'), book_two)

    def test_empty_results(self):
        isbn_10_exception = {
            'isbn': '9744537984',
            'exception': 1
        }
        self.assertEqual(structure_book_data('9744537984'), isbn_10_exception)

        isbn_13_exception = {
            'isbn': '9742544919120',
            'exception': 1
        }
        self.assertEqual(structure_book_data('9742544919120'), isbn_13_exception)

    def test_invalid_numerics(self):
        with self.assertRaises(Exception) as assert_error:
            structure_book_data('123456')
        self.assertEqual(assert_error.exception.args[1], '123456')

        with self.assertRaises(Exception) as assert_error:
            structure_book_data('9758734587345796')
        self.assertEqual(assert_error.exception.args[1], '9758734587345796')

    def test_invalid_alphabetics(self):
        # Length: 13
        with self.assertRaises(Exception) as assert_error:
            structure_book_data('abcdefghijklm')
        self.assertEqual(assert_error.exception.args[1], 'abcdefghijklm')

        # Length: 10
        with self.assertRaises(Exception) as assert_error:
            structure_book_data('abcdefghij')
        self.assertEqual(assert_error.exception.args[1], 'abcdefghij')


if __name__ == '__main__':
    unittest.main(verbosity=2)