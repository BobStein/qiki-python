# coding=utf-8
"""
Testing qiki word.py
"""

from __future__ import print_function
import unittest
import six
import sys
import time
import uuid
import warnings

import qiki
from number import hex_from_string
from word import idn_from_word_or_number

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

class WordTests(unittest.TestCase):

    def setUp(self):
        credentials = secure.credentials.for_unit_testing_database.copy()
        if RANDOMIZE_DATABASE_TABLE:
            credentials['table'] = 'word_' + uuid.uuid4().hex
        self.lex = qiki.LexMySQL(**credentials)
        self.lex.uninstall_to_scratch()
        self.lex.install_from_scratch()

    def tearDown(self):
        if not LET_DATABASE_RECORDS_REMAIN:
            self.lex.uninstall_to_scratch()
        self.lex.disconnect()

    def display_all_word_descriptions(self):
        words = self.lex.find_words()
        for word in words:
            print(int(word.idn), word.description())

    def show_txt_in_utf8(self, idn):
        word = self.lex(idn)
        utf8 = word.txt.encode('utf-8')
        hexadecimal = hex_from_string(utf8)
        print("\"{txt}\" in utf8 is {hex}".format(
            txt=word.txt.encode('unicode_escape'),   # Python 3 doubles up the backslashes ... shrug.
            hex=hexadecimal,
        ))

    def assertSensibleWhen(self, whn):
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

    def assertNoNewWords(self, message=None):
        return self.assertNewWords(0, message)

    def assertNewWord(self, message=None):
        return self.assertNewWords(1, message)


class InternalTestWordTests(WordTests):
    """Test WordTests class itself."""

    def test_assertNoNewWords(self):
        with self.assertNoNewWords():
            pass
        with self.assertRaises(self._CheckNewWordCount.WordCountFailure):
            with self.assertNoNewWords():
                self._make_one_new_word('shrubbery')

    def test_assertNewWords(self):
        with self.assertNewWords(1):
            self._make_one_new_word('shrubbery')
        with self.assertRaises(self._CheckNewWordCount.WordCountFailure):
            with self.assertNewWords(1):
                pass

    def test_assertNewWord(self):
        with self.assertNewWord():   # Succeeds if just the right number of words are created.
            self._make_one_new_word('shrubbery')
        with self.assertNewWords(2):
            self._make_one_new_word('swallow')
            self._make_one_new_word('gopher')
        with self.assertRaises(self._CheckNewWordCount.WordCountFailure):
            with self.assertNewWord():   # Fails if too few.
                pass
        with self.assertRaises(self._CheckNewWordCount.WordCountFailure):
            with self.assertNewWord():   # Fails if too many.
                self._make_one_new_word('knight')
                self._make_one_new_word('rabbit')

    def _make_one_new_word(self, txt):
        self.lex.define(self.lex('noun'), txt)

    def test_missing_from_lex(self):
        self.lex(qiki.Word._IDN_DEFINE)
        with self.assertRaises(qiki.Word.MissingFromLex):
            self.lex(qiki.Number(-42))


