# coding=utf-8
"""
Testing qiki word.py
"""

from __future__ import print_function
import unittest
import six
import sys
import time

import qiki
from number import hex_from_string

try:
    import secure.credentials
except ImportError:
    secure = None
    print("""
        Example secure/credentials.py

            for_example_database = dict(
                language= 'MySQL',
                host=     'localhost',
                port=     8000,
                user=     'user',
                password= 'password',
                database= 'database',
                table=    'word',
            )

        You also need an empty secure/__init__.py
        Why?  See http://stackoverflow.com/questions/10863268/how-is-an-empty-init-py-file-correct
    """)
    sys.exit(1)


LET_DATABASE_RECORDS_REMAIN = True   # Each run always starts the test database over from scratch.
                                     # Set this to True to manually examine the database after running it.
TEST_ASTRAL_PLANE = True   # Test txt with Unicode characters on an astral-plane (beyond the base 64K)
SHOW_UTF8_EXAMPLES = False

class WordTests(unittest.TestCase):

    def setUp(self):
        # try:
            self.lex = qiki.LexMySQL(**secure.credentials.for_unit_testing_database)
            self.lex.uninstall_to_scratch()
            self.lex.install_from_scratch()
            # cursor = self.lex._connection.cursor()
            # cursor.execute("SELECT txt FROM `{table}` ORDER BY idn ASC".format(table=self.lex._table))
            # print("Word database:", ", ".join([row[0] for row in cursor]))
            # cursor.close()
        # except:
        #     self.fail()

    def tearDown(self):
        if not LET_DATABASE_RECORDS_REMAIN:
            self.lex.uninstall_to_scratch()
        self.lex.disconnect()

    def describe_all_words(self):
        idn_array = self.lex.get_all_idns()
        for _idn in idn_array:
            print(int(_idn), self.lex(_idn).description())

    def show_txt_in_utf8(self, idn):
        word = self.lex(idn)
        utf8 = word.txt.encode('utf8')
        hexadecimal = hex_from_string(utf8)
        print("\"{txt}\" in utf8 is {hex}".format(
            txt=word.txt.encode('unicode_escape'),   # Python 3 doubles up the backslashes ... shrug.
            hex=hexadecimal,
        ))

    def assertReasonableWhen(self, whn):
        self.assertGreaterEqual(time.time(), float(whn))
        self.assertLessEqual(1447029882.792, float(whn))


class WordFirstTests(WordTests):

    def test_00_number(self):
        n = qiki.Number(1)
        self.assertEqual(1, int(n))

    def test_01_lex(self):
        self.assertEqual(self.lex._ID_LEX,         self.lex.idn)
        self.assertEqual(self.lex._ID_LEX,         self.lex.sbj)
        self.assertEqual(self.lex('define').idn,   self.lex.vrb)
        self.assertEqual(self.lex('agent').idn,    self.lex.obj)
        self.assertEqual(qiki.Number(1),           self.lex.num)
        self.assertEqual('lex',                    self.lex.txt)
        self.assertReasonableWhen(                 self.lex.whn)
        self.assertTrue(self.lex.is_lex())

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
        self.assertEqual(qiki.Word._ID_MAX_FIXED, self.lex.max_idn())

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
        base_max_idn = self.lex.max_idn()
        thing1 = noun('thing')
        self.assertEqual(base_max_idn+1, self.lex.max_idn())
        thing2 = noun('thing')
        self.assertEqual(base_max_idn+1, self.lex.max_idn())
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
        agent = self.lex(qiki.Word._ID_AGENT)
        self.assertEqual(agent.txt, 'agent')

    def test_10b_word_by_lex_txt(self):
        agent = self.lex('agent')
        self.assertEqual(agent.idn, qiki.Word._ID_AGENT)

    def test_11a_noun_inserted(self):
        new_word = self.lex.noun('something')
        max_idn = self.lex.max_idn()

        self.assertEqual(max_idn,                  new_word.idn)
        self.assertEqual(self.lex._ID_LEX,         new_word.sbj)
        self.assertEqual(self.lex('define').idn,   new_word.vrb)
        self.assertEqual(self.lex('noun').idn,     new_word.obj)
        self.assertEqual(qiki.Number(1),           new_word.num)
        self.assertEqual('something',              new_word.txt)
        self.assertReasonableWhen(                 new_word.whn)

    def test_11b_whn(self):
        define = self.lex('define')
        new_word = self.lex.noun('something')
        self.assertReasonableWhen(define.whn)
        self.assertReasonableWhen(new_word.whn)
        self.assertGreaterEqual(float(new_word.whn), float(define.whn))


