# coding=utf-8
"""
Testing qiki word.py
"""

from __future__ import print_function
import unittest
import sys

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


class WordTests(unittest.TestCase):

    def setUp(self):
        self.system = qiki.SystemMySQL(**secure.credentials.for_unit_testing_database)
        self.system.uninstall_to_scratch()
        self.system.install_from_scratch()
        # cursor = self.system._connection.cursor()
        # cursor.execute("SELECT txt FROM `{table}` ORDER BY idn ASC".format(table=self.system._table))
        # print("Word database:", ", ".join([row[0] for row in cursor]))
        # cursor.close()

    def tearDown(self):
        if not LET_DATABASE_RECORDS_REMAIN:
            self.system.uninstall_to_scratch()
        self.system.disconnect()

    def describe_all_words(self):
        idn_array = self.system.get_all_idns()
        for _idn in idn_array:
            print(int(_idn), self.system(_idn).description())

    def show_txt_in_utf8(self, idn):
        word = self.system(idn)
        utf8 = word.txt.encode('utf8')
        hexadecimal = hex_from_string(utf8)
        print("\"{txt}\" in utf8 is {hex}".format(
            txt=word.txt.encode('unicode_escape'),   # Python 3 doubles up the backslashes.  Shrug.
            hex=hexadecimal,
        ))


class WordFirstTests(WordTests):

    def test_00_number(self):
        n = qiki.Number(1)
        self.assertEqual(1, int(n))

    def test_01_system(self):
        self.assertTrue(self.system.is_system())
        self.assertEqual('system', self.system.txt)
        self.assertEqual(self.system._ID_SYSTEM, self.system.idn)
        self.assertEqual(self.system._ID_SYSTEM, self.system.sbj)
        self.assertEqual(self.system('define').idn, self.system.vrb)
        self.assertEqual(self.system('agent').idn, self.system.obj)

    def test_02_noun(self):
        noun = self.system('noun')
        self.assertTrue(noun.exists)
        self.assertTrue(noun.is_noun())
        self.assertEqual('noun', noun.txt)

    def test_02a_str(self):
        self.assertEqual('noun', str(self.system('noun')))

    def test_02b_repr(self):
        noun_id = int(qiki.Number(qiki.Word._ID_NOUN))
        self.assertEqual("Word({})".format(noun_id), repr(self.system('noun')))

    def test_03a_max_idn(self):
        self.assertEqual(qiki.Word._ID_MAX_FIXED, self.system.max_idn())

    def test_03b_noun_spawn(self):
        noun = self.system('noun')
        thing = noun('thing')
        self.assertTrue(thing.exists)
        self.assertEqual('thing', thing.txt)

    def test_03c_noun_spawn_crazy_syntax(self):
        thing = self.system('noun')('thing')
        self.assertTrue(thing.exists)
        self.assertEqual('thing', thing.txt)

    def test_04_is_a(self):
        verb = self.system('verb')
        noun = self.system('noun')
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
        noun = self.system.noun
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
        self.assertTrue(self.system.is_a_noun())
        self.assertTrue(self.system('system').is_a_noun())
        self.assertTrue(self.system('agent').is_a_noun())
        self.assertTrue(self.system('noun').is_a_noun(reflexive=True))
        self.assertTrue(self.system('noun').is_a_noun(reflexive=False))   # noun is explicitly defined as a noun
        self.assertTrue(self.system('noun').is_a_noun())
        self.assertTrue(self.system('verb').is_a_noun())
        self.assertTrue(self.system('define').is_a_noun())

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

    def test_07_noun_great_great_grandchild(self):
        greatgrandchild = self.system('noun')('child')('grandchild')('greatgrandchild')
        greatgreatgrandchild = greatgrandchild('greatgreatgrandchild')
        self.assertEqual('greatgreatgrandchild', greatgreatgrandchild.txt)

    def test_07_is_a_noun_great_great_grandchild(self):
        noun = self.system('noun')
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
        noun = self.system('noun')
        base_max_idn = self.system.max_idn()
        thing1 = noun('thing')
        self.assertEqual(base_max_idn+1, self.system.max_idn())
        thing2 = noun('thing')
        self.assertEqual(base_max_idn+1, self.system.max_idn())
        self.assertEqual(thing1.idn, thing2.idn)

    def test_09a_equality(self):
        self.assertEqual(self.system.noun, self.system.noun)
        self.assertNotEqual(self.system.noun, self.system.verb)
        self.assertNotEqual(self.system.verb, self.system.noun)
        self.assertEqual(self.system.verb, self.system.verb)

    def test_09a_equality_by_attribute(self):
        noun1 = self.system.noun
        noun2 = self.system.noun
        self.assertEqual(noun1, noun2)
        self.assertIsNot(noun1, noun2)

    def test_09a_equality_by_call(self):
        noun1 = self.system('noun')
        noun2 = self.system('noun')
        self.assertEqual(noun1, noun2)
        self.assertIsNot(noun1, noun2)

    def test_09a_equality_by_copy_constructor(self):
        noun1 = self.system('noun')
        noun2 = qiki.Word(noun1)
        self.assertEqual(noun1, noun2)
        self.assertIsNot(noun1, noun2)

    def test_09b_system_singleton_by_attribute(self):
        system1 = self.system
        system2 = self.system.system
        self.assertEqual(system1, system2)
        self.assertIs(system1, system2)

    def test_09b_system_singleton_by_call(self):
        system1 = self.system
        system2 = self.system('system')
        self.assertEqual(system1, system2)
        self.assertIs(system1, system2)   # Why does this work?

    def test_09b_system_singleton_cant_do_by_copy_constructor(self):
        with self.assertRaises(ValueError):
            qiki.Word(self.system)

    def test_10a_word_by_system_idn(self):
        agent = self.system(qiki.Word._ID_AGENT)
        self.assertEqual(agent.txt, 'agent')

    def test_10b_word_by_system_txt(self):
        agent = self.system('agent')
        self.assertEqual(agent.idn, qiki.Word._ID_AGENT)


