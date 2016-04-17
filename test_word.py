# coding=utf-8
"""
Testing qiki word.py
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import operator
import sys
import time
import unicodedata
import unittest
import uuid

import six

import qiki
from number import hex_from_string
from word import idn_from_word_or_number   # , to_kwargs, ToKwargsException

try:
    import secure.credentials
except ImportError:
    secure = None
    print("""
        Example secure/credentials.py

            for_unit_testing_database = dict(
                language='MySQL',
                host=    'localhost',
                port=    8000,
                user=    'user',
                password='password',
                database='database',
                table=   'word',
            )

        You also need an empty secure/__init__.py
        Why?  See http://stackoverflow.com/questions/10863268/how-is-an-empty-init-py-file-correct

        In MySQL you only need to create the database:  (LexMySQL will create the table.)

            CREATE DATABASE `database`;
            GRANT CREATE, INSERT, SELECT ON `database`.* TO 'user'@'localhost' IDENTIFIED BY 'password';
    """)
    sys.exit(1)


LET_DATABASE_RECORDS_REMAIN = False   # Each run always starts the test database over from scratch.
                                      # Set this to True to manually examine the database after running it.
                                      # If True, you may want to make RANDOMIZE_DATABASE_TABLE False.
TEST_ASTRAL_PLANE = True   # Test txt with Unicode characters on an astral-plane (beyond the base 64K)
SHOW_UTF8_EXAMPLES = False   # Prints a few unicode test strings in both \u escape syntax and UTF-8 hexadecimal.
                             # e.g.  "\u262e on earth" in utf8 is E298AE206F6E206561727468
RANDOMIZE_DATABASE_TABLE = True   # True supports concurrent unit test runs.
                                  # If LET_DATABASE_RECORDS_REMAIN is also True, tables will accumulate.


# For some reason, PyCharm got stupid about which secure.credentials were active when unit testing,
# while a project was loaded with another secure.credentials.  Hence the following noinspection.
# The correct package imports when run however.
# noinspection PyUnresolvedReferences
class SafeNameTests(unittest.TestCase):
    def test_table_name_at_creation_good(self):
        credentials = secure.credentials.for_unit_testing_database.copy()

        def good_table_name(name):
            credentials['table'] = name
            lex = qiki.LexMySQL(**credentials)
            self.assertEqual('verb', lex['define'].obj.txt)
            lex.uninstall_to_scratch()
            lex.disconnect()

        good_table_name('word_with_no_funny_business')
        good_table_name('word')
        good_table_name('w')

    def test_table_name_at_creation_bad(self):
        credentials = secure.credentials.for_unit_testing_database.copy()

        def bad_table_name(name):
            credentials['table'] = name
            with self.assertRaises(qiki.LexMySQL.IllegalTableName):
                qiki.LexMySQL(**credentials)

        bad_table_name('')
        bad_table_name('word_with_backtick_`_oops')
        bad_table_name('word_with_single_quote_\'_oops')
        bad_table_name('word_with_double_quote_\"_oops')
        bad_table_name('word_ending_in_backslash_oops_\\')
        bad_table_name('word with spaces oops')

    def test_engine_name_good(self):
        credentials = secure.credentials.for_unit_testing_database.copy()

        def good_engine_name(name):
            credentials['engine'] = name
            lex = qiki.LexMySQL(**credentials)
            self.assertEqual('verb', lex['define'].obj.txt)
            lex.uninstall_to_scratch()
            lex.disconnect()

        good_engine_name('MEMORY')
        good_engine_name('InnoDB')

    def test_engine_name_bad(self):
        credentials = secure.credentials.for_unit_testing_database.copy()

        def bad_engine_name(name):
            credentials['table'] = 'word_for_engine_name_test'
            credentials['engine'] = name
            with self.assertRaises(qiki.LexMySQL.IllegalEngineName):
                qiki.LexMySQL(**credentials)

        bad_engine_name('MEMORY_oops_\'')
        bad_engine_name('MEMORY_oops_\"')
        bad_engine_name('MEMORY_oops_`')
        bad_engine_name('MEMORY_oops_\\')
        bad_engine_name('MEMORY oops')

    def test_engine_name_bad_explicit_install(self):
        credentials = secure.credentials.for_unit_testing_database.copy()

        def bad_engine_name(name):
            credentials['table'] = 'word_for_engine_name_test_explicit_install'
            lex = qiki.LexMySQL(**credentials)
            lex.uninstall_to_scratch()
            lex._engine = name
            with self.assertRaises(qiki.LexMySQL.IllegalEngineName):
                lex.install_from_scratch()
            lex.disconnect()

        bad_engine_name('MEMORY_backtick_`_oops')
        bad_engine_name('MEMORY_quote_\'_oops')
        bad_engine_name('MEMORY_quote_\"_oops')

    def test_table_name_later_bad(self):
        credentials = secure.credentials.for_unit_testing_database.copy()
        credentials['table'] = 'innocent_table_name_to_start_with'
        lex = qiki.LexMySQL(**credentials)
        self.assertEqual('verb', lex['define'].obj.txt)

        lex._table = 'evil_table_name_later_`\'_\"_oops_\\"'
        with self.assertRaises(qiki.LexMySQL.IllegalTableName):
            self.assertEqual('verb', lex['define'].obj.txt)
        lex._table = 'innocent_table_name_to_start_with'
        lex.uninstall_to_scratch()
        lex.disconnect()


# noinspection PyUnresolvedReferences
class LexErrorTests(unittest.TestCase):
    """Try to generate common errors with instatiating a Lex."""

    def test_bad_password(self):
        """
        Example of the entire bad-password exception message:

        1045 (28000): Access denied for user 'unittest'@'localhost' (using password: YES)
        """
        credentials = secure.credentials.for_unit_testing_database.copy()
        credentials['password'] = 'wrong'
        with self.assertRaisesRegexp(qiki.Lex.ConnectError, r'Access denied'):
            qiki.LexMySQL(**credentials)

    def test_two_lex(self):
        lex1 = qiki.LexMySQL(**secure.credentials.for_unit_testing_database)
        max_start = lex1.max_idn()
        lex1.define(lex1.noun(), u'borg')
        self.assertEqual(max_start+1, lex1.max_idn())
        lex2 = qiki.LexMySQL(**secure.credentials.for_unit_testing_database)
        self.assertEqual(max_start+1, lex2.max_idn())

        # lex2.uninstall_to_scratch()   # WHy does this cause infinite hang?
        lex2.disconnect()
        lex1.uninstall_to_scratch()
        lex1.disconnect()

    def test_connection_neglect(self):
        """Test automatic reconnection of the Lex."""
        lex = qiki.LexMySQL(**secure.credentials.for_unit_testing_database)
        self.assertEqual(1, lex.noun(u'noun').num)
        lex._simulate_connection_neglect()
        self.assertEqual(1, lex.noun(u'noun').num)
        lex.disconnect()


# noinspection PyUnresolvedReferences
class WordTests(unittest.TestCase):

    def setUp(self):
        credentials = secure.credentials.for_unit_testing_database.copy()
        if RANDOMIZE_DATABASE_TABLE:
            credentials['table'] = 'word_' + uuid.uuid4().hex
        self.lex = qiki.LexMySQL(**credentials)
        if LET_DATABASE_RECORDS_REMAIN:
            self.lex.uninstall_to_scratch()
            self.lex.install_from_scratch()
            # Delete and insert all records for a fresh start.

    def tearDown(self):
        if not LET_DATABASE_RECORDS_REMAIN:
            self.lex.uninstall_to_scratch()
        self.lex.disconnect()

    def display_all_word_descriptions(self):
        histogram = {}
        def count(i):
            try:
                histogram[i] += 1
            except KeyError:
                histogram[i] = 1

        words = self.lex.find_words()
        for word in words:
            count(word.sbj)
            count(word.vrb)
            count(word.obj)
            print(int(word.idn), word.description())

        histogram_high_to_low = sorted(histogram.items(), key=operator.itemgetter(1), reverse=True)
        # THANKS:  Sorting a dictionary by value, http://stackoverflow.com/a/2258273/673991

        print()
        for idn, quantity in histogram_high_to_low:
            print(quantity, unicodedata.lookup('dot operator'), repr(self.lex[idn]))

    def show_txt_in_utf8(self, idn):
        word = self.lex[idn]
        utf8 = word.txt.encode('utf-8')
        # FIXME:  This will double encode in Python 2
        hexadecimal = hex_from_string(utf8)
        print("\"{txt}\" in utf8 is {hex}".format(
            txt=word.txt.encode('unicode_escape'),   # Python 3 doubles up the backslashes ... shrug.
            hex=hexadecimal,
        ))

    def assertSensibleWhen(self, whn):
        self.assertIsNotNone(whn)
        self.assertGreaterEqual(time.time(), float(whn))
        self.assertLessEqual(1447029882.792, float(whn))

    class _CheckNewWordCount(object):
        """Expect the creation of a specific number of words."""
        def __init__(self, lex, expected_new_words, message=None):
            self.lex = lex
            self.expected_new_words = expected_new_words
            self.message = message

        def __enter__(self):
            self.word_count_before = self.lex.max_idn()

        # noinspection PyUnusedLocal
        def __exit__(self, exc_type, exc_val, exc_tb):
            word_count_after = self.lex.max_idn()
            actual_new_words = int(word_count_after - self.word_count_before)
            if actual_new_words != self.expected_new_words and exc_type is None:
                stock_message = "Expected {expected} new words, actually there were {actual}.".format(
                    expected=self.expected_new_words,
                    actual=actual_new_words,
                )
                if self.message is None:
                    use_message = stock_message
                else:
                    use_message = stock_message + "\n" + self.message
                raise self.WordCountFailure(use_message)

        class WordCountFailure(unittest.TestCase.failureException):
            pass

    def assertNewWords(self, expected_new_words, message=None):
        """Expect n words to be created.

        with self.assertNewWords(2):
            do_something_that_should_create_exactly_2_new_words()

        """
        return self._CheckNewWordCount(self.lex, expected_new_words, message)

    def assertNoNewWord(self, message=None):
        return self.assertNewWords(0, message)

    def assertNewWord(self, message=None):
        return self.assertNewWords(1, message)

    def assertTripleEqual(self, first, second):
        """Same value and same type."""
        self.assertEqual(first, second)
        self.assertIs(type(first), type(second))

    def assertExactlyFalse(self, falsie):
        self.assertTripleEqual(False, falsie)

    def fails(self):
        return self.assertRaises(AssertionError)


class WordDemoTests(WordTests):

    # noinspection PyUnusedLocal
    def test_syntaxes(self):
        lex = self.lex
        s = lex.define(u'agent', u's')
        v = lex.define(u'verb', u'v')
        o = self.lex.define(u'noun', u'o')
        t = u'some text'
        n = qiki.Number(42)

        # Deleters
        s(v)[o] = 0
        s.says(v,o,0)

        # Setters
        s(v)[o] = n,t
        s(v)[o] = t,n
        s(v)[o] = t
        s(v)[o] = n
        s(v)[o] = 1
        # s(v) = o,n,t
        # s = v,o,n,t
        # lex[s] = v,o,n,t
        # lex[s][v] = o,n,t
        lex[s](v)[o] = n,t
        lex[s](v)[o] = t,n
        lex[s](v)[o] = n
        lex[s](v)[o] = t
        lex[s](v)[o] = 1
        s.says(vrb=v, obj=o, num=n, txt=t)
        s.says(v, o, n, t)
        s.says(v, o, t, n)
        s.says(v, o, n)
        s.says(v, o, t)
        s.says(v, o)
        # s.v(o, n)
        # s.v(o, n, t)
        # s.v(o, num=n)

        # Definers
        # s(define)[o] &= t ???
        s(u'define')[o] = t
        s.define(o, t)

        # Getters
        w = lex[s](v)[o]
        w = s(v)[o]
        w = s.said(v, o)

        # Setter if it does not exist already.  Getter only if it does.
        # w = lex[s](v, n, t)[o]
        # w = lex[s](v, num=n, txt=t)[o]
        # w = lex[s](v).setdefault(o, n, t)
        # w = s(v).setdefault(o, n, t)
        # w = s(v)[o].setdefault(n, t)
        # w = s(v, n)[o].setdefault(t)
        # w = s(v, t)[o].setdefault(n)
        # w = s(v)[o].append(n, t)
        # s(v)[o] |= 1 ???
        s(v, use_already=True)[o] = 1;  w = s(v)[o]
        s(v, use_already=True)[o] = n,t;  w = s(v)[o]
        w = s.says(v, o, n, t, use_already=True)
        w = s.says(v, o, use_already=True)
        # w = s.v(o, n, use_already=True)
        # w = s.v(o, n, t, use_already=True)

        # Set and get the object.
        s(v)[o] = n,t; w = s(v)[o]
        w = s.says(v, o, n, t)

        # Delta if it exists already.  Setter if it does not.
        # s(v)[o] += n
        # s(v, num_add=n)[o]
        s.says(v, o, num_add=n)
        # s.v(o, num_add=n)


class WordExoticTests(WordTests):

    def test_square_circle_square(self):
        subject_ = self.lex.define(u'agent', u'subject_')
        verb_    = self.lex.verb(u'verb_')
        object_  = self.lex.noun(u'object_')
        with self.assertNewWord():

            # DONE:  w = subject_.says(vrb=verb_, obj=object_, num=42, txt=u"courage")

            # GONE:  w = subject_.verb_(object_, 42, u"courage")

            subject_(verb_)[object_] = 42, u"courage"
            w = subject_(verb_)[object_]

            # TODO:  self.lex[subject_](verb_, num=42, txt=u"courage")[object_]
            # TODO:  w = self.lex[subject_](verb)[object_]

        self.assertEqual(u'subject_', w.sbj.txt)
        self.assertEqual(u'verb_',    w.vrb.txt)
        self.assertEqual(u'object_',  w.obj.txt)
        self.assertEqual(u'object_',  w.obj.txt)
        self.assertEqual(42,          w.num)
        self.assertEqual(u'courage',  w.txt)


class InternalTestWordTests(WordTests):
    """Test the WordTests class itself."""

    def test_assertNoNewWord(self):
        with self.assertNoNewWord():
            pass
        with self.assertRaises(self._CheckNewWordCount.WordCountFailure):
            with self.assertNoNewWord():
                self._make_one_new_word(u'shrubbery')

    def test_assertNewWords(self):
        with self.assertNewWords(1):
            self._make_one_new_word(u'shrubbery')
        with self.assertRaises(self._CheckNewWordCount.WordCountFailure):
            with self.assertNewWords(1):
                pass

    def test_assertNewWord(self):
        with self.assertNewWord():   # Succeeds if just the right number of words are created.
            self._make_one_new_word(u'shrubbery')
        with self.assertNewWords(2):
            self._make_one_new_word(u'swallow')
            self._make_one_new_word(u'gopher')
        with self.assertRaises(self._CheckNewWordCount.WordCountFailure):
            with self.assertNewWord():   # Fails if too few.
                pass
        with self.assertRaises(self._CheckNewWordCount.WordCountFailure):
            with self.assertNewWord():   # Fails if too many.
                self._make_one_new_word(u'knight')
                self._make_one_new_word(u'rabbit')

    def _make_one_new_word(self, txt):
        self.lex.define(self.lex[u'noun'], txt)

    def test_missing_from_lex_number(self):
        bogus_word = self.lex[qiki.Number(-42)]
        self.assertFalse(bogus_word.exists())

    def test_missing_from_lex_name(self):
        bogus_word = self.lex['bogus nonexistent name']
        self.assertFalse(bogus_word.exists())
        legit_word = self.lex[qiki.Lex._IDN_DEFINE]   # Lex[idn] is good
        self.assertTrue(legit_word.exists())
        bogus_word = self.lex[qiki.Lex._IDN_DEFINE.qstring()]   # Lex[idn.qstring()] is bad
        self.assertFalse(bogus_word.exists())

    def test_assert_triple_equal(self):
        self.assertTripleEqual(4, 2+2)
        with self.fails(): self.assertTripleEqual(5, 2+2)
        with self.fails(): self.assertTripleEqual('4', 2+2)

        self.assertTripleEqual(b'string', b'string')
        self.assertTripleEqual(u'string', u'string')
        with self.fails(): self.assertTripleEqual(b'string', u'string')
        with self.fails(): self.assertTripleEqual(u'string', b'string')

        with self.fails(): self.assertTripleEqual(six.binary_type(b'string)'), u'string')
        with self.fails(): self.assertTripleEqual(          bytes(b'string)'), u'string')
        with self.fails(): self.assertTripleEqual(      bytearray(b'string)'), u'string')

        with self.fails(): self.assertTripleEqual(six.binary_type(b'string)'), b'string')
        with self.fails(): self.assertTripleEqual(          bytes(b'string)'), b'string')
        with self.fails(): self.assertTripleEqual(      bytearray(b'string)'), b'string')

    def test_assert_exactly_false(self):
        self.assertExactlyFalse(False)
        with self.fails(): self.assertExactlyFalse(True)
        with self.fails(): self.assertExactlyFalse(None)
        with self.fails(): self.assertExactlyFalse(0)
        with self.fails(): self.assertExactlyFalse(())
        with self.fails(): self.assertExactlyFalse([])
        with self.fails(): self.assertExactlyFalse({})
        with self.fails(): self.assertExactlyFalse('')


class Word001aFirstTests(WordTests):

    def test_00_number(self):
        n = qiki.Number(1)
        self.assertEqual(1, int(n))

    def test_01a_lex(self):
        self.assertEqual(self.lex._IDN_LEX,   self.lex.idn)
        self.assertEqual(self.lex,            self.lex.sbj)
        self.assertEqual(self.lex[u'define'], self.lex.vrb)
        self.assertEqual(self.lex[u'agent'],  self.lex.obj)
        self.assertEqual(qiki.Number(1),      self.lex.num)
        self.assertEqual(u'lex',              self.lex.txt)
        self.assertSensibleWhen(              self.lex.whn)
        self.assertTrue(self.lex.is_lex())

    def test_01b_lex_getter(self):
        define = self.lex[u'define']
        self.assertTrue(define.exists())
        self.assertEqual(define.idn,     qiki.Word._IDN_DEFINE)
        self.assertEqual(define.sbj.idn, qiki.Word._IDN_LEX)
        self.assertEqual(define.vrb.idn, qiki.Word._IDN_DEFINE)
        self.assertEqual(define.obj.idn, qiki.Word._IDN_VERB)
        self.assertEqual(define.num,     qiki.Number(1))
        self.assertEqual(define.txt,     u'define')

    def test_01c_lex_bum_getter(self):
        nonword = self.lex[u'word that does not exist']
        self.assertFalse(nonword.exists())
        self.assertTrue(nonword.idn.is_nan())
        self.assertIsNone(nonword.sbj)
        self.assertIsNone(nonword.vrb)
        self.assertIsNone(nonword.obj)
        self.assertIsNone(nonword.num)
        self.assertIsNone(nonword.whn)
        self.assertEqual(nonword.txt, u'word that does not exist')

    def test_02_noun(self):
        noun = self.lex[u'noun']
        self.assertTrue(noun.exists())
        self.assertTrue(noun.is_noun())
        self.assertEqual(u'noun', noun.txt)

    def test_02a_str(self):
        if six.PY2:
            self.assertTripleEqual(b'noun', str(self.lex[u'noun']))
        if six.PY3:
            self.assertTripleEqual(u'noun', str(self.lex[u'noun']))

    def test_02b_unicode(self):
        self.assertTripleEqual(u'noun', six.text_type(self.lex[u'noun']))

    def test_02c_repr(self):
        self.assertEqual(u"Word(u'noun')", repr(self.lex[u'noun']))

    def test_03a_max_idn_fixed(self):
        self.assertEqual(qiki.Word._IDN_MAX_FIXED, self.lex.max_idn())

    def test_03b_max_idn(self):
        self.assertEqual(qiki.Word._IDN_MAX_FIXED, self.lex.max_idn())
        self.lex.verb(u'splurge')
        self.assertEqual(qiki.Word._IDN_MAX_FIXED + 1, self.lex.max_idn())

    def test_03c_noun_spawn(self):
        noun = self.lex[u'noun']
        # thing = noun(u'thing')
        # thing = self.lex(noun, u'thing')
        thing = self.lex.define(noun, u'thing')
        self.assertTrue(thing.exists())
        self.assertEqual(u'thing', thing.txt)

    def test_03d_noun_spawn_crazy_syntax(self):
        # thing = self.lex(u'noun')(u'thing')
        thing = self.lex.define(u'noun', u'thing')
        self.assertTrue(thing.exists())
        self.assertEqual(u'thing', thing.txt)

    def test_04_is_a(self):
        verb = self.lex[u'verb']
        noun = self.lex[u'noun']
        thing = self.lex.define(noun, u'thing')
        cosa = self.lex.define(thing, u'cosa')

        self.assertTrue(verb.is_a(noun))
        self.assertTrue(noun.is_a(noun))
        self.assertTrue(thing.is_a(noun))
        self.assertTrue(cosa.is_a(noun))

        self.assertFalse(verb.is_a(thing))
        self.assertFalse(noun.is_a(thing))
        self.assertTrue(thing.is_a(thing))
        self.assertTrue(thing.is_a(thing, reflexive=True))
        self.assertFalse(thing.is_a(thing, reflexive=False))
        self.assertTrue(cosa.is_a(thing))

        self.assertFalse(verb.is_a(cosa))
        self.assertFalse(noun.is_a(cosa))
        self.assertFalse(thing.is_a(cosa))
        self.assertTrue(cosa.is_a(cosa))

        self.assertTrue(verb.is_a(verb))
        self.assertFalse(noun.is_a(verb))
        self.assertFalse(thing.is_a(verb))
        self.assertFalse(cosa.is_a(verb))

    def test_04_is_a_recursion(self):
        noun = self.lex[u'noun']
        self.assertTrue(noun.is_a_noun(recursion=0))
        self.assertTrue(noun.is_a_noun(recursion=1))
        self.assertTrue(noun.is_a_noun(recursion=2))
        self.assertTrue(noun.is_a_noun(recursion=3))

        child1 = self.lex.define(noun, u'child1')
        self.assertFalse(child1.is_a_noun(recursion=0))
        self.assertTrue(child1.is_a_noun(recursion=1))
        self.assertTrue(child1.is_a_noun(recursion=2))
        self.assertTrue(child1.is_a_noun(recursion=3))

        child2 = self.lex.define(child1, u'child2')
        self.assertFalse(child2.is_a_noun(recursion=0))
        self.assertFalse(child2.is_a_noun(recursion=1))
        self.assertTrue(child2.is_a_noun(recursion=2))
        self.assertTrue(child2.is_a_noun(recursion=3))

        # child12 = child2(u'child3')(u'child4')(u'child5')(u'child6')(u'child7')(u'child8')(u'child9')(u'child10')(u'child11')(u'child12')
        # self.assertFalse(child12.is_a_noun(recursion=10))
        # self.assertFalse(child12.is_a_noun(recursion=11))
        # self.assertTrue(child12.is_a_noun(recursion=12))
        # self.assertTrue(child12.is_a_noun(recursion=13))

    def test_04_is_a_noun(self):
        self.assertTrue(self.lex.is_a_noun())
        self.assertTrue(self.lex[u'lex'].is_a_noun())
        self.assertTrue(self.lex[u'agent'].is_a_noun())
        self.assertTrue(self.lex[u'noun'].is_a_noun(reflexive=True))
        self.assertTrue(self.lex[u'noun'].is_a_noun(reflexive=False))   # noun is explicitly defined as a noun
        self.assertTrue(self.lex[u'noun'].is_a_noun())
        self.assertTrue(self.lex[u'verb'].is_a_noun())
        self.assertTrue(self.lex[u'define'].is_a_noun())

    def test_05_noun_grandchild(self):
        agent = self.lex[u'agent']
        human = self.lex.define(agent, u'human')
        self.assertEqual(u'human', human.txt)

    def test_06_noun_great_grandchild(self):
        noun = self.lex[u'noun']
        self.assertTrue(noun.is_noun())

        child = self.lex.define(noun, u'child')
        self.assertFalse(child.is_noun())
        self.assertTrue(child.obj.is_noun())

        grandchild = self.lex.define(child, u'grandchild')
        self.assertFalse(grandchild.is_noun())
        self.assertFalse(grandchild.obj.is_noun())
        self.assertTrue(grandchild.obj.obj.is_noun())

        greatgrandchild = self.lex.define(grandchild, u'greatgrandchild')
        self.assertFalse(greatgrandchild.is_noun())
        self.assertFalse(greatgrandchild.obj.is_noun())
        self.assertFalse(greatgrandchild.obj.obj.is_noun())
        self.assertTrue(greatgrandchild.obj.obj.obj.is_noun())
        self.assertEqual(u'greatgrandchild', greatgrandchild.txt)

    # def test_07_noun_great_great_grandchild(self):
    #     greatgrandchild = self.lex(u'noun')(u'child')(u'grandchild')(u'greatgrandchild')
    #     greatgreatgrandchild = greatgrandchild(u'greatgreatgrandchild')
    #     self.assertEqual(u'greatgreatgrandchild', greatgreatgrandchild.txt)

    def test_07_is_a_noun_great_great_grandchild(self):
        noun = self.lex[u'noun']
        child = self.lex.define(noun, u'child')
        grandchild = self.lex.define(child, u'grandchild')
        greatgrandchild = self.lex.define(grandchild, u'greatgrandchild')
        greatgreatgrandchild =self.lex.define(greatgrandchild, u'greatgreatgrandchild')
        self.assertTrue(noun.is_a_noun())
        self.assertTrue(child.is_a_noun())
        self.assertTrue(grandchild.is_a_noun())
        self.assertTrue(greatgrandchild.is_a_noun())
        self.assertTrue(greatgreatgrandchild.is_a_noun())

    def test_08_noun_twice(self):
        noun = self.lex[u'noun']
        with self.assertNewWord():
            thing1 = self.lex.define(noun, u'thing')
        with self.assertNoNewWord():
            thing2 = self.lex.define(noun, u'thing')
        self.assertEqual(thing1.idn, thing2.idn)

    def test_09a_equality(self):
        self.assertEqual(self.lex.noun, self.lex.noun)
        self.assertNotEqual(self.lex.noun, self.lex.verb)
        self.assertNotEqual(self.lex.verb, self.lex.noun)
        self.assertEqual(self.lex.verb, self.lex.verb)

    def test_09a_equality_by_attribute(self):
        noun1 = self.lex.noun
        noun2 = self.lex.noun
        self.assertEqual(noun1, noun2)
        self.assertIsNot(noun1, noun2)

    def test_09a_equality_by_call(self):
        noun1 = self.lex[u'noun']
        noun2 = self.lex[u'noun']
        self.assertEqual(noun1, noun2)
        self.assertIsNot(noun1, noun2)

    def test_09a_equality_by_copy_constructor(self):
        noun1 = self.lex[u'noun']
        noun2 = qiki.Word(noun1)
        self.assertEqual(noun1, noun2)
        self.assertTrue(noun1 == noun2)
        self.assertFalse(noun1 != noun2)   # Exercises Word.__ne__()!

    def test_09b_copy_constructor_not_clone_constructor(self):
        noun1 = self.lex[u'noun']
        noun2 = qiki.Word(noun1)
        self.assertIsNot(noun1, noun2)   # Must not copy by reference.

    def test_09c_lex_singleton_by_attribute(self):
        lex1 = self.lex
        lex2 = self.lex.lex
        self.assertEqual(lex1, lex2)
        self.assertIs(lex1, lex2)

    def test_09d_lex_singleton_by_call(self):
        lex1 = self.lex
        lex2 = self.lex[u'lex']
        self.assertEqual(lex1, lex2)
        self.assertIs(lex1, lex2)   # Why does this work?

    def test_09e_idn_constructor_does_not_enforce_lex_singleton(self):
        lex_by_idn = self.lex.spawn(self.lex.idn)
        self.assertEqual(lex_by_idn, self.lex)
        self.assertIsNot(lex_by_idn, self.lex)

    def test_09f_word_copy_constructor_does_not_enforce_lex_singleton(self):
        lex_by_word = self.lex.spawn(self.lex)
        self.assertEqual(lex_by_word, self.lex)
        self.assertIsNot(lex_by_word, self.lex)

    def test_09g_word_constructor_bogus_type(self):
        class BogusType:
            def __init__(self):
                pass
        bogus_instance = BogusType()
        with self.assertRaisesRegexp(TypeError, '^((?!unicode).)*$'):
            # THANKS:  For negative regex, http://stackoverflow.com/a/406408/673991
            qiki.Word(bogus_instance)
        class BogusNewType(object):
            def __init__(self):
                pass
        bogus_new_instance = BogusNewType()
        with self.assertRaisesRegexp(TypeError, '^((?!unicode).)*$'):
            qiki.Word(bogus_new_instance)

    def test_09h_word_constructor_by_name_must_be_unicode(self):
        with self.assertRaisesRegexp(TypeError, "unicode"):
            qiki.Word(b'this is not unicode')
        with self.assertRaisesRegexp(TypeError, "unicode"):
            qiki.Word(bytearray(b'this is not unicode'))
        with self.assertRaisesRegexp(TypeError, "unicode"):
            qiki.Word(bytes(b'this is not unicode'))
        w = qiki.Word(u'this is unicode', lex=self.lex)
        self.assertFalse(w.exists())

    # TODO:  Prevent cloning lex?
    # def test_09x_lex_singleton_cant_do_by_copy_constructor(self):
    #     with self.assertRaises(ValueError):
    #         qiki.Word(self.lex)

    def test_10a_word_by_lex_idn(self):
        agent = self.lex[qiki.Word._IDN_AGENT]
        self.assertEqual(agent.txt, u'agent')

    def test_10b_word_by_lex_txt(self):
        agent = self.lex[u'agent']
        self.assertEqual(agent.idn, qiki.Word._IDN_AGENT)

    def test_11a_noun_inserted(self):
        new_word = self.lex.noun(u'something')
        self.assertEqual(self.lex.max_idn(),  new_word.idn)
        self.assertEqual(self.lex,            new_word.sbj)
        self.assertEqual(self.lex[u'define'], new_word.vrb)
        self.assertEqual(self.lex[u'noun'],   new_word.obj)
        self.assertEqual(qiki.Number(1),      new_word.num)
        self.assertEqual(u'something',        new_word.txt)
        self.assertSensibleWhen(              new_word.whn)

    def test_11b_whn(self):
        define = self.lex[u'define']
        new_word = self.lex.noun(u'something')
        self.assertSensibleWhen(define.whn)
        self.assertSensibleWhen(new_word.whn)
        self.assertGreaterEqual(float(new_word.whn), float(define.whn))

    # def test_12a_non_vrb(self):
    #     # anna = self.lex.define(u'agent', u'anna')
    #     anna = self.lex.define(u'agent', u'anna')
    #     like = self.lex.verb(u'like')
    #     self.lex.noun(u'yurt')
    #     zarf = self.lex.noun(u'zarf')
    #     anna.says(vrb=like, obj=zarf, num=1)
    #     self.assertTrue(anna.like.is_a_verb())
    #     self.assertFalse(anna.yurt.is_a_verb())
    #     self.assertEqual(u'yurt', anna.yurt.txt)
    #     with self.assertRaises(TypeError):
    #         anna.yurt(zarf, txt=u'', num=1)
    #         # FIXME:  Can we even come up with a s.v(o) where v is not a verb,
    #         # and something else isn't happening?  This example is at best a highly
    #         # corrupted form of o(t), aka lex.define(o,t).

    def test_13a_text(self):
        txt = qiki.Text(u'simple letters')
        self.assertEqual(u'simple letters', txt)
        self.assertEqual(b'simple letters', txt.utf8())
        self.assertIs(six.binary_type, type(txt.utf8()))

    def test_13b_text_class(self):
        t0 = u"some text"
        t1 = qiki.Text(t0)
        t2 = qiki.Text(t1)
        t3 = qiki.Text(t2)
        self.assertTripleEqual(u"some text", t1.unicode())
        self.assertTripleEqual(b"some text", t1.utf8())
        self.assertTripleEqual(u"some text", t2.unicode())
        self.assertTripleEqual(b"some text", t2.utf8())
        self.assertTripleEqual(u"some text", t3.unicode())
        self.assertTripleEqual(b"some text", t3.utf8())

    def test_13c_text_native(self):
        if six.PY2:
            self.assertTripleEqual(b'string', qiki.Text(u'string').native())
        if six.PY3:
            self.assertTripleEqual(u'string', qiki.Text(u'string').native())

    def test_13c_text_not_unicode(self):
        with self.assertRaises(TypeError):
            qiki.Text(b'string')

    def test_13d_text_decode(self):
        self.assertTripleEqual(qiki.Text(u'string'), qiki.Text.decode_if_you_must(u'string'))
        self.assertTripleEqual(qiki.Text(u'string'), qiki.Text.decode_if_you_must(b'string'))

    # noinspection SpellCheckingInspection
    def test_13e_text_postel(self):
        """Verify the Text class follows Postel's Law -- liberal in, conservative out."""
        def example(the_input, _unicode, _utf8):
            txt = qiki.Text(the_input)
            self.assertTripleEqual(_unicode, txt.unicode())
            self.assertTripleEqual(_utf8, txt.utf8())

        example(b'ascii'.decode('utf-8'), u'ascii', b'ascii')
        example(u'ascii',                 u'ascii', b'ascii')

        example(unicodedata.lookup('latin small letter a with ring above') +
                          u'ring', u'\U000000E5ring', b'\xC3\xA5ring')
        example(         u'åring', u'\U000000E5ring', b'\xC3\xA5ring')
        example(u'\U000000E5ring', u'\U000000E5ring', b'\xC3\xA5ring')
        example(  b'\xC3\xA5ring'.decode('utf-8'),
                                   u'\U000000E5ring', b'\xC3\xA5ring')

        example(unicodedata.lookup('greek small letter mu') +
                          u'icro', u'\U000003BCicro', b'\xCE\xBCicro')
        example(         u'μicro', u'\U000003BCicro', b'\xCE\xBCicro')
        example(u'\U000003BCicro', u'\U000003BCicro', b'\xCE\xBCicro')
        example(  b'\xCE\xBCicro'.decode('utf-8'),
                                   u'\U000003BCicro', b'\xCE\xBCicro')

        example(unicodedata.lookup('tetragram for aggravation') +
                                  u'noid', u'\U0001D351noid', b'\xF0\x9D\x8D\x91noid')
        example(        u'\U0001D351noid', u'\U0001D351noid', b'\xF0\x9D\x8D\x91noid')
        example(  b'\xF0\x9D\x8D\x91noid'.decode('utf-8'),
                                           u'\U0001D351noid', b'\xF0\x9D\x8D\x91noid')

    def test_14a_word_text(self):
        """Verify the txt field follows Postel's Law -- liberal in, conservative out.

        Liberal in:  str, unicode, bytes, bytearray, Text and Python 2 or 3
        Conservative out:  str, which is unicode in Python 3, UTF-8 in Python 2."""
        s = self.lex.noun(u's')
        v = self.lex.verb(u'v')
        o = self.lex.noun(u'o')
        def works_as_txt(txt):
            # word = o(txt)
            # self.assertIs(qiki.Text, type(word.txt))
            # self.assertTripleEqual(qiki.Text(u'apple'), word.txt)

            word = s.define(o, txt)
            self.assertIs(qiki.Text, type(word.txt))
            self.assertTripleEqual(qiki.Text(u'apple'), word.txt)

            word = s.says(vrb=v, obj=o, num=1, txt=txt)
            self.assertIs(qiki.Text, type(word.txt))
            self.assertTripleEqual(qiki.Text(u'apple'), word.txt)

        works_as_txt(b'apple'.decode('utf-8'))
        works_as_txt(bytearray('apple', 'utf-8').decode('utf-8'))
        works_as_txt(u'apple')
        works_as_txt(qiki.Text(b'apple'.decode('utf-8')))
        works_as_txt(qiki.Text(bytearray('apple', 'utf-8').decode('utf-8')))
        works_as_txt(qiki.Text(u'apple'))

    def test_15_word_chain(self):
        define = self.lex[u'define']
        verb = self.lex[u'verb']
        noun = self.lex[u'noun']
        self.assertEqual(self.lex, self.lex.sbj)
        self.assertEqual(self.lex, self.lex.sbj.sbj)
        self.assertEqual(self.lex, self.lex.sbj.sbj.sbj)
        self.assertEqual(self.lex, self.lex.sbj.sbj.sbj.sbj)
        self.assertEqual(self.lex, self.lex.sbj.sbj.sbj.sbj.sbj)
        self.assertEqual(define,   self.lex.sbj.sbj.sbj.sbj.sbj.vrb)
        self.assertEqual(self.lex, self.lex.sbj.sbj.sbj.sbj.sbj.vrb.sbj)
        self.assertEqual(define,   self.lex.sbj.sbj.sbj.sbj.sbj.vrb.sbj.vrb)
        self.assertEqual(verb,     self.lex.sbj.sbj.sbj.sbj.sbj.vrb.sbj.vrb.obj)
        self.assertEqual(noun,     self.lex.sbj.sbj.sbj.sbj.sbj.vrb.sbj.vrb.obj.obj)

    def test_16_django_template_not_callable(self):
        w = self.lex.spawn()
        self.assertTrue(w.do_not_call_in_templates)
        self.assertIs(type(w.do_not_call_in_templates), bool)

    def test_17a_inchoate(self):
        """A word constructed by its idn is inchoate."""
        w = self.lex[qiki.Lex._IDN_DEFINE]
        self.assertTrue(w._is_inchoate, "How can idn define be choate? " + repr(w))

    def test_17b_choate(self):
        """A word that tries to use one of its parts becomes choate."""
        w = self.lex[qiki.Lex._IDN_DEFINE]
        self.assertEqual(self.lex, w.sbj)
        self.assertFalse(w._is_inchoate)

    def test_17c_inchoate_copy_constructor(self):
        """The Word(Word) copy constructor copies the inchoate-ness."""
        w1 = self.lex[qiki.Lex._IDN_DEFINE]
        w2 = self.lex[w1]
        self.assertTrue(w1._is_inchoate)   # Tests the source didn't BECOME choate by copying.
        self.assertTrue(w2._is_inchoate)   # Tests the destination is also inchoate.

    def test_17d_choate_copy_constructor(self):
        """The Word(Word) copy constructor copies the choate-ness."""
        w1 = self.lex[qiki.Lex._IDN_DEFINE]
        # noinspection PyStatementEffect
        w1.sbj
        w2 = self.lex[w1]
        self.assertFalse(w1._is_inchoate)
        self.assertFalse(w2._is_inchoate)

    def test_17e_inchoate_txt(self):
        agent = self.lex[qiki.Lex._IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertEqual(u"agent", agent.txt)
        self.assertFalse(agent._is_inchoate)

    def test_17e_inchoate_str(self):
        agent = self.lex[qiki.Lex._IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertIn(u"agent", str(agent))
        self.assertFalse(agent._is_inchoate)

    def test_17f_inchoate_hasattr(self):
        agent = self.lex[qiki.Lex._IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertTrue(hasattr(agent, 'txt'))
        self.assertFalse(agent._is_inchoate)

    def test_17g_inchoate_idn(self):
        agent = self.lex[qiki.Lex._IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertEqual(qiki.Lex._IDN_AGENT, agent.idn)
        self.assertTrue(agent._is_inchoate)

    def test_17h_inchoate_hash(self):
        agent = self.lex[qiki.Lex._IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertIsInstance(hash(agent), int)
        self.assertTrue(agent._is_inchoate)

    def test_17i_inchoate_hash(self):
        agent1 = self.lex[qiki.Lex._IDN_AGENT]
        agent2 = self.lex[qiki.Lex._IDN_AGENT]
        self.assertTrue(agent1._is_inchoate)
        self.assertTrue(agent2._is_inchoate)
        self.assertTrue(agent1 == agent2)
        self.assertTrue(agent1._is_inchoate)
        self.assertTrue(agent2._is_inchoate)

    def test_17j_inchoate_copy(self):
        agent = self.lex[qiki.Lex._IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertIn(u"agent", agent.txt)
        self.assertFalse(agent._is_inchoate)

        agent2 = agent.inchoate_copy()
        self.assertTrue(agent2._is_inchoate)

        self.assertFalse(agent._is_inchoate)
        self.assertIsNot(agent, agent2)
        self.assertEqual(qiki.Lex._IDN_AGENT, agent.idn)
        self.assertEqual(qiki.Lex._IDN_AGENT, agent2.idn)
        self.assertEqual(agent, agent2)

    def test_17k_inchoate_lex(self):
        agent = self.lex[qiki.Lex._IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertIs(self.lex, agent.lex)
        self.assertTrue(agent._is_inchoate)

    # def test_18_define_with_num(self):
    #     rock3 = self.lex.define(u'noun', u'rock', 3)
    #     self.assertEqual(3, rock3.num)
    #     rock33 = self.lex.define(u'noun', u'rock', 33)
    #     self.assertEqual(33, rock33.num)
    #     rock = self.lex.define(u'noun', u'rock')
    #     self.assertEqual(1, rock.num)
    #     self.display_all_word_descriptions()

    def test_18a_define_duplicate(self):
        noun = self.lex[u'noun']
        define = self.lex[u'define']
        punt1 = self.lex.says(define, noun, txt=u'punt')
        punt2 = self.lex.says(define, noun, txt=u'punt')
        self.assertNotEqual(punt1.idn, punt2.idn)
        punt = self.lex.define(noun, u'punt')
        self.assertEqual(punt.idn, punt1.idn)


    # TODO:  Words as dictionary keys preserve their inchoate-ness.


class Word001bUtilities(WordTests):

    def test_idn_from_word_or_number(self):
        agent = self.lex[u'agent']
        self.assertEqual(qiki.Word._IDN_AGENT, idn_from_word_or_number(agent.idn))
        self.assertEqual(qiki.Word._IDN_AGENT, idn_from_word_or_number(agent))
        with self.assertRaises(TypeError):
            idn_from_word_or_number('')
        with self.assertRaises(TypeError):
            idn_from_word_or_number(0)
        with self.assertRaises(TypeError):
            idn_from_word_or_number(None)

    def test_inequality_words_and_numbers(self):
        """Sanity check to make sure words and idns aren't intrinsically equal or something."""
        word = self.lex[u'agent']
        idn = word.idn
        self.assertEqual(idn, idn)
        self.assertNotEqual(idn, word)
        self.assertNotEqual(word, idn)
        self.assertEqual(word, word)

    def test_words_from_idns(self):
        noun = self.lex[u'noun']
        agent = self.lex[u'agent']
        define = self.lex[u'define']
        self.assertEqual([
            noun,
            agent,
            define
        ], self.lex.words_from_idns([
            noun.idn,
            agent.idn,
            define.idn
        ]))

    def test_raw_values_from_idns(self):
        noun = self.lex[u'noun']
        agent = self.lex[u'agent']
        define = self.lex[u'define']
        self.assertEqual([
            noun.idn.raw,
            agent.idn.raw,
            define.idn.raw,
        ], self.lex.raws_from_idns([
            noun.idn,
            agent.idn,
            define.idn,
        ]))

    # def test_to_kwargs(self):
    #     self.assertEqual(dict(i=42, s='x'), to_kwargs((42, 'x'), dict(), dict(i=[int], s=[str]), dict(i=0, s='')))
    #     self.assertEqual(dict(i=42, s='x'), to_kwargs(('x',), dict(i=42), dict(i=[int], s=[str]), dict(i=0, s='')))
    #     self.assertEqual(dict(i=42, s='x'), to_kwargs((42,), dict(s='x'), dict(i=[int], s=[str]), dict(i=0, s='')))
    #     self.assertEqual(dict(i=42, s='x'), to_kwargs((), dict(i=42, s='x'), dict(i=[int], s=[str]), dict(i=0, s='')))
    #
    # def test_to_kwargs_bad(self):
    #     with self.assertRaises(ToKwargsException):
    #         to_kwargs((), {}, dict(a=[], b=[]), dict(x=None, y=None))
    #
    # def test_to_kwargs_ambiguous(self):
    #     with self.assertRaises(ToKwargsException):
    #         to_kwargs((42,42), dict(), dict(i=[int], s=[str]), dict(i=0, s=''))
    #     with self.assertRaises(ToKwargsException):
    #         to_kwargs((42,), dict(i=42), dict(i=[int], s=[str]), dict(i=0, s=''))
    #     with self.assertRaises(ToKwargsException):
    #         to_kwargs(('x', 'x'), dict(), dict(i=[int], s=[str]), dict(i=0, s=''))
    #     with self.assertRaises(ToKwargsException):
    #         to_kwargs(('x',), dict(s='x'), dict(i=[int], s=[str]), dict(i=0, s=''))


class Word001cBrackets(WordTests):

    def setUp(self):
        super(Word001cBrackets, self).setUp()
        self.art = self.lex.define(u'agent', u'art')
        self.got = self.lex.verb(u'got')
        self.lek = self.lex.noun(u'lek')

    def test_01_subject_says(self):
        with self.assertNewWord():
            word = self.art.says(self.got, self.lek, 236)
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(236, word.num)

    def test_02a_subject_circle_square_num(self):
        with self.assertNewWord():
            self.art(self.got)[self.lek] = 236
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(236, word.num)

    def test_02b_subject_circle_square_txt(self):
        with self.assertNewWord():
            self.art(self.got)[self.lek] = u"turnpike"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(u"turnpike", word.txt)

    def test_02c_subject_circle_square_txt_num(self):
        with self.assertNewWord():
            self.art(self.got)[self.lek] = (u"turnpike", 496)
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(u"turnpike", word.txt)
        self.assertEqual(496, word.num)

    def test_02d_subject_circle_square_num_txt(self):
        with self.assertNewWord():
            self.art(self.got)[self.lek] = 496, u"turnpike"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(u"turnpike", word.txt)
        self.assertEqual(496, word.num)

    def test_02e_subject_circle_square_num_txt_list(self):
        with self.assertNewWord():
            self.art(self.got)[self.lek] = [496, u"turnpike"]
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(u"turnpike", word.txt)
        self.assertEqual(496, word.num)

    def test_03a_subject_circle_bad(self):
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.art(self.got)[self.lek] = some_type

    def test_03b_subject_circle_bad(self):
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.art(self.got)[self.lek] = [some_type]

    def test_04a_lex_square_circle_square_num(self):
        with self.assertNewWord():
            self.lex[self.art](self.got)[self.lek] = 236
            word = self.lex[self.art](self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(236, word.num)
        self.assertEqual(u"", word.txt)

    def test_04b_lex_square_circle_square_num_txt(self):
        with self.assertNewWord():
            self.lex[self.art](self.got)[self.lek] = 236, u"route"
            word = self.lex[self.art](self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(236, word.num)
        self.assertEqual(u"route", word.txt)

    def test_04c_lex_square_circle_square_txt_num(self):
        with self.assertNewWord():
            self.lex[self.art](self.got)[self.lek] = u"route", 236
            word = self.lex[self.art](self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(236, word.num)
        self.assertEqual(u"route", word.txt)

    def test_05a_lex_circle_square_num(self):
        with self.assertNewWord():
            self.lex(self.got)[self.lek] = 1
            word = self.lex(self.got)[self.lek]
        self.assertEqual(self.lex, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(1, word.num)

    def test_05b_lex_circle_square_num_txt(self):
        with self.assertNewWord():
            self.lex(self.got)[self.lek] = 99, u"brief as can be"
            word = self.lex(self.got)[self.lek]
        self.assertEqual(self.lex, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(99, word.num)
        self.assertEqual(u"brief as can be", word.txt)

    def test_06a_subject_circle_text_square(self):
        with self.assertNewWord():
            self.art(u'got')[self.lek] = 2, u"two"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(2, word.num)
        self.assertEqual(u"two", word.txt)

    def test_06b_subject_circle_square_text(self):
        with self.assertNewWord():
            self.art(self.got)[u'lek'] = 2, u"two"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(2, word.num)
        self.assertEqual(u"two", word.txt)

    def test_06c_lex_square_text_circle_square(self):
        with self.assertNewWord():
            self.lex[u'art'](self.got)[self.lek] = 2, u"two"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(2, word.num)
        self.assertEqual(u"two", word.txt)

    def test_06c_lex_square_circle_square_all_text(self):
        with self.assertNewWord():
            self.lex[u'art'](u'got')[u'lek'] = 2, u"two"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(2, word.num)
        self.assertEqual(u"two", word.txt)

    def test_07a_subject_circle_use_already_square(self):
        with self.assertNewWord():
            self.art(self.got)[self.lek] = 2, u"two"
        with self.assertNewWord():
            self.art(self.got)[self.lek] = 2, u"two"
        with self.assertNoNewWord():
            self.art(self.got, use_already=True)[self.lek] = 2, u"two"


class WordUnicode(WordTests):

    def setUp(self):
        super(WordUnicode, self).setUp()
        self.anna =    self.lex.noun(u'anna')
        self.comment = self.lex.verb(u'comment')
        self.zarf =    self.lex.noun(u'zarf')


class WordUnicodeTxt(WordUnicode):
    """Unicode characters in non-definition word descriptions, e.g. comments.

    In each pair of tests, the string may go in as either """

    def test_unicode_b_ascii(self):
        self.assertEqual(u"ascii", self.lex[self.anna.says(self.comment, self.zarf, 1, u"ascii").idn].txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    def test_unicode_d_spanish(self):
        comment = self.anna.says(self.comment, self.zarf, 1, u"mañana")
        self.assertEqual(u"ma\u00F1ana", self.lex[comment.idn].txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    def test_unicode_f_peace(self):
        comment = self.anna.says(self.comment, self.zarf, 1, u"☮ on earth")
        self.assertEqual(u"\u262E on earth", self.lex[comment.idn].txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    if TEST_ASTRAL_PLANE:

        def test_unicode_h_unicode_pile_of_poo(self):
            comment = self.anna.says(self.comment, self.zarf, 1, u"stinky \U0001F4A9")
            self.assertEqual(u"stinky \U0001F4A9", self.lex[comment.idn].txt)
            if SHOW_UTF8_EXAMPLES:
                self.show_txt_in_utf8(self.lex.max_idn())


# noinspection SpellCheckingInspection
class Word002UnicodeVerb(WordUnicode):
    """Unicode characters in verb names."""
    # TODO:  OBSOLETE, verb names are no longer method names

    def test_unicode_j_verb_ascii(self):
        sentence1 = self.lex.define(self.comment, u"remark")
        sentence2 = self.lex[sentence1.idn]
        self.assertEqual(u"remark", sentence2.txt)
        self.assertTrue(self.lex['remark'].is_a_verb())

    def test_unicode_l_verb_spanish(self):
        sentence1 = self.lex.define(self.comment, u"comentó")
        sentence2 = self.lex[sentence1.idn]
        self.assertEqual(u"comentó", sentence2.txt)
        if six.PY2:
            with self.assertRaises(SyntaxError):
                eval(u'self.lex.comentó.is_a_verb()')
        if six.PY3:
            self.assertTrue(eval(u'self.lex["comentó"].is_a_verb()'))
        self.assertTrue(self.lex[u'comentó'].exists())
        self.assertTrue(self.lex[u'comentó'].is_a_verb())

    def test_unicode_n_verb_encourage(self):
        sentence1 = self.lex.define(self.comment, u"enc☺urage")
        sentence2 = self.lex[sentence1.idn]
        self.assertEqual(u"enc☺urage", sentence2.txt)
        with self.assertRaises(SyntaxError):
            eval(u'self.lex.enc☺urage.is_a_verb()')
        self.assertTrue(self.lex[u'enc☺urage'].exists())
        self.assertTrue(self.lex[u'enc☺urage'].is_a_verb())

    if TEST_ASTRAL_PLANE:

        def test_unicode_o_verb_alien_face(self):
            sentence1 = self.lex.define(self.comment, u"\U0001F47Dlienate")
            sentence2 = self.lex[sentence1.idn]
            self.assertEqual(u"\U0001F47Dlienate", sentence2.txt)
            with self.assertRaises(SyntaxError):
                eval(u'self.lex.\U0001F47Dlienate.is_a_verb()')
            self.assertTrue(self.lex[u'\U0001F47Dlienate'].exists())
            self.assertTrue(self.lex[u'\U0001F47Dlienate'].is_a_verb())


class Word003MoreTests(WordTests):

    def test_describe(self):
        thing = self.lex.noun(u'thingamajig')
        self.assertIn(u'thingamajig', thing.description())

    # def test_short_and_long_ways(self):
    #     noun = self.lex[u'noun']
    #     thing1 = noun(u'thing')
    #     thing2 = self.lex.noun(u'thing')
    #     thing3 = self.lex.define(noun, u'thing')
    #     self.assertEqual(thing1.idn,           thing2.idn          )
    #     self.assertEqual(thing1.idn,           thing3.idn          )
    #     self.assertEqual(thing1.description(), thing2.description())
    #     self.assertEqual(thing1.description(), thing3.description())
    #     self.assertEqual(thing1,               thing2              )
    #     self.assertEqual(thing1,               thing3              )
    #
    #     subthing1 = thing1(u'subthing1')
    #     subthing2 = thing2(u'subthing2')
    #     subthing3 = thing3(u'subthing3')
    #     self.assertTrue(subthing1.exists())
    #     self.assertTrue(subthing2.exists())
    #     self.assertTrue(subthing3.exists())
    #     self.assertEqual(u'subthing1', subthing1.txt)
    #     self.assertEqual(u'subthing2', subthing2.txt)
    #     self.assertEqual(u'subthing3', subthing3.txt)

    def test_description_uses_txt(self):
        """Detects word names in a sentence description.

        Detects a bug where Word.description() showed all the parts as their idn.qstring()."""
        description = self.lex[qiki.Lex._IDN_AGENT].description()
        self.assertIn('lex', description)
        self.assertIn('define', description)
        self.assertIn('noun', description)
        self.assertIn('agent', description)

    def test_verb(self):
        self.lex.verb(u'like')
        like = self.lex[u'like']
        self.assertEqual(self.lex, like.sbj)

    def test_is_a_verb(self):
        verb = self.lex[u'verb']
        noun = self.lex[u'noun']
        like = self.lex.verb(u'like')
        yurt = self.lex.noun(u'yurt')
        self.assertTrue(like.is_a_verb())
        self.assertTrue(verb.is_a_verb(reflexive=True))
        self.assertFalse(verb.is_a_verb(reflexive=False))
        self.assertFalse(verb.is_a_verb())
        self.assertFalse(noun.is_a_verb())
        self.assertFalse(yurt.is_a_verb())

        self.assertFalse(self.lex[u'noun'].is_a_verb())
        self.assertFalse(self.lex[u'verb'].is_a_verb())
        self.assertTrue(self.lex[u'define'].is_a_verb())
        self.assertFalse(self.lex[u'agent'].is_a_verb())
        self.assertFalse(self.lex[u'lex'].is_a_verb())

    def test_verb_use(self):
        """Test that sbj.vrb(obj, num) creates a word.  And sbj.vrb(obj).num reads it back."""
        agent = self.lex[u'agent']
        human = self.lex.define(agent, u'human')
        like = self.lex.verb(u'like')
        anna = self.lex.define(human, u'anna')
        bart = self.lex.define(human, u'bart')
        chad = self.lex.define(human, u'chad')
        dirk = self.lex.define(human, u'dirk')
        anna.says(like, anna, 1, u"Narcissism.")
        anna.says(like, bart, 8, u"Okay.")
        anna.says(like, chad, 10)
        anna.says(like, dirk, 1)
        self.assertFalse(like.is_lex())
        self.assertFalse(like.is_verb())
        self.assertEqual(1, anna.said(like, anna).num)
        self.assertEqual(8, anna.said(like, bart).num)
        self.assertEqual(10, anna.said(like, chad).num)
        self.assertEqual(1, anna.said(like, dirk).num)
        self.assertEqual(u"Narcissism.", anna.said(like, anna).txt)
        self.assertEqual(u"Okay.", anna.said(like, bart).txt)
        self.assertEqual(u"", anna.said(like, chad).txt)
        self.assertEqual(u"", anna.said(like, dirk).txt)

    def test_verb_use_alt(self):
        """Test that lex.verb can be copied by assignment, and still work."""
        human = self.lex.define(u'agent', u'human')
        anna = self.lex.define(human, u'anna')
        bart = self.lex.define(human, u'bart')
        verb = self.lex.verb
        like = verb(u'like')
        anna.says(like, bart, 13)
        self.assertEqual(13, anna.said(like, bart).num)

    def test_verb_txt(self):
        """Test s.v(o, n, txt).  Read with s.v(o).txt"""
        human = self.lex.define(u'agent', u'human')
        anna = self.lex.define(human, u'anna')
        bart = self.lex.define(human, u'bart')
        like = self.lex.verb(u'like')
        anna.says(like, bart, 5, u"just as friends")
        self.assertEqual(u"just as friends", anna.said(like, bart).txt)

    def test_verb_overlay(self):
        """Test multiple s.says(v,o,n,t) calls with different num's.
        Reading with s.said(v,o).num should only get the latest value.

        The feature that makes this work is something like 'ORDER BY idn DESC LIMIT 1'
        in Lex.populate_word_from_sbj_vrb_obj() via the 'getter' syntax s.said(v,o)"""
        human = self.lex.define(u'agent', u'human')
        anna = self.lex.define(human, u'anna')
        bart = self.lex.define(human, u'bart')
        like = self.lex.verb(u'like')

        with self.assertNewWord():
            anna.says(like, bart, 8)
        with self.assertNoNewWord():
            anna.said(like, bart)
        self.assertEqual(8, anna.said(like, bart).num)

        with self.assertNewWord():
            anna.says(like, bart, 10)
        self.assertEqual(10, anna.said(like, bart).num)

        with self.assertNewWord():
            anna.says(like, bart, 2)
        self.assertEqual(2, anna.said(like, bart).num)

    def test_verb_overlay_duplicate(self):
        human = self.lex.define(u'agent', u'human')
        anna = self.lex.define(human, u'anna')
        bart =self.lex.define( human, u'bart')
        like = self.lex.verb(u'like')


        # with self.assertNoNewWord("Identical s.v(o,n,t) shouldn't generate a new word."):
        #     anna.says(like, bart, 5, "just as friends")
        # TODO:  Decide whether these "duplicates" should be errors or insert new records or not...
        # TODO:  Probably it should be an error for some verbs (e.g. like) and not for others (e.g. comment)
        # TODO: 'unique' option?  Imbue "like" verb with properties using Words??

        with self.assertNewWord():    anna.says(like, bart, 5, u"just as friends")
        with self.assertNewWord():    anna.says(like, bart, 5, u"maybe more than friends")
        with self.assertNewWord():    anna.says(like, bart, 6, u"maybe more than friends")
        with self.assertNewWord():    anna.says(like, bart, 7, u"maybe more than friends")
        with self.assertNewWord():    anna.says(like, bart, 7, u"maybe more than friends")
        with self.assertNoNewWord():  anna.says(like, bart, 7, u"maybe more than friends", use_already=True)
        self.assertEqual(7, anna.said(like, bart).num)
        with self.assertNewWord():    anna.says(like, bart, 6, u"maybe more than friends")
        self.assertEqual(6, anna.said(like, bart).num)
        with self.assertNewWord():
            anna.says(like, bart, 7, u"maybe more than friends", use_already=True)
            # There was an earlier, identical sentence.
            # But it's not the latest with that s,v,o.   (There's a 6.)
            # So a new sentence should be generated.
            # TODO:  Deal with a diversity of feature contours that might be wanted.
            # (1) What is identical?  Just s,v,o?  Or s,v,o,n,t?
            # (2) What is earlier, simply a lower idn?  How about on other lexes?
        self.assertEqual(7, anna.said(like, bart).num)
        with self.assertNewWord():    anna.says(like, bart, 5, u"just friends")
        self.assertEqual(5, anna.said(like, bart).num)

    def test_is_defined(self):
        self.assertTrue(self.lex[u'noun'].is_defined())
        self.assertTrue(self.lex[u'verb'].is_defined())
        self.assertTrue(self.lex[u'define'].is_defined())
        self.assertTrue(self.lex[u'agent'].is_defined())
        self.assertTrue(self.lex.is_defined())

        human = self.lex.define(u'agent', u'human')
        anna = self.lex.define(human, u'anna')
        bart = self.lex.define(human, u'bart')
        like = self.lex.verb(u'like')
        liking = anna.says(like, bart, 5)

        self.assertTrue(human.is_defined())
        self.assertTrue(anna.is_defined())
        self.assertTrue(bart.is_defined())
        self.assertTrue(like.is_defined())
        self.assertFalse(liking.is_defined())

    # def test_non_verb_undefined_as_function_disallowed(self):
    #     human = self.lex.define(u'agent', u'human')
    #     anna = self.lex.define(human, u'anna')
    #     bart = self.lex.define(human, u'bart')
    #     like = self.lex.verb(u'like')
    #
    #     liking = anna.says(like, bart, 5)
    #     with self.assertRaises(TypeError):
    #         liking(bart)
    #     with self.assertRaises(qiki.Word.NonVerbUndefinedAsFunctionException):
    #         liking(bart)

    def test_lex_is_lex(self):
        """Various ways a lex is a singleton, with it's lex."""
        sys1 = self.lex
        sys2 = self.lex[u'lex']
        sys3 = self.lex[u'lex'][u'lex'][u'lex']
        sys4 = self.lex[u'lex'].lex[u'lex'].lex.lex.lex[u'lex'][u'lex'][u'lex']
        self.assertEqual(sys1.idn, sys2.idn)
        self.assertEqual(sys1.idn, sys3.idn)
        self.assertEqual(sys1.idn, sys4.idn)
        self.assertIs(sys1, sys2)
        self.assertIs(sys1, sys3)
        self.assertIs(sys1, sys4)

    def test_idn_setting_not_allowed(self):
        lex = self.lex[u'lex']
        self.assertEqual(lex.idn, self.lex._IDN_LEX)
        with self.assertRaises(AttributeError):
            lex.idn = 999
        self.assertEqual(lex.idn, self.lex._IDN_LEX)

    def test_idn_suffix(self):
        """Make sure adding a suffix to the lex's idn does not modify lex.idn."""
        lex = self.lex[u'lex']
        self.assertEqual(lex.idn, self.lex._IDN_LEX)
        suffixed_lex_idn = lex.idn.add_suffix(3)
        self.assertEqual(lex.idn, self.lex._IDN_LEX)
        self.assertEqual(suffixed_lex_idn, qiki.Number('0q82_05__030100'))

    # def test_verb_paren_object(self):
    #     """An orphan verb can spawn a sentence.
    #     v = lex[u'name of a verb']; v(o) is equivalent to lex.v(o).
    #     Lex is the implicit subject."""
    #     some_object = self.lex.noun(u'some object')
    #     verb = self.lex[u'verb']
    #     oobleck = verb(u'oobleck')
    #     self.assertTrue(oobleck.is_a_verb())
    #     with self.assertNewWord():
    #         blob = oobleck(some_object, qiki.Number(42), u'new sentence')
    #     self.assertTrue(blob.exists())
    #     self.assertEqual(blob.sbj, self.lex)
    #     self.assertEqual(blob.vrb, oobleck)
    #     self.assertEqual(blob.obj, some_object)
    #     self.assertEqual(blob.num, qiki.Number(42))
    #     self.assertEqual(blob.txt, u"new sentence")

    # def test_verb_paren_object_text_number(self):
    #     """More orphan verb features.  v = lex[...]; v(o,t,n) is also equivalent to lex.v(o,t,n)."""
    #     some_object = self.lex.noun(u'some object')
    #     verb = self.lex[u'verb']
    #     oobleck = verb(u'oobleck')
    #     self.assertTrue(oobleck.is_a_verb())
    #     with self.assertNewWord():
    #         blob = oobleck(some_object, qiki.Number(11), u"blob")
    #     self.assertTrue(blob.exists())
    #     self.assertEqual(blob.obj, some_object)
    #     self.assertEqual(blob.num, qiki.Number(11))
    #     self.assertEqual(blob.txt, u"blob")

    def test_define_object_type_string(self):
        """Specify the object of a definition by its txt."""
        oobleck = self.lex.define(u'verb', u'oobleck')
        self.assertTrue(oobleck.exists())
        self.assertEqual(oobleck.sbj, self.lex)
        self.assertEqual(oobleck.vrb, self.lex[u'define'])
        self.assertEqual(oobleck.obj, self.lex[u'verb'])
        self.assertEqual(oobleck.num, qiki.Number(1))
        self.assertEqual(oobleck.txt, u"oobleck")

    # def test_verb_paren_object_deferred_subject(self):
    #     """A patronized verb can spawn a sentence.
    #     That's a verb such as subject.verb that is generated as if it were an attribute.
    #     x = s.v; x(o) is equivalent to s.v(o).
    #     So a verb word instance can remember its subject for later spawning a new word."""
    #
    #     some_object = self.lex.noun(u'some object')
    #     self.lex.verb(u'oobleck')
    #     lex_oobleck = self.lex[u'oobleck']   # word from an orphan verb
    #
    #     xavier = self.lex.define(u'agent', u'xavier')
    #     self.assertNotEqual(xavier, self.lex)
    #     xavier_oobleck = xavier.oobleck   # word from a patronized verb
    #
    #     # Weirdness: the verb instances are equal but behave differently
    #     self.assertEqual(lex_oobleck, xavier_oobleck)   # TODO:  Should these be unequal??
    #     self.assertFalse(hasattr(lex_oobleck, '_word_before_the_dot'))
    #     self.assertTrue(hasattr(xavier_oobleck, '_word_before_the_dot'))
    #     # self.assertNotEqual(lex_oobleck._word_before_the_dot, xavier_oobleck._word_before_the_dot)
    #
    #     xavier_blob = xavier_oobleck(some_object, qiki.Number(42), u"xavier blob")
    #     self.assertTrue(xavier_blob.exists())
    #     self.assertEqual(xavier_blob.sbj, xavier)
    #     self.assertEqual(xavier_blob.vrb, xavier_oobleck)
    #     self.assertEqual(xavier_blob.obj, some_object)
    #     self.assertEqual(xavier_blob.num, qiki.Number(42))
    #     self.assertEqual(xavier_blob.txt, u"xavier blob")

    def test_lex_number(self):
        agent_by_txt = self.lex[u'agent']
        agent_by_idn = self.lex[qiki.Word._IDN_AGENT]
        self.assertEqual(agent_by_txt, agent_by_idn)
        self.assertEqual(u'agent', agent_by_idn.txt)
        self.assertEqual(qiki.Word._IDN_AGENT, agent_by_txt.idn)

    def test_num_explicit(self):
        anna = self.lex.define(u'agent', u'anna')
        hate = self.lex.verb(u'hate')
        oobleck = self.lex.noun(u'oobleck')
        with self.assertNewWord():
            anna.says(hate, oobleck, 10)
        self.assertEqual(10, anna.said(hate, oobleck).num)
        with self.assertNewWord():
            anna.says(hate, oobleck, num=11)
        self.assertEqual(11, anna.said(hate, oobleck).num)

    def test_bogus_define_kwarg(self):
        with self.assertRaises(TypeError):
            # noinspection PyArgumentList
            self.lex.define(not_a_keyword_argument=33)
        # TODO:  How to do the following?  Better way than (ick) a wrapper function for define()?
        # with self.assertRaises(qiki.Word.NoSuchKwarg):
        #     # noinspection PyArgumentList
        #     self.lex.define(not_a_keyword_argument=33)

    # def test_bogus_sentence_kwarg(self):
    #     blurt = self.lex.verb(u'blurt')
    #     self.lex.says(blurt, self.lex, 1, u'')
    #     with self.assertRaises(TypeError):
    #         self.lex.says(blurt, self.lex, no_such_keyword_argument=666)
    #     with self.assertRaises(qiki.Word.SentenceArgs):
    #         self.lex.says(blurt, self.lex, no_such_keyword_argument=666)

    # def test_missing_sentence_obj(self):
    #     self.lex.verb(u'blurt')
    #     with self.assertRaises(TypeError):
    #         self.lex.blurt()
    #     with self.assertRaises(qiki.Word.MissingObj):
    #         self.lex.blurt()

    def test_missing_word_getter(self):
        alf = self.lex.define(u'agent', u'alf')
        clap = self.lex.verb(u'clap')
        eve = self.lex.verb(u'eve')
        with self.assertNewWord():
            alf.says(clap, eve, 55)
        word = alf.said(clap, eve)
        self.assertEqual(55, word.num)
        with self.assertRaises(qiki.Word.NotExist):
            eve.said(clap, alf)

    # def test_missing_lex_getter(self):
    #     self.assertEqual(qiki.Lex._IDN_DEFINE, self.lex[u'define'].idn)
    #     with self.assertRaises(qiki.Word.NotExist):
    #         self.lex[u'defibrillator']


class Word004SentenceTests(WordTests):

    def setUp(self):
        super(Word004SentenceTests, self).setUp()
        self.sam = self.lex.define(u'agent', u'sam')
        self.vet = self.lex.verb(u'vet')
        self.orb = self.lex.noun(u'orb')

    def assertGoodSentence(self, sentence, the_num=1, the_txt=u''):
        self.assertTrue(sentence.exists())
        self.assertEqual(self.sam, sentence.sbj)
        self.assertEqual(self.vet, sentence.vrb)
        self.assertEqual(self.orb, sentence.obj)
        self.assertEqual(the_num, sentence.num)
        self.assertEqual(the_txt, sentence.txt)
        return sentence

    # def assertSentenceEquals(self, word, sbj, vrb, obj, num, txt):
    #     self.assertEqual(sbj, word.sbj)
    #     self.assertEqual(vrb, word.vrb)
    #     self.assertEqual(obj, word.obj)
    #     self.assertEqual(num, word.num)
    #     self.assertEqual(txt, word.txt)

    def test_sentence_00_plain(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=42, txt=u'sentence'), 42, u'sentence')

    def test_sentence_01a_keyword(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=42, txt=u'sentence'), 42, u'sentence')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=42), 42)
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, txt=u'sentence'), 1, u'sentence')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb))

    def test_sentence_01b_missing(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb))
        with self.assertRaises(TypeError):   # was self.assertRaisesRegexp(qiki.Word.SentenceArgs, 'obj'):
            self.assertGoodSentence(self.sam.says(vrb=self.vet))
        with self.assertRaises(TypeError):   # was self.assertRaisesRegexp(qiki.Word.SentenceArgs, 'vrb'):
            self.assertGoodSentence(self.sam.says(obj=self.orb))

    def test_sentence_02a_positional(self):
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, 42, u'sentence'), 42, u'sentence')
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, u'sentence', 42), 42, u'sentence')
        self.assertGoodSentence(self.sam.says(self.vet, self.orb))
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, 42), 42)
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, True), 1)
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, u'x'), 1, u'x')

    def test_sentence_02b_positional_mix_keyword(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=42, txt=u'sentence'), 42, u'sentence')
        self.assertGoodSentence(self.sam.says(self.vet, obj=self.orb, num=42, txt=u'sentence'), 42, u'sentence')
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, num=42, txt=u'sentence'), 42, u'sentence')
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, 42, txt=u'sentence'), 42, u'sentence')
        # self.assertGoodSentence(self.sam.says(self.vet, self.orb, u'x', num=42), 42, u'x')
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, 42, txt=u'x'), 42, u'x')

    def test_sentence_02c_wrong_type(self):
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, some_type))
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, some_type, 1))
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, some_type, u''))
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, 1, some_type))
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, u'', some_type))

    def test_sentence_02d_ambiguous_type(self):
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, 42, 42))
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, u'x', u'x'))
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, u'x', txt=u'x'))
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, u'x', u'0q80'))
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, u'0q80', u'x'))
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, u'x', u'0x80'))
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, u'0x80', u'x'))

    def test_sentence_by_idn(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet.idn, obj=self.orb.idn, num=42, txt=u'sentence'), 42, u'sentence')

    def test_sentence_args(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=42, txt=u'sentence'), 42, u'sentence')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=qiki.Number(42), txt=u'sentence'), 42, u'sentence')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb))
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=99), 99)
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, txt=u'flop'), 1, u'flop')

    def test_sentence_use_already(self):
        w1 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt=u'x'), 9, u'x')
        w2 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt=u'x'), 9, u'x')
        self.assertLess(w1.idn, w2.idn)

        w3a = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=8, txt=u'y'), 8, u'y')
        w3b = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=8, txt=u'y', use_already=True), 8, u'y')
        self.assertEqual(w3a.idn, w3b.idn)

        w4 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=7, txt=u'z'), 7, u'z')
        w5 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=7, txt=u'z', use_already=False), 7, u'z')
        self.assertLess(w4.idn, w5.idn)

    def test_sentence_whn(self):
        w1 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt=u'x'), 9, u'x')
        self.assertSensibleWhen(w1.whn)

        w2 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt=u'x'), 9, u'x')
        self.assertSensibleWhen(w2.whn)
        self.assertLess(w1.idn, w2.idn)
        self.assertLessEqual(w1.whn, w2.whn)

        w2b = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt=u'x', use_already=True), 9, u'x')
        self.assertSensibleWhen(w2b.whn)
        self.assertEqual(w2.idn, w2b.idn)
        self.assertEqual(w2.whn, w2b.whn)

        w3 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt=u'x', use_already=False), 9, u'x')
        self.assertSensibleWhen(w3.whn)
        self.assertLess(w2.idn, w3.idn)
        self.assertLessEqual(w2.whn, w3.whn)
    #
    # def test_sentence_bad_positional(self):
    #     with self.assertRaises(qiki.Word.SentenceArgs):
    #         self.lex.says(self.sam, self.vet, self.orb, 1, u'')
    #     with self.assertRaises(qiki.Word.SentenceArgs):
    #         self.lex.says(self.sam, self.vet, self.orb, 1)
    #     with self.assertRaises(qiki.Word.SentenceArgs):
    #         self.lex.says(self.sam, self.vet, self.orb)
    #     with self.assertRaises(qiki.Word.SentenceArgs):
    #         self.lex.says()

    def test_sentence_bad_args(self):
        # with self.assertRaises(qiki.Word.SentenceArgs):
        with self.assertRaises(TypeError):
            self.sam.says(vrb=self.vet, obj=self.orb, no_such_arg=0)

    def test_sentence_num_add(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt=u'x'), 9, u'x')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num_add=2, txt=u'x'), 11, u'x')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num_add=2, txt=u'x'), 13, u'x')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=None, num_add=2, txt=u'x'), 15, u'x')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=8, num_add=None, txt=u'x'), 8, u'x')

    def test_sentence_conflict_num_num_add(self):
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.sam.says(vrb=self.vet, obj=self.orb, num=99, num_add=-99)

    def test_call_conflict_num_num_add(self):
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.sam.says(self.vet, self.orb, num=99, num_add=-99)
        with self.assertRaises(qiki.Word.SentenceArgs):
            self.sam.says(self.vet, self.orb, 99, num_add=-99)
        # with self.assertRaises(qiki.Word.SentenceArgs):
        #     self.sam.says(self.vet, self.orb, 99, num=-99)
        # with self.assertRaises(qiki.Word.SentenceArgs):
        #     self.sam.says(self.vet, self.orb, 99, num=-99, num_add=999999)


