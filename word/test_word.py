"""
Testing qiki word.py
"""

import unittest
import os
from number import Number
from word import Word

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

    def test_01_word(self):
        define = Word('define')
        self.assertEqual(define.vrb, define.id)

    def test_02_word_by_name(self):
        define = Word('define')
        self.assertEqual('define', define.txt)

    def test_02_word_by_id(self):
        define = Word('define')
        define_too = Word(define.id)
        self.assertEqual('define', define_too.txt)

    def test_02_word_by_word(self):
        """Word copy constructor."""
        define = Word('define')
        define_too = Word(define)
        self.assertEqual('define', define_too.txt)

    def test_id_cannot_set_id(self):
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

    def test_word_cant_construct_unfamiliar_class(self):
        # noinspection PyClassHasNoInit
        class UnExpected:
            pass
        with self.assertRaises(TypeError):
            Word(UnExpected)

    def test_number_from_mysql(self):
        mysql_42 = bytearray(b'\x82\x2A')
        num_42 = Number(42)
        self.assertEqual(num_42, Word.number_from_mysql(mysql_42))

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

    def test_max_id(self):
        num_max_id = Word.max_id()
        int_max_id = int(num_max_id)
        self.assertEqual(Word._ID_MAX_FIXED, int_max_id)

    def test_describe(self):
        noun = Word('noun')
        noun_description = noun.description()
        self.assertIn('noun', noun_description)
        print(noun_description)

    def test_is_a(self):
        self.assertTrue( Word('verb').is_a(Word('noun')))
        self.assertFalse(Word('noun').is_a(Word('verb')))

    def test_zz1_define_noun(self):
        system = Word('system')
        noun = Word('noun')
        human = system.define(noun, 'human')
        self.assertTrue(human.exists)
        self.assertEqual('human', human.txt)

    def test_zz1_define_by_id(self):
        system = Word('system')
        noun = Word('noun')
        human = system.define(noun, 'human')
        self.assertTrue(human.exists)
        self.assertEqual('human', human.txt)

    def test_zz1_noun_method(self):
        system = Word('system')
        thing = system.noun('thing')
        self.assertTrue(thing.exists)
        self.assertEqual('thing', thing.txt)

    def test_zz2_define_collision(self):
        system = Word('system')
        noun = Word('noun')
        system.define(noun, 'human')
        with self.assertRaises(Word.DefineDuplicateException):
            system.define(noun, 'human')

    def test_zz3_define_verb(self):
        system = Word('system')
        verb = Word('verb')
        like = system.define(verb, 'like')
        self.assertEqual(like.txt, 'like')
        Word.like = like
        rating = system.like(system, 'loving itself', 100)
        print(rating.description())
        self.assertEqual(Number(100), rating.num)
        self.assertEqual('loving itself', rating.txt)

if __name__ == '__main__':
    import unittest
    unittest.main()