class WordUnicode(WordTests):

    def setUp(self):
        super(WordUnicode, self).setUp()
        self.system.noun('comment')

    def test_11a_utf8_ascii(self):
        self.assertEqual(u"ascii", self.system(self.system.comment(b"ascii").idn).txt)

    def test_11b_unicode_ascii(self):
        self.assertEqual(u"ascii", self.system(self.system.comment(u"ascii").idn).txt)
        self.show_txt_in_utf8(self.system.max_idn())

    def test_11c_utf8_spanish(self):
        assert u"mañana" == u"ma\xF1ana"
        comment = self.system.comment(u"mañana".encode('utf8'))
        self.assertEqual(u"ma\xF1ana", self.system(comment.idn).txt)

    def test_11d_unicode_spanish(self):
        comment = self.system.comment(u"mañana")
        self.assertEqual(u"ma\xF1ana", self.system(comment.idn).txt)
        self.show_txt_in_utf8(self.system.max_idn())

    def test_11e_utf8_peace(self):
        assert u"☮ on earth" == u"\u262E on earth"
        comment = self.system.comment(u"☮ on earth".encode('utf8'))
        self.assertEqual(u"\u262E on earth", self.system(comment.idn).txt)

    def test_11f_unicode_peace(self):
        comment = self.system.comment(u"☮ on earth")
        self.assertEqual(u"\u262E on earth", self.system(comment.idn).txt)
        self.show_txt_in_utf8(self.system.max_idn())

    if TEST_ASTRAL_PLANE:

        def test_11g_utf8_pile_of_poo(self):
            # Source code is base plane only, so cannot:  assert u"stinky ?" == u"stinky \U0001F4A9"
            comment = self.system.comment(u"stinky \U0001F4A9".encode('utf8'))
            self.assertEqual(u"stinky \U0001F4A9", self.system(comment.idn).txt)

        def test_11h_unicode_pile_of_poo(self):
            comment = self.system.comment(u"stinky \U0001F4A9")
            self.assertEqual(u"stinky \U0001F4A9", self.system(comment.idn).txt)
            self.show_txt_in_utf8(self.system.max_idn())