class WordListingTests(WordTests):

    class Student(qiki.Listing):
        names_and_grades = [
            (u"Archie", 4.0),
            (u"Barbara", 3.0),
            (u"Chad", 3.0),
            (u"Deanne", 1.0),
        ]

        def lookup(self, index, callback):
            try:
                name_and_grade = self.names_and_grades[int(index)]
            except IndexError:
                raise self.NotFound
            name = name_and_grade[0]
            grade = name_and_grade[1]
            callback(name, grade)

    def setUp(self):
        super(WordListingTests, self).setUp()
        self.listing = self.lex.noun(u'listing')
        qiki.Listing.install(self.listing)
        self.names = self.lex.define(self.listing, u'names')
        self.Student.install(self.names)


class Word005aListingBasicTests(WordListingTests):

    def test_listing_suffix(self):
        number_two = qiki.Number(2)
        chad = self.Student(number_two)
        self.assertEqual(number_two, chad.index)
        self.assertEqual(   u"Chad", chad.txt)
        self.assertEqual(       3.0, chad.num)
        self.assertTrue(chad.exists())

        idn_suffix = chad.idn.parse_suffixes()
        self.assertEqual(2, len(idn_suffix))
        idn = idn_suffix[0]
        suffix = idn_suffix[1]
        self.assertEqual(idn, self.names.idn)
        self.assertEqual(suffix.payload_number(), number_two)

    def test_listing_using_spawn_and_save(self):
        archie = self.Student(qiki.Number(0))
        bless = self.lex.verb(u'bless')
        blessed_name = self.lex.spawn(
            sbj=self.lex.idn,
            vrb=bless.idn,
            obj=archie.idn,
            txt=u"mah soul",
            num=qiki.Number(666),
        )
        blessed_name.save()

        blessed_name_too = self.lex.spawn(blessed_name.idn)
        self.assertTrue(blessed_name_too.exists())
        self.assertEqual(blessed_name_too.sbj.idn, qiki.Word._IDN_LEX)
        self.assertEqual(blessed_name_too.vrb, bless)
        self.assertEqual(blessed_name_too.obj, archie)
        self.assertEqual(blessed_name_too.num, qiki.Number(666))
        self.assertEqual(blessed_name_too.txt, u"mah soul")

        laud = self.lex.verb(u'laud')
        thing = self.lex.noun(u'thing')
        lauded_thing = self.lex.spawn(
            sbj=archie.idn,
            vrb=laud.idn,
            obj=thing.idn,
            txt=u"most sincerely",
            num=qiki.Number(123456789),
        )
        lauded_thing.save()

    def test_listing_using_method_verb(self):
        archie = self.Student(qiki.Number(0))
        bless = self.lex.verb(u'bless')
        blessed_name = self.lex.says(vrb=bless, obj=archie, num=qiki.Number(666), txt=u"mah soul")

        blessed_name_too = self.lex.spawn(blessed_name.idn)
        self.assertTrue(blessed_name_too.exists())
        self.assertEqual(blessed_name_too.sbj.idn, qiki.Word._IDN_LEX)
        self.assertEqual(blessed_name_too.vrb, bless)
        self.assertEqual(blessed_name_too.obj, archie)
        self.assertEqual(blessed_name_too.num, qiki.Number(666))
        self.assertEqual(blessed_name_too.txt, u"mah soul")

        laud = self.lex.verb(u'laud')
        thing = self.lex.noun(u'thing')
        with self.assertNewWord():
            archie.says(vrb=laud, obj=thing, num=qiki.Number(123456789), txt=u"most sincerely")

    def test_listing_not_found(self):
        with self.assertRaises(qiki.Listing.NotFound):
            self.Student(qiki.Number(5))

    def test_listing_index_Number(self):
        deanne = self.Student(qiki.Number(3))
        self.assertEqual(u"Deanne", deanne.txt)

    def test_listing_index_int(self):
        deanne = self.Student(3)
        self.assertEqual(u"Deanne", deanne.txt)

    def test_listing_as_nouns(self):
        barbara = self.Student(1)
        deanne = self.Student(3)
        like = self.lex.verb(u'like')
        with self.assertNewWords(2):
            barbara.says(vrb=like, obj=deanne, num=qiki.Number(1))
            deanne.says(vrb=like, obj=barbara, num=qiki.Number(-1000000000))

    def test_listing_by_lex_idn(self):
        """Make sure lex[suffixed number] will look up a listing."""
        chad1 = self.Student(2)
        idn_chad = chad1.idn
        chad2 = self.lex[idn_chad]
        self.assertEqual(u"Chad", chad1.txt)
        self.assertEqual(u"Chad", chad2.txt)