class WordFirstTests(WordTests):

    def test_00_number(self):
        n = qiki.Number(1)
        self.assertEqual(1, int(n))

    def test_01a_lex(self):
        self.assertEqual(self.lex._IDN_LEX,        self.lex.idn)
        self.assertEqual(self.lex._IDN_LEX,        self.lex.sbj)
        self.assertEqual(self.lex('define').idn,   self.lex.vrb)
        self.assertEqual(self.lex('agent').idn,    self.lex.obj)
        self.assertEqual(qiki.Number(1),           self.lex.num)
        self.assertEqual('lex',                    self.lex.txt)
        self.assertSensibleWhen(                   self.lex.whn)
        self.assertTrue(self.lex.is_lex())

    def test_01b_lex_getter(self):
        define = self.lex('define')
        self.assertTrue(define.exists)
        self.assertEqual(define.idn, qiki.Word._IDN_DEFINE)
        self.assertEqual(define.sbj, qiki.Word._IDN_LEX)
        self.assertEqual(define.vrb, qiki.Word._IDN_DEFINE)
        self.assertEqual(define.obj, qiki.Word._IDN_VERB)
        self.assertEqual(define.num, qiki.Number(1))
        self.assertEqual(define.txt, 'define')

    def test_01c_lex_bum_getter(self):
        define = self.lex('word that does not exist')
        self.assertFalse(define.exists)
        self.assertTrue(define.idn.is_nan())
        self.assertFalse(hasattr(define, 'sbj'))
        self.assertFalse(hasattr(define, 'vrb'))
        self.assertFalse(hasattr(define, 'obj'))
        self.assertFalse(hasattr(define, 'num'))
        self.assertEqual(define.txt, 'word that does not exist')

    def test_02_noun(self):
        noun = self.lex('noun')
        self.assertTrue(noun.exists)
        self.assertTrue(noun.is_noun())
        self.assertEqual('noun', noun.txt)

    def test_02a_str(self):
        self.assertEqual('noun', str(self.lex('noun')))

    def test_02b_unicode(self):
        self.assertEqual(u'noun', six.text_type(self.lex('noun')))
        self.assertIsInstance(six.text_type(self.lex('noun')), six.text_type)

    def test_02b_repr(self):
        self.assertEqual("Word('noun')", repr(self.lex('noun')))

    def test_03a_max_idn(self):
        self.assertEqual(qiki.Word._IDN_MAX_FIXED, self.lex.max_idn())

    def test_03b_noun_spawn(self):
        noun = self.lex('noun')
        thing = noun('thing')
        self.assertTrue(thing.exists)
        self.assertEqual('thing', thing.txt)

    def test_03c_noun_spawn_crazy_syntax(self):
        thing = self.lex('noun')('thing')
        self.assertTrue(thing.exists)
        self.assertEqual('thing', thing.txt)

    def test_04_is_a(self):
        verb = self.lex('verb')
        noun = self.lex('noun')
        thing = noun('thing')
        cosa = thing('cosa')

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
        noun = self.lex.noun
        self.assertTrue(noun.is_a_noun(recursion=0))
        self.assertTrue(noun.is_a_noun(recursion=1))
        self.assertTrue(noun.is_a_noun(recursion=2))
        self.assertTrue(noun.is_a_noun(recursion=3))

        child1 = noun('child1')
        self.assertFalse(child1.is_a_noun(recursion=0))
        self.assertTrue(child1.is_a_noun(recursion=1))
        self.assertTrue(child1.is_a_noun(recursion=2))
        self.assertTrue(child1.is_a_noun(recursion=3))

        child2 = child1('child2')
        self.assertFalse(child2.is_a_noun(recursion=0))
        self.assertFalse(child2.is_a_noun(recursion=1))
        self.assertTrue(child2.is_a_noun(recursion=2))
        self.assertTrue(child2.is_a_noun(recursion=3))

        child12 = child2('child3')('child4')('child5')('child6')('child7')('child8')('child9')('child10')('child11')('child12')
        self.assertFalse(child12.is_a_noun(recursion=10))
        self.assertFalse(child12.is_a_noun(recursion=11))
        self.assertTrue(child12.is_a_noun(recursion=12))
        self.assertTrue(child12.is_a_noun(recursion=13))

    def test_04_is_a_noun(self):
        self.assertTrue(self.lex.is_a_noun())
        self.assertTrue(self.lex('lex').is_a_noun())
        self.assertTrue(self.lex('agent').is_a_noun())
        self.assertTrue(self.lex('noun').is_a_noun(reflexive=True))
        self.assertTrue(self.lex('noun').is_a_noun(reflexive=False))   # noun is explicitly defined as a noun
        self.assertTrue(self.lex('noun').is_a_noun())
        self.assertTrue(self.lex('verb').is_a_noun())
        self.assertTrue(self.lex('define').is_a_noun())

    def test_05_noun_grandchild(self):
        agent = self.lex('agent')
        human = agent('human')
        self.assertEqual('human', human.txt)

    def test_06_noun_great_grandchild(self):
        noun = self.lex('noun')
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

    def test_07_noun_great_great_grandchild(self):
        greatgrandchild = self.lex('noun')('child')('grandchild')('greatgrandchild')
        greatgreatgrandchild = greatgrandchild('greatgreatgrandchild')
        self.assertEqual('greatgreatgrandchild', greatgreatgrandchild.txt)

    def test_07_is_a_noun_great_great_grandchild(self):
        noun = self.lex('noun')
        child = noun('child')
        grandchild = child('grandchild')
        greatgrandchild = grandchild('greatgrandchild')
        greatgreatgrandchild = greatgrandchild('greatgreatgrandchild')
        self.assertTrue(noun.is_a_noun())
        self.assertTrue(child.is_a_noun())
        self.assertTrue(grandchild.is_a_noun())
        self.assertTrue(greatgrandchild.is_a_noun())
        self.assertTrue(greatgreatgrandchild.is_a_noun())

    def test_08_noun_twice(self):
        noun = self.lex('noun')
        with self.assertNewWord():
            thing1 = noun('thing')
        with self.assertNoNewWords():
            thing2 = noun('thing')
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
        noun1 = self.lex('noun')
        noun2 = self.lex('noun')
        self.assertEqual(noun1, noun2)
        self.assertIsNot(noun1, noun2)

    def test_09a_equality_by_copy_constructor(self):
        noun1 = self.lex('noun')
        noun2 = qiki.Word(noun1)
        self.assertEqual(noun1, noun2)
        self.assertIsNot(noun1, noun2)

    def test_09b_lex_singleton_by_attribute(self):
        lex1 = self.lex
        lex2 = self.lex.lex
        self.assertEqual(lex1, lex2)
        self.assertIs(lex1, lex2)

    def test_09b_lex_singleton_by_call(self):
        lex1 = self.lex
        lex2 = self.lex('lex')
        self.assertEqual(lex1, lex2)
        self.assertIs(lex1, lex2)   # Why does this work?

    def test_09b_lex_singleton_cant_do_by_copy_constructor(self):
        with self.assertRaises(ValueError):
            qiki.Word(self.lex)

    def test_10a_word_by_lex_idn(self):
        agent = self.lex(qiki.Word._IDN_AGENT)
        self.assertEqual(agent.txt, 'agent')

    def test_10b_word_by_lex_txt(self):
        agent = self.lex('agent')
        self.assertEqual(agent.idn, qiki.Word._IDN_AGENT)

    def test_11a_noun_inserted(self):
        new_word = self.lex.noun('something')
        self.assertEqual(self.lex.max_idn(),     new_word.idn)
        self.assertEqual(self.lex._IDN_LEX,       new_word.sbj)
        self.assertEqual(self.lex('define').idn, new_word.vrb)
        self.assertEqual(self.lex('noun').idn,   new_word.obj)
        self.assertEqual(qiki.Number(1),         new_word.num)
        self.assertEqual('something',            new_word.txt)
        self.assertSensibleWhen(                 new_word.whn)

    def test_11b_whn(self):
        define = self.lex('define')
        new_word = self.lex.noun('something')
        self.assertSensibleWhen(define.whn)
        self.assertSensibleWhen(new_word.whn)
        self.assertGreaterEqual(float(new_word.whn), float(define.whn))

    def test_12_vrb(self):
        anna = self.lex.agent('anna')
        self.lex.verb('like')
        self.lex.noun('yurt')
        zarf = self.lex.noun('zarf')
        anna.like(zarf, 1)
        self.assertTrue(anna.like.is_a_verb())
        self.assertFalse(anna.yurt.is_a_verb())
        self.assertEqual('yurt', anna.yurt.txt)
        with self.assertRaises(TypeError):
            anna.yurt(zarf, txt='', num=1)
            # FIXME:  Can we even come up with a s.v(o) where v is not a verb,
            # and something else isn't happening?  This example is at best a highly
            # corrupted form of o(t), aka lex.define(o,t).