class WordMoreTests(WordTests):

    def test_describe(self):
        thing = self.system('noun')('thingamajig')
        self.assertIn('thingamajig', thing.description())

    def test_short_and_long_ways(self):
        noun = self.system('noun')
        thing1 = noun('thing')
        thing2 = self.system.noun('thing')
        thing3 = self.system.define(noun, 'thing')
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
        self.system.verb('like')
        like = self.system('like')
        self.assertEqual(self.system.idn, like.sbj)

    def test_is_a_verb(self):
        verb = self.system('verb')
        like = verb('like')
        self.assertTrue(like.is_a_verb())
        self.assertTrue(verb.is_a_verb(reflexive=True))
        self.assertFalse(verb.is_a_verb(reflexive=False))
        self.assertFalse(verb.is_a_verb())
        self.assertFalse(self.system('noun').is_a_verb())
        self.assertTrue(self.system('define').is_a_verb())
        self.assertFalse(self.system('agent').is_a_verb())
        self.assertFalse(self.system('system').is_a_verb())

    def test_verb_use(self):
        """Test that sbj.vrb(obj, num) creates a word.  And sbj.vrb(obj).num reads it back."""
        agent = self.system('agent')
        human = agent('human')
        self.system.verb('like')
        anna = human('anna')
        bart = human('bart')
        chad = human('chad')
        dirk = human('dirk')
        anna.like(anna, 1, "Narcissism.")
        anna.like(bart, 8, "Okay.")
        anna.like(chad, 10)
        anna.like(dirk, 1)
        self.assertFalse(anna.like.is_system())
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
        """Test that system.verb can be copied by assignment, and still work."""
        human = self.system.agent('human')
        anna = human('anna')
        bart = human('bart')
        verb = self.system.verb
        verb('like')
        anna.like(bart, 13)
        self.assertEqual(13, anna.like(bart).num)

    # def OBSOLETE_test_repr(self):
    #     self.assertEqual("Word('noun')", repr(self.system('noun')))
    #     human = self.system.agent('human')
    #     self.assertEqual("Word('human')", repr(human))
    #     like = self.system.verb('like')
    #     self.assertEqual("Word('like')", repr(like))
    #     liking = self.system.like(human, 10)
    #     self.assertEqual("Word(Number({idn}))".format(idn=liking.idn.qstring()), repr(liking))
    #     # w = self.system.spawn(sbj=Number(15), vrb=Number(31), obj=Number(63), num=Number(127), txt='something')
    #     # Word(sbj=0q82_0F, vrb=0q82_1F, obj=0q82_3F, txt='something', num=0q82_7F)
    #     # print(repr(w))

    def test_verb_txt(self):
        """Test s.v(o, n, txt).  Read with s.v(o).txt"""
        human = self.system.agent('human')
        anna = human('anna')
        bart = human('bart')
        self.system.verb('like')
        anna.like(bart, 5, "just as friends")
        self.assertEqual("just as friends", anna.like(bart).txt)

    def test_verb_overlay(self):
        """Test multiple s.v(o, num) calls with different num's.  Read with s.v(o).num"""
        human = self.system.agent('human')
        anna = human('anna')
        bart = human('bart')
        self.system.verb('like')
        max_idn = self.system.max_idn()

        anna.like(bart, 8)
        self.assertEqual(max_idn+1, self.system.max_idn())
        self.assertEqual(8, anna.like(bart).num)

        anna.like(bart, 10)
        self.assertEqual(max_idn+2, self.system.max_idn())
        self.assertEqual(10, anna.like(bart).num)

        anna.like(bart, 2)
        self.assertEqual(max_idn+3, self.system.max_idn())
        self.assertEqual(2, anna.like(bart).num)

    def test_verb_overlay_duplicate(self):
        human = self.system.agent('human')
        anna = human('anna')
        bart = human('bart')
        self.system.verb('like')
        max_idn = self.system.max_idn()

        anna.like(bart, 5, "just as friends")
        self.assertEqual(max_idn+1, self.system.max_idn())

        # anna.like(bart, 5, "just as friends")
        # self.assertEqual(max_idn+1, self.system.max_idn(), "Identical s.v(o,n,t) shouldn't generate a new word.")
        # TODO:  Decide whether these "duplicates" should be errors or insert new records or not...
        # TODO:  Probably it should be an error for some verbs (e.g. like) and not for others (e.g. comment)
        # TODO: 'unique' option?  Imbue "like" verb with properties using Words??

        anna.like(bart, 5, "maybe more than friends")
        self.assertEqual(max_idn+2, self.system.max_idn(), "New t should generate a new word.")

        anna.like(bart, 6, "maybe more than friends")
        self.assertEqual(max_idn+3, self.system.max_idn(), "New n should generate a new word.")

        anna.like(bart, 7, "maybe more than friends")
        self.assertEqual(max_idn+4, self.system.max_idn())

        # anna.like(bart, 7, "maybe more than friends")
        # self.assertEqual(max_idn+4, self.system.max_idn())

        anna.like(bart, 5, "just as friends")
        self.assertEqual(max_idn+5, self.system.max_idn(), "Reverting to an old n,t should generate a new word.")

    def test_is_definition(self):
        self.assertTrue(self.system('noun').is_definition())
        self.assertTrue(self.system('verb').is_definition())
        self.assertTrue(self.system('define').is_definition())
        self.assertTrue(self.system('agent').is_definition())
        self.assertTrue(self.system.is_definition())

        human = self.system.agent('human')
        anna = human('anna')
        bart = human('bart')
        like = self.system.verb('like')
        liking = anna.like(bart, 5)

        self.assertTrue(human.is_definition())
        self.assertTrue(anna.is_definition())
        self.assertTrue(bart.is_definition())
        self.assertTrue(like.is_definition())
        self.assertFalse(liking.is_definition())

    def test_non_verb_undefined_as_function_disallowed(self):
        human = self.system.agent('human')
        anna = human('anna')
        bart = human('bart')
        self.system.verb('like')

        liking = anna.like(bart, 5)
        with self.assertRaises(qiki.Word.NonVerbUndefinedAsFunctionException):
            liking(bart)

    def test_system_is_system(self):
        sys1 = self.system
        sys2 = self.system('system')
        sys3 = self.system('system')('system')('system')
        sys4 = self.system('system').system('system').system.system.system('system')('system')('system')
        self.assertEqual(sys1.idn, sys2.idn)
        self.assertEqual(sys1.idn, sys3.idn)
        self.assertEqual(sys1.idn, sys4.idn)
        self.assertIs(sys1, sys2)
        self.assertIs(sys1, sys3)
        self.assertIs(sys1, sys4)

    def test_idn_setting_not_allowed(self):
        _system = self.system('system')
        self.assertEqual(_system.idn, self.system._ID_SYSTEM)
        with self.assertRaises(RuntimeError):
            _system.idn = 999
        self.assertEqual(_system.idn, self.system._ID_SYSTEM)

    def test_idn_suffix(self):
        _system = self.system('system')
        self.assertEqual(_system.idn, self.system._ID_SYSTEM)
        suffixed_system_idn = _system.idn.add_suffix(3)
        self.assertEqual(_system.idn, self.system._ID_SYSTEM)
        self.assertEqual(suffixed_system_idn, qiki.Number('0q82_05__030100'))


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
        self.listing = self.system.noun('listing')
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
        bless = self.system.verb('bless')
        blessed_name = self.system.spawn(
            sbj=self.system.idn,
            vrb=bless.idn,
            obj=archie.idn,
            txt="mah soul",
            num=qiki.Number(666),
        )
        blessed_name.save()

        blessed_name_too = self.system.spawn(blessed_name.idn)
        self.assertTrue(blessed_name_too.exists)
        self.assertEqual(blessed_name_too.sbj, qiki.Word._ID_SYSTEM)
        self.assertEqual(blessed_name_too.vrb, bless.idn)
        self.assertEqual(blessed_name_too.obj, archie.idn)
        self.assertEqual(blessed_name_too.num, qiki.Number(666))
        self.assertEqual(blessed_name_too.txt, "mah soul")

        laud = self.system.verb('laud')
        thing = self.system.noun('thing')
        lauded_thing = self.system.spawn(
            sbj=archie.idn,
            vrb=laud.idn,
            obj=thing.idn,
            txt="most sincerely",
            num=qiki.Number(123456789),
        )
        lauded_thing.save()

    def test_listing_using_method_verb(self):
        archie = self.Student(qiki.Number(0))
        bless = self.system.verb('bless')
        blessed_name = self.system.bless(archie, qiki.Number(666), "mah soul")

        blessed_name_too = self.system.spawn(blessed_name.idn)
        self.assertTrue(blessed_name_too.exists)
        self.assertEqual(blessed_name_too.sbj, qiki.Word._ID_SYSTEM)
        self.assertEqual(blessed_name_too.vrb, bless.idn)
        self.assertEqual(blessed_name_too.obj, archie.idn)
        self.assertEqual(blessed_name_too.num, qiki.Number(666))
        self.assertEqual(blessed_name_too.txt, "mah soul")

        self.system.verb('laud')
        thing = self.system.noun('thing')
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
        self.system.verb('like')
        barbara.like(deanne, qiki.Number(1))
        deanne.like(barbara, qiki.Number(-1000000000))

        self.describe_all_words()

    def test_listing_by_system_idn(self):
        """Make sure system(suffixed number) will look up a listing."""
        chad1 = self.Student(2)
        idn_chad = chad1.idn
        chad2 = self.system(idn_chad)
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
        self.SubStudent.install(self.system.noun('sub_student'))
        self.AnotherListing.install(self.system.noun('another_listing'))

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
        # Serious assumption here, that only 5 words were defined before system.noun('listing').
        # But this helps to demonstrate Listing meta_word and instance idn contents.
        self.assertEqual('0q82_06', qiki.Listing.meta_word.idn.qstring())
        self.assertEqual('0q82_07', self.Student.meta_word.idn.qstring())   # Number(7)
        self.assertEqual('0q82_07__8202_1D0300', chad.idn.qstring())   # Root is Number(7), payload is Number(2).
        self.assertEqual('0q82_08', self.SubStudent.meta_word.idn.qstring())
        self.assertEqual('0q82_09', self.AnotherListing.meta_word.idn.qstring())






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
    #     system = qiki.Word('system')
    #     self.assertEqual(system.sbj, system.idn)
    #     self.assertEqual(system.obj, agent.idn)
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
    #     system = qiki.Word('system')
    #     noun = qiki.Word('noun')
    #     human = system.define(noun, 'human')
    #     self.assertTrue(human.exists)
    #     self.assertEqual('human', human.txt)
    #
    # def test_zz1_define_by_idn(self):
    #     system = qiki.Word('system')
    #     noun = qiki.Word('noun')
    #     human = system.define(noun, 'human')
    #     self.assertTrue(human.exists)
    #     self.assertEqual('human', human.txt)
    #
    # def test_zz1_noun_method(self):
    #     system = qiki.Word('system')
    #     thing = system.noun('thing')
    #     self.assertTrue(thing.exists)
    #     self.assertEqual('thing', thing.txt)
    #
    # def test_zz2_define_collision(self):
    #     system = qiki.Word('system')
    #     noun = qiki.Word('noun')
    #     system.define(noun, 'human')
    #     with self.assertRaises(qiki.Word.DefineDuplicateException):
    #         system.define(noun, 'human')
    #
    # def test_zz3_define_verb(self):
    #     system = qiki.Word('system')
    #     verb = qiki.Word('verb')
    #     like = system.define(verb, 'like')
    #     self.assertEqual(like.txt, 'like')
    #     self.assertEqual(like.obj, verb.idn)
    #     qiki.Word.make_verb_a_method(like)
    #     rating = system.like(system, system, 'loving itself', qiki.Number(100))
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