class Word005bListingInternalsTests(WordListingTests):

    class SubStudent(WordListingTests.Student):
        def lookup(self, index, callback):
            raise self.NotFound

    class AnotherListing(qiki.Listing):
        def lookup(self, index, callback):
            raise self.NotFound

    def setUp(self):
        super(Word005bListingInternalsTests, self).setUp()
        self.SubStudent.install(self.lex.noun(u'sub_student'))
        self.AnotherListing.install(self.lex.noun(u'another_listing'))

    def test_one_class_dictionary(self):
        self.assertIs(qiki.Listing.class_dictionary, self.Student.class_dictionary)
        self.assertIs(qiki.Listing.class_dictionary, self.SubStudent.class_dictionary)
        self.assertIs(qiki.Listing.class_dictionary, self.AnotherListing.class_dictionary)

    def test_one_meta_word_per_subclass(self):
        self.assertNotEqual(qiki.Listing.meta_word.idn, self.Student.meta_word.idn)
        self.assertNotEqual(qiki.Listing.meta_word.idn, self.SubStudent.meta_word.idn)
        self.assertNotEqual(qiki.Listing.meta_word.idn, self.AnotherListing.meta_word.idn)

        self.assertNotEqual(self.Student.meta_word.idn, self.SubStudent.meta_word.idn)
        self.assertNotEqual(self.Student.meta_word.idn, self.AnotherListing.meta_word.idn)

        self.assertNotEqual(self.SubStudent.meta_word.idn, self.AnotherListing.meta_word.idn)

    def test_idn_suffixed(self):
        chad = self.Student(2)
        deanne = self.Student(3)
        self.assertFalse(qiki.Listing.meta_word.idn.is_suffixed())
        self.assertFalse(self.Student.meta_word.idn.is_suffixed())
        self.assertFalse(self.SubStudent.meta_word.idn.is_suffixed())
        self.assertTrue(chad.idn.is_suffixed())
        self.assertTrue(deanne.idn.is_suffixed())

    def test_example_idn(self):
        chad = self.Student(2)
        # Serious assumption here, that only 5 words were defined before lex.noun('listing').
        # But this helps to demonstrate Listing meta_word and instance idn contents.
        self.assertEqual('0q82_06', qiki.Listing.meta_word.idn.qstring())
        self.assertEqual('0q82_07', self.Student.meta_word.idn.qstring())   # Number(7)
        self.assertEqual('0q82_07__8202_1D0300', chad.idn.qstring())   # Root is Number(7), payload is Number(2).
        self.assertEqual('0q82_08', self.SubStudent.meta_word.idn.qstring())
        self.assertEqual('0q82_09', self.AnotherListing.meta_word.idn.qstring())

    def test_listing_word_lookup(self):
        chad = self.Student(2)
        self.assertEqual(u"Chad", chad.txt)
        chad_clone = qiki.Listing.word_lookup(chad.idn)
        self.assertEqual(chad, chad_clone)

    def test_listing_word_lookup_not_suffixed(self):
        with self.assertRaises(qiki.Listing.NotAListing):
            qiki.Listing.word_lookup(qiki.Number(666))

    def test_listing_word_lookup_wrong_suffixed(self):
        with self.assertRaises(qiki.Listing.NotAListing):
            qiki.Listing.word_lookup(qiki.Number(666+666j))

    def test_listing_word_lookup_not_listing(self):
        chad = self.Student(2)
        (listing_class_idn, listed_thing_number) = chad.idn.parse_suffixes()
        not_a_listing_idn = qiki.Number(listing_class_idn + 666)
        not_a_listing_idn.add_suffix(listed_thing_number)
        with self.assertRaises(qiki.Listing.NotAListing):
            qiki.Listing.word_lookup(not_a_listing_idn)

    def test_class_from_meta_idn(self):
        chad = self.Student(2)
        chad_class_idn = chad.idn.parse_suffixes()[0]
        chad_class = qiki.Listing.class_from_meta_idn(chad_class_idn)

        self.assertEqual(self.Student, chad_class)
        self.assertNotEqual(qiki.Listing, chad_class)

        self.assertTrue(issubclass(chad_class, self.Student))
        self.assertTrue(issubclass(chad_class, qiki.Listing))

    def test_class_from_meta_idn_bogus(self):
        some_word = self.lex.noun(u'some word')
        with self.assertRaises(qiki.Listing.NotAListing):
            qiki.Listing.class_from_meta_idn(some_word.idn)

    def test_non_listing_suffix(self):
        bogus_word = self.lex[qiki.Number(1+2j)]
        with self.assertRaises(qiki.Word.NotAWord):
            bogus_word.exists()