class WordUnicode(WordTests):

    def setUp(self):
        super(WordUnicode, self).setUp()
        self.lex.noun('comment')

    def test_unicode_a_utf8_ascii(self):
        self.assertEqual(u"ascii", self.lex(self.lex.comment(b"ascii").idn).txt)

    def test_unicode_b_unicode_ascii(self):
        self.assertEqual(u"ascii", self.lex(self.lex.comment(u"ascii").idn).txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    def test_unicode_c_utf8_spanish(self):
        assert u"mañana" == u"ma\xF1ana"
        comment = self.lex.comment(u"mañana".encode('utf8'))
        self.assertEqual(u"ma\xF1ana", self.lex(comment.idn).txt)

    def test_unicode_d_unicode_spanish(self):
        comment = self.lex.comment(u"mañana")
        self.assertEqual(u"ma\xF1ana", self.lex(comment.idn).txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    def test_unicode_e_utf8_peace(self):
        assert u"☮ on earth" == u"\u262E on earth"
        comment = self.lex.comment(u"☮ on earth".encode('utf8'))
        self.assertEqual(u"\u262E on earth", self.lex(comment.idn).txt)

    def test_unicode_f_unicode_peace(self):
        comment = self.lex.comment(u"☮ on earth")
        self.assertEqual(u"\u262E on earth", self.lex(comment.idn).txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    if TEST_ASTRAL_PLANE:

        def test_unicode_g_utf8_pile_of_poo(self):
            # Source code is base plane only, so cannot:  assert u"stinky ?" == u"stinky \U0001F4A9"
            comment = self.lex.comment(u"stinky \U0001F4A9".encode('utf8'))
            self.assertEqual(u"stinky \U0001F4A9", self.lex(comment.idn).txt)

        def test_unicode_h_unicode_pile_of_poo(self):
            comment = self.lex.comment(u"stinky \U0001F4A9")
            self.assertEqual(u"stinky \U0001F4A9", self.lex(comment.idn).txt)
            if SHOW_UTF8_EXAMPLES:
                self.show_txt_in_utf8(self.lex.max_idn())


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
        self.assertTrue(like.is_a_verb())
        self.assertTrue(verb.is_a_verb(reflexive=True))
        self.assertFalse(verb.is_a_verb(reflexive=False))
        self.assertFalse(verb.is_a_verb())
        self.assertFalse(noun.is_a_verb())

        self.assertFalse(self.lex('noun').is_a_verb())
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
        max_idn = self.lex.max_idn()

        anna.like(bart, 8)
        self.assertEqual(max_idn+1, self.lex.max_idn())
        self.assertEqual(8, anna.like(bart).num)

        anna.like(bart, 10)
        self.assertEqual(max_idn+2, self.lex.max_idn())
        self.assertEqual(10, anna.like(bart).num)

        anna.like(bart, 2)
        self.assertEqual(max_idn+3, self.lex.max_idn())
        self.assertEqual(2, anna.like(bart).num)

    def test_verb_overlay_duplicate(self):
        human = self.lex.agent('human')
        anna = human('anna')
        bart = human('bart')
        self.lex.verb('like')
        max_idn = self.lex.max_idn()

        anna.like(bart, 5, "just as friends")
        self.assertEqual(max_idn+1, self.lex.max_idn())

        # anna.like(bart, 5, "just as friends")
        # self.assertEqual(max_idn+1, self.lex.max_idn(), "Identical s.v(o,n,t) shouldn't generate a new word.")
        # TODO:  Decide whether these "duplicates" should be errors or insert new records or not...
        # TODO:  Probably it should be an error for some verbs (e.g. like) and not for others (e.g. comment)
        # TODO: 'unique' option?  Imbue "like" verb with properties using Words??

        anna.like(bart, 5, "maybe more than friends")
        self.assertEqual(max_idn+2, self.lex.max_idn(), "New t should generate a new word.")

        anna.like(bart, 6, "maybe more than friends")
        self.assertEqual(max_idn+3, self.lex.max_idn(), "New n should generate a new word.")

        anna.like(bart, 7, "maybe more than friends")
        self.assertEqual(max_idn+4, self.lex.max_idn())

        # anna.like(bart, 7, "maybe more than friends")
        # self.assertEqual(max_idn+4, self.lex.max_idn())

        anna.like(bart, 5, "just as friends")
        self.assertEqual(max_idn+5, self.lex.max_idn(), "Reverting to an old n,t should generate a new word.")

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
        self.assertEqual(lex.idn, self.lex._ID_LEX)
        with self.assertRaises(RuntimeError):
            lex.idn = 999
        self.assertEqual(lex.idn, self.lex._ID_LEX)

    def test_idn_suffix(self):
        lex = self.lex('lex')
        self.assertEqual(lex.idn, self.lex._ID_LEX)
        suffixed_lex_idn = lex.idn.add_suffix(3)
        self.assertEqual(lex.idn, self.lex._ID_LEX)
        self.assertEqual(suffixed_lex_idn, qiki.Number('0q82_05__030100'))


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
        self.assertEqual(blessed_name_too.sbj, qiki.Word._ID_LEX)
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
        self.assertEqual(blessed_name_too.sbj, qiki.Word._ID_LEX)
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


class WordUseAlready(WordTests):

    def setUp(self):
        super(WordUseAlready, self).setUp()
        self.narcissus = self.lex.agent('narcissus')
        self.lex.verb('like')

    # When num and txt are the same

    def test_use_already_same_default(self):
        word1 = self.narcissus.like(self.narcissus, 100, "Mirror")
        max_idn_1 = self.lex.max_idn()
        word2 = self.narcissus.like(self.narcissus, 100, "Mirror")
        max_idn_2 = self.lex.max_idn()
        self.assertEqual(word1.idn+1, word2.idn)
        self.assertEqual(max_idn_1+1, max_idn_2)

    def test_use_already_same_false(self):
        word1 = self.narcissus.like(self.narcissus, 100, "Mirror")
        max_idn_1 = self.lex.max_idn()
        word2 = self.narcissus.like(self.narcissus, 100, "Mirror", use_already=False)
        max_idn_2 = self.lex.max_idn()
        self.assertEqual(word1.idn+1, word2.idn)
        self.assertEqual(max_idn_1+1, max_idn_2)

    def test_use_already_same_true(self):
        word1 = self.narcissus.like(self.narcissus, 100, "Mirror")
        max_idn_1 = self.lex.max_idn()
        word2 = self.narcissus.like(self.narcissus, 100, "Mirror", use_already=True)
        max_idn_2 = self.lex.max_idn()
        self.assertEqual(word1.idn, word2.idn)
        self.assertEqual(max_idn_1, max_idn_2)

    # When txt differs

    def test_use_already_differ_txt_default(self):
        word1 = self.narcissus.like(self.narcissus, 100, "Mirror")
        max_idn_1 = self.lex.max_idn()
        word2 = self.narcissus.like(self.narcissus, 100, "Puddle")
        max_idn_2 = self.lex.max_idn()
        self.assertEqual(word1.idn+1, word2.idn)
        self.assertEqual(max_idn_1+1, max_idn_2)

    def test_use_already_differ_txt_false(self):
        word1 = self.narcissus.like(self.narcissus, 100, "Mirror")
        max_idn_1 = self.lex.max_idn()
        word2 = self.narcissus.like(self.narcissus, 100, "Puddle", use_already=False)
        max_idn_2 = self.lex.max_idn()
        self.assertEqual(word1.idn+1, word2.idn)
        self.assertEqual(max_idn_1+1, max_idn_2)

    def test_use_already_differ_txt_true(self):
        word1 = self.narcissus.like(self.narcissus, 100, "Mirror")
        max_idn_1 = self.lex.max_idn()
        word2 = self.narcissus.like(self.narcissus, 100, "Puddle", use_already=True)
        max_idn_2 = self.lex.max_idn()
        self.assertEqual(word1.idn+1, word2.idn)
        self.assertEqual(max_idn_1+1, max_idn_2)

    # When num differs

    def test_use_already_differ_num_default(self):
        word1 = self.narcissus.like(self.narcissus, 100, "Mirror")
        max_idn_1 = self.lex.max_idn()
        word2 = self.narcissus.like(self.narcissus, 200, "Mirror")
        max_idn_2 = self.lex.max_idn()
        self.assertEqual(word1.idn+1, word2.idn)
        self.assertEqual(max_idn_1+1, max_idn_2)

    def test_use_already_differ_num_false(self):
        word1 = self.narcissus.like(self.narcissus, 100, "Mirror")
        max_idn_1 = self.lex.max_idn()
        word2 = self.narcissus.like(self.narcissus, 200, "Mirror", use_already=False)
        max_idn_2 = self.lex.max_idn()
        self.assertEqual(word1.idn+1, word2.idn)
        self.assertEqual(max_idn_1+1, max_idn_2)

    def test_use_already_differ_num_true(self):
        word1 = self.narcissus.like(self.narcissus, 100, "Mirror")
        max_idn_1 = self.lex.max_idn()
        word2 = self.narcissus.like(self.narcissus, 200, "Mirror", use_already=True)
        max_idn_2 = self.lex.max_idn()
        self.assertEqual(word1.idn+1, word2.idn)
        self.assertEqual(max_idn_1+1, max_idn_2)


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

    def test_select_words_txt(self):
        apple_words = self.lex._select_words("SELECT idn FROM word WHERE txt=?", ['apple'])
        self.assertEqual(1, len(apple_words))
        self.assertEqual(self.apple.idn, apple_words[0].idn)

    def test_select_words_obj(self):
        apple_words = self.lex._select_words("SELECT idn FROM word WHERE obj=?", [self.apple.idn.raw])
        self.assertEqual(3, len(apple_words))
        self.assertEqual(self.macintosh.idn, apple_words[0].idn)
        self.assertEqual(self.braburn.idn, apple_words[1].idn)
        self.assertEqual(self.honeycrisp.idn, apple_words[2].idn)

    def test_find_obj(self):
        apple_words = self.lex.find(obj=self.apple.idn)
        self.assertEqual(3, len(apple_words))
        self.assertEqual(self.braburn.idn, apple_words[1].idn)
        self.assertEqual(self.honeycrisp.idn, apple_words[2].idn)

    def test_find_obj_sbj(self):
        self.fred.crave(self.curry, qiki.Number(1), "Yummy.")
        fred_words = self.lex.find(sbj=self.fred.idn)
        self.assertEqual(1, len(fred_words))
        self.assertEqual("Yummy.", fred_words[0].txt)

    def test_find_obj_vrb(self):
        self.fred.crave(self.curry, qiki.Number(1), "Yummy.")
        crave_words = self.lex.find(vrb=self.crave.idn)
        self.assertEqual(1, len(crave_words))
        self.assertEqual("Yummy.", crave_words[0].txt)

    def test_find_chronology(self):
        self.fred.crave(self.apple, qiki.Number(1))
        self.fred.crave(self.berry, qiki.Number(1))
        self.fred.crave(self.curry, qiki.Number(1))




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
