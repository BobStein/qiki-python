"""
Testing qiki Word.py
"""

import unittest
import os
from Number import Number
from Word import Word

LET_DATABASE_RECORDS_REMAIN = True


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
        if not LET_DATABASE_RECORDS_REMAIN:
            Word.uninstall()
        Word.disconnect()

    def test_00_number(self):
        n = Number(1)
        self.assertEqual(1, int(n))

    def test_00_word(self):
        define = Word('define')
        self.assertEqual(define.vrb, define.id)

    def test_id_unsettable(self):
        define = Word('define')
        with self.assertRaises(RuntimeError):
            define.id = -1

    def test_quintuple_self_evident(self):
        define = Word('define')
        self.assertEqual(define.vrb, define.id)
        noun = Word('noun')
        self.assertEqual(noun.obj, noun.id)
        verb = Word('verb')
        self.assertEqual(verb.obj, noun.id)
        agent = Word('agent')
        self.assertEqual(agent.obj, noun.id)
        system = Word('system')
        self.assertEqual(system.sbj, system.id)
        self.assertEqual(system.obj, agent.id)

    def test_by_wawa(self):
        class unexpected:
            pass
        with self.assertRaises(TypeError):
            Word(unexpected)

    def test_by_id(self):
        define = Word('define')
        define2 = Word(define.id)
        self.assertEqual('define', define2.txt)
        self.assertEqual(define.id, define2.id)

    def test_repr(self):
        define = Word('define')
        self.assertIn('define', repr(define))
        self.assertEqual("Word('define')", repr(define))

    def test_defined_verb(self):
        self.assertTrue(Word('define').exists)

    def test_undefined_verb(self):
        u = Word('_undefined_verb_')
        self.assertFalse(u.exists)

    def test_define_method(self):
        system = Word('system')
        self.assertEqual('system', system.txt)
        noun = Word('noun')
        human = system.define(noun, 'human')
        self.assertTrue(human.exists)
        self.assertEqual('human', human.txt)

if __name__ == '__main__':
    import unittest
    unittest.main()