class WordUnicode(WordTests):

    def setUp(self):
        super(WordUnicode, self).setUp()
        self.anna =    self.lex.noun('anna')
        self.comment = self.lex.verb('comment')
        self.zarf =    self.lex.noun('zarf')

    def test_unicode_a_utf8_ascii(self):
        assert u"ascii" == u"ascii"
        if six.PY2:
            assert u"ascii" == b"ascii"
            assert u"ascii" == u"ascii".encode('utf-8')
        if six.PY3:
            assert u"ascii" != b"ascii"
            assert u"ascii" != u"ascii".encode('utf-8')
        self.assertEqual(u"ascii", self.lex(self.anna.comment(self.zarf, 1, b"ascii").idn).txt)

    def test_unicode_b_unicode_ascii(self):
        self.assertEqual(u"ascii", self.lex(self.anna.comment(self.zarf, 1, u"ascii").idn).txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    # TODO:  D.R.Y. the pairs of tests that follow

    # Unicode characters in comments

    def test_unicode_c_utf8_spanish(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            assert u"mañana" == u"ma\xF1ana"
            assert u"mañana" != u"ma\xF1ana".encode('utf-8')
            assert b"ma\xc3\xb1ana" == u"ma\xF1ana".encode('utf-8')
        comment = self.anna.comment(self.zarf, 1, u"mañana".encode('utf-8'))
        self.assertEqual(u"ma\xF1ana", self.lex(comment.idn).txt)

    def test_unicode_d_unicode_spanish(self):
        comment = self.anna.comment(self.zarf, 1, u"mañana")
        self.assertEqual(u"ma\xF1ana", self.lex(comment.idn).txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    def test_unicode_e_utf8_peace(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            assert u"☮ on earth" == u"\u262E on earth"
            assert u"☮ on earth" != u"\u262E on earth".encode('utf-8')
            assert b"\xe2\x98\xae on earth" == u"\u262E on earth".encode('utf-8')
        comment = self.anna.comment(self.zarf, 1, u"☮ on earth".encode('utf-8'))
        self.assertEqual(u"\u262E on earth", self.lex(comment.idn).txt)

    def test_unicode_f_unicode_peace(self):
        comment = self.anna.comment(self.zarf, 1, u"☮ on earth")
        self.assertEqual(u"\u262E on earth", self.lex(comment.idn).txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    if TEST_ASTRAL_PLANE:

        def test_unicode_g_utf8_pile_of_poo(self):
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                assert u"stinky \U0001F4A9" == u"stinky \U0001F4A9"
                assert u"stinky \U0001F4A9" != u"stinky \U0001F4A9".encode('utf-8')
                assert b"stinky \xf0\x9f\x92\xa9" == u"stinky \U0001F4A9".encode('utf-8')
            # Source code is base plane only, so cannot:  assert u"stinky ?" == u"stinky \U0001F4A9"
            # PyCharm editor limitation?
            comment = self.anna.comment(self.zarf, 1, u"stinky \U0001F4A9".encode('utf-8'))
            self.assertEqual(u"stinky \U0001F4A9", self.lex(comment.idn).txt)

        def test_unicode_h_unicode_pile_of_poo(self):
            comment = self.anna.comment(self.zarf, 1, u"stinky \U0001F4A9")
            self.assertEqual(u"stinky \U0001F4A9", self.lex(comment.idn).txt)
            if SHOW_UTF8_EXAMPLES:
                self.show_txt_in_utf8(self.lex.max_idn())

    # Unicode characters in verbs

    def test_unicode_i_verb_utf8_ascii(self):
        sentence1 = self.lex.define(self.comment, u"remark".encode('utf-8'))
        sentence2 = self.lex(sentence1.idn)
        self.assertEqual(u"remark", sentence2.txt)
        self.assertTrue(self.lex.remark.is_a_verb())

    def test_unicode_j_verb_unicode_ascii(self):
        sentence1 = self.lex.define(self.comment, u"remark")
        sentence2 = self.lex(sentence1.idn)
        self.assertEqual(u"remark", sentence2.txt)
        self.assertTrue(self.lex.remark.is_a_verb())

    def test_unicode_k_verb_utf8_spanish(self):
        sentence1 = self.lex.define(self.comment, u"comentó".encode('utf-8'))
        sentence2 = self.lex(sentence1.idn)
        self.assertEqual(u"comentó", sentence2.txt)
        if six.PY3:
            # Only Python 3 supports international characters in Python symbols.
            self.assertTrue(eval(u'self.lex.comentó.is_a_verb()'))
        if six.PY2:
            with self.assertRaises(SyntaxError):
                eval(u'self.lex.comentó.is_a_verb()')
        self.assertTrue(self.lex(u'comentó').exists)
        self.assertTrue(self.lex(u'comentó').is_a_verb())
        self.assertTrue(self.lex(u'comentó'.encode('utf-8')).exists)
        self.assertTrue(self.lex(u'comentó'.encode('utf-8')).is_a_verb())

    def test_unicode_l_verb_unicode_spanish(self):
        sentence1 = self.lex.define(self.comment, u"comentó")
        sentence2 = self.lex(sentence1.idn)
        self.assertEqual(u"comentó", sentence2.txt)
        if six.PY3:
            self.assertTrue(eval(u'self.lex.comentó.is_a_verb()'))
        if six.PY2:
            with self.assertRaises(SyntaxError):
                eval(u'self.lex.comentó.is_a_verb()')
        self.assertTrue(self.lex(u'comentó').exists)
        self.assertTrue(self.lex(u'comentó').is_a_verb())
        self.assertTrue(self.lex(u'comentó'.encode('utf-8')).exists)
        self.assertTrue(self.lex(u'comentó'.encode('utf-8')).is_a_verb())

    # noinspection SpellCheckingInspection
    def test_unicode_m_verb_utf8_encourage(self):
        sentence1 = self.lex.define(self.comment, u"enc☺urage".encode('utf-8'))
        sentence2 = self.lex(sentence1.idn)
        self.assertEqual(u"enc☺urage", sentence2.txt)
        with self.assertRaises(SyntaxError):
            # Even Python has restraint.
            eval(u'self.lex.enc☺urage.is_a_verb()')
        self.assertTrue(self.lex(u'enc☺urage').exists)
        self.assertTrue(self.lex(u'enc☺urage').is_a_verb())
        self.assertTrue(self.lex(u'enc☺urage'.encode('utf-8')).exists)
        self.assertTrue(self.lex(u'enc☺urage'.encode('utf-8')).is_a_verb())

    # noinspection SpellCheckingInspection
    def test_unicode_n_verb_unicode_encourage(self):
        sentence1 = self.lex.define(self.comment, u"enc☺urage")
        sentence2 = self.lex(sentence1.idn)
        self.assertEqual(u"enc☺urage", sentence2.txt)
        with self.assertRaises(SyntaxError):
            eval(u'self.lex.enc☺urage.is_a_verb()')
        self.assertTrue(self.lex(u'enc☺urage').exists)
        self.assertTrue(self.lex(u'enc☺urage').is_a_verb())
        self.assertTrue(self.lex(u'enc☺urage'.encode('utf-8')).exists)
        self.assertTrue(self.lex(u'enc☺urage'.encode('utf-8')).is_a_verb())

    if TEST_ASTRAL_PLANE:

        # noinspection SpellCheckingInspection
        def test_unicode_o_verb_utf8_alien_face(self):
            sentence1 = self.lex.define(self.comment, u"\U0001F47Dlienate".encode('utf-8'))
            sentence2 = self.lex(sentence1.idn)
            self.assertEqual(u"\U0001F47Dlienate", sentence2.txt)
            with self.assertRaises(SyntaxError):
                eval(u'self.lex.\U0001F47Dlienate.is_a_verb()')
            self.assertTrue(self.lex(u'\U0001F47Dlienate').exists)
            self.assertTrue(self.lex(u'\U0001F47Dlienate').is_a_verb())
            self.assertTrue(self.lex(u'\U0001F47Dlienate'.encode('utf-8')).exists)
            self.assertTrue(self.lex(u'\U0001F47Dlienate'.encode('utf-8')).is_a_verb())

        # noinspection SpellCheckingInspection
        def test_unicode_o_verb_unicode_alien_face(self):
            sentence1 = self.lex.define(self.comment, u"\U0001F47Dlienate")
            sentence2 = self.lex(sentence1.idn)
            self.assertEqual(u"\U0001F47Dlienate", sentence2.txt)
            with self.assertRaises(SyntaxError):
                eval(u'self.lex.\U0001F47Dlienate.is_a_verb()')
            self.assertTrue(self.lex(u'\U0001F47Dlienate').exists)
            self.assertTrue(self.lex(u'\U0001F47Dlienate').is_a_verb())
            self.assertTrue(self.lex(u'\U0001F47Dlienate'.encode('utf-8')).exists)
            self.assertTrue(self.lex(u'\U0001F47Dlienate'.encode('utf-8')).is_a_verb())


class WordMoreTests(WordTests):

    def test_describe(self):
        thing = self.lex('noun')('thingamajig')
        self.assertIn('thingamajig', thing.description())

    def test_short_and_long_ways(self):
        noun = self.lex('noun')
        thing1 = noun('thing')
        thing2 = self.lex.noun('thing')
        thing3 = self.lex.define(noun, 'thing')
        self.assertEqual(thing1.idn,           thing2.idn          )
        self.assertEqual(thing1.idn,           thing3.idn          )
        self.assertEqual(thing1.description(), thing2.description())
        self.assertEqual(thing1.description(), thing3.description())
        self.assertEqual(thing1,               thing2              )
        self.assertEqual(thing1,               thing3              )

        subthing1 = thing1('subthing1')
        subthing2 = thing2('subthing2')
        subthing3 = thing3('subthing3')
        self.assertTrue(subthing1.exists)
        self.assertTrue(subthing2.exists)
        self.assertTrue(subthing3.exists)
        self.assertEqual('subthing1', subthing1.txt)
        self.assertEqual('subthing2', subthing2.txt)
        self.assertEqual('subthing3', subthing3.txt)

    def test_verb(self):
        self.lex.verb('like')
        like = self.lex('like')
        self.assertEqual(self.lex.idn, like.sbj)

    def test_is_a_verb(self):
        verb = self.lex('verb')
        noun = self.lex('noun')
        like = verb('like')
        yurt = self.lex.noun('yurt')
        self.assertTrue(like.is_a_verb())
        self.assertTrue(verb.is_a_verb(reflexive=True))
        self.assertFalse(verb.is_a_verb(reflexive=False))
        self.assertFalse(verb.is_a_verb())
        self.assertFalse(noun.is_a_verb())
        self.assertFalse(yurt.is_a_verb())

        self.assertFalse(self.lex('noun').is_a_verb())
        self.assertFalse(self.lex('verb').is_a_verb())
        self.assertTrue(self.lex('define').is_a_verb())
        self.assertFalse(self.lex('agent').is_a_verb())
        self.assertFalse(self.lex('lex').is_a_verb())

    def test_verb_use(self):
        """Test that sbj.vrb(obj, num) creates a word.  And sbj.vrb(obj).num reads it back."""
        agent = self.lex('agent')
        human = agent('human')
        self.lex.verb('like')
        anna = human('anna')
        bart = human('bart')
        chad = human('chad')
        dirk = human('dirk')
        anna.like(anna, 1, "Narcissism.")
        anna.like(bart, 8, "Okay.")
        anna.like(chad, 10)
        anna.like(dirk, 1)
        self.assertFalse(anna.like.is_lex())
        self.assertFalse(anna.like.is_verb())
        self.assertEqual(1, anna.like(anna).num)
        self.assertEqual(8, anna.like(bart).num)
        self.assertEqual(10, anna.like(chad).num)
        self.assertEqual(1, anna.like(dirk).num)
        self.assertEqual("Narcissism.", anna.like(anna).txt)
        self.assertEqual("Okay.", anna.like(bart).txt)
        self.assertEqual("", anna.like(chad).txt)
        self.assertEqual("", anna.like(dirk).txt)

    def test_verb_use_alt(self):
        """Test that lex.verb can be copied by assignment, and still work."""
        human = self.lex.agent('human')
        anna = human('anna')
        bart = human('bart')
        verb = self.lex.verb
        verb('like')
        anna.like(bart, 13)
        self.assertEqual(13, anna.like(bart).num)

    # def OBSOLETE_test_repr(self):
    #     self.assertEqual("Word('noun')", repr(self.lex('noun')))
    #     human = self.lex.agent('human')
    #     self.assertEqual("Word('human')", repr(human))
    #     like = self.lex.verb('like')
    #     self.assertEqual("Word('like')", repr(like))
    #     liking = self.lex.like(human, 10)
    #     self.assertEqual("Word(Number({idn}))".format(idn=liking.idn.qstring()), repr(liking))
    #     # w = self.lex.spawn(sbj=Number(15), vrb=Number(31), obj=Number(63), num=Number(127), txt='something')
    #     # Word(sbj=0q82_0F, vrb=0q82_1F, obj=0q82_3F, txt='something', num=0q82_7F)
    #     # print(repr(w))

    def test_verb_txt(self):
        """Test s.v(o, n, txt).  Read with s.v(o).txt"""
        human = self.lex.agent('human')
        anna = human('anna')
        bart = human('bart')
        self.lex.verb('like')
        anna.like(bart, 5, "just as friends")
        self.assertEqual("just as friends", anna.like(bart).txt)

    def test_verb_overlay(self):
        """Test multiple s.v(o, num) calls with different num's.  Read with s.v(o).num"""
        human = self.lex.agent('human')
        anna = human('anna')
        bart = human('bart')
        self.lex.verb('like')

        with self.assertNewWord():
            anna.like(bart, 8)
        with self.assertNoNewWords():
            anna.like(bart)
        self.assertEqual(8, anna.like(bart).num)

        with self.assertNewWord():
            anna.like(bart, 10)
        self.assertEqual(10, anna.like(bart).num)

        with self.assertNewWord():
            anna.like(bart, 2)
        self.assertEqual(2, anna.like(bart).num)

    def test_verb_overlay_duplicate(self):
        human = self.lex.agent('human')
        anna = human('anna')
        bart = human('bart')
        self.lex.verb('like')

        with self.assertNewWord():
            anna.like(bart, 5, "just as friends")

        # with self.assertNoNewWords("Identical s.v(o,n,t) shouldn't generate a new word."):
        #     anna.like(bart, 5, "just as friends")
        # TODO:  Decide whether these "duplicates" should be errors or insert new records or not...
        # TODO:  Probably it should be an error for some verbs (e.g. like) and not for others (e.g. comment)
        # TODO: 'unique' option?  Imbue "like" verb with properties using Words??

        with self.assertNewWord():
            anna.like(bart, 5, "maybe more than friends")

        with self.assertNewWord():
            anna.like(bart, 6, "maybe more than friends")

        with self.assertNewWord():
            anna.like(bart, 7, "maybe more than friends")

        # with self.assertNoNewWords():
        #     anna.like(bart, 7, "maybe more than friends")

        with self.assertNewWord():
            anna.like(bart, 5, "just friends")

    def test_is_defined(self):
        self.assertTrue(self.lex('noun').is_defined())
        self.assertTrue(self.lex('verb').is_defined())
        self.assertTrue(self.lex('define').is_defined())
        self.assertTrue(self.lex('agent').is_defined())
        self.assertTrue(self.lex.is_defined())

        human = self.lex.agent('human')
        anna = human('anna')
        bart = human('bart')
        like = self.lex.verb('like')
        liking = anna.like(bart, 5)

        self.assertTrue(human.is_defined())
        self.assertTrue(anna.is_defined())
        self.assertTrue(bart.is_defined())
        self.assertTrue(like.is_defined())
        self.assertFalse(liking.is_defined())

    def test_non_verb_undefined_as_function_disallowed(self):
        human = self.lex.agent('human')
        anna = human('anna')
        bart = human('bart')
        self.lex.verb('like')

        liking = anna.like(bart, 5)
        with self.assertRaises(qiki.Word.NonVerbUndefinedAsFunctionException):
            liking(bart)

    def test_lex_is_lex(self):
        """Various ways a lex is a singleton, with it's lex."""
        sys1 = self.lex
        sys2 = self.lex('lex')
        sys3 = self.lex('lex')('lex')('lex')
        sys4 = self.lex('lex').lex('lex').lex.lex.lex('lex')('lex')('lex')
        self.assertEqual(sys1.idn, sys2.idn)
        self.assertEqual(sys1.idn, sys3.idn)
        self.assertEqual(sys1.idn, sys4.idn)
        self.assertIs(sys1, sys2)
        self.assertIs(sys1, sys3)
        self.assertIs(sys1, sys4)

    def test_idn_setting_not_allowed(self):
        lex = self.lex('lex')
        self.assertEqual(lex.idn, self.lex._IDN_LEX)
        with self.assertRaises(RuntimeError):
            lex.idn = 999
        self.assertEqual(lex.idn, self.lex._IDN_LEX)

    def test_idn_suffix(self):
        """Make sure adding a suffix to the lex's idn does not modify lex.idn."""
        lex = self.lex('lex')
        self.assertEqual(lex.idn, self.lex._IDN_LEX)
        suffixed_lex_idn = lex.idn.add_suffix(3)
        self.assertEqual(lex.idn, self.lex._IDN_LEX)
        self.assertEqual(suffixed_lex_idn, qiki.Number('0q82_05__030100'))

    def test_verb_paren_object(self):
        """An orphan verb can spawn a sentence.
        v = lex('name of a verb'); v(o) is equivalent to lex.v(o).
        Lex is the implicit subject."""
        some_object = self.lex.noun('some object')
        verb = self.lex('verb')
        oobleck = verb('oobleck')
        self.assertTrue(oobleck.is_a_verb())
        with self.assertNewWord():
            blob = oobleck(some_object, qiki.Number(42), 'new sentence')
        self.assertTrue(blob.exists)
        self.assertEqual(blob.sbj, self.lex.idn)
        self.assertEqual(blob.vrb, oobleck.idn)
        self.assertEqual(blob.obj, some_object.idn)
        self.assertEqual(blob.num, qiki.Number(42))
        self.assertEqual(blob.txt, "new sentence")

    def test_verb_paren_object_text_number(self):
        """More orphan verb features.  v = lex(...); v(o,t,n) is also equivalent to lex.v(o,t,n)."""
        some_object = self.lex.noun('some object')
        verb = self.lex('verb')
        oobleck = verb('oobleck')
        self.assertTrue(oobleck.is_a_verb())
        with self.assertNewWord():
            blob = oobleck(some_object, qiki.Number(11), "blob")
        self.assertTrue(blob.exists)
        self.assertEqual(blob.obj, some_object.idn)
        self.assertEqual(blob.num, qiki.Number(11))
        self.assertEqual(blob.txt, "blob")

    def test_define_object_type_string(self):
        """Specify the object of a definition by its txt."""
        oobleck = self.lex.define('verb', 'oobleck')
        self.assertTrue(oobleck.exists)
        self.assertEqual(oobleck.sbj, self.lex.idn)
        self.assertEqual(oobleck.vrb, self.lex('define').idn)
        self.assertEqual(oobleck.obj, self.lex('verb').idn)
        self.assertEqual(oobleck.num, qiki.Number(1))
        self.assertEqual(oobleck.txt, "oobleck")

    def test_verb_paren_object_deferred_subject(self):
        """A patronized verb can spawn a sentence.
        That's a verb such as subject.verb that is generated as if it were an attribute.
        x = s.v; x(o) is equivalent to s.v(o).
        So a verb word instance can remember its subject for later spawning a new word."""

        some_object = self.lex.noun('some object')
        self.lex.verb('oobleck')
        lex_oobleck = self.lex('oobleck')   # word from an orphan verb

        xavier = self.lex.agent('xavier')
        self.assertNotEqual(xavier, self.lex)
        xavier_oobleck = xavier.oobleck   # word from a patronized verb

        # Weirdness: the verb instances are equal but behave differently
        self.assertEqual(lex_oobleck, xavier_oobleck)   # TODO:  Should these be unequal??
        self.assertIsNone(lex_oobleck._word_before_the_dot)
        self.assertIsNotNone(xavier_oobleck._word_before_the_dot)
        self.assertNotEqual(lex_oobleck._word_before_the_dot, xavier_oobleck._word_before_the_dot)

        xavier_blob = xavier_oobleck(some_object, qiki.Number(42), "xavier blob")
        self.assertTrue(xavier_blob.exists)
        self.assertEqual(xavier_blob.sbj, xavier.idn)
        self.assertEqual(xavier_blob.vrb, xavier_oobleck.idn)
        self.assertEqual(xavier_blob.obj, some_object.idn)
        self.assertEqual(xavier_blob.num, qiki.Number(42))
        self.assertEqual(xavier_blob.txt, "xavier blob")

    def test_lex_number(self):
        agent_by_txt = self.lex('agent')
        agent_by_idn = self.lex(qiki.Word._IDN_AGENT)
        self.assertEqual(agent_by_txt, agent_by_idn)
        self.assertEqual('agent', agent_by_idn.txt)
        self.assertEqual(qiki.Word._IDN_AGENT, agent_by_txt.idn)


class WordListingTests(WordTests):

    class Student(qiki.Listing):
        names_and_grades = [
            ("Archie", 4.0),
            ("Barbara", 3.0),
            ("Chad", 3.0),
            ("Deanne", 1.0),
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
        self.listing = self.lex.noun('listing')
        qiki.Listing.install(self.listing)
        self.names = self.listing('names')
        self.Student.install(self.names)


class WordListingBasicTests(WordListingTests):

    def test_listing_suffix(self):
        number_two = qiki.Number(2)
        chad = self.Student(number_two)
        self.assertEqual(number_two, chad.index)
        self.assertEqual(    "Chad", chad.txt)
        self.assertEqual(       3.0, chad.num)
        self.assertTrue(chad.exists)

        idn_suffix = chad.idn.parse_suffixes()
        self.assertEqual(2, len(idn_suffix))
        idn = idn_suffix[0]
        suffix = idn_suffix[1]
        self.assertEqual(idn, self.names.idn)
        self.assertEqual(suffix.payload_number(), number_two)

    def test_listing_using_spawn_and_save(self):
        archie = self.Student(qiki.Number(0))
        bless = self.lex.verb('bless')
        blessed_name = self.lex.spawn(
            sbj=self.lex.idn,
            vrb=bless.idn,
            obj=archie.idn,
            txt="mah soul",
            num=qiki.Number(666),
        )
        blessed_name.save()

        blessed_name_too = self.lex.spawn(blessed_name.idn)
        self.assertTrue(blessed_name_too.exists)
        self.assertEqual(blessed_name_too.sbj, qiki.Word._IDN_LEX)
        self.assertEqual(blessed_name_too.vrb, bless.idn)
        self.assertEqual(blessed_name_too.obj, archie.idn)
        self.assertEqual(blessed_name_too.num, qiki.Number(666))
        self.assertEqual(blessed_name_too.txt, "mah soul")

        laud = self.lex.verb('laud')
        thing = self.lex.noun('thing')
        lauded_thing = self.lex.spawn(
            sbj=archie.idn,
            vrb=laud.idn,
            obj=thing.idn,
            txt="most sincerely",
            num=qiki.Number(123456789),
        )
        lauded_thing.save()

    def test_listing_using_method_verb(self):
        archie = self.Student(qiki.Number(0))
        bless = self.lex.verb('bless')
        blessed_name = self.lex.bless(archie, qiki.Number(666), "mah soul")

        blessed_name_too = self.lex.spawn(blessed_name.idn)
        self.assertTrue(blessed_name_too.exists)
        self.assertEqual(blessed_name_too.sbj, qiki.Word._IDN_LEX)
        self.assertEqual(blessed_name_too.vrb, bless.idn)
        self.assertEqual(blessed_name_too.obj, archie.idn)
        self.assertEqual(blessed_name_too.num, qiki.Number(666))
        self.assertEqual(blessed_name_too.txt, "mah soul")

        self.lex.verb('laud')
        thing = self.lex.noun('thing')
        archie.laud(thing, qiki.Number(123456789), "most sincerely")

    def test_listing_not_found(self):
        with self.assertRaises(qiki.Listing.NotFound):
            self.Student(qiki.Number(5))

    def test_listing_index_Number(self):
        deanne = self.Student(qiki.Number(3))
        self.assertEqual("Deanne", deanne.txt)

    def test_listing_index_int(self):
        deanne = self.Student(3)
        self.assertEqual("Deanne", deanne.txt)

    def test_listing_as_nouns(self):
        barbara = self.Student(1)
        deanne = self.Student(3)
        self.lex.verb('like')
        barbara.like(deanne, qiki.Number(1))
        deanne.like(barbara, qiki.Number(-1000000000))

    def test_listing_by_lex_idn(self):
        """Make sure lex(suffixed number) will look up a listing."""
        chad1 = self.Student(2)
        idn_chad = chad1.idn
        chad2 = self.lex(idn_chad)
        self.assertEqual("Chad", chad1.txt)
        self.assertEqual("Chad", chad2.txt)


class WordListingInternalsTests(WordListingTests):

    class SubStudent(WordListingTests.Student):
        def lookup(self, index, callback):
            raise self.NotFound

    class AnotherListing(qiki.Listing):
        def lookup(self, index, callback):
            raise self.NotFound

    def setUp(self):
        super(WordListingInternalsTests, self).setUp()
        self.SubStudent.install(self.lex.noun('sub_student'))
        self.AnotherListing.install(self.lex.noun('another_listing'))

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
        self.assertEqual("Chad", chad.txt)
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
        some_word = self.lex.noun('some word')
        with self.assertRaises(qiki.Listing.NotAListing):
            qiki.Listing.class_from_meta_idn(some_word.idn)

    def test_non_listing_suffix(self):
        with self.assertRaises(qiki.Word.NotAWord):
            self.lex(qiki.Number(1+2j))


class WordUseAlready(WordTests):

    def setUp(self):
        super(WordUseAlready, self).setUp()
        self.narcissus = self.lex.agent('narcissus')
        self.lex.verb('like')

    # When txt differs

    def test_use_already_differ_txt_default(self):
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Puddle")

    def test_use_already_differ_txt_false(self):
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Puddle", use_already=False)

    def test_use_already_differ_txt_true(self):
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Puddle", use_already=True)

    # When num differs

    def test_use_already_differ_num_default(self):
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 200, "Mirror")

    def test_use_already_differ_num_false(self):
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 200, "Mirror", use_already=False)

    def test_use_already_differ_num_true(self):
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 200, "Mirror", use_already=True)

    # When num and txt are the same

    def test_use_already_same_default(self):
        with self.assertNewWord():  word1 = self.narcissus.like(self.narcissus, 100, "Mirror")
        with self.assertNewWord():  word2 = self.narcissus.like(self.narcissus, 100, "Mirror")
        self.assertEqual(word1.idn+1, word2.idn)

    def test_use_already_same_false(self):
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.like(self.narcissus, 100, "Mirror", use_already=False)

    def test_use_already_same_true(self):
        with self.assertNewWord():     self.narcissus.like(self.narcissus, 100, "Mirror")
        with self.assertNoNewWords():  self.narcissus.like(self.narcissus, 100, "Mirror", use_already=True)

    # TODO:  Deal with the inconsistency that when defining a word, use_already defaults to True.


class WordFindTests(WordTests):

    def setUp(self):
        super(WordFindTests, self).setUp()
        self.apple = self.lex.noun('apple')
        self.berry = self.lex.noun('berry')
        self.curry = self.lex.noun('curry')
        self.macintosh = self.lex.apple('macintosh')
        self.braburn = self.lex.apple('braburn')
        self.honeycrisp = self.lex.apple('honeycrisp')
        self.crave = self.lex.verb('crave')
        self.fred = self.lex.agent('fred')

    def test_was_select_idns_now_super_select(self):
        # apple_words = self.lex._select_idns('SELECT idn FROM word WHERE txt=?', ['apple'])
        apple_words = self.lex.super_select('SELECT idn FROM', self.lex, 'WHERE txt=', qiki.Text('apple'))
        self.assertEqual(1, len(apple_words))
        # self.assertEqual(self.apple.idn, apple_words[0])
        self.assertEqual({'idn': self.apple.idn}, apple_words[0])

    def test_select_words_txt(self):
        apple_words = self.lex._select_words('SELECT idn FROM '+self.lex._table+' WHERE txt=?', ['apple'])
        self.assertEqual(1, len(apple_words))
        self.assertEqual(self.apple.idn, apple_words[0].idn)

    def test_select_words_obj(self):
        apple_words = self.lex._select_words('SELECT idn FROM '+self.lex._table+' WHERE obj=?', [self.apple.idn.raw])
        self.assertEqual(3, len(apple_words))
        self.assertEqual(self.macintosh.idn, apple_words[0].idn)
        self.assertEqual(self.braburn.idn, apple_words[1].idn)
        self.assertEqual(self.honeycrisp.idn, apple_words[2].idn)

    def test_select_fields(self):
        apple_fields = self.lex._select_fields('SELECT txt,idn FROM '+self.lex._table+' WHERE obj=?', [self.apple.idn.raw])
        self.assertEqual(3, len(apple_fields))
        self.assertEqual(2, len(apple_fields[0]))
        self.assertEqual(2, len(apple_fields[1]))
        self.assertEqual(2, len(apple_fields[2]))
        self.assertEqual((b'macintosh',   self.macintosh.idn.raw), apple_fields[0])
        self.assertEqual((b'braburn',       self.braburn.idn.raw), apple_fields[1])
        self.assertEqual((b'honeycrisp', self.honeycrisp.idn.raw), apple_fields[2])

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
        self.fred.crave(self.curry, qiki.Number(1), "Yummy.")
        fred_words = self.lex.find_words(sbj=self.fred.idn)
        self.assertEqual(1, len(fred_words))
        self.assertEqual("Yummy.", fred_words[0].txt)

    def test_find_sbj_word(self):
        fred_word = self.fred.crave(self.curry, qiki.Number(1), "Yummy.")
        self.assertEqual([fred_word], self.lex.find_words(sbj=self.fred))

    def test_find_vrb(self):
        self.fred.crave(self.curry, qiki.Number(1), "Yummy.")
        crave_words = self.lex.find_words(vrb=self.crave.idn)
        self.assertEqual(1, len(crave_words))
        self.assertEqual("Yummy.", crave_words[0].txt)

    def test_find_vrb_word(self):
        crave_word = self.fred.crave(self.curry, qiki.Number(1), "Yummy.")
        self.assertEqual([crave_word], self.lex.find_words(vrb=self.crave))

    def test_find_chronology(self):
        craving_apple = self.fred.crave(self.apple, qiki.Number(1))
        craving_berry = self.fred.crave(self.berry, qiki.Number(1))
        craving_curry = self.fred.crave(self.curry, qiki.Number(1))

        self.assertEqual([craving_apple, craving_berry, craving_curry], self.lex.find_words(sbj=self.fred))
        self.assertEqual([craving_apple, craving_berry, craving_curry], self.lex.find_words(vrb=self.crave))

    def test_find_empty(self):
        self.fred.crave(self.apple, qiki.Number(1))
        self.fred.crave(self.berry, qiki.Number(1))
        self.fred.crave(self.curry, qiki.Number(1))

        self.assertEqual([], self.lex.find_words(sbj=self.crave))
        self.assertEqual([], self.lex.find_words(vrb=self.fred))

    def test_find_idns(self):
        idns = self.lex.find_idns()
        for idn in idns:
            self.assertIsInstance(idn, qiki.Number)

    def test_find_by_vrb(self):
        crave1 = self.fred.crave(self.apple, 1)
        crave2 = self.fred.crave(self.braburn, 10)
        crave3 = self.fred.crave(self.macintosh, 0.5)
        self.assertEqual([crave1, crave2, crave3], self.lex.find_words(vrb=self.crave))
        self.assertEqual([crave1, crave2, crave3], self.lex.find_words(vrb=self.crave.idn))
        self.assertEqual([crave1.idn, crave2.idn, crave3.idn], self.lex.find_idns(vrb=self.crave))
        self.assertEqual([crave1.idn, crave2.idn, crave3.idn], self.lex.find_idns(vrb=self.crave.idn))

    def test_find_by_vrb_list(self):
        c1 = self.fred.crave(self.apple, 1)
        c2 = self.fred.crave(self.braburn, 10)
        retch = self.lex.verb('retch')
        r3 = self.fred.retch(self.macintosh, -1)
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
        idns = self.lex.find_idns(sql='ORDER BY idn ASC')
        self.assertLess(idns[0], idns[-1])
        idns = self.lex.find_idns(sql='ORDER BY idn DESC')
        self.assertGreater(idns[0], idns[-1])

    def test_find_words_sql(self):
        words = self.lex.find_words(sql='ORDER BY idn ASC')
        self.assertLess(words[0].idn, words[-1].idn)
        words = self.lex.find_words(sql='ORDER BY idn DESC')
        self.assertGreater(words[0].idn, words[-1].idn)

class WordUtilities(WordTests):

    def test_idn_from_word_or_number(self):
        agent = self.lex.agent
        self.assertEqual(qiki.Word._IDN_AGENT, idn_from_word_or_number(agent.idn))
        self.assertEqual(qiki.Word._IDN_AGENT, idn_from_word_or_number(agent))
        with self.assertRaises(TypeError):
            idn_from_word_or_number('')
        with self.assertRaises(TypeError):
            idn_from_word_or_number(0)

    # noinspection PyStatementEffect
    def test_inequality_words_and_numbers(self):
        """Sanity check to make sure words and idns aren't intrinsically equal or something."""
        word = self.lex.agent
        idn = word.idn
        exceptions = (qiki.Number.Incomparable, qiki.Word.Incomparable)
        with self.assertRaises(exceptions):   idn == word
        with self.assertRaises(exceptions):   idn != word
        with self.assertRaises(exceptions):   word == idn
        with self.assertRaises(exceptions):   word != idn

    def test_words_from_idns(self):
        noun = self.lex('noun')
        agent = self.lex('agent')
        define = self.lex('define')
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
        noun = self.lex('noun')
        agent = self.lex('agent')
        define = self.lex('define')
        self.assertEqual([
            noun.idn.raw,
            agent.idn.raw,
            define.idn.raw,
        ], self.lex.raws_from_idns([
            noun.idn,
            agent.idn,
            define.idn,
        ]))


class WordQoolbarTests(WordTests):

    def setUp(self):
        super(WordQoolbarTests, self).setUp()
        self.qool = self.lex.verb('qool')
        self.like = self.lex.verb('like')
        self.delete = self.lex.verb('delete')
        self.lex.qool(self.like, qiki.Number(1))
        self.lex.qool(self.delete, qiki.Number(1))
        self.anna = self.lex.agent('anna')
        self.bart = self.lex.agent('bart')
        self.youtube = self.lex.noun('youtube')
        self.zigzags = self.lex.noun('zigzags')

        self.anna.like(self.youtube, 1)
        self.bart.like(self.youtube, 10)
        self.anna.like(self.zigzags, 2)
        self.bart.delete(self.zigzags, 1)

        qool_declarations = self.lex.find_words(vrb=self.qool.idn)
        self.qool_idns = [w.obj for w in qool_declarations]

    def test_get_all_qool_verbs(self):
        self.assertEqual([self.like.idn, self.delete.idn], self.qool_idns)
        # print(", ".join([w.idn.qstring() for w in qool_words]))
        # print(", ".join([n.qstring() for n in qool_idns]))

    def test_find_qool_(self):
        """Find by a list of verbs."""
        qool_uses = self.lex.find_words(vrb=self.qool_idns)
        self.assertEqual(4, len(qool_uses))
        self.assertEqual(qool_uses[0].sbj, self.anna.idn)
        self.assertEqual(qool_uses[1].sbj, self.bart.idn)
        self.assertEqual(qool_uses[2].sbj, self.anna.idn)
        self.assertEqual(qool_uses[3].sbj, self.bart.idn)

        qool_uses = self.lex.find_words(vrb=self.qool_idns, obj=self.youtube)
        self.assertEqual(2, len(qool_uses))
        self.assertEqual(qool_uses[0].sbj, self.anna.idn)
        self.assertEqual(qool_uses[0].num, qiki.Number(1))
        self.assertEqual(qool_uses[1].sbj, self.bart.idn)
        self.assertEqual(qool_uses[1].num, qiki.Number(10))

        qool_uses = self.lex.find_words(vrb=self.qool_idns, sbj=self.bart)
        self.assertEqual(2, len(qool_uses))
        self.assertEqual(qool_uses[0].obj, self.youtube.idn)
        self.assertEqual(qool_uses[0].num, qiki.Number(10))
        self.assertEqual(qool_uses[1].obj, self.zigzags.idn)
        self.assertEqual(qool_uses[1].num, qiki.Number(1))

    def test_super_select(self):
        self.assertEqual([{'txt': 'define'},], self.lex.super_select(
            'SELECT txt FROM',
            self.lex,
            'WHERE idn =',
            qiki.Word._IDN_DEFINE
        ))
        self.assertEqual([{'idn': qiki.Word._IDN_DEFINE},], self.lex.super_select(
            'SELECT idn FROM',
            self.lex,
            'WHERE txt =',
            qiki.Text('define')
        ))

    def test_super_select_with_none(self):
        """To concatenate two strings of literal SQL code, intersperse a None."""
        self.assertEqual([{'txt': 'define'},], self.lex.super_select(
            'SELECT txt', None, 'FROM',
            self.lex,
            'WHERE', None, 'idn =',
            qiki.Word._IDN_DEFINE
        ))

    def test_super_select_string_string(self):
        with self.assertRaises(qiki.LexMySQL.SuperSelectStringString):
            self.lex.super_select('string', 'string', self.lex)
        with self.assertRaises(qiki.LexMySQL.SuperSelectStringString):
            self.lex.super_select(self.lex, 'string', 'string')
        self.lex.super_select('SELECT * FROM', self.lex)

        with self.assertRaises(qiki.LexMySQL.SuperSelectStringString):
            self.lex.super_select('SELECT * FROM', self.lex._table, 'WHERE txt=', 'define')
        with self.assertRaises(qiki.LexMySQL.SuperSelectStringString):
            self.lex.super_select('SELECT * FROM', self.lex, 'WHERE txt=', 'define')
        self.lex.super_select('SELECT * FROM', self.lex, 'WHERE txt=', qiki.Text('define'))

    def test_super_select_type_error(self):
        class ExoticType(object):
            pass

        with self.assertRaises(qiki.LexMySQL.SuperSelectTypeError):
            self.lex.super_select(ExoticType)

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

    def test_wrong_word_method_infinity(self):
        word = self.lex('noun')
        with self.assertRaises(qiki.Word.NoSuchAttribute):
            word.no_such_method()

    def test_wrong_lex_method_infinity(self):
        with self.assertRaises(qiki.Word.NoSuchAttribute):
            self.lex.no_such_method()



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
    # def test_idn_cannot_set_idn(self):
    #     define = qiki.Word('define')
    #     with self.assertRaises(RuntimeError):
    #         define.idn = -1
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


if __name__ == '__main__':
    import unittest
    unittest.main()
