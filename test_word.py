"""
Testing qiki word.py
"""

from __future__ import print_function
import unittest
import os
import types
from number import Number
from word import Word

LET_DATABASE_RECORDS_REMAIN = True


class WordTestCase(unittest.TestCase):

    def setUp(self):
        self.system = Word.system(
            service= os.environ['DATABASE_SERVICE'],
            host=    os.environ['DATABASE_HOST'],
            port=    os.environ['DATABASE_PORT'],
            user=    os.environ['DATABASE_USER'],
            password=os.environ['DATABASE_PASSWORD'],
            database=os.environ['DATABASE_DATABASE'],
            table=   os.environ['DATABASE_TABLE'],
        )
        self.system.install_from_scratch()

    def tearDown(self):
        if not LET_DATABASE_RECORDS_REMAIN:
            self.system.uninstall_to_scratch()
        self.system.disconnect()

    def test_00_number(self):
        n = Number(1)
        self.assertEqual(1, int(n))

    def test_01_system(self):
        self.assertTrue(self.system.is_system())
        self.assertEqual('system', self.system.txt)

    def test_02_noun(self):
        noun = self.system('noun')
        self.assertTrue(noun.exists)
        self.assertTrue(noun.is_noun())
        self.assertEqual('noun', noun.txt)

    def test_03_noun_spawn(self):
        noun = self.system('noun')
        thing = noun('thing')
        self.assertTrue(thing.exists)
        self.assertEqual('thing', thing.txt)

    def test_03b_noun_spawn_crazy_syntax(self):
        thing = self.system('noun')('thing')
        self.assertTrue(thing.exists)
        self.assertEqual('thing', thing.txt)

    def test_04_is_a(self):
        noun = self.system('noun')
        thing = noun('thing')
        cosa = thing('cosa')
        self.assertTrue(noun.is_a(noun))
        self.assertTrue(thing.is_a(noun))
        self.assertTrue(cosa.is_a(noun))

    def test_05_noun_grandchild(self):
        agent = self.system('agent')
        human = agent('human')
        self.assertEqual('human', human.txt)

    def test_06_noun_great_grandchild(self):
        noun = self.system('noun')
        self.assertTrue(noun.is_noun())

        child = noun('child')
        self.assertFalse(child.is_noun())
        self.assertTrue( child.spawn(child.obj).is_noun())

        grandchild = child('grandchild')
        self.assertFalse(grandchild.is_noun())
        self.assertFalse(grandchild.spawn(grandchild.obj).is_noun())
        self.assertTrue( grandchild.spawn(grandchild.spawn(grandchild.obj).obj).is_noun())

        greatgrandchild = grandchild('greatgrandchild')
        self.assertFalse(greatgrandchild.is_noun())
        self.assertFalse(greatgrandchild.spawn(greatgrandchild.obj).is_noun())
        self.assertFalse(greatgrandchild.spawn(greatgrandchild.spawn(greatgrandchild.obj).obj).is_noun())
        self.assertTrue( greatgrandchild.spawn(greatgrandchild.spawn(greatgrandchild.spawn(greatgrandchild.obj).obj).obj).is_noun())
        self.assertEqual('greatgrandchild', greatgrandchild.txt)

    ########## Internals ##########

    def test_00_number_from_mysql(self):
        mysql_42 = bytearray(b'\x82\x2A')
        num_42 = Number(42)
        self.assertEqual(num_42, Word.number_from_mysql(mysql_42))



    if False:
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
            self.assertEqual(like.obj, verb.id)
            Word.make_verb_a_method(like)
            rating = system.like(system, system, 'loving itself', Number(100))
            print(rating.description())
            self.assertEqual(Number(100), rating.num)
            self.assertEqual('loving itself', rating.txt)

        def someday_test_zz3_define_verb_slimmer(self):
            Word.noun('human')
            Word.verb('like')
            anna = Word.human('Anna')
            bart = Word.human('Bart')
            chet = Word.human('Chet')
            anna_likes_bart = anna.like(bart, "He's just so dreamy.", Number(10))
            anna_likes_chet = anna.like(chet, "He's alright I guess.", Number(9))


if __name__ == '__main__':
    import unittest
    unittest.main()
