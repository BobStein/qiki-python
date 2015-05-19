"""
Testing qiki Word.py
"""

import unittest
import os
from Number import Number
from Word import Word


class WordTestCase(unittest.TestCase):

    def setUp(self):
        Word.connect({
            'host':     os.environ['DATABASE_HOST'],
            'port':     os.environ['DATABASE_PORT'],
            'user':     os.environ['DATABASE_USER'],
            'password': os.environ['DATABASE_PASSWORD'],
            'database': os.environ['DATABASE_DATABASE'],
        }, table='word')
        Word.install_from_scratch()

    def tearDown(self):
        Word.disconnect()

    def test_00_number(self):
        n = Number(1)
        self.assertEqual(1, int(n))

    def test_00_word(self):
        define = Word('define')
        self.assertEqual(define.verb, define.id)

    def test_id_unsettable(self):
        define = Word('define')
        with self.assertRaises(RuntimeError):
            define.id = -1

    def test_triple_self_evident(self):
        define = Word('define')
        self.assertEqual(define.subject, define.id)
        noun = Word('noun')
        self.assertEqual(noun.subject, noun.id)
        verb = Word('verb')
        self.assertEqual(verb.subject, verb.id)


if __name__ == '__main__':
    import unittest
    unittest.main()