class Word006UseAlready(WordTests):

    def setUp(self):
        super(Word006UseAlready, self).setUp()
        self.narcissus = self.lex.define(u'agent', u'narcissus')
        self.like = self.lex.verb(u'like')

    # When txt differs

    def test_use_already_differ_txt_default(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Puddle")

    def test_use_already_differ_txt_false(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Puddle", use_already=False)

    def test_use_already_differ_txt_true(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Puddle", use_already=True)

    # When num differs

    def test_use_already_differ_num_default(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 200, u"Mirror")

    def test_use_already_differ_num_false(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 200, u"Mirror", use_already=False)

    def test_use_already_differ_num_true(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 200, u"Mirror", use_already=True)

    # When num and txt are the same

    def test_use_already_same_default(self):
        with self.assertNewWord():  word1 = self.narcissus.says(self.like, self.narcissus, 100, u"Mirror")
        with self.assertNewWord():  word2 = self.narcissus.says(self.like, self.narcissus, 100, u"Mirror")
        self.assertEqual(word1.idn+1, word2.idn)

    def test_use_already_same_false(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Mirror", use_already=False)

    def test_use_already_same_true(self):
        with self.assertNewWord():    self.narcissus.says(self.like, self.narcissus, 100, u"Mirror")
        with self.assertNoNewWord():  self.narcissus.says(self.like, self.narcissus, 100, u"Mirror", use_already=True)

    # TODO:  Deal with the inconsistency that when defining a word, use_already defaults to True.


class Word007FindTests(WordTests):

    def setUp(self):
        super(Word007FindTests, self).setUp()
        self.apple = self.lex.noun(u'apple')
        self.berry = self.lex.noun(u'berry')
        self.curry = self.lex.noun(u'curry')
        self.macintosh = self.lex.define(u'apple', u'macintosh')
        self.braburn = self.lex.define(u'apple', u'braburn')
        self.honeycrisp = self.lex.define(u'apple', u'honeycrisp')
        self.crave = self.lex.verb(u'crave')
        self.fred = self.lex.define(u'agent', u'fred')

        # WordFindTests's lex:
        #
        # 1 lex.define(verb, 1, u'define')
        # 2 lex.define(noun, 1, u'noun')
        # 3 lex.define(noun, 1, u'verb')
        # 4 lex.define(noun, 1, u'agent')
        # 5 lex.define(agent, 1, u'lex')
        # 6 lex.define(noun, 1, u'apple')
        # 7 lex.define(noun, 1, u'berry')
        # 8 lex.define(noun, 1, u'curry')
        # 9 lex.define(apple, 1, u'macintosh')
        # 10 lex.define(apple, 1, u'braburn')
        # 11 lex.define(apple, 1, u'honeycrisp')
        # 12 lex.define(verb, 1, u'crave')
        # 13 lex.define(agent, 1, u'fred')
        #
        # 13 ⋅ Word(u'lex')
        # 13 ⋅ Word(u'define')
        # 6 ⋅ Word(u'noun')
        # 3 ⋅ Word(u'apple')
        # 2 ⋅ Word(u'agent')
        # 2 ⋅ Word(u'verb')

    def test_find_obj(self):
        apple_words = self.lex.find_words(obj=self.apple.idn)
        self.assertEqual(3, len(apple_words))
        self.assertEqual(self.macintosh, apple_words[0])
        self.assertEqual(self.braburn, apple_words[1])
        self.assertEqual(self.honeycrisp, apple_words[2])
        self.assertEqual([self.macintosh, self.braburn, self.honeycrisp], apple_words)

    def test_find_obj_word(self):
        self.assertEqual([self.macintosh, self.braburn, self.honeycrisp], self.lex.find_words(obj=self.apple))

    def test_find_sbj(self):
        self.fred.says(self.crave, self.curry, qiki.Number(1), u"Yummy.")
        fred_words = self.lex.find_words(sbj=self.fred.idn)
        self.assertEqual(1, len(fred_words))
        self.assertEqual(u"Yummy.", fred_words[0].txt)

    def test_find_sbj_word(self):
        fred_word = self.fred.says(self.crave, self.curry, qiki.Number(1), u"Yummy.")
        self.assertEqual([fred_word], self.lex.find_words(sbj=self.fred))

    def test_find_vrb(self):
        self.fred.says(self.crave, self.curry, qiki.Number(1), u"Yummy.")
        crave_words = self.lex.find_words(vrb=self.crave.idn)
        self.assertEqual(1, len(crave_words))
        self.assertEqual(u"Yummy.", crave_words[0].txt)

    def test_find_vrb_word(self):
        crave_word = self.fred.says(self.crave, self.curry, qiki.Number(1), u"Yummy.")
        self.assertEqual([crave_word], self.lex.find_words(vrb=self.crave))

    def test_find_chronology(self):
        craving_apple = self.fred.says(self.crave, self.apple, qiki.Number(1))
        craving_berry = self.fred.says(self.crave, self.berry, qiki.Number(1))
        craving_curry = self.fred.says(self.crave, self.curry, qiki.Number(1))

        self.assertEqual([craving_apple, craving_berry, craving_curry], self.lex.find_words(sbj=self.fred))
        self.assertEqual([craving_apple, craving_berry, craving_curry], self.lex.find_words(vrb=self.crave))

    def test_find_empty(self):
        self.fred.says(self.crave, self.apple, qiki.Number(1))
        self.fred.says(self.crave, self.berry, qiki.Number(1))
        self.fred.says(self.crave, self.curry, qiki.Number(1))

        self.assertEqual([], self.lex.find_words(sbj=self.crave))
        self.assertEqual([], self.lex.find_words(vrb=self.fred))

    def test_find_idns(self):
        idns = self.lex.find_idns()
        for idn in idns:
            self.assertIsInstance(idn, qiki.Number)

    def test_find_by_vrb(self):
        crave1 = self.fred.says(self.crave, self.apple, 1)
        crave2 = self.fred.says(self.crave, self.braburn, 10)
        crave3 = self.fred.says(self.crave, self.macintosh, 0.5)
        self.assertEqual([crave1, crave2, crave3], self.lex.find_words(vrb=self.crave))
        self.assertEqual([crave1, crave2, crave3], self.lex.find_words(vrb=self.crave.idn))
        self.assertEqual([crave1.idn, crave2.idn, crave3.idn], self.lex.find_idns(vrb=self.crave))
        self.assertEqual([crave1.idn, crave2.idn, crave3.idn], self.lex.find_idns(vrb=self.crave.idn))

    def test_find_by_vrb_list(self):
        c1 = self.fred.says(self.crave, self.apple, 1)
        c2 = self.fred.says(self.crave, self.braburn, 10)
        retch = self.lex.verb(u'retch')
        r3 = self.fred.says(retch, self.macintosh, -1)
        self.assertEqual([c1, c2    ], self.lex.find_words(vrb=[self.crave        ]))
        self.assertEqual([c1, c2, r3], self.lex.find_words(vrb=[self.crave,     retch    ]))
        self.assertEqual([c1, c2, r3], self.lex.find_words(vrb=[self.crave,     retch.idn]))
        self.assertEqual([c1, c2, r3], self.lex.find_words(vrb=[self.crave.idn, retch    ]))
        self.assertEqual([c1, c2, r3], self.lex.find_words(vrb=[self.crave.idn, retch.idn]))
        self.assertEqual([c1.idn, c2.idn, r3.idn], self.lex.find_idns(vrb=[self.crave    , retch    ]))
        self.assertEqual([c1.idn, c2.idn, r3.idn], self.lex.find_idns(vrb=[self.crave.idn, retch.idn]))
        self.assertEqual([                r3.idn], self.lex.find_idns(vrb=[                retch.idn]))

    def test_find_words(self):
        words = self.lex.find_words()
        for word in words:
            self.assertIsInstance(word, qiki.Word)

    def test_find_idns_with_sql(self):
        idns = self.lex.find_idns(idn_order='ASC')
        self.assertLess(idns[0], idns[-1])
        idns = self.lex.find_idns(idn_order='DESC')
        self.assertGreater(idns[0], idns[-1])

    def test_find_words_sql(self):
        words = self.lex.find_words(idn_order='ASC')
        self.assertLess(words[0].idn, words[-1].idn)
        words = self.lex.find_words(idn_order='DESC')
        self.assertGreater(words[0].idn, words[-1].idn)

    def test_find_idn(self):
        lex_by_idn = self.lex.find_words(idn=qiki.Word._IDN_LEX)
        self.assertEqual(1, len(lex_by_idn))
        self.assertEqual(u"lex", lex_by_idn[0].txt)

        lex_by_idn = self.lex.find_idns(idn=qiki.Word._IDN_LEX)
        self.assertEqual(1, len(lex_by_idn))
        self.assertEqual(self.lex.idn, lex_by_idn[0])

    def test_find_idn_word(self):
        lex_by_idn = self.lex.find_words(idn=self.lex)
        self.assertEqual(1, len(lex_by_idn))
        self.assertEqual(u"lex", lex_by_idn[0].txt)

        lex_by_idn = self.lex.find_idns(idn=self.lex)
        self.assertEqual(1, len(lex_by_idn))
        self.assertEqual(self.lex.idn, lex_by_idn[0])

    def test_find_idn_not(self):
        lex_by_idn = self.lex.find_words(idn=qiki.Number(-42))
        self.assertEqual(0, len(lex_by_idn))

    def test_find_last(self):
        w = self.lex.find_last(obj=self.lex['noun'])
        self.assertEqual(self.curry, w)

    def test_find_last_not(self):
        with self.assertRaises(qiki.Lex.NotFound):
            self.lex.find_last(obj=self.curry)


# noinspection SqlDialectInspection
class WordQoolbarTests(WordTests):

    def setUp(self):
        super(WordQoolbarTests, self).setUp()
        self.qool = self.lex.verb(u'qool')
        self.like = self.lex.verb(u'like')
        self.delete = self.lex.verb(u'delete')
        self.lex.says(self.qool, self.like, qiki.Number(1))
        self.lex.says(self.qool, self.delete, qiki.Number(1))
        self.anna = self.lex.define(u'agent', u'anna')
        self.bart = self.lex.define(u'agent', u'bart')
        self.youtube = self.lex.noun(u'youtube')
        self.zigzags = self.lex.noun(u'zigzags')

        self.anna_like_youtube = self.anna.says(self.like, self.youtube, 1)
        self.bart_like_youtube = self.bart.says(self.like, self.youtube, 10)
        self.anna_like_zigzags = self.anna.says(self.like, self.zigzags, 2)
        self.bart_delete_zigzags = self.bart.says(self.delete, self.zigzags, 1)

        qool_declarations = self.lex.find_words(vrb=self.qool.idn)
        self.qool_idns = [w.obj.idn for w in qool_declarations]

    def disabled_test_display_all_word_descriptions(self):
        """
        1 [lex](define, u'define')[verb]
        2 [lex](define, u'noun')[noun]
        3 [lex](define, u'verb')[noun]
        4 [lex](define, u'agent')[noun]
        5 [lex](define, u'lex')[agent]
        6 [lex](define, u'qool')[verb]
        7 [lex](define, u'like')[verb]
        8 [lex](define, u'delete')[verb]
        9 [lex](qool)[like]
        10 [lex](qool)[delete]
        11 [lex](define, u'anna')[agent]
        12 [lex](define, u'bart')[agent]
        13 [lex](define, u'youtube')[noun]
        14 [lex](define, u'zigzags')[noun]
        15 [anna](like)[youtube]
        16 [bart](like, 10)[youtube]
        17 [anna](like, 2)[zigzags]
        18 [bart](delete)[zigzags]

        14 ⋅ Word(u'lex')
        12 ⋅ Word(u'define')
        5 ⋅ Word(u'noun')
        4 ⋅ Word(u'like')
        4 ⋅ Word(u'verb')
        3 ⋅ Word(u'agent')
        2 ⋅ Word(u'qool')
        2 ⋅ Word(u'bart')
        2 ⋅ Word(u'youtube')
        2 ⋅ Word(u'zigzags')
        2 ⋅ Word(u'delete')
        2 ⋅ Word(u'anna')
        """
        self.display_all_word_descriptions()

    def test_get_all_qool_verbs(self):
        self.assertEqual([self.like.idn, self.delete.idn], self.qool_idns)
        # print(", ".join([w.idn.qstring() for w in qool_words]))
        # print(", ".join([n.qstring() for n in qool_idns]))

    def test_find_qool_(self):
        """Find by a list of verbs."""
        qool_uses = self.lex.find_words(vrb=self.qool_idns)
        self.assertEqual(4, len(qool_uses))
        self.assertEqual(qool_uses[0].sbj, self.anna)
        self.assertEqual(qool_uses[1].sbj, self.bart)
        self.assertEqual(qool_uses[2].sbj, self.anna)
        self.assertEqual(qool_uses[3].sbj, self.bart)

        qool_uses = self.lex.find_words(vrb=self.qool_idns, obj=self.youtube)
        self.assertEqual(2, len(qool_uses))
        self.assertEqual(qool_uses[0].sbj, self.anna)
        self.assertEqual(qool_uses[0].num, qiki.Number(1))
        self.assertEqual(qool_uses[1].sbj, self.bart)
        self.assertEqual(qool_uses[1].num, qiki.Number(10))

        qool_uses = self.lex.find_words(vrb=self.qool_idns, sbj=self.bart)
        self.assertEqual(2, len(qool_uses))
        self.assertEqual(qool_uses[0].obj, self.youtube)
        self.assertEqual(qool_uses[0].num, qiki.Number(10))
        self.assertEqual(qool_uses[1].obj, self.zigzags)
        self.assertEqual(qool_uses[1].num, qiki.Number(1))

    def test_super_select_idn(self):
        self.assertEqual([{'txt': u'define'},], list(self.lex.super_select(
            'SELECT txt FROM',
            self.lex.table,
            'WHERE idn =',
            qiki.Word._IDN_DEFINE
        )))

    def test_super_select_word(self):
        define_word = self.lex[u'define']
        self.assertEqual([{'txt': u'define'},], list(self.lex.super_select(
            'SELECT txt FROM',
            self.lex.table,
            'WHERE idn =',
            define_word
        )))

    def test_super_select_txt(self):
        self.assertEqual([{'idn': qiki.Word._IDN_DEFINE},], list(self.lex.super_select(
            'SELECT idn FROM',
            self.lex.table,
            'WHERE txt =',
            qiki.Text(u'define')
        )))

    def test_super_select_with_none(self):
        """To concatenate two strings of literal SQL code, intersperse a None."""
        self.assertEqual([{'txt': u'define'}], list(self.lex.super_select(
            'SELECT txt', None, 'FROM',
            self.lex.table,
            'WHERE', None, 'idn =',
            qiki.Word._IDN_DEFINE
        )))

    def test_super_select_string_concatenate_alternatives(self):
        """Showcase of all the valid ways one might concatenate strings with super_select().

        That is, strings that make up SQL.  Not the content of fields, e.g. txt."""
        def good_super_select(*args):
            self.assertEqual([{'txt':u'define'}], list(self.lex.super_select(*args)))
        def bad_super_select(*args):
            with self.assertRaises(qiki.LexMySQL.SuperSelectStringString):
                list(self.lex.super_select(*args))
        txt = 'txt'

        good_super_select('SELECT          txt          FROM', self.lex.table, 'WHERE idn=',qiki.Word._IDN_DEFINE)
        good_super_select('SELECT '       'txt'       ' FROM', self.lex.table, 'WHERE idn=',qiki.Word._IDN_DEFINE)
        good_super_select('SELECT '   +   'txt'   +   ' FROM', self.lex.table, 'WHERE idn=',qiki.Word._IDN_DEFINE)
        good_super_select('SELECT', None, 'txt', None, 'FROM', self.lex.table, 'WHERE idn=',qiki.Word._IDN_DEFINE)
        good_super_select('SELECT '   +    txt    +   ' FROM', self.lex.table, 'WHERE idn=',qiki.Word._IDN_DEFINE)
        good_super_select('SELECT', None,  txt , None, 'FROM', self.lex.table, 'WHERE idn=',qiki.Word._IDN_DEFINE)

        bad_super_select( 'SELECT',       'txt',       'FROM', self.lex.table, 'WHERE idn=',qiki.Word._IDN_DEFINE)
        bad_super_select( 'SELECT',        txt ,       'FROM', self.lex.table, 'WHERE idn=',qiki.Word._IDN_DEFINE)

    def test_super_select_string_string(self):
        """Concatenating two literal strings is an error.

        This avoids confusion between literal strings, table names, and txt fields."""
        with self.assertRaises(qiki.LexMySQL.SuperSelectStringString):
            list(self.lex.super_select('string', 'string', self.lex.table))
        with self.assertRaises(qiki.LexMySQL.SuperSelectStringString):
            list(self.lex.super_select(self.lex.table, 'string', 'string'))
        self.lex.super_select('SELECT * FROM', self.lex.table)

        with self.assertRaises(qiki.LexMySQL.SuperSelectStringString):
            list(self.lex.super_select('SELECT * FROM', self.lex.table, 'WHERE txt=', 'define'))
        with self.assertRaises(qiki.LexMySQL.SuperSelectStringString):
            list(self.lex.super_select('SELECT * FROM', self.lex.table, 'WHERE txt=', 'define'))
        self.lex.super_select('SELECT * FROM', self.lex.table, 'WHERE txt=', qiki.Text(u'define'))

    def test_super_select_null(self):
        self.assertEqual([{'x': None}], list(self.lex.super_select('SELECT NULL as x')))
        self.assertEqual([{'x': None}], list(self.lex.super_select('SELECT', None, 'NULL as x')))

    def test_super_select_type_error(self):
        class ExoticType(object):
            pass

        with self.assertRaises(qiki.LexMySQL.SuperSelectTypeError):
            list(self.lex.super_select(ExoticType))

    def test_lex_from_idn(self):
        word = self.lex.spawn()
        self.lex.populate_word_from_idn(word, self.zigzags.idn)
        self.assertEqual(self.zigzags.idn, word.idn)
        self.assertEqual(self.zigzags.sbj, word.sbj)
        self.assertEqual(self.zigzags.vrb, word.vrb)
        self.assertEqual(self.zigzags.obj, word.obj)
        self.assertEqual(self.zigzags.num, word.num)
        self.assertEqual(self.zigzags.txt, word.txt)
        self.assertEqual(self.zigzags.whn, word.whn)

    def test_lex_from_definition(self):
        word = self.lex.spawn()
        self.lex.populate_word_from_definition(word, self.zigzags.txt)
        self.assertEqual(self.zigzags.idn, word.idn)
        self.assertEqual(self.zigzags.sbj, word.sbj)
        self.assertEqual(self.zigzags.vrb, word.vrb)
        self.assertEqual(self.zigzags.obj, word.obj)
        self.assertEqual(self.zigzags.num, word.num)
        self.assertEqual(self.zigzags.txt, word.txt)
        self.assertEqual(self.zigzags.whn, word.whn)

    def test_lex_from_sbj_vrb_obj_idns(self):
        word = self.lex.spawn()
        self.lex.populate_word_from_sbj_vrb_obj(
            word,
            self.zigzags.sbj,
            self.zigzags.vrb,
            self.zigzags.obj
        )
        self.assertEqual(self.zigzags.idn, word.idn)
        self.assertEqual(self.zigzags.sbj, word.sbj)
        self.assertEqual(self.zigzags.vrb, word.vrb)
        self.assertEqual(self.zigzags.obj, word.obj)
        self.assertEqual(self.zigzags.num, word.num)
        self.assertEqual(self.zigzags.txt, word.txt)
        self.assertEqual(self.zigzags.whn, word.whn)

    def test_lex_from_sbj_vrb_obj_words(self):
        word = self.lex.spawn()
        self.lex.populate_word_from_sbj_vrb_obj(
            word,
            self.lex[self.zigzags.sbj],
            self.lex[self.zigzags.vrb],
            self.lex[self.zigzags.obj]
        )
        self.assertEqual(self.zigzags.idn, word.idn)
        self.assertEqual(self.zigzags.sbj, word.sbj)
        self.assertEqual(self.zigzags.vrb, word.vrb)
        self.assertEqual(self.zigzags.obj, word.obj)
        self.assertEqual(self.zigzags.num, word.num)
        self.assertEqual(self.zigzags.txt, word.txt)
        self.assertEqual(self.zigzags.whn, word.whn)

    def test_lex_from_sbj_vrb_obj_num_txt_idns(self):
        word = self.lex.spawn()
        self.lex.populate_word_from_sbj_vrb_obj_num_txt(
            word,
            self.zigzags.sbj,
            self.zigzags.vrb,
            self.zigzags.obj,
            self.zigzags.num,
            self.zigzags.txt
        )
        self.assertEqual(self.zigzags.idn, word.idn)
        self.assertEqual(self.zigzags.sbj, word.sbj)
        self.assertEqual(self.zigzags.vrb, word.vrb)
        self.assertEqual(self.zigzags.obj, word.obj)
        self.assertEqual(self.zigzags.num, word.num)
        self.assertEqual(self.zigzags.txt, word.txt)
        self.assertEqual(self.zigzags.whn, word.whn)

    def test_lex_from_sbj_vrb_obj_num_txt_words(self):
        word = self.lex.spawn()
        self.lex.populate_word_from_sbj_vrb_obj_num_txt(
            word,
            self.lex[self.zigzags.sbj],
            self.lex[self.zigzags.vrb],
            self.lex[self.zigzags.obj],
            self.zigzags.num,
            self.zigzags.txt
        )
        self.assertEqual(self.zigzags.idn, word.idn)
        self.assertEqual(self.zigzags.sbj, word.sbj)
        self.assertEqual(self.zigzags.vrb, word.vrb)
        self.assertEqual(self.zigzags.obj, word.obj)
        self.assertEqual(self.zigzags.num, word.num)
        self.assertEqual(self.zigzags.txt, word.txt)
        self.assertEqual(self.zigzags.whn, word.whn)

    def test_lex_table_not_writable(self):
        with self.assertRaises(AttributeError):
            # noinspection PyPropertyAccess
            self.lex.table = 'something'

    # def test_wrong_word_method_infinity(self):
    #     word = self.lex[u'noun']
    #     with self.assertRaises(qiki.Word.NoSuchAttribute):
    #         # noinspection PyStatementEffect
    #         word.no_such_attribute
    #     with self.assertRaises(qiki.Word.NoSuchAttribute):
    #         word.no_such_method()

    # def test_wrong_lex_method_infinity(self):
    #     with self.assertRaises(qiki.Word.NoSuchAttribute):
    #         # noinspection PyStatementEffect
    #         self.lex.no_such_attribute
    #     with self.assertRaises(qiki.Word.NoSuchAttribute):
    #         self.lex.no_such_method()

    def test_super_select_idn_list(self):
        anna_and_bart = list(self.lex.super_select(
            'SELECT txt FROM', self.lex.table,
            'WHERE idn IN (', [
                self.anna.idn,
                self.bart.idn
            ], ')'
        ))
        self.assertEqual([
            {'txt': u'anna'},
            {'txt': u'bart'},
        ], anna_and_bart)

    def test_super_select_word_list(self):
        anna_and_bart = list(self.lex.super_select(
            'SELECT txt FROM', self.lex.table,
            'WHERE idn IN (', [
                self.anna,
                self.bart
            ], ')'
        ))
        self.assertEqual([
            {'txt': u'anna'},
            {'txt': u'bart'},
        ], anna_and_bart)

    def test_super_select_idn_tuple(self):
        anna_and_bart = list(self.lex.super_select(
            'SELECT txt FROM',self.lex.table,
            'WHERE idn IN (', (
                self.anna.idn,
                self.bart.idn
            ), ')'
        ))
        self.assertEqual([
            {'txt': u'anna'},
            {'txt': u'bart'},
        ], anna_and_bart)

    def test_super_select_word_tuple(self):
        anna_and_bart = list(self.lex.super_select(
            'SELECT txt FROM', self.lex.table,
            'WHERE idn IN (', (
                self.anna,
                self.bart
            ), ')'
        ))
        self.assertEqual([
            {'txt': u'anna'},
            {'txt': u'bart'},
        ], anna_and_bart)

    def test_super_select_mixed_tuple(self):
        anna_and_bart = list(self.lex.super_select(
            'SELECT txt FROM', self.lex.table,
            'WHERE idn IN (', (
                self.anna,
                self.bart.idn
            ), ')'
        ))
        self.assertEqual([
            {'txt': u'anna'},
            {'txt': u'bart'},
        ], anna_and_bart)

    def test_super_select_idn_set(self):
        set_of_idns = {
            self.anna.idn,
            self.bart.idn
        }
        assert type(set_of_idns) is set
        anna_and_bart = list(self.lex.super_select(
            'SELECT txt FROM',self.lex.table,
            'WHERE idn IN (', set_of_idns, ')'
        ))
        self.assertEqual([
            {'txt': u'anna'},
            {'txt': u'bart'},
        ], anna_and_bart)

    def test_super_select_word_set(self):
        set_of_words = {
            self.anna,
            self.bart
        }
        assert type(set_of_words) is set
        anna_and_bart = list(self.lex.super_select(
            'SELECT txt FROM',self.lex.table,
            'WHERE idn IN (', set_of_words, ')'
        ))
        self.assertEqual([
            {'txt': u'anna'},
            {'txt': u'bart'},
        ], anna_and_bart)

    def test_super_select_join(self):
        likings = list(self.lex.super_select(
            'SELECT '
                'w.idn AS idn, '
                'qool.idn AS qool_idn, '
                'qool.num AS qool_num '
            'FROM', self.lex.table, 'AS w '
            'JOIN', self.lex.table, 'AS qool '
                'ON qool.obj = w.idn '
                    'AND qool.vrb =', self.like,
            'ORDER BY w.idn, qool.idn ASC',
            debug=False
            # Query SELECT w.idn AS idn, qool.idn AS qool_idn, qool.num AS qool_num FROM `word_e3cda38fc1db4005a21808aec5d11cdf` AS w LEFT JOIN `word_e3cda38fc1db4005a21808aec5d11cdf` AS qool ON qool.obj = w.idn AND qool.vrb = ? WHERE qool.idn IS NOT NULL ORDER BY w.idn, qool.idn ASC
            # 	idn Number('0q82_0D'); qool_idn Number('0q82_0F'); qool_num Number('0q82_01');
            # 	idn Number('0q82_0D'); qool_idn Number('0q82_10'); qool_num Number('0q82_0A');
            # 	idn Number('0q82_0E'); qool_idn Number('0q82_11'); qool_num Number('0q82_02');
        ))
        self.assertEqual([
            {'idn': self.youtube.idn, 'qool_idn': self.anna_like_youtube.idn, 'qool_num': self.anna_like_youtube.num},
            {'idn': self.youtube.idn, 'qool_idn': self.bart_like_youtube.idn, 'qool_num': self.bart_like_youtube.num},
            {'idn': self.zigzags.idn, 'qool_idn': self.anna_like_zigzags.idn, 'qool_num': self.anna_like_zigzags.num},
        ], likings)

    def test_super_select_join_qool_list(self):
        likings = list(self.lex.super_select(
            'SELECT '
                'w.idn AS idn, '
                'qool.idn AS qool_idn, '
                'qool.num AS qool_num '
            'FROM', self.lex.table, 'AS w '
            'JOIN', self.lex.table, 'AS qool '
                'ON qool.obj = w.idn '
                    'AND qool.vrb IN (', self.qool_idns, ') '
            'ORDER BY w.idn, qool.idn ASC',
            debug=False
        ))
        self.assertEqual([
            {'idn': self.youtube.idn, 'qool_idn': self.anna_like_youtube.idn,   'qool_num': self.anna_like_youtube.num},
            {'idn': self.youtube.idn, 'qool_idn': self.bart_like_youtube.idn,   'qool_num': self.bart_like_youtube.num},
            {'idn': self.zigzags.idn, 'qool_idn': self.anna_like_zigzags.idn,   'qool_num': self.anna_like_zigzags.num},
            {'idn': self.zigzags.idn, 'qool_idn': self.bart_delete_zigzags.idn, 'qool_num': self.bart_delete_zigzags.num},
        ], likings)

    def test_find_words(self):
        nouns = self.lex.find_words(obj=self.lex.noun())
        self.assertEqual(5, len(nouns))
        self.assertEqual(u'noun', nouns[0].txt)
        self.assertEqual(u'verb', nouns[1].txt)
        self.assertEqual(u'agent', nouns[2].txt)
        self.assertEqual(u'youtube', nouns[3].txt)
        self.assertEqual(u'zigzags', nouns[4].txt)

    def test_find_words_jbo(self):
        nouns = self.lex.find_words(obj=self.lex.noun(), jbo_vrb=self.qool_idns)
        self.assertEqual(5, len(nouns))

        self.assertEqual(u'noun',    nouns[0].txt)
        self.assertEqual(u'verb',    nouns[1].txt)
        self.assertEqual(u'agent',   nouns[2].txt)
        self.assertEqual(u'youtube', nouns[3].txt)
        self.assertEqual(u'zigzags', nouns[4].txt)

        self.assertEqual(0, len(nouns[0].jbo))
        self.assertEqual(0, len(nouns[1].jbo))
        self.assertEqual(0, len(nouns[2].jbo))
        self.assertEqual(2, len(nouns[3].jbo))
        self.assertEqual(       nouns[3].jbo[0].idn, self.anna_like_youtube.idn)
        self.assertEqual(       nouns[3].jbo[0].num, qiki.Number(1))
        self.assertEqual(       nouns[3].jbo[1].idn, self.bart_like_youtube.idn)
        self.assertEqual(       nouns[3].jbo[1].num, qiki.Number(10))
        self.assertEqual(2, len(nouns[4].jbo))
        self.assertEqual(       nouns[4].jbo[0].idn, self.anna_like_zigzags.idn)
        self.assertEqual(       nouns[4].jbo[0].num, qiki.Number(2))
        self.assertEqual(       nouns[4].jbo[1].idn, self.bart_delete_zigzags.idn)
        self.assertEqual(       nouns[4].jbo[1].num, qiki.Number(1))

    # TODO:  Test jbo_vrb = a single verb, not just a container
    # TODO:  Test jbo_vrb = idn

    def find_b_l_y(self):   # Find all the words where bart likes youtube.
        return self.lex.find_words(sbj=self.bart, vrb=self.like, obj=self.youtube)

    def test_num_replace_num(self):
        b_l_y_before = self.find_b_l_y()
        self.bart.says(self.like, self.youtube, 20)
        b_l_y_after = self.find_b_l_y()
        self.assertEqual(len(b_l_y_after), len(b_l_y_before) + 1)
        self.assertEqual(qiki.Number(20), b_l_y_after[-1].num)

    def test_num_replace_named_num(self):
        b_l_y_before = self.find_b_l_y()
        self.bart.says(self.like, self.youtube, num=20)
        b_l_y_after = self.find_b_l_y()
        self.assertEqual(len(b_l_y_after), len(b_l_y_before) + 1)
        self.assertEqual(qiki.Number(20), b_l_y_after[-1].num)

    def test_num_add(self):
        b_l_y_before = self.find_b_l_y()
        self.bart.says(self.like, self.youtube, num_add=20)
        b_l_y_after = self.find_b_l_y()
        self.assertEqual(len(b_l_y_after), len(b_l_y_before) + 1)
        self.assertEqual(10, b_l_y_before[-1].num)
        self.assertEqual(30, b_l_y_after[-1].num)

    def find_a_d_z(self):   # Find all the words where bart likes youtube.
        return self.lex.find_words(sbj=self.anna, vrb=self.delete, obj=self.zigzags)

    def test_num_add_out_of_the_blue(self):
        a_d_z_before = self.find_a_d_z()
        self.assertEqual(0, len(a_d_z_before))
        self.anna.says(self.delete, self.zigzags, num_add=-100)
        a_d_z_after = self.find_a_d_z()
        self.assertEqual(1, len(a_d_z_after))
        self.assertEqual(-100, a_d_z_after[0].num)


    ################## obsolete or maybe someday #################################

    # def test_02_word_by_name(self):
    #     define = qiki.Word('define')
    #     self.assertEqual('define', define.txt)
    #
    # def test_02_word_by_idn(self):
    #     define = qiki.Word('define')
    #     define_too = qiki.Word(define.idn)
    #     self.assertEqual('define', define_too.txt)
    #
    # def test_02_word_by_word(self):
    #     """Word copy constructor."""
    #     define = qiki.Word('define')
    #     define_too = qiki.Word(define)
    #     self.assertEqual('define', define_too.txt)
    #
    # def test_quintuple_self_evident(self):
    #     define = qiki.Word('define')
    #     self.assertEqual(define.vrb, define.idn)
    #     noun = qiki.Word('noun')
    #     self.assertEqual(noun.obj, noun.idn)
    #     verb = qiki.Word('verb')
    #     self.assertEqual(verb.obj, noun.idn)
    #     agent = qiki.Word('agent')
    #     self.assertEqual(agent.obj, noun.idn)
    #     lex = qiki.Word('lex')
    #     self.assertEqual(lex.sbj, lex.idn)
    #     self.assertEqual(lex.obj, agent.idn)
    #
    # def test_word_cant_construct_unfamiliar_class(self):
    #     # noinspection PyClassHasNoInit
    #     class UnExpected:
    #         pass
    #     with self.assertRaises(TypeError):
    #         qiki.Word(UnExpected)
    #
    # def test_by_idn(self):
    #     define = qiki.Word('define')
    #     define2 = qiki.Word(define.idn)
    #     self.assertEqual('define', define2.txt)
    #     self.assertEqual(define.idn, define2.idn)
    #
    # def test_repr(self):
    #     define = qiki.Word('define')
    #     self.assertIn('define', repr(define))
    #     self.assertEqual("Word('define')", repr(define))
    #
    # def test_defined_verb(self):
    #     self.assertTrue(qiki.Word('define').exists)
    #
    # def test_undefined_verb(self):
    #     u = qiki.Word('_undefined_verb_')
    #     self.assertFalse(u.exists)
    #
    # def test_is_a(self):
    #     self.assertTrue( qiki.Word('verb').is_a(qiki.Word('noun')))
    #     self.assertFalse(qiki.Word('noun').is_a(qiki.Word('verb')))
    #
    # def test_zz1_define_noun(self):
    #     lex = qiki.Word('lex')
    #     noun = qiki.Word('noun')
    #     human = lex.define(noun, 'human')
    #     self.assertTrue(human.exists)
    #     self.assertEqual('human', human.txt)
    #
    # def test_zz1_define_by_idn(self):
    #     lex = qiki.Word('lex')
    #     noun = qiki.Word('noun')
    #     human = lex.define(noun, 'human')
    #     self.assertTrue(human.exists)
    #     self.assertEqual('human', human.txt)
    #
    # def test_zz1_noun_method(self):
    #     lex = qiki.Word('lex')
    #     thing = lex.noun('thing')
    #     self.assertTrue(thing.exists)
    #     self.assertEqual('thing', thing.txt)
    #
    # def test_zz2_define_collision(self):
    #     lex = qiki.Word('lex')
    #     noun = qiki.Word('noun')
    #     lex.define(noun, 'human')
    #     with self.assertRaises(qiki.Word.DefineDuplicateException):
    #         lex.define(noun, 'human')
    #
    # def test_zz3_define_verb(self):
    #     lex = qiki.Word('lex')
    #     verb = qiki.Word('verb')
    #     like = lex.define(verb, 'like')
    #     self.assertEqual(like.txt, 'like')
    #     self.assertEqual(like.obj, verb.idn)
    #     qiki.Word.make_verb_a_method(like)
    #     rating = lex.like(lex, lex, 'loving itself', qiki.Number(100))
    #     print(rating.description())
    #     self.assertEqual(qiki.Number(100), rating.num)
    #     self.assertEqual('loving itself', rating.txt)
    #
    # def someday_test_zz3_define_verb_slimmer(self):
    #     qiki.Word.noun('human')
    #     qiki.Word.verb('like')
    #     anna = qiki.Word.human('Anna')
    #     bart = qiki.Word.human('Bart')
    #     chet = qiki.Word.human('Chet')
    #     anna_likes_bart = anna.like(bart, "He's just so dreamy.", qiki.Number(10))
    #     anna_likes_chet = anna.like(chet, "He's alright I guess.", qiki.Number(9))
    #     print("anna likes two boys", anna_likes_bart.num, anna_likes_chet.num)


# noinspection PyClassHasNoInit
class SomeType:
    pass
some_type = SomeType()


if __name__ == '__main__':
    import unittest
    unittest.main()
