# coding=utf-8
"""
Testing qiki word.py
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import calendar
import inspect
import json
import re
import sys
import threading
import time
import unicodedata
import unittest
import uuid

import mysql.connector
import six

import qiki
from qiki.number import hex_from_bytes
from qiki.number import type_name
from qiki.word import is_iterable
from qiki.word import SubjectedVerb

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
                user=    'example_user',
                password='example_password',
                database='example_database',
                table=   'word',
                engine=  'MEMORY',        # About 2x faster unit testing.
                txt_type='VARCHAR(255)',  # Because MEMORY doesn't support TEXT.
            )

        You also need to create an empty (0 bytes) file named secure/__init__.py
        Why?  See https://stackoverflow.com/questions/10863268/how-is-an-empty-init-py-file-correct
        Short answer:  that makes 'secure' into a package so we can import from it 'credentials.py' 
        which is a module.

        In MySQL you will need to create the example_database and the example_user.
        LexMySQL will create the table.  Example MySQL commands to do all that:
                
            CREATE DATABASE `example_database`;
            CREATE USER 'example_user'@'localhost';
            ALTER USER  'example_user'@'localhost' 
                IDENTIFIED BY 'example_password';
            GRANT CREATE, INSERT, SELECT, DROP 
                ON `example_database`.* 
                TO 'example_user'@'localhost';
            
    \n""", end="")
    sys.exit(1)


LET_DATABASE_RECORDS_REMAIN = False
# NOTE:  False = Each run deletes its table
#        True = Each run leaves its table behind, for human examination
#               If RANDOMIZE_DATABASE_TABLE = True
#                   then HUNDREDS of tables remain, after running all tests
#               If RANDOMIZE_DATABASE_TABLE = False
#                   then only table 'word' remains -- and I GUESS it contains the results of
#                   whatever test HAPPENED to run last.  So this is mainly useful when
#                   running individual tests.
#        Either way, each test starts with an empty, virgin lex.

RANDOMIZE_DATABASE_TABLE = False
# NOTE:  False = table name e.g. 'word'
#                See secure.credentials.for_unit_testing_database.table for actual table name.
#        True = this supports concurrent test runs (e.g. Word2.7 and Word3.9).
#               Table name e.g. word_ce09954b2e784cd8811b640079497568
# CAUTION:  if LET_DATABASE_RECORDS_REMAIN is also True, then
#           HUNDREDS of tables will accumulate after each full test run.

TEST_ASTRAL_PLANE = True   # Test txt with Unicode characters on an astral-plane (beyond the base 64K)

SHOW_UTF8_EXAMPLES = False   # Prints a few unicode test strings in both \u escape syntax and UTF-8 hexadecimal.
                             # e.g.  "\u262e on earth" in utf8 is E298AE206F6E206561727468


class TestFlavors(object):
    """Run each test derived from WordTests using the following variations."""
    SPECS = [
        # dict(name="LexMySQL/InnoDB", lex_class=qiki.LexMySQL, engine='InnoDB'),
        dict(name="LexMySQL/Memory", lex_class=qiki.LexMySQL, engine='MEMORY'),
        dict(name="LexInMemory",     lex_class=qiki.LexInMemory),
    ]
    NON_CREDENTIAL_SPECS = 'name', 'lex_class'   # SPECS column names
    SQL_LEXES = [qiki.LexMySQL]                  # SPECS row subset (of lex_class column values)

    counts = {spec['name'] : 0 for spec in SPECS}

    @classmethod
    def all_specs(cls):
        return [s for s in cls.SPECS]

    @classmethod
    def all_sql_specs(cls):
        return [s for s in cls.SPECS if s['lex_class'] in cls.SQL_LEXES]

    @classmethod
    def credentials_from_specs(cls, spec):
        """
        Extract credential modifiers from specs.

        I know I know, this should be part of a "Spec" class, along with much else.
        """
        return {k: v for k, v in spec.items() if k not in cls.NON_CREDENTIAL_SPECS}

    @classmethod
    def count_test(cls, spec):
        cls.counts[spec['name']] += 1

    @classmethod
    def report(cls):
        return "\n".join(cls.report_lines())

    @classmethod
    def report_lines(cls):
        for spec in cls.SPECS:
            name = spec['name']
            yield "{count:5d} tests on {name}".format(
                name=name,
                count=cls.counts[name],
            )


class TestBaseClass(unittest.TestCase):
    """Base class for all qiki.Word tests."""


# noinspection PyPep8Naming
def tearDownModule():
    print(TestFlavors.report())    # Run once after all tests.


# mysql_client_version = subprocess.Popen(
#     'mysql --version',
#     shell=True,
#     stdout=subprocess.PIPE
# ).stdout.read().decode('unicode_escape').strip()


def version_report():
    print("Python version", ".".join(str(x) for x in sys.version_info))
    # EXAMPLE:  Python version 2.7.14.final.0
    # EXAMPLE:  Python version 2.7.16.final.0
    # EXAMPLE:  Python version 3.4.3.final.0
    # EXAMPLE:  Python version 3.5.4.final.0
    # EXAMPLE:  Python version 3.6.8.final.0
    # EXAMPLE:  Python version 3.7.3.final.0
    # EXAMPLE:  Python version 3.8.0.alpha.4

    print("MySQL Python Connector version", mysql.connector.version.VERSION_TEXT)
    # EXAMPLE:  MySQL Python Connector version 2.0.3
    # EXAMPLE:  MySQL Python Connector version 2.2.2b1
    # EXAMPLE:  MySQL Python Connector version 8.0.16

    # print("MySQL Client version " + mysql_client_version + "\n", end="")
    # NOTE:  Python 2 quirks in THIS print() call:
    #            appends a \n to the subprocess output
    #            ignores the end= parameter
    #            never outputs a newline, unless it's explicit in the string
    # EXAMPLE:  MySQL Client version mysql  Ver 14.14 Distrib 5.7.24, for Win64 (x86_64)
    # NOTE:  Maybe we don't care what mysql --version says.
    #        Isn't the python connector the "real" "client" we're running here?

    credentials = secure.credentials.for_unit_testing_database.copy()
    try:
        lex = qiki.LexMySQL(**credentials)
    except qiki.LexMySQL.ConnectError:
        print("(cannot determine MySQL server version)")
    else:
        server_version = lex.server_version()

        # lex.uninstall_to_scratch()
        # TODO:  Wasn't uninstall_to_scratch() rather brutish if all we did was server_version()?

        lex.disconnect()
        print("MySQL Server version", server_version)
        # EXAMPLE:  MySQL Server version 5.7.24


version_report()


class SafeNameTests(TestBaseClass):
    """Test LexMySQL naming of tables and engines."""

    # NOTE:  For some reason, PyCharm got stupid about which secure.credentials were active when
    #        unit testing, while a project was loaded with another secure.credentials.  Hence the
    #        following noinspection.  The correct package imports when run however.
    # noinspection PyUnresolvedReferences

    def test_table_name_at_creation_good(self):
        credentials = secure.credentials.for_unit_testing_database.copy()

        def good_table_name(name):
            credentials['table'] = name
            lex = qiki.LexMySQL(**credentials)
            lex.uninstall_to_scratch()   # in case left over from a botched test
            lex.install_from_scratch()

            self.assertEqual('verb', lex['define'].obj.txt)
            # NOTE:  Former error about None having no txt attribute goes away by deleting the table.
            #        But it shouldn't happen now that we uninstall and install.

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

        # 2018.0712 - long hang on test 14 of 255.
        # Restarting the MySQL server got it unstuck, but it just keeps
        # happening now.  So something is effed up.
        # After implementing LexMemory and switching (clumsily) back and forth
        # to LexMySQL.
        # Then specifically was trying to get (groan) show_version to work.
        # Oh!  It was failure to lex.disconnect() from another test.

        def good_engine_name(engine_name):
            credentials['engine'] = engine_name
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
                # Why did this break once (a few times in a row) for 3 of these bad engine names?
                # Seemed to fix itself after a few hours.  Or switching python versions.

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
        lex.uninstall_to_scratch()   # in case left over from a botched test
        lex.install_from_scratch()

        self.assertEqual('verb', lex['define'].obj.txt)

        lex._table = 'evil_table_name_later_`\'_\"_oops_\\"'
        with self.assertRaises(qiki.LexMySQL.IllegalTableName):
            self.assertEqual('verb', lex['define'].obj.txt)
        lex._table = 'innocent_table_name_to_start_with'
        lex.uninstall_to_scratch()
        lex.disconnect()


class LexErrorTests(TestBaseClass):
    """Try to generate common errors with instatiating a Lex."""

    def test_bad_password(self):
        """
        Example of the entire bad-password exception message:

        1045 (28000): Access denied for user 'unittest'@'localhost' (using password: YES)
        """
        credentials = secure.credentials.for_unit_testing_database.copy()
        credentials['password'] = 'wrong'
        # noinspection SpellCheckingInspection,SpellCheckingInspection
        with six.assertRaisesRegex(self, qiki.LexSentence.ConnectError, r'Access denied'):
            # EXAMPLE:  1045 (28000): Access denied for user 'unittest'@'localhost' (using password: YES)
            qiki.LexMySQL(**credentials)
            # TODO:  Prevent ResourceWarning in Python 3.4 - 3.6
            # EXAMPLE:   (appears every time running tests Word3.4, Word3.5, Word3.6)
            #        ResourceWarning: unclosed <socket.socket fd=524, family=AddressFamily.AF_INET,
            #        type=SocketKind.SOCK_STREAM, proto=6, laddr=('127.0.0.1', 59546),
            #        raddr=('127.0.0.1', 3306)>
            # EXAMPLE:  (intermittently appears below "OK" after all tests pass)
            #        sys:1: ResourceWarning: unclosed file <_io.BufferedReader name=3>
            # EXAMPLE:  (intermittently appears below "OK" after all tests pass)
            #        C:\Python34\lib\importlib\_bootstrap.py:2150: ImportWarning: sys.meta_path is empty

    def test_two_lex(self):
        lex1 = qiki.LexMySQL(**secure.credentials.for_unit_testing_database)
        max_start = lex1.max_idn()

        lex1.define(lex1.noun(), 'borg')
        self.assertEqual(max_start + 1, lex1.max_idn())

        lex2 = qiki.LexMySQL(**secure.credentials.for_unit_testing_database)
        self.assertEqual(max_start + 1, lex2.max_idn())

        # lex2.uninstall_to_scratch()   # Why does this cause infinite hang?
        lex2.disconnect()
        lex1.uninstall_to_scratch()
        lex1.disconnect()

    def test_connection_neglect(self):
        """Test automatic reconnection of the Lex."""
        lex = qiki.LexMySQL(**secure.credentials.for_unit_testing_database)
        self.assertEqual(1, lex.noun('noun').num)
        lex._simulate_connection_neglect()
        self.assertEqual(1, lex.noun('noun').num)
        lex.disconnect()


# noinspection PyUnresolvedReferences
class WordTests(TestBaseClass):
    """Base class for qiki.Word tests that use a standard, empty self.lex.  Has no tests itself."""

    first_setup = True

    def __init__(self, *args, **kwargs):
        super(WordTests, self).__init__(*args, **kwargs)
        self.all_flavors()
        self.flavor_spec = None

    def all_flavors(self):
        self.flavor_specs = TestFlavors.all_specs()

    def only_sql_flavors(self):
        self.flavor_specs = TestFlavors.all_sql_specs()

    def run(self, result=None):
        """
        Run the unit tests on each of the Lex classes.

        If one version of the tests raises an exception, the other version may never be tested.
        
        This may slightly confuse the test framework on the total number of tests being run.
        """
        # THANKS:  Parameterizing tests, https://eli.thegreenplace.net/2011/08/02/python-unit-testing-parametrized-test-cases
        #          In classes derived from WordTests, tests are parameterized by self.flavor_specs.

        break_flavor_loop = False
        for self.flavor_spec in self.flavor_specs:
            if break_flavor_loop:
                break

            try:
                result = super(WordTests, self).run(result)
            except self.AbortAllTests as e:
                # NOTE:  Take #1 handling AbortAllTests.
                if result is not None:

                    result.stop()
                    # THANKS:  result.stop() in run() aborts all tests,
                    #          https://stackoverflow.com/a/59955861/673991

                    print("Aborting tests:", str(e))
                else:
                    print("Unable to abort tests?", str(e))
                break_flavor_loop = True
            else:
                if WordTests.AbortAllTests.has_ever_been_instantiated:
                    # NOTE:  Take #2 handling AbortAllTests.
                    #        May be necessary because take #1 relies on an undocumented
                    #        nuance of the test framework, that it handles all exceptions
                    #        but KeyboardInterrupt.

                    print("Aborting tests, take two.")
                    if result is not None:
                        result.stop()
                    break_flavor_loop = True
                else:
                    TestFlavors.count_test(self.flavor_spec)

            # TODO:  Encapsulate this take one / take two ugliness in
            #        AbortAllTests, along with the related ugliness of relying on
            #        KeyboardInterrupt special re-raising.

        return result

    def lex_class(self):
        return self.flavor_spec['lex_class']

    def setUp(self):
        super(WordTests, self).setUp()
        credentials = secure.credentials.for_unit_testing_database.copy()
        if RANDOMIZE_DATABASE_TABLE:
            credentials['table'] = 'word_' + uuid.uuid4().hex
            # EXAMPLE:  word_ce09954b2e784cd8811b640079497568

        credentials.update(TestFlavors.credentials_from_specs(self.flavor_spec))
        try:
            self.lex = self.lex_class()(**credentials)
        except qiki.LexMySQL.ConnectError as e:

            print("MySQL down?")
            # NOTE:  Twice weird how this SOMETIMES appears BELOW the print()s
            #        from processing AbortAllTests.

            raise self.AbortAllTests("CANNOT CONNECT MYSQL: " + str(e))

            # self.fail("CANNOT CONNECT MYSQL: " + str(e))
            # NO THANKS:  Only aborts THIS test, not ALL tests, https://stackoverflow.com/a/7779760/673991
        else:
            def cleanup_disconnect():
                if not LET_DATABASE_RECORDS_REMAIN:
                    self.lex.uninstall_to_scratch()
                    # NOTE:  The corresponding self.lex.install_from_scratch() happens automagically
                    #        in the next flavor's call to its lex constructor in setUp().
                self.lex.disconnect()

            self.addCleanup(cleanup_disconnect)
            # THANKS:  addCleanup vs tearDown, https://stackoverflow.com/q/37534021/673991

            if LET_DATABASE_RECORDS_REMAIN or WordTests.first_setup:
                WordTests.first_setup = False
                self.lex.uninstall_to_scratch()
                self.lex.install_from_scratch()
                # NOTE:  Delete old table from last test, insert fresh new table for this test.

    class AbortAllTests(KeyboardInterrupt):
        """No reason to run any other tests if this happens."""

        # THANKS:  KeyboardInterrupt bubbles, https://stackoverflow.com/a/45518359/673991
        #          This is a dirty bit of insider knowledge to take advantage of,
        #          but it makes error handling slightly better.
        #          TestCase.run() calls unittest/case.py _Outcome.testPartExecutor()
        #          That function intercepts and re-raises KeyboardInterrupt,
        #          but it intercepts all other exceptions without re-raising them.
        #          At least it behaves that way in 2020.  Hence the fallback on sentinel
        #          variable has_ever_been_raised.

        has_ever_been_instantiated = False

        def __init__(self, *args, **kwargs):

            WordTests.AbortAllTests.has_ever_been_instantiated = True
            # CAUTION:  Cannot set class variables via self.

            # FALSE WARNING:  Unexpected argument -- wtf is wrong with **kwargs??
            # noinspection PyArgumentList
            super(WordTests.AbortAllTests, self).__init__(*args, **kwargs)

    def lex_report(self):

        print()
        print(inspect.stack()[0][3], "<--", inspect.stack()[1][3])
        print()

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

        histogram_high_to_low = sorted(histogram.items(), key=lambda pair: pair[1], reverse=True)
        # THANKS:  Sorting a dictionary by value, http://stackoverflow.com/a/2258273/673991

        print()
        for idn, quantity in histogram_high_to_low:
            print(quantity, unicodedata.lookup('dot operator'), repr(self.lex[idn]))

        print()
        print("Mesa lexes")
        for key, lex in self.lex.mesa_lexes.items():
            if key is None:
                print("    None: {class_}".format(
                    class_=type_name(lex),
                ))
            else:
                print("    {key}: {instance} -- {class_}".format(
                    key=key.qstring(),
                    instance=self.lex[key].txt,
                    class_=type_name(lex),
                ))

    def show_txt_in_utf8(self, idn):
        word = self.lex[idn]
        utf8 = word.txt.encode('utf-8')
        # FIXME:  This will double encode in Python 2
        hexadecimal = hex_from_bytes(utf8)
        print("\"{txt}\" in utf8 is {hex}".format(
            txt=word.txt.encode('unicode_escape'),   # Python 3 doubles up the backslashes ... shrug.
            hex=hexadecimal,
        ))

    def assertSensibleWhen(self, whn):
        self.assertIsNotNone(whn)
        self.assertGreaterEqual(self.lex.now_number(), float(whn))
        self.assertLessEqual(1447029882.792, float(whn))

    class _CheckNewWordCount(object):
        """Expect the creation of a specific number of words."""
        def __init__(self, lex, expected_new_words, msg=None):
            self.lex = lex
            self.expected_new_words = expected_new_words
            self.msg = msg

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
                if self.msg is None:
                    use_message = stock_message
                else:
                    use_message = stock_message + "\n" + self.msg
                raise self.WrongCount(use_message)

        class WrongCount(Exception):
            pass

    def assertNewWords(self, expected_new_words, msg=None):
        """Expect n words to be created.

        with self.assertNewWords(2):
            do_something_that_should_create_exactly_2_new_words()
        """
        return self._CheckNewWordCount(self.lex, expected_new_words, msg)

    def assertNoNewWord(self, msg=None):
        return self.assertNewWords(0, msg)

    def assertNewWord(self, msg=None):
        return self.assertNewWords(1, msg)

    def assertTripleEqual(self, first, second, msg=None):
        """Same value and same type.  (Ala javascript === operator.)"""
        self.assertEqual(first, second, msg)
        self.assertIs(type(first), type(second), msg)

    def assertExactlyFalse(self, x):
        """Not just falsy."""
        self.assertTripleEqual(False, x)

    def fails(self, msg=None):
        return self.assertRaises(AssertionError, msg=msg)
        # NOTE:  It appears that .assertRaises() is the only assert-method that requires the msg
        #        parameter be passed by name.


class WordDemoTests(WordTests):

    # noinspection PyUnusedLocal
    def test_syntaxes(self):
        """
        Demonstrate qiki-python:  qiki actions in Python code.

        This doesn't test so much as show off code.
        """
        lex = self.lex
        s = lex.define('agent', 's')
        v = lex.define('verb', 'v')
        o = lex.define('noun', 'o')
        t = 'some text'
        n = qiki.Number(42)

        # Deleters, the zero way
        s(v)[o] = 0
        lex.create_word(s,v,o,0)

        # Deleters, the NAN way
        s(v)[o] = qiki.Number.NAN
        lex.create_word(s,v,o,qiki.Number.NAN)

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
        lex[s](v)[o] = ''
        lex.create_word(sbj=s, vrb=v, obj=o, num=n, txt=t)
        lex.create_word(s, v, o, num=n, txt=t)
        lex.create_word(s, v, o, txt=t, num=n)
        lex.create_word(s, v, o, num=n)
        lex.create_word(s, v, o, txt=t)   # boo hoo swapped positional arguments will break
        lex.create_word(s, v, o)
        # s.v(o, n)
        # s.v(o, n, t)
        # s.v(o, num=n)

        # Definers
        # s(define)[o] &= t ???
        lex.define(o, t)
        s('define')[o] = t

        # Getters (but not setters)
        w = lex[s](v)[o]
        w = s(v)[o]
        w = s.said(v, o)

        # Setter if it does not exist already.  Getter either way.
        # (By exist, I mean all five match: s,v,o,n,t.)
        w = s(v, num=n, txt=t)[o]
        w = s(v, n, t)[o]
        # (w := lex[s](v)[o]) = n,t   # in Python 3.8?!
        # w = lex[s](v).setdefault(o, n, t)
        # w = s(v).setdefault(o, n, t)
        # w = s(v)[o].setdefault(n, t)
        # w = s(v, n)[o].setdefault(t)
        # w = s(v, t)[o].setdefault(n)
        # w = s(v)[o].append(n, t)
        # s(v)[o] |= 1 ???
        s(v, use_already=True)[o] = 1;  w = s(v)[o]
        s(v, use_already=True)[o] = n,t;  w = s(v)[o]
        w = lex.create_word(s, v, o, n, t, use_already=True)
        w = lex.create_word(s, v, o, use_already=True)
        # w = s.v(o, n, use_already=True)
        # w = s.v(o, n, t, use_already=True)
        w = s(v, n, t)[o]
        w = s(v, num=n, txt=t)[o]

        # Set and get the object.
        s(v)[o] = n,t; w = s(v)[o]
        w = lex.create_word(s, v, o, n, t)

        # Delta if it exists already.  Setter if it does not.
        # s(v)[o] += n   TODO, but how?
        # s(v, num_add=n)[o]   TODO?
        lex.create_word(s, v, o, num_add=n)
        # s.v(o, num_add=n)

        # NOTE:  Are these more Pythonic?
        #            s.v(o)
        #            s.v(o, n, t)
        #            lex.s.v(o, n, t)?
        #            lex[s].v(o, n, t)

    def test_read_md(self):
        """Example code in README.md"""
        lex = qiki.LexInMemory()
        hello = lex.verb('hello')
        world = lex.noun('world')

        lex[lex](hello)[world] = 42,"How are ya!"

        word = lex[lex](hello)[world]

        # print(int(word.num), word.txt)
        # # 42 How are ya!
        #
        # print("{:svo}".format(word))
        # # Word(sbj=lex,vrb=hello,obj=world)

        self.assertEqual("42", str(int(word.num)))
        self.assertEqual("How are ya!", str(word.txt))
        self.assertEqual("Word(sbj=lex,vrb=hello,obj=world)", "{:svo}".format(word))


class WordExoticTests(WordTests):

    def test_square_circle_square_assignment(self):
        subject_ = self.lex.define('agent', 'subject_')
        verb_    = self.lex.verb('verb_')
        object_  = self.lex.noun('object_')

        with self.assertNewWord():
            subject_(verb_)[object_] = 42, "courage"
            w = subject_(verb_)[object_]

        self.assertEqual('subject_', w.sbj.txt)
        self.assertEqual('verb_',    w.vrb.txt)
        self.assertEqual('object_',  w.obj.txt)
        self.assertEqual('object_',  w.obj.txt)
        self.assertEqual(42,          w.num)
        self.assertEqual('courage',  w.txt)

    def test_square_circle_square_parameters(self):
        subject_ = self.lex.define('agent', 'subject_')
        verb_    = self.lex.verb('verb_')
        object_  = self.lex.noun('object_')

        with self.assertNewWord():
            w = self.lex[subject_](verb_, num=42, txt="courage")[object_]

        self.assertEqual('subject_', w.sbj.txt)
        self.assertEqual('verb_',    w.vrb.txt)
        self.assertEqual('object_',  w.obj.txt)
        self.assertEqual('object_',  w.obj.txt)
        self.assertEqual(42,          w.num)
        self.assertEqual('courage',  w.txt)

    def test_extract_txt_num(self):

        def extract_test(expected_pair, *args, **kwargs):
            """Verify extract_txt_num() returns the right pair.  And rejects non-Unicode."""
            args_list = list(args)   # shallow copy
            kwargs_dict = dict(kwargs)  # shallow copy
            actual_pair = SubjectedVerb.extract_txt_num(args_list, kwargs_dict)
            self.assertEqual(expected_pair, actual_pair)
            self.assertEqual([], args_list)
            self.assertEqual({}, kwargs_dict)   # Make sure all args,kwargs were removed in-place

            if (
                any(isinstance(x, six.text_type) for x in args) or
                any(isinstance(x, six.text_type) for k,x in kwargs.items())
            ) :
                # NOTE:  Some of the args or kwargs are unicode strings.
                #        Make sure they cause a TypeError if they're byte-strings.
                args_non_unicode = [
                    x.encode('ascii') if isinstance(x,six.text_type) else x
                    for x in args
                ]
                kwargs_non_unicode = {
                    k:x.encode('ascii') if isinstance(x,six.text_type) else x
                    for k,x in kwargs.items()
                }
                with six.assertRaisesRegex(self, TypeError, re.compile(r'unicode', re.IGNORECASE)):
                    SubjectedVerb.extract_txt_num(args_non_unicode, kwargs_non_unicode)

        extract_test((   '',  1), )

        extract_test(('foo',  1), 'foo')
        extract_test(('foo',  1), txt='foo')

        extract_test((   '', 42), 42)
        extract_test((   '', 42), num=42)

        extract_test((   '', 42), qiki.Number(42))
        extract_test((   '', 42), num=qiki.Number(42))

        extract_test(('foo', 42), 'foo', 42)
        extract_test(('foo', 42), 42, 'foo')
        extract_test(('foo', 42), 'foo', num=42)
        extract_test(('foo', 42), txt='foo', num=42)
        extract_test(('foo', 42), 42, txt='foo')

        extract_test(('foo', 42), 'foo', qiki.Number(42))
        extract_test(('foo', 42), qiki.Number(42), 'foo')
        extract_test(('foo', 42), 'foo', num=qiki.Number(42))
        extract_test(('foo', 42), txt='foo', num=qiki.Number(42))
        extract_test(('foo', 42), qiki.Number(42), txt='foo')

        # noinspection PyPep8Naming
        EXTRA_KWARGS = dict(any=0, other=1, keywords=2)

        def extract_test_extra_kwargs(expected_pair, *args, **kwargs):
            """Verify extract_txt_num() leaves behind kwargs it can't use."""
            args_mutable = list(args)
            actual_pair = SubjectedVerb.extract_txt_num(args_mutable, kwargs)
            self.assertEqual(expected_pair, actual_pair)
            self.assertEqual([], args_mutable)
            self.assertEqual(EXTRA_KWARGS, kwargs)

        extract_test_extra_kwargs(('foo', 42), 'foo', 42,         **EXTRA_KWARGS)
        extract_test_extra_kwargs(('foo', 42), 'foo', num=42,     **EXTRA_KWARGS)
        extract_test_extra_kwargs(('foo', 42), 42, txt='foo',     **EXTRA_KWARGS)
        extract_test_extra_kwargs(('foo', 42), num=42, txt='foo', **EXTRA_KWARGS)

        extract_test_extra_kwargs(('foo',  1), txt='foo',         **EXTRA_KWARGS)
        extract_test_extra_kwargs(('foo',  1), 'foo',             **EXTRA_KWARGS)

        extract_test_extra_kwargs(('',    42), 42,                **EXTRA_KWARGS)
        extract_test_extra_kwargs(('',    42), num=42,            **EXTRA_KWARGS)

        extract_test_extra_kwargs((''   ,  1),                    **EXTRA_KWARGS)
        extract_test_extra_kwargs((''   ,  1),                    **EXTRA_KWARGS)

        def extract_test_bombs(*args, **kwargs):
            """Verify conditions where extract_txt_num() should raise an exception."""
            with self.assertRaises(TypeError):
                _, _ = SubjectedVerb.extract_txt_num(args, kwargs)

        extract_test_bombs(42, 99)              # two numerics
        extract_test_bombs('foo', 'bar')        # two texts
        extract_test_bombs(42, 'foo', 99)       # two numerics with a text between
        extract_test_bombs('foo', 42, 'bar')    # two texts with a numeric between

        extract_test_bombs(42, num=99)          # both positional and keyword numeric
        extract_test_bombs('foo', txt='bar')    # both positional and keyword text

        extract_test_bombs(num='foo')           # num=non-numeric
        extract_test_bombs(42, num='foo')       # num=non-numeric
        extract_test_bombs('bar', num='foo')    # num=non-numeric
        extract_test_bombs(txt=42)              # txt=non-text
        extract_test_bombs(99, txt=42)          # txt=non-text
        extract_test_bombs('foo', txt=42)       # txt=non-text

    def test_extract_txt_num_singleton(self):
        self.assertEqual(("foo", 1), SubjectedVerb.extract_txt_num("foo", dict()))
        self.assertEqual(("",   42), SubjectedVerb.extract_txt_num(42, dict()))

    def test_extract_txt_num_tuple(self):
        self.assertEqual(("foo",  1), SubjectedVerb.extract_txt_num(("foo",), dict()))
        self.assertEqual(("",    42), SubjectedVerb.extract_txt_num((42,), dict()))
        self.assertEqual(("foo", 42), SubjectedVerb.extract_txt_num((42, "foo"), dict()))
        self.assertEqual(("foo", 42), SubjectedVerb.extract_txt_num(("foo", 42), dict()))

    def test_setter_and_getter(self):
        self.assertFalse(self.lex['animal'].exists())
        animal = self.lex['lex']('define', txt='animal')['noun']
        self.assertTrue(self.lex['animal'].exists())
        self.assertEqual(animal, self.lex['animal'])
        self.assertEqual(
            ('lex'         , 'define'      , 'noun'        , 'animal'),
            (animal.sbj.txt, animal.vrb.txt, animal.obj.txt, animal.txt)
        )

        unicorn = self.lex['lex']('define', txt='unicorn', num=42)['animal']
        self.assertEqual(
            ('lex'          , 'define'       , 'animal'       , 'unicorn'  , 42),
            (unicorn.sbj.txt, unicorn.vrb.txt, unicorn.obj.txt, unicorn.txt, unicorn.num)
        )

    def test_lex_square_txt_nonexistent(self):
        # TODO:  Why is this not a ValueError?
        self.assertFalse(             self.lex['nevermore'].exists())
        self.assertEqual(None,        self.lex['nevermore'].idn)
        self.assertEqual(None,        self.lex['nevermore'].sbj)
        self.assertEqual(None,        self.lex['nevermore'].vrb)
        self.assertEqual(None,        self.lex['nevermore'].obj)
        self.assertEqual(None,        self.lex['nevermore'].num)
        self.assertEqual('nevermore', self.lex['nevermore'].txt)
        self.assertEqual(None,        self.lex['nevermore'].whn)

        self.assertEqual('nevermore', str(self.lex['nevermore']))

        six.assertRegex(self, repr(self.lex['nevermore']), r'undefined')
        six.assertRegex(self, repr(self.lex['nevermore']), r'nevermore')

        # print("Nonexistent txt str:", str(self.lex['nevermore']))
        # EXAMPLE:  nevermore

        # print("Nonexistent txt repr:", repr(self.lex['nevermore']))
        # EXAMPLE:  Word(undefined 'nevermore')

    def test_lex_square_idn_nonexistent(self):
        # TODO:  Why is this not a ValueError?
        not_an_idn = qiki.Number(-999)
        self.assertFalse(            self.lex[not_an_idn].exists())
        self.assertEqual(not_an_idn, self.lex[not_an_idn].idn)
        self.assertEqual(None,       self.lex[not_an_idn].sbj)
        self.assertEqual(None,       self.lex[not_an_idn].vrb)
        self.assertEqual(None,       self.lex[not_an_idn].obj)
        self.assertEqual(None,       self.lex[not_an_idn].num)
        self.assertEqual(None,       self.lex[not_an_idn].txt)
        self.assertEqual(None,       self.lex[not_an_idn].whn)

        six.assertRegex(self, str(self.lex[not_an_idn]), r'unidentified')

        six.assertRegex(self, repr(self.lex[not_an_idn]), r'unidentified')
        self.assertIn(not_an_idn.qstring(), repr(self.lex[not_an_idn]))

        # print("Nonexistent idn str:", str(self.lex[not_an_idn]))
        # EXAMPLE:  Word(unidentified Number('0q7C_FC19'))

        # print("Nonexistent idn repr:", repr(self.lex[not_an_idn]))
        # EXAMPLE:  Word(unidentified Number('0q7C_FC19'))


class Aardvark002InternalWordTests(WordTests):
    """Test the WordTests class itself."""

    def test_assertNoNewWord(self):
        with self.assertNoNewWord():
            pass

    def test_assertNoNewWord_failure(self):
        with self.assertRaises(self._CheckNewWordCount.WrongCount):
            with self.assertNoNewWord():
                self._make_one_new_word('shrubbery')
        with self.assertRaises(self._CheckNewWordCount.WrongCount):
            with self.assertNoNewWord():
                self._make_one_new_word('bushes')
                self._make_one_new_word('swallow')

    def test_assertNewWord(self):
        with self.assertNewWord():
            self._make_one_new_word('shrubbery')

    def test_assertNewWord_failure(self):
        with self.assertRaises(self._CheckNewWordCount.WrongCount):
            with self.assertNewWord():
                pass
        with self.assertRaises(self._CheckNewWordCount.WrongCount):
            with self.assertNewWord():
                self._make_one_new_word('shrubbery')
                self._make_one_new_word('swallow')
        with self.assertRaises(self._CheckNewWordCount.WrongCount):
            with self.assertNewWords(1):
                self._make_one_new_word('barn')
                self._make_one_new_word('tail')

    def test_assertNewWords_2(self):
        with self.assertNewWords(2):
            self._make_one_new_word('swallow')
            self._make_one_new_word('gopher')

    def test_assertNewWords_2_failure(self):
        with self.assertRaises(self._CheckNewWordCount.WrongCount):
            with self.assertNewWords(2):   # Fails if too few.
                pass
        with self.assertRaises(self._CheckNewWordCount.WrongCount):
            with self.assertNewWords(2):   # Fails if too few.
                self._make_one_new_word('knight')
        with self.assertRaises(self._CheckNewWordCount.WrongCount):
            with self.assertNewWords(2):   # Fails if too many.
                self._make_one_new_word('nit')
                self._make_one_new_word('rabbit')
                self._make_one_new_word('scratch')

    def _make_one_new_word(self, txt):
        self.lex.define(self.lex['noun'], txt)

    def test_missing_from_lex_number(self):
        bogus_word = self.lex[qiki.Number(-42)]
        self.assertFalse(bogus_word.exists())

    def test_missing_from_lex_name(self):
        bogus_word = self.lex['bogus nonexistent name']
        self.assertFalse(bogus_word.exists())
        legit_word = self.lex[qiki.LexSentence.IDN_DEFINE]   # Lex[idn] is good
        self.assertTrue(legit_word.exists())
        bogus_word = self.lex[qiki.LexSentence.IDN_DEFINE.qstring()]   # Lex[idn.qstring()] is bad
        self.assertFalse(bogus_word.exists())

    def test_assert_triple_equal(self):
        self.assertTripleEqual(b'string', b'string')
        self.assertTripleEqual( 'string',  'string')
        with self.fails(): self.assertTripleEqual(b'string',  'string')
        with self.fails(): self.assertTripleEqual( 'string', b'string')

        with self.fails(): self.assertTripleEqual(six.binary_type(b'string'), 'string')
        with self.fails(): self.assertTripleEqual(          bytes(b'string'), 'string')
        with self.fails(): self.assertTripleEqual(      bytearray(b'string'), 'string')

        with self.fails(): self.assertTripleEqual(      bytearray(b'string'), b'string')

        self.assertTripleEqual(six.binary_type(b'string'), b'string')
        self.assertTripleEqual(          bytes(b'string'), b'string')

        with self.fails(): self.assertTripleEqual('ignore this', 'false alarm')
        # NOTE:  Cosmetic workaround of a quirk in testing.
        #        The last failing .assertTripleEqual() leaves its error message in the output,
        #        despite that it was expected to fail.  (That's why it's in the .fails() clause.)
        #        Only happens if there are any failing tests ANYWHERE in the module.
        #        So this is one last test so the message reminds test runners to ignore the message.

    def test_assert_exactly_false(self):
        self.assertExactlyFalse(False)
        with self.fails(): self.assertExactlyFalse(True)
        with self.fails(): self.assertExactlyFalse(None)
        with self.fails(): self.assertExactlyFalse(0)
        with self.fails(): self.assertExactlyFalse(())
        with self.fails(): self.assertExactlyFalse([])
        with self.fails(): self.assertExactlyFalse({})
        with self.fails(): self.assertExactlyFalse('')

    def test_the_fails_method(self):
        self.assertEqual(4, 2+2)

        with self.fails():
            self.assertEqual(5, 2+2)

        with self.fails():
            with self.fails():
                self.assertEqual(4, 2+2)

        with self.fails():
            with self.fails():
                with self.fails():
                    self.assertEqual(5, 2+2)


class Word0011FirstTests(WordTests):

    def test_00_number(self):
        n = qiki.Number(1)
        # NOTE:  Can't class Number(..., typing.SupportsInt).
        # Because then can't isinstance(..., Number).
        # So suppress the following error the hard way:
        #     Unexpected type(s): (Number) Possible types: (SupportsInt) (Union[str, unicode, bytearray])
        # noinspection PyTypeChecker
        self.assertEqual(1, int(n))

    def test_01a_lex(self):
        with self.assertRaises(AttributeError):
            # noinspection PyUnresolvedReferences
            _ = self.lex.idn
        with self.assertRaises(AttributeError):
            # noinspection PyUnresolvedReferences
            _ = self.lex.sbj
        with self.assertRaises(AttributeError):
            # noinspection PyUnresolvedReferences
            _ = self.lex.vrb
        with self.assertRaises(AttributeError):
            # noinspection PyUnresolvedReferences
            _ = self.lex.obj

        # noinspection PyUnresolvedReferences
        self.assertEqual(self.lex.IDN_LEX,    self.lex._lex.idn)
        self.assertNotEqual(self.lex,         self.lex._lex.sbj)
        self.assertEqual(self.lex._lex,       self.lex._lex.sbj)
        self.assertEqual(self.lex.IDN_DEFINE, self.lex._lex.vrb.idn)
        self.assertEqual(self.lex.IDN_AGENT,  self.lex._lex.obj.idn)
        self.assertEqual(qiki.Number(1),      self.lex._lex.num)
        self.assertEqual('lex',               self.lex._lex.txt)
        self.assertSensibleWhen(              self.lex._lex.whn)
        self.assertTrue(self.lex._lex.is_lex())

    def test_01b_lex_by_definition(self):
        self.assertEqual(self.lex._lex,       self.lex['lex'])
        self.assertIsNot(self.lex._lex,       self.lex['lex'])
        self.assertEqual(self.lex.IDN_LEX,    self.lex['lex'].idn)
        self.assertEqual(self.lex.IDN_DEFINE, self.lex['define'].idn)
        self.assertEqual(self.lex.IDN_NOUN,   self.lex['noun'].idn)
        self.assertEqual(self.lex.IDN_VERB,   self.lex['verb'].idn)
        self.assertEqual(self.lex.IDN_AGENT,  self.lex['agent'].idn)

    def test_01c_lex_getter(self):
        define = self.lex['define']
        self.assertTrue(define.exists())
        self.assertEqual(define.idn,     qiki.LexSentence.IDN_DEFINE)
        self.assertEqual(define.sbj.idn, qiki.LexSentence.IDN_LEX)
        self.assertEqual(define.vrb.idn, qiki.LexSentence.IDN_DEFINE)
        self.assertEqual(define.obj.idn, qiki.LexSentence.IDN_VERB)
        self.assertEqual(define.num,     qiki.Number(1))
        self.assertEqual(define.txt,     'define')

    def test_01d_lex_bum_getter(self):
        nonword = self.lex['word that does not exist']
        self.assertFalse(nonword.exists())
        self.assertTrue(nonword.idn.is_nan())
        self.assertIsNone(nonword.sbj)
        self.assertIsNone(nonword.vrb)
        self.assertIsNone(nonword.obj)
        self.assertIsNone(nonword.num)
        self.assertIsNone(nonword.whn)
        self.assertEqual(nonword.txt, 'word that does not exist')

    def test_01e_class_names(self):
        self.assertEqual(self.lex_class().__name__, type_name(self.lex))
        self.assertEqual('WordClassJustForThisLex', type_name(self.lex._lex))


    def test_01f_word_classes_distinct(self):
        """Even though named the same, default word classes for different lexes are distinct."""
        # TODO:  Move to a TestClass that doesn't setup self.lex
        #        i.e. not derived from WordTests
        #        because this test runs on LexInMemory only.
        #        or would it be too hard to try it on a LexMySQL too?
        lex1 = qiki.LexInMemory()
        lex2 = qiki.LexInMemory()
        self.assertEqual(lex1.word_class.__name__, lex2.word_class.__name__)
        self.assertNotEqual(lex1.word_class, lex2.word_class)

    def test_02_noun(self):
        noun = self.lex['noun']
        self.assertTrue(noun.exists())
        self.assertTrue(noun.is_noun())
        self.assertEqual('noun', noun.txt)

    def test_02a_str(self):
        if six.PY2:
            self.assertTripleEqual(b'noun', str(self.lex['noun']))
        else:
            self.assertTripleEqual( 'noun', str(self.lex['noun']))

    def test_02b_unicode(self):
        self.assertTripleEqual('noun', six.text_type(self.lex['noun']))

    def test_02c_repr(self):
        self.assertEqual("Word('noun')", repr(self.lex['noun']))

    # noinspection PyStringFormat
    def test_02d_format(self):
        word = self.lex.noun('frog')

        self.assertEqual(      "frog", str(word))
        self.assertEqual("Word('frog')", repr(word))
        self.assertEqual("Word('frog')", "{}".format(word))
        self.assertEqual("Word('frog')", "{:}".format(word))
        self.assertEqual("Word(idn=5)", "{:i}".format(word))
        self.assertEqual("Word(txt='frog')", "{:t}".format(word))
        self.assertEqual("Word(sbj=lex,vrb=define,obj=noun)", "{:svo}".format(word))
        # noinspection SpellCheckingInspection
        self.assertEqual("Word(idn=5,sbj=lex,vrb=define,obj=noun,num=1,txt='frog')", "{:isvont}".format(word))
        six.assertRegex(self, "{:w}".format(word), r"^Word\(whn=\d\d\d\d.\d\d\d\d.\d\d\d\d.\d\d\)$")

    def test_02e_to_dict(self):
        """Word.to_dict() converts a word to a 7-tuple dictionary."""
        cod = self.lex.noun('cod')
        cod_word_dictionary = dict(
            idn=cod.idn,   # EXAMPLE:  5
            sbj=self.lex.IDN_LEX,
            vrb=self.lex.IDN_DEFINE,
            obj=self.lex.IDN_NOUN,
            whn=cod.whn,   # EXAMPLE:  1615592035.738819
            txt='cod',
        )
        self.assertDictEqual(cod_word_dictionary, cod.to_dict())

        # EXAMPLE:   (This won't work because the whn changes.)
        #     self.assertEqual(
        #         '{"idn": 5, "sbj": 0, "vrb": 1, "obj": 2, "whn": 1615592908.500739, "txt": "cod"}',
        #         json.dumps(cod.to_dict())
        #     )

    def test_02f_to_json(self):
        """Word.to_json() is like .to_dict() but for customized json.dumps() conversion."""
        cod = self.lex.noun('cod')
        cod_word_dictionary_for_json = dict(
            idn=cod.idn,   # EXAMPLE:  5
            sbj=self.lex.IDN_LEX,
            vrb=self.lex.IDN_DEFINE,
            obj=self.lex.IDN_NOUN,
            txt='cod',
            # NOTE:  whn is missing
        )
        self.assertDictEqual(cod_word_dictionary_for_json, cod.to_json())

        class BetterJson(json.JSONEncoder):
            def default(self, x):
                try:
                    return x.to_json()
                except AttributeError:
                    return super(BetterJson, self).default(x)

        self.assertEqual(
            json.dumps(cod_word_dictionary_for_json, cls=BetterJson, sort_keys=True),
            json.dumps(cod,                          cls=BetterJson, sort_keys=True)
        )
        self.assertEqual(
            '{"idn": 5, "obj": 2, "sbj": 0, "txt": "cod", "vrb": 1}',
            json.dumps(cod, cls=BetterJson, sort_keys=True)
        )

        # NOTE:  This statement:
        #            json.dumps(cod)
        #        raises this exception:
        #            TypeError: Object of type WordClassJustForThisLex is not JSON serializable
        #        This statement:
        #            json.dumps(cod_word_dictionary_for_json)
        #        raises this exception:
        #            TypeError: Object of type Number is not JSON serializable
        #        The BetterJson class solves both of these problems because
        #        qiki.Number and qiki.Word classes have .to_json() methods.

    def test_03a_max_idn_fixed(self):
        self.assertEqual(qiki.LexSentence.IDN_MAX_FIXED, self.lex.max_idn())

    def test_03b_max_idn(self):
        self.assertEqual(qiki.LexSentence.IDN_MAX_FIXED, self.lex.max_idn())
        self.lex.verb('splurge')
        self.assertEqual(qiki.LexSentence.IDN_MAX_FIXED + 1, self.lex.max_idn())

    def test_03c_noun_word_can_be_an_obj(self):
        noun = self.lex['noun']
        thing = self.lex.define(noun, 'thing')
        self.assertTrue(thing.exists())
        self.assertEqual('thing', thing.txt)

    def test_03d_noun_string_can_be_an_obj(self):
        thing = self.lex.define('noun', 'thing')
        self.assertTrue(thing.exists())
        self.assertEqual('thing', thing.txt)

    def test_03e_string_obj_bracket_syntax(self):
        self.lex['lex']('define')['noun'] = 'thing',42
        thing = self.lex['thing']
        self.assertTrue(thing.exists())
        self.assertEqual(self.lex.IDN_LEX,    thing.sbj.idn)
        self.assertEqual(self.lex.IDN_DEFINE, thing.vrb.idn)
        self.assertEqual(self.lex.IDN_NOUN,   thing.obj.idn)
        self.assertEqual('thing', thing.txt)
        self.assertEqual(42, thing.num)

    def test_03f_lex_define(self):
        thing = self.lex.define('noun', 'thing')
        self.assertTrue(thing.exists())
        self.assertEqual('thing', thing.txt)

    def test_04_is_a(self):
        verb = self.lex['verb']
        noun = self.lex['noun']
        thing = self.lex.define(noun, 'thing')
        cosa = self.lex.define(thing, 'cosa')

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
        noun = self.lex['noun']
        self.assertTrue(noun.is_a_noun(recursion=0))
        self.assertTrue(noun.is_a_noun(recursion=1))
        self.assertTrue(noun.is_a_noun(recursion=2))
        self.assertTrue(noun.is_a_noun(recursion=3))

        child1 = self.lex.define(noun, 'child1')
        self.assertFalse(child1.is_a_noun(recursion=0))
        self.assertTrue(child1.is_a_noun(recursion=1))
        self.assertTrue(child1.is_a_noun(recursion=2))
        self.assertTrue(child1.is_a_noun(recursion=3))

        child2 = self.lex.define(child1, 'child2')
        self.assertFalse(child2.is_a_noun(recursion=0))
        self.assertFalse(child2.is_a_noun(recursion=1))
        self.assertTrue(child2.is_a_noun(recursion=2))
        self.assertTrue(child2.is_a_noun(recursion=3))

        # child12 = child2('child3')('child4')('child5')('child6')('child7')('child8')('child9')('child10')('child11')('child12')
        # self.assertFalse(child12.is_a_noun(recursion=10))
        # self.assertFalse(child12.is_a_noun(recursion=11))
        # self.assertTrue(child12.is_a_noun(recursion=12))
        # self.assertTrue(child12.is_a_noun(recursion=13))

    def test_04_is_a_noun(self):
        self.assertTrue(self.lex._lex.is_a_noun())
        self.assertTrue(self.lex['lex'].is_a_noun())
        self.assertTrue(self.lex['agent'].is_a_noun())
        self.assertTrue(self.lex['noun'].is_a_noun(reflexive=True))
        self.assertTrue(self.lex['noun'].is_a_noun(reflexive=False))   # noun is explicitly defined as a noun
        self.assertTrue(self.lex['noun'].is_a_noun())
        self.assertTrue(self.lex['verb'].is_a_noun())
        self.assertTrue(self.lex['define'].is_a_noun())

    def test_05_noun_grandchild(self):
        agent = self.lex['agent']
        human = self.lex.define(agent, 'human')
        self.assertEqual('human', human.txt)

    def test_06_noun_great_grandchild(self):
        noun = self.lex['noun']
        self.assertTrue(noun.is_noun())

        child = self.lex.define(noun, 'child')
        self.assertFalse(child.is_noun())
        self.assertTrue(child.obj.is_noun())

        grandchild = self.lex.define(child, 'grandchild')
        self.assertFalse(grandchild.is_noun())
        self.assertFalse(grandchild.obj.is_noun())
        self.assertTrue(grandchild.obj.obj.is_noun())

        greatgrandchild = self.lex.define(grandchild, 'greatgrandchild')
        self.assertFalse(greatgrandchild.is_noun())
        self.assertFalse(greatgrandchild.obj.is_noun())
        self.assertFalse(greatgrandchild.obj.obj.is_noun())
        self.assertTrue(greatgrandchild.obj.obj.obj.is_noun())
        self.assertEqual('greatgrandchild', greatgrandchild.txt)

    def test_07_is_a_noun_great_great_grandchild(self):
        noun = self.lex['noun']
        child = self.lex.define(noun, 'child')
        grandchild = self.lex.define(child, 'grandchild')
        greatgrandchild = self.lex.define(grandchild, 'greatgrandchild')
        greatgreatgrandchild = self.lex.define(greatgrandchild, 'greatgreatgrandchild')
        self.assertTrue(noun.is_a_noun())
        self.assertTrue(child.is_a_noun())
        self.assertTrue(grandchild.is_a_noun())
        self.assertTrue(greatgrandchild.is_a_noun())
        self.assertTrue(greatgreatgrandchild.is_a_noun())

    def test_08a_noun_twice(self):
        noun = self.lex['noun']
        with self.assertNewWord():
            thing1 = self.lex.define(noun, 'thing')
        with self.assertNoNewWord():
            thing2 = self.lex.define(noun, 'thing')
        self.assertEqual(thing1.idn, thing2.idn)

    def test_08b_defines_with_different_objs(self):
        """Changing a definition from noun to verb still gets the old definition"""
        noun = self.lex['noun']
        verb = self.lex['verb']

        with self.assertNewWord():
            fling1 = self.lex.define(noun, 'fling')
        with self.assertNoNewWord():
            fling2 = self.lex.define(verb, 'fling')
        self.assertEqual(fling1.idn, fling2.idn)

    def test_08c_duplicate_definition_notify(self):
        noun = self.lex['noun']
        define = self.lex['define']

        class LocalContext:
            report_count = 0

        # noinspection PyUnusedLocal
        def report(*args):
            LocalContext.report_count += 1
            # print(*args)
            # EXAMPLE:  fling Duplicate definitions for 'fling': 0q82_05, 0q82_06
        self.lex.duplicate_definition_notify(report)

        with self.assertNewWord():
            fling1 = self.lex.create_word(
                sbj=self.lex[self.lex],
                vrb=define,
                obj=noun,
                txt='fling'
            )
        self.assertEqual(0, LocalContext.report_count)

        with self.assertNewWord():
            fling2 = self.lex.create_word(
                sbj=self.lex[self.lex],
                vrb=define,
                obj=noun,
                txt='fling'
            )
        self.assertEqual(0, LocalContext.report_count)

        with self.assertNoNewWord():
            fling3 = self.lex.define(noun, 'fling')
        self.assertEqual(1, LocalContext.report_count)

        self.assertEqual(1, LocalContext.report_count)
        self.assertNotEqual(fling1.idn, fling2.idn)
        self.assertEqual   (fling1.idn, fling3.idn)

    def test_09a_equality(self):
        # TODO:  WTF do I really want to test *methods* here??  Shouldn't these be words?
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
        noun1 = self.lex['noun']
        noun2 = self.lex['noun']
        self.assertEqual(noun1, noun2)
        self.assertIsNot(noun1, noun2)

    def test_09a_equality_by_copy_constructor(self):
        noun1 = self.lex['noun']
        noun2 = self.lex.word_class(noun1)
        self.assertEqual(noun1, noun2)
        self.assertTrue(noun1 == noun2)
        self.assertFalse(noun1 != noun2)   # Exercises Word.__ne__()!

    def test_09b_copy_constructor_not_clone_constructor(self):
        noun1 = self.lex['noun']
        noun2 = self.lex.word_class(noun1)
        self.assertIsNot(noun1, noun2)   # Must not copy by reference.

    def test_09c_lex_singleton_by_attribute(self):
        lex1 = self.lex
        lex2 = self.lex._lex.lex
        self.assertEqual(lex1, lex2)
        self.assertIs(lex1, lex2)

    def test_09d_lex_not_singleton_by_index(self):
        lex1 = self.lex._lex
        lex2 = self.lex['lex']
        self.assertEqual(lex1, lex2)
        self.assertIsNot(lex1, lex2)

    def test_09e_idn_constructor_does_not_enforce_lex_singleton(self):
        lex_by_idn = self.lex._lex.spawn(self.lex._lex.idn)
        self.assertEqual(lex_by_idn, self.lex._lex)
        self.assertIsNot(lex_by_idn, self.lex._lex)

    def test_09f_word_copy_constructor_does_not_enforce_lex_singleton(self):
        lex_by_word = self.lex._lex.spawn(self.lex._lex)
        self.assertEqual(lex_by_word, self.lex._lex)
        self.assertIsNot(lex_by_word, self.lex._lex)

    def test_09g_word_constructor_bogus_type(self):
        class BogusType:
            def __init__(self):
                pass
        bogus_instance = BogusType()
        with six.assertRaisesRegex(self, TypeError, '^((?!unicode).)*$'):
            # THANKS:  For negative regex, http://stackoverflow.com/a/406408/673991
            self.lex.word_class(bogus_instance)

        class BogusNewType(object):
            def __init__(self):
                pass
        bogus_new_instance = BogusNewType()
        with six.assertRaisesRegex(self, TypeError, '^((?!unicode).)*$'):
            self.lex.word_class(bogus_new_instance)

    def test_09h_word_constructor_by_name_must_be_unicode(self):
        self.assertFalse(self.lex.word_class(               'this is unicode').exists())
        with self.assertRaises(TypeError):
            self.assertFalse(self.lex.word_class(          b'this is not unicode').exists())
        with self.assertRaises(TypeError):
            self.assertFalse(self.lex.word_class(bytearray(b'this is not unicode')).exists())
        with self.assertRaises(TypeError):
            self.assertFalse(self.lex.word_class(    bytes(b'this is not unicode')).exists())

    def test_09g_define_must_be_unicode(self):
        agent = self.lex['agent']
        self.assertEqual("ninja", self.lex.define(obj=agent, txt='ninja').txt)

        with self.assertRaises(TypeError):
            self.lex.define(obj=agent, txt=b'ninja')

        with self.assertRaises(qiki.LexSentence.DefinitionMustBeUnicode):
            self.lex.define(obj=agent, txt=b'ninja')

    def test_09h_noun_must_be_unicode(self):
        self.assertEqual("name", self.lex.noun('name').txt)

        with self.assertRaises(TypeError):
            self.lex.noun(b'name')

        with self.assertRaises(qiki.LexSentence.DefinitionMustBeUnicode):
            self.lex.noun(b'name')

        self.assertTrue(issubclass(qiki.LexSentence.DefinitionMustBeUnicode, TypeError))

    def test_09i_verb_must_be_unicode(self):
        self.assertEqual("name", self.lex.verb('name').txt)

        with self.assertRaises(TypeError):
            self.lex.verb(b'name')

        with self.assertRaises(qiki.LexSentence.DefinitionMustBeUnicode):
            self.lex.verb(b'name')

    # TODO:  Prevent cloning lex?
    # def test_09x_lex_singleton_cant_do_by_copy_constructor(self):
    #     with self.assertRaises(ValueError):
    #         self.lex.word_class(self.lex)

    def test_10a_word_by_lex_idn(self):
        agent = self.lex[qiki.LexSentence.IDN_AGENT]
        self.assertEqual(agent.txt, 'agent')

    def test_10b_word_by_lex_txt(self):
        agent = self.lex['agent']
        self.assertEqual(agent.idn, qiki.LexSentence.IDN_AGENT)

    def test_11a_noun_inserted(self):
        new_word = self.lex.noun('something')
        self.assertEqual(self.lex.max_idn(),  new_word.idn)
        self.assertEqual(self.lex._lex,       new_word.sbj)
        self.assertEqual(self.lex['define'], new_word.vrb)
        self.assertEqual(self.lex['noun'],   new_word.obj)
        self.assertEqual(qiki.Number(1),      new_word.num)
        self.assertEqual('something',        new_word.txt)
        self.assertSensibleWhen(              new_word.whn)

    def test_11b_whn(self):
        define = self.lex['define']
        new_word = self.lex.noun('something')
        self.assertSensibleWhen(define.whn)
        self.assertSensibleWhen(new_word.whn)
        self.assertGreaterEqual(float(new_word.whn), float(define.whn))

    def test_11c_vrb_by_name(self):
        bart = self.lex.define('agent', 'bart')
        cook = self.lex.verb('cook')
        deer = self.lex.noun('deer')

        deer_bbq = bart(cook, txt="Yummy")[deer]
        self.assertEqual("Yummy", deer_bbq.txt)
        self.assertEqual(cook, deer_bbq.vrb)

        #                  v--- the point of this test -- 'cook' is a string for the vrb
        deer_dry = bart('cook', "A little dry")[deer]
        #                            ^--- assumed to be the txt

        self.assertEqual("A little dry", deer_dry.txt)
        self.assertEqual(cook, deer_dry.vrb)

    def test_11d_idn_by_int(self):
        frog = self.lex.noun('frog')
        self.assertEqual(frog, self.lex[    frog.idn ])
        self.assertEqual(frog, self.lex[int(frog.idn)])

    def test_11d_idn_by_float(self):
        frog = self.lex.noun('frog')
        self.assertEqual(frog, self.lex[      frog.idn ])
        self.assertEqual(frog, self.lex[float(frog.idn)])

    def test_11e_svo_by_int(self):
        bart = self.lex.define('agent', 'bart')
        cook = self.lex.verb('cook')
        deer = self.lex.noun('deer')
        deer_bbq = bart(cook, txt="Yummy")[deer]

        self.assertEqual(deer_bbq, self.lex[    bart     ](cook)[deer])
        self.assertEqual(deer_bbq, self.lex[    bart.idn ](cook)[deer])
        self.assertEqual(deer_bbq, self.lex[int(bart.idn)](cook)[deer])

        self.assertEqual(deer_bbq, self.lex[bart](    cook     )[deer])
        self.assertEqual(deer_bbq, self.lex[bart](    cook.idn )[deer])
        self.assertEqual(deer_bbq, self.lex[bart](int(cook.idn))[deer])

        self.assertEqual(deer_bbq, self.lex[bart](cook)[    deer     ])
        self.assertEqual(deer_bbq, self.lex[bart](cook)[    deer.idn ])
        self.assertEqual(deer_bbq, self.lex[bart](cook)[int(deer.idn)])


    # def test_12a_non_vrb(self):
    #     # anna = self.lex.define('agent', 'anna')
    #     anna = self.lex.define('agent', 'anna')
    #     like = self.lex.verb('like')
    #     self.lex.noun('yurt')
    #     zarf = self.lex.noun('zarf')
    #     anna.says(vrb=like, obj=zarf, num=1)
    #     self.assertTrue(anna.like.is_a_verb())
    #     self.assertFalse(anna.yurt.is_a_verb())
    #     self.assertEqual('yurt', anna.yurt.txt)
    #     with self.assertRaises(TypeError):
    #         anna.yurt(zarf, txt='', num=1)
    #         # FIXME:  Can we even come up with a s.v(o) where v is not a verb,
    #         # and something else isn't happening?  This example is at best a highly
    #         # corrupted form of o(t), aka lex.define(o,t).

    def test_13a_text(self):
        txt = qiki.Text('simple letters')
        self.assertEqual('simple letters', txt)
        self.assertEqual(b'simple letters', txt.utf8())
        self.assertIs(six.binary_type, type(txt.utf8()))

    def test_13b_text_class(self):
        t0 = "some text"
        t1 = qiki.Text(t0)
        t2 = qiki.Text(t1)
        t3 = qiki.Text(t2)
        self.assertTripleEqual( "some text", t1.unicode())
        self.assertTripleEqual(b"some text", t1.utf8())
        self.assertTripleEqual( "some text", t2.unicode())
        self.assertTripleEqual(b"some text", t2.utf8())
        self.assertTripleEqual( "some text", t3.unicode())
        self.assertTripleEqual(b"some text", t3.utf8())

    def test_13c_text_native(self):
        if six.PY2:
            self.assertTripleEqual(b'string', qiki.Text('string').native())
        else:
            self.assertTripleEqual('string', qiki.Text('string').native())

    def test_13c_text_not_unicode_okay(self):
        if six.PY2:  self.assertEqual('string' ,           b'string' )
        else:     self.assertNotEqual('string' ,           b'string' )

    def test_13d_text_decode(self):
        self.assertTripleEqual(qiki.Text('string'), qiki.Text.decode_if_you_must('string'))
        self.assertTripleEqual(qiki.Text('string'), qiki.Text.decode_if_you_must(b'string'))

    # noinspection SpellCheckingInspection
    def test_13e_text_postel(self):
        """Verify the Text class follows Postel's Law -- liberal in, conservative out."""
        def example(the_input, _unicode, _utf8):
            txt = qiki.Text(the_input)
            self.assertTripleEqual(_unicode, txt.unicode())
            self.assertTripleEqual(_utf8, txt.utf8())

        example(bytes(b'ascii').decode('utf-8'), 'ascii', b'ascii')
        example('ascii',                 'ascii', b'ascii')

        example(unicodedata.lookup('latin small letter a with ring above') +
                          'ring', '\U000000E5ring', b'\xC3\xA5ring')
        example(         'åring', '\U000000E5ring', b'\xC3\xA5ring')
        example('\U000000E5ring', '\U000000E5ring', b'\xC3\xA5ring')
        # noinspection PyUnresolvedReferences
        example(                                    b'\xC3\xA5ring'.decode('utf-8'),
                                  '\U000000E5ring', b'\xC3\xA5ring')

        example(unicodedata.lookup('greek small letter mu') +
                          'icro', '\U000003BCicro', b'\xCE\xBCicro')
        example(         'μicro', '\U000003BCicro', b'\xCE\xBCicro')
        example('\U000003BCicro', '\U000003BCicro', b'\xCE\xBCicro')
        # noinspection PyUnresolvedReferences
        example(                                    b'\xCE\xBCicro'.decode('utf-8'),
                                  '\U000003BCicro', b'\xCE\xBCicro')

        example(unicodedata.lookup('tetragram for aggravation') +
                          'noid', '\U0001D351noid', b'\xF0\x9D\x8D\x91noid')
        example('\U0001D351noid', '\U0001D351noid', b'\xF0\x9D\x8D\x91noid')
        # noinspection PyUnresolvedReferences
        example(                                    b'\xF0\x9D\x8D\x91noid'.decode('utf-8'),
                                  '\U0001D351noid', b'\xF0\x9D\x8D\x91noid')

    def test_14a_word_text(self):
        """Verify the txt field follows Postel's Law -- liberal in, conservative out.

        Liberal in:  str, unicode, bytes, bytearray, Text and Python 2 or 3
        Conservative out:  str, which is unicode in Python 3, UTF-8 in Python 2."""
        s = self.lex.noun('s')
        v = self.lex.verb('v')
        o = self.lex.noun('o')

        def works_as_txt(txt):
            # word = o(txt)
            # self.assertIs(qiki.Text, type(word.txt))
            # self.assertTripleEqual(qiki.Text('apple'), word.txt)

            word = self.lex.define(o, txt)
            self.assertIs(qiki.Text, type(word.txt))
            self.assertTripleEqual(qiki.Text('apple'), word.txt)

            word = self.lex.create_word(sbj=s, vrb=v, obj=o, num=1, txt=txt)
            self.assertIs(qiki.Text, type(word.txt))
            self.assertTripleEqual(qiki.Text('apple'), word.txt)

        works_as_txt(bytes(b'apple').decode('utf-8'))
        works_as_txt(bytearray('apple', 'utf-8').decode('utf-8'))
        works_as_txt('apple')
        works_as_txt(qiki.Text(bytes(b'apple').decode('utf-8')))
        works_as_txt(qiki.Text(bytearray('apple', 'utf-8').decode('utf-8')))
        works_as_txt(qiki.Text('apple'))

    def test_15_word_chain(self):
        define = self.lex['define']
        verb = self.lex['verb']
        noun = self.lex['noun']
        self.assertEqual(self.lex._lex, self.lex._lex.sbj)
        self.assertEqual(self.lex._lex, self.lex._lex.sbj.sbj)
        self.assertEqual(self.lex._lex, self.lex._lex.sbj.sbj.sbj)
        self.assertEqual(self.lex._lex, self.lex._lex.sbj.sbj.sbj.sbj)
        self.assertEqual(self.lex._lex, self.lex._lex.sbj.sbj.sbj.sbj.sbj)
        self.assertEqual(define,        self.lex._lex.sbj.sbj.sbj.sbj.sbj.vrb)
        self.assertEqual(self.lex._lex, self.lex._lex.sbj.sbj.sbj.sbj.sbj.vrb.sbj)
        self.assertEqual(define,        self.lex._lex.sbj.sbj.sbj.sbj.sbj.vrb.sbj.vrb)
        self.assertEqual(verb,          self.lex._lex.sbj.sbj.sbj.sbj.sbj.vrb.sbj.vrb.obj)
        self.assertEqual(noun,          self.lex._lex.sbj.sbj.sbj.sbj.sbj.vrb.sbj.vrb.obj.obj)

    def test_16_django_template_not_callable(self):
        w = self.lex._lex.spawn()
        self.assertTrue(w.do_not_call_in_templates)
        self.assertIs(type(w.do_not_call_in_templates), bool)

    def test_17a_inchoate(self):
        """A word constructed by its idn is inchoate."""
        w = self.lex[qiki.LexSentence.IDN_DEFINE]
        self.assertTrue(w._is_inchoate, "How can idn define be choate? " + repr(w))

    def test_17b_choate(self):
        """A word that tries to use one of its parts becomes choate."""
        w = self.lex[qiki.LexSentence.IDN_DEFINE]
        self.assertEqual(self.lex._lex, w.sbj)
        self.assertFalse(w._is_inchoate)

    def test_17c_inchoate_copy_constructor(self):
        """The lex[word] copy constructor:  inchoate <-- inchoate"""
        w1 = self.lex[qiki.LexSentence.IDN_DEFINE]
        w2 = self.lex[w1]
        self.assertTrue(w1._is_inchoate)   # Tests the source didn't BECOME choate by copying.
        self.assertTrue(w2._is_inchoate)   # Tests the destination is also inchoate.

    def test_17d_choate_copy_constructor(self):
        """The lex[word] copy constructor:  inchoate <-- choate"""
        w1 = self.lex[qiki.LexSentence.IDN_DEFINE]
        self.assertTrue(w1._is_inchoate)
        _ = w1.sbj
        self.assertFalse(w1._is_inchoate)

        w2 = self.lex[w1]
        self.assertTrue(w2._is_inchoate)

    def test_17e_inchoate_txt(self):
        agent = self.lex[qiki.LexSentence.IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertEqual("agent", agent.txt)
        self.assertFalse(agent._is_inchoate)

    def test_17e_inchoate_str(self):
        agent = self.lex[qiki.LexSentence.IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertIn("agent", str(agent))
        self.assertFalse(agent._is_inchoate)

    def test_17f_inchoate_hasattr(self):
        agent = self.lex[qiki.LexSentence.IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertTrue(hasattr(agent, 'txt'))
        self.assertFalse(agent._is_inchoate)

    def test_17g_inchoate_idn(self):
        agent = self.lex[qiki.LexSentence.IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertEqual(qiki.LexSentence.IDN_AGENT, agent.idn)
        self.assertTrue(agent._is_inchoate)

    def test_17h_inchoate_hash(self):
        agent = self.lex[qiki.LexSentence.IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertIsInstance(hash(agent), int)
        self.assertTrue(agent._is_inchoate)

    def test_17i_inchoate_hash(self):
        agent1 = self.lex[qiki.LexSentence.IDN_AGENT]
        agent2 = self.lex[qiki.LexSentence.IDN_AGENT]
        self.assertTrue(agent1._is_inchoate)
        self.assertTrue(agent2._is_inchoate)
        self.assertTrue(agent1 == agent2)
        self.assertTrue(agent1._is_inchoate)
        self.assertTrue(agent2._is_inchoate)

    def test_17j_inchoate_copy(self):
        agent = self.lex[qiki.LexSentence.IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertIn("agent", agent.txt)
        self.assertFalse(agent._is_inchoate)

        agent2 = agent.inchoate_copy()
        self.assertTrue(agent2._is_inchoate)

        self.assertFalse(agent._is_inchoate)
        self.assertIsNot(agent, agent2)
        self.assertEqual(qiki.LexSentence.IDN_AGENT, agent.idn)
        self.assertEqual(qiki.LexSentence.IDN_AGENT, agent2.idn)
        self.assertEqual(agent, agent2)

    def test_17k_inchoate_lex(self):
        agent = self.lex[qiki.LexSentence.IDN_AGENT]
        self.assertTrue(agent._is_inchoate)
        self.assertIs(self.lex, agent.lex)
        self.assertTrue(agent._is_inchoate)

    def test_18a_create_word_multiple_words(self):
        lex = self.lex._lex
        define = self.lex['define']
        noun = self.lex['noun']
        with self.assertNewWord():
            punt1 = self.lex.create_word(sbj=lex, vrb=define, obj=noun, txt='punt')
        with self.assertNewWord():
            punt2 = self.lex.create_word(sbj=lex, vrb=define, obj=noun, txt='punt')

        self.assertNotEqual(punt1.idn, punt2.idn)
        self.assertNotEqual(punt1,     punt2)

    def test_18b_create_word_use_already_single_word(self):
        lex = self.lex._lex
        define = self.lex['define']
        noun = self.lex['noun']
        with self.assertNewWord():
            punt1 = self.lex.create_word(sbj=lex, vrb=define, obj=noun, txt='punt', use_already=True)
        with self.assertNoNewWord():
            punt2 = self.lex.create_word(sbj=lex, vrb=define, obj=noun, txt='punt', use_already=True)

        self.assertEqual(punt1.idn, punt2.idn)
        self.assertEqual(punt1,     punt2)

    def test_18c_define_single_word(self):
        noun = self.lex['noun']
        with self.assertNewWord():
            punt1 = self.lex.define(obj=noun, txt='punt')
        with self.assertNoNewWord():
            punt2 = self.lex.define(obj=noun, txt='punt')

        self.assertEqual(punt1.idn, punt2.idn)

    def test_18d_define_prefers_earlier_definition(self):
        lex_word = self.lex._lex
        define = self.lex['define']
        noun = self.lex['noun']
        with self.assertNewWord():
            punt1 = self.lex.create_word(sbj=lex_word, vrb=define, obj=noun, txt='punt')
        with self.assertNewWord():
            punt2 = self.lex.create_word(sbj=lex_word, vrb=define, obj=noun, txt='punt')

        with self.assertNoNewWord():
            punt3 = self.lex.define(noun, 'punt')
        self.assertEqual(   punt3.idn, punt1.idn)
        self.assertNotEqual(punt3.idn, punt2.idn)

    def test_18e_create_word_by_name(self):
        lex = self.lex
        anna = lex.define(lex['agent'], 'anna')
        bale = lex.verb('bale')
        carp = lex.noun('carp')

        abc = lex.create_word(sbj='anna', vrb='bale', obj='carp', num=123)
        self.assertEqual(anna, abc.sbj)
        self.assertEqual(bale, abc.vrb)
        self.assertEqual(carp, abc.obj)
        self.assertEqual(123,  abc.num)

    def test_18g_define_by_name(self):
        lex = self.lex
        anna = lex.define(lex['agent'], 'anna')
        carp = lex.noun('carp')

        # adc = lex.define('carp', 'Garp', sbj='anna')
        adc = lex.create_word(sbj='anna', vrb='define', obj='carp', txt='Garp')

        self.assertEqual(anna,          adc.sbj)
        self.assertEqual(lex['define'], adc.vrb)
        self.assertEqual(carp,          adc.obj)
        self.assertEqual('Garp',        adc.txt)

    def test_18h_define_lex_only(self):
        """Only sbj=lex defines matter"""
        anna = self.lex.define('agent', 'anna')
        define = self.lex['define']
        noun = self.lex['noun']
        with self.assertNewWord():
            punt1 = self.lex.create_word(sbj=anna, vrb=define, obj=noun, txt='punt')
        with self.assertNewWord():
            punt2 = self.lex.define(noun, 'punt')
        self.assertNotEqual(punt2.idn, punt1.idn)

    def test_18i_define_lex_only(self):
        """define() will never find sbj=non-lex definitions"""
        lex_word = self.lex._lex
        anna = self.lex.define('agent', 'anna')
        define = self.lex['define']
        noun = self.lex['noun']
        with self.assertNewWord():
            punt1 = self.lex.create_word(sbj=anna,     vrb=define, obj=noun, txt='punt')
        with self.assertNewWord():
            punt2 = self.lex.create_word(sbj=lex_word, vrb=define, obj=noun, txt='punt')
        with self.assertNewWord():
            punt3 = self.lex.create_word(sbj=anna,     vrb=define, obj=noun, txt='punt')

        with self.assertNoNewWord():
            punt4 = self.lex.define(noun, 'punt')
        self.assertNotEqual(punt4.idn, punt1.idn)
        self.assertEqual(   punt4.idn, punt2.idn)
        self.assertNotEqual(punt4.idn, punt3.idn)

    def test_19a_time_lex_now(self):
        now_word = qiki.word.TimeLex().now_word()
        # print("TimeLex", now_word.num.qstring(), float(now_word.num), now_word.txt)
        # EXAMPLE:  TimeLex 0q85_5CEFC9AE6BC6A8 1559218606.42 2019.0530.1216.46

        self.assertGreater(now_word.idn, qiki.Number(1560516598))
        # NOTE:  There was a bug where idn would be NAN until referencing txt or num
        #        because the word was "inchoate" until then.

        six.assertRegex(self, str(now_word.txt), r'^\d\d\d\d.\d\d\d\d.\d\d\d\d.\d\d$')   # Y10K bug
        self.assertGreater(now_word.txt, qiki.Text('2019.0530.1216.46'))
        # noinspection SpellCheckingInspection
        self.assertGreater(now_word.num, qiki.Number('0q85_5CEFC9AE6BC6A8'))
        self.assertGreater(now_word.num, qiki.Number(1559218606.421))
        # 7:16am Thursday 30-May-2019, US Central Daylight Time

        self.assertEqual(now_word.num, now_word.idn)
        self.assertEqual(now_word.num, now_word.whn)

    def test_19a_time_lex_fixed(self):
        y2k_unix_epoch = calendar.timegm(time.struct_time((1999,12,31, 23,59,59, 0,0,0)))
        # THANKS:  UTC from 9-tuple, https://stackoverflow.com/a/2956997/673991

        self.assertEqual(946684799, y2k_unix_epoch)
        # THANKS:  Unix epoch from Gregorian date-time, https://www.epochconverter.com/

        self.assertEqual((30*365 + 7)*24*60*60 - 1, y2k_unix_epoch)
        # NOTE:  30 years and 7 leaps between 1/1/1970 and 12/31/1999.

        y2k_word = qiki.word.TimeLex()[qiki.Number(y2k_unix_epoch)]
        self.assertEqual(y2k_unix_epoch, float(y2k_word.num))
        self.assertEqual(y2k_unix_epoch, float(y2k_word.whn))
        self.assertEqual('1999.1231.2359.59', str(y2k_word))

    def test_19a_time_lex_delta(self):
        time_lex = qiki.TimeLex()
        y2k_before = time_lex[946684799]
        y2k_after  = time_lex[946684800]

        delta = time_lex[y2k_before]('differ')[y2k_after]
        self.assertEqual(qiki.Number(1), delta.num)

        self.assertEqual(qiki.Number(1), time_lex[946684799]('differ')[946684800].num)


    # TODO:  Words as dictionary keys preserve their inchoate-ness.

    # TODO:  .define(... sbj=)
    # TODO:  .verb(... sbj=)
    # TODO:  .create_word(... vrb='define')


class Word0012Utilities(WordTests):

    def test_idn_ify(self):
        agent = self.lex['agent']
        self.assertEqual(qiki.LexSentence.IDN_AGENT, self.lex.idn_ify(agent.idn))
        self.assertEqual(qiki.LexSentence.IDN_AGENT, self.lex.idn_ify(agent))
        self.assertEqual(qiki.LexSentence.IDN_AGENT, self.lex.idn_ify(qiki.LexSentence.IDN_AGENT))
        self.assertEqual(qiki.Number(42),            self.lex.idn_ify(42))
        self.assertEqual(qiki.LexSentence.IDN_NOUN,  self.lex.idn_ify('noun'))
        self.assertEqual(qiki.LexSentence.IDN_VERB,  self.lex.idn_ify('verb'))
        with self.assertRaises(ValueError):
            self.lex.idn_ify('nonexistent')
        with self.assertRaises(TypeError):
            self.lex.idn_ify(b'noun')
        with self.assertRaises(TypeError):
            self.lex.idn_ify(None)

    def test_inequality_words_and_numbers(self):
        """Sanity check to make sure words and idns aren't intrinsically equal or something."""
        word = self.lex['agent']
        idn = word.idn
        self.assertEqual(idn, idn)
        self.assertNotEqual(idn, word)
        self.assertNotEqual(word, idn)
        self.assertEqual(word, word)

    # def test_words_from_idns(self):
    #     noun = self.lex['noun']
    #     agent = self.lex['agent']
    #     define = self.lex['define']
    #     self.assertEqual([
    #         noun,
    #         agent,
    #         define
    #     ], self.lex.words_from_idns([
    #         noun.idn,
    #         agent.idn,
    #         define.idn
    #     ]))

    # def test_raw_values_from_idns(self):
    #     noun = self.lex['noun']
    #     agent = self.lex['agent']
    #     define = self.lex['define']
    #     self.assertEqual([
    #         noun.idn.raw,
    #         agent.idn.raw,
    #         define.idn.raw,
    #     ], self.lex.raws_from_idns([
    #         noun.idn,
    #         agent.idn,
    #         define.idn,
    #     ]))

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


class Word0013Brackets(WordTests):

    def setUp(self):
        super(Word0013Brackets, self).setUp()
        self.art = self.lex.define('agent', 'art')
        self.got = self.lex.verb('got')
        self.lek = self.lex.noun('lek')

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
            self.art(self.got)[self.lek] = "turnpike"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual("turnpike", word.txt)

    def test_02c_subject_circle_square_txt_num(self):
        with self.assertNewWord():
            self.art(self.got)[self.lek] = ("turnpike", 496)
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual("turnpike", word.txt)
        self.assertEqual(496, word.num)

    def test_02d_subject_circle_square_num_txt(self):
        with self.assertNewWord():
            self.art(self.got)[self.lek] = 496, "turnpike"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual("turnpike", word.txt)
        self.assertEqual(496, word.num)

    def test_02e_subject_circle_square_num_txt_list(self):
        with self.assertNewWord():
            self.art(self.got)[self.lek] = [496, "turnpike"]
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual("turnpike", word.txt)
        self.assertEqual(496, word.num)

    def test_03a_subject_circle_bad(self):
        with self.assertRaises(TypeError):
            self.art(self.got)[self.lek] = some_type

    def test_03b_subject_circle_bad(self):
        with self.assertRaises(TypeError):
            self.art(self.got)[self.lek] = [some_type]

    def test_04a_lex_square_circle_square_num(self):
        with self.assertNewWord():
            self.lex[self.art](self.got)[self.lek] = 236
            word = self.lex[self.art](self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(236, word.num)
        self.assertEqual("", word.txt)

    def test_04b_lex_square_circle_square_num_txt(self):
        with self.assertNewWord():
            self.lex[self.art](self.got)[self.lek] = 236, "route"
            word = self.lex[self.art](self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(236, word.num)
        self.assertEqual("route", word.txt)

    def test_04c_lex_square_circle_square_txt_num(self):
        with self.assertNewWord():
            self.lex[self.art](self.got)[self.lek] = "route", 236
            word = self.lex[self.art](self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(236, word.num)
        self.assertEqual("route", word.txt)

    def test_04d_lex_square_circle_square_txt_txt(self):
        with self.assertRaises(TypeError):
            self.lex[self.art](self.got)[self.lek] = "one string", "another string"
        with self.assertRaises(TypeError):
            self.lex[self.art](self.got)[self.lek] = "one string", "another string", "third"

    def test_04e_lex_square_circle_square_num_num(self):
        with self.assertRaises(TypeError):
            self.lex[self.art](self.got)[self.lek] = 42, 24
        with self.assertRaises(TypeError):
            self.lex[self.art](self.got)[self.lek] = 11, 22, 33

    def test_04f_lex_square_circle_square_num_num_txt_txt(self):
        with self.assertRaises(TypeError):
            self.lex[self.art](self.got)[self.lek] = 11, 22, "one"
        with self.assertRaises(TypeError):
            self.lex[self.art](self.got)[self.lek] = 11, "one", 22
        with self.assertRaises(TypeError):
            self.lex[self.art](self.got)[self.lek] = "one", 11, 22
        with self.assertRaises(TypeError):
            self.lex[self.art](self.got)[self.lek] = 11, "one", "two"
        with self.assertRaises(TypeError):
            self.lex[self.art](self.got)[self.lek] = "one", 11, "two"
        with self.assertRaises(TypeError):
            self.lex[self.art](self.got)[self.lek] = "one", "two", 11

    # TODO:  What about lex[s](v)[o] = (n,t)   (In other words, explicit tuple)
    # TODO:  What about lex[s](v)[o] = (n,)
    # TODO:  What about lex[s](v)[o] = ()

    def test_05a_lex_circle_square_num(self):
        with self.assertNewWord():
            self.lex._lex(self.got)[self.lek] = 1
            word = self.lex._lex(self.got)[self.lek]
        self.assertEqual(self.lex._lex, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(1, word.num)

    def test_05b_lex_circle_square_num_txt(self):
        with self.assertNewWord():
            self.lex._lex(self.got)[self.lek] = 99, "brief as can be"
            word = self.lex._lex(self.got)[self.lek]
        self.assertEqual(self.lex._lex, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(99, word.num)
        self.assertEqual("brief as can be", word.txt)

    def test_06a_subject_circle_text_square(self):
        with self.assertNewWord():
            self.art('got')[self.lek] = 2, "two"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(2, word.num)
        self.assertEqual("two", word.txt)

    def test_06b_subject_circle_square_text(self):
        with self.assertNewWord():
            self.art(self.got)['lek'] = 2, "two"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(2, word.num)
        self.assertEqual("two", word.txt)

    def test_06c_lex_square_text_circle_square(self):
        with self.assertNewWord():
            self.lex['art'](self.got)[self.lek] = 2, "two"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(2, word.num)
        self.assertEqual("two", word.txt)

    def test_06d_lex_square_circle_square_by_name(self):
        with self.assertNewWord():
            self.lex['art']('got')['lek'] = 2, "two"
            word = self.art(self.got)[self.lek]
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(2, word.num)
        self.assertEqual("two", word.txt)

    def test_06e_lex_square_circle_square_bad_binary(self):
        with self.assertNewWord():
            self.lex['art']('got')['lek'] = "foo bar"
        self.assertEqual("foo bar", self.lex['art']('got')['lek'].txt)

        with six.assertRaisesRegex(self, TypeError, re.compile(r'unicode', re.IGNORECASE)):
            _ = self.lex[b'art']('got')['lek']
        with six.assertRaisesRegex(self, TypeError, re.compile(r'verb.*unicode', re.IGNORECASE)):
            _ = self.lex['art'](b'got')['lek']
        with six.assertRaisesRegex(self, TypeError, re.compile(r'object.*unicode', re.IGNORECASE)):
            _ = self.lex['art']('got')[b'lek']

    def test_06f_lex_square_circle_square_bad_binary_txt(self):
        with self.assertNewWord():
            _ = self.lex['art']('got', txt='flea bar', use_already=True)['lek']
        with self.assertNoNewWord():
            _ = self.lex['art']('got', txt='flea bar', use_already=True)['lek']
        with six.assertRaisesRegex(self, TypeError, re.compile(r'unicode', re.IGNORECASE)):
            _ = self.lex['art']('got', txt=b'flea bar', use_already=True)['lek']

    def test_06g_lex_square_circle_square_assign_bad_binary_txt(self):
        with self.assertNewWord():
            self.lex['art']('got', use_already=True)['lek'] = 'flea bar'
        with six.assertRaisesRegex(self, TypeError, re.compile(r'unicode', re.IGNORECASE)):
            self.lex['art']('got', use_already=True)['lek'] = b'flea bar'

    def test_07a_subject_circle_use_already_square(self):
        with self.assertNewWord():
            self.art(self.got)[self.lek] = 2, "two"
        with self.assertNewWord():
            self.art(self.got)[self.lek] = 2, "two"
        with self.assertNoNewWord():
            self.art(self.got, use_already=True)[self.lek] = 2, "two"

    # def test_08_lex_square_lex(self):   NOPE
    #     """Lex is a singleton when indexing itself."""
    #     self.assertIs(self.lex[self.lex], self.lex)

    def test_08_lex_itself(self):
        """Ways to get the word in a lex that refers to the lex itself."""
        lex = self.lex
        word_for_lex_1 = lex['lex']
        word_for_lex_2 = lex[qiki.LexSentence.IDN_LEX]
        word_for_lex_3 = lex[lex]   # <-- new and improved!

        self.assertEqual(word_for_lex_1, word_for_lex_2)
        self.assertEqual(word_for_lex_1, word_for_lex_3)
        self.assertEqual(word_for_lex_2, word_for_lex_3)   # Equal ...

        self.assertIsNot(word_for_lex_1, word_for_lex_2)   # ... but distinct
        self.assertIsNot(word_for_lex_1, word_for_lex_3)
        self.assertIsNot(word_for_lex_2, word_for_lex_3)

        self.assertNotEqual(word_for_lex_1, lex)
        self.assertNotEqual(word_for_lex_2, lex)
        self.assertNotEqual(word_for_lex_3, lex)


class Word0014CreateWord(WordTests):

    def setUp(self):
        super(Word0014CreateWord, self).setUp()
        self.art = self.lex.define('agent', 'art')
        self.got = self.lex.verb('got')
        self.lek = self.lex.noun('lek')

    def test_01(self):
        with self.assertNewWord():
            word = self.lex.create_word(self.art, self.got, self.lek, 236, "tao")
        self.assertEqual(self.art, word.sbj)
        self.assertEqual(self.got, word.vrb)
        self.assertEqual(self.lek, word.obj)
        self.assertEqual(236, word.num)
        self.assertEqual("tao", word.txt)

    def test_02_num_add(self):
        with self.assertNewWord():
            old_word = self.lex.create_word(self.art, self.got, self.lek, 236)
        with self.assertNewWord():
            new_word = self.lex.create_word(self.art, self.got, self.lek, num_add=1)
        self.assertEqual(self.art, new_word.sbj)
        self.assertEqual(self.got, new_word.vrb)
        self.assertEqual(self.lek, new_word.obj)
        self.assertEqual(237, new_word.num)
        self.assertEqual(236, old_word.num)

    def test_03_use_already_same(self):
        """Will reuse an old word if it's the same txt & num."""
        with self.assertNewWord():
            old_word = self.lex.create_word(self.art, self.got, self.lek, 236, "tao")
        with self.assertNoNewWord():
            new_word = self.lex.create_word(self.art, self.got, self.lek, 236, "tao", use_already=True)
        self.assertEqual(new_word.idn, old_word.idn)

    def test_04_use_already_different_num(self):
        """Will not reuse, if num differs."""
        with self.assertNewWord():
            old_word = self.lex.create_word(self.art, self.got, self.lek, 236, "tao")
        with self.assertNewWord():
            new_word = self.lex.create_word(self.art, self.got, self.lek, 744, "tao", use_already=True)
        self.assertNotEqual(new_word.idn, old_word.idn)
        self.assertEqual(236, old_word.num)
        self.assertEqual(744, new_word.num)

    def test_05_use_already_unchange_num(self):
        """
        Will not reuse if num "unchanges".

        Reuse only looks at the most recently matching txt
            (with same sbj-vrb-obj of course).
        If that's a different num, no reuse occurs,
            even if an OLDER word did match in txt and num.
        Because in this situation, the word's num changed, then unchanged.
        So we must preserve the history of all three events.
        """
        with self.assertNewWord():
            older_word = self.lex.create_word(self.art, self.got, self.lek, 744, "tao")
        with self.assertNewWord():
            old_word = self.lex.create_word(self.art, self.got, self.lek, 236, "tao")
        with self.assertNewWord():
            new_word = self.lex.create_word(self.art, self.got, self.lek, 744, "tao", use_already=True)

        self.assertNotEqual(new_word.idn, older_word.idn)   # Older word matched, but hidden by old
        self.assertNotEqual(new_word.idn, old_word.idn)     # Old word had a different num

        self.assertTrue(older_word.idn < old_word.idn < new_word.idn)

        self.assertEqual(744, older_word.num)
        self.assertEqual(236, old_word.num)
        self.assertEqual(744, new_word.num)

    def test_06_use_already_different_txt(self):
        with self.assertNewWord():
            old_word = self.lex.create_word(self.art, self.got, self.lek, 236, "tao")
        with self.assertNewWord():
            new_word = self.lex.create_word(self.art, self.got, self.lek, 236, "eta", use_already=True)
        self.assertNotEqual(new_word.idn, old_word.idn)
        self.assertEqual("tao", old_word.txt)
        self.assertEqual("eta", new_word.txt)

    # TODO:  Test Lex.create_word(override_idn) and/or Word.save(override_idn)


class WordUnicode(WordTests):

    def setUp(self):
        super(WordUnicode, self).setUp()
        self.anna =    self.lex.noun('anna')
        self.comment = self.lex.verb('comment')
        self.zarf =    self.lex.noun('zarf')


class WordUnicodeTxt(WordUnicode):
    """Unicode characters in non-definition word descriptions, e.g. comments.

    In each pair of tests, the string may go in as either """

    def test_unicode_b_ascii(self):
        self.assertEqual("ascii", self.lex[self.anna.says(self.comment, self.zarf, 1, "ascii").idn].txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    def test_unicode_d_spanish(self):
        comment = self.anna.says(self.comment, self.zarf, 1, "mañana")
        self.assertEqual("ma\u00F1ana", self.lex[comment.idn].txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    def test_unicode_f_peace(self):
        comment = self.anna.says(self.comment, self.zarf, 1, "☮ on earth")
        self.assertEqual("\u262E on earth", self.lex[comment.idn].txt)
        if SHOW_UTF8_EXAMPLES:
            self.show_txt_in_utf8(self.lex.max_idn())

    if TEST_ASTRAL_PLANE:

        def test_unicode_h_unicode_pile_of_poo(self):
            comment = self.anna.says(self.comment, self.zarf, 1, "stinky \U0001F4A9")
            self.assertEqual("stinky \U0001F4A9", self.lex[comment.idn].txt)
            if SHOW_UTF8_EXAMPLES:
                self.show_txt_in_utf8(self.lex.max_idn())


# noinspection SpellCheckingInspection
class Word0020UnicodeVerb(WordUnicode):
    """Unicode characters in verb names."""

    def test_unicode_j_verb_ascii(self):
        sentence1 = self.lex.define(self.comment, "remark")
        sentence2 = self.lex[sentence1.idn]
        self.assertEqual("remark", sentence2.txt)
        self.assertTrue(self.lex['remark'].exists())
        self.assertTrue(self.lex['remark'].is_a_verb())

    def test_unicode_l_verb_spanish(self):
        sentence1 = self.lex.define(self.comment, "comentó")
        sentence2 = self.lex[sentence1.idn]
        self.assertEqual("comentó", sentence2.txt)
        self.assertTrue(self.lex['comentó'].exists())
        self.assertTrue(self.lex['comentó'].is_a_verb())

    def test_unicode_n_verb_encourage(self):
        """Unicode smiley in string literal."""
        self.assertEqual("\U0000263A", "☺")
        sentence1 = self.lex.define(self.comment, "enc☺urage")
        sentence2 = self.lex[sentence1.idn]
        self.assertEqual("enc☺urage", sentence2.txt)
        self.assertTrue(self.lex['enc☺urage'].is_a_verb())
        self.assertTrue(self.lex['enc☺urage'].exists())
        self.assertTrue(self.lex['enc☺urage'].is_a_verb())

    if TEST_ASTRAL_PLANE:

        def test_unicode_o_verb_alien_face(self):
            sentence1 = self.lex.define(self.comment, "\U0001F47Dlienate")
            sentence2 = self.lex[sentence1.idn]
            self.assertEqual("\U0001F47Dlienate", sentence2.txt)
            self.assertTrue(self.lex['\U0001F47Dlienate'].exists())
            self.assertTrue(self.lex['\U0001F47Dlienate'].is_a_verb())


class Word0030MoreTests(WordTests):

    def test_describe(self):
        thing = self.lex.noun('thingamajig')
        self.assertIn('thingamajig', thing.description())

    # def test_short_and_long_ways(self):
    #     noun = self.lex['noun']
    #     thing1 = noun('thing')
    #     thing2 = self.lex.noun('thing')
    #     thing3 = self.lex.define(noun, 'thing')
    #     self.assertEqual(thing1.idn,           thing2.idn          )
    #     self.assertEqual(thing1.idn,           thing3.idn          )
    #     self.assertEqual(thing1.description(), thing2.description())
    #     self.assertEqual(thing1.description(), thing3.description())
    #     self.assertEqual(thing1,               thing2              )
    #     self.assertEqual(thing1,               thing3              )
    #
    #     subthing1 = thing1('subthing1')
    #     subthing2 = thing2('subthing2')
    #     subthing3 = thing3('subthing3')
    #     self.assertTrue(subthing1.exists())
    #     self.assertTrue(subthing2.exists())
    #     self.assertTrue(subthing3.exists())
    #     self.assertEqual('subthing1', subthing1.txt)
    #     self.assertEqual('subthing2', subthing2.txt)
    #     self.assertEqual('subthing3', subthing3.txt)

    def test_description_uses_txt(self):
        """Detects word names in a sentence description.

        Detects a bug where Word.description() showed all the parts as their idn.qstring()."""
        description = self.lex[qiki.LexSentence.IDN_AGENT].description()
        self.assertIn('lex', description)
        self.assertIn('define', description)
        self.assertIn('noun', description)
        self.assertIn('agent', description)

    def test_verb(self):
        self.lex.verb('like')
        like = self.lex['like']
        self.assertEqual(self.lex._lex, like.sbj)

    def test_is_a_verb(self):
        verb = self.lex['verb']
        noun = self.lex['noun']
        like = self.lex.verb('like')
        yurt = self.lex.noun('yurt')
        self.assertTrue(like.is_a_verb())
        self.assertTrue(verb.is_a_verb(reflexive=True))
        self.assertFalse(verb.is_a_verb(reflexive=False))
        self.assertFalse(verb.is_a_verb())
        self.assertFalse(noun.is_a_verb())
        self.assertFalse(yurt.is_a_verb())

        self.assertFalse(self.lex['noun'].is_a_verb())
        self.assertFalse(self.lex['verb'].is_a_verb())
        self.assertTrue(self.lex['define'].is_a_verb())
        self.assertFalse(self.lex['agent'].is_a_verb())
        self.assertFalse(self.lex['lex'].is_a_verb())

    def test_verb_use(self):
        """Test that sbj.vrb(obj, num) creates a word.  And sbj.vrb(obj).num reads it back."""
        agent = self.lex['agent']
        human = self.lex.define(agent, 'human')
        like = self.lex.verb('like')
        anna = self.lex.define(human, 'anna')
        bart = self.lex.define(human, 'bart')
        chad = self.lex.define(human, 'chad')
        dirk = self.lex.define(human, 'dirk')
        anna.says(like, anna, 1, "Narcissism.")
        anna.says(like, bart, 8, "Okay.")
        anna.says(like, chad, 10)
        anna.says(like, dirk, 1)
        self.assertFalse(like.is_lex())
        self.assertFalse(like.is_verb())
        self.assertEqual(1, anna.said(like, anna).num)
        self.assertEqual(8, anna.said(like, bart).num)
        self.assertEqual(10, anna.said(like, chad).num)
        self.assertEqual(1, anna.said(like, dirk).num)
        self.assertEqual("Narcissism.", anna.said(like, anna).txt)
        self.assertEqual("Okay.", anna.said(like, bart).txt)
        self.assertEqual("", anna.said(like, chad).txt)
        self.assertEqual("", anna.said(like, dirk).txt)

    def test_verb_use_alt(self):
        """Test that lex.verb can be copied by assignment, and still work."""
        human = self.lex.define('agent', 'human')
        anna = self.lex.define(human, 'anna')
        bart = self.lex.define(human, 'bart')
        verb = self.lex.verb   # [sic] yes, just the bound method
        like = verb('like')
        anna.says(like, bart, 13)
        self.assertEqual(13, anna.said(like, bart).num)

    def test_verb_txt(self):
        """Test s.v(o, n, txt).  Read with s.v(o).txt"""
        human = self.lex.define('agent', 'human')
        anna = self.lex.define(human, 'anna')
        bart = self.lex.define(human, 'bart')
        like = self.lex.verb('like')
        anna.says(like, bart, 5, "just as friends")
        self.assertEqual("just as friends", anna.said(like, bart).txt)

    def test_verb_overlay(self):
        """Test multiple s.says(v,o,n,t) calls with different num's.
        Reading with s.said(v,o).num should only get the latest value.

        The feature that makes this work is something like 'ORDER BY idn DESC LIMIT 1'
        in Lex.populate_word_from_sbj_vrb_obj() via the 'getter' syntax s.said(v,o)"""
        human = self.lex.define('agent', 'human')
        anna = self.lex.define(human, 'anna')
        bart = self.lex.define(human, 'bart')
        like = self.lex.verb('like')

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
        human = self.lex.define('agent', 'human')
        anna = self.lex.define(human, 'anna')
        bart = self.lex.define( human, 'bart')
        like = self.lex.verb('like')


        # with self.assertNoNewWord("Identical s.v(o,n,t) shouldn't generate a new word."):
        #     anna.says(like, bart, 5, "just as friends")
        # TODO:  Decide whether these "duplicates" should be errors or insert new records or not...
        # TODO:  Probably it should be an error for some verbs (e.g. like) and not for others (e.g. comment)
        # TODO: 'unique' option?  Imbue "like" verb with properties using Words??

        with self.assertNewWord():    anna.says(like, bart, 5, "just as friends")
        with self.assertNewWord():    anna.says(like, bart, 5, "maybe more than friends")
        with self.assertNewWord():    anna.says(like, bart, 6, "maybe more than friends")
        with self.assertNewWord():    anna.says(like, bart, 7, "maybe more than friends")
        with self.assertNewWord():    anna.says(like, bart, 7, "maybe more than friends")
        with self.assertNoNewWord():  anna.says(like, bart, 7, "maybe more than friends", use_already=True)
        self.assertEqual(7, anna.said(like, bart).num)
        with self.assertNewWord():    anna.says(like, bart, 6, "maybe more than friends")
        self.assertEqual(6, anna.said(like, bart).num)
        with self.assertNewWord():
            anna.says(like, bart, 7, "maybe more than friends", use_already=True)
            # There was an earlier, identical sentence.
            # But it's not the latest with that s,v,o.   (There's a 6.)
            # So a new sentence should be generated.
            # TODO:  Deal with a diversity of feature contours that might be wanted.
            # (1) What is identical?  Just s,v,o?  Or s,v,o,n,t?
            # (2) What is earlier, simply a lower idn?  How about on other lexes?
        self.assertEqual(7, anna.said(like, bart).num)
        with self.assertNewWord():    anna.says(like, bart, 5, "just friends")
        self.assertEqual(5, anna.said(like, bart).num)

    def test_is_defined(self):
        self.assertTrue(self.lex['noun'].is_defined())
        self.assertTrue(self.lex['verb'].is_defined())
        self.assertTrue(self.lex['define'].is_defined())
        self.assertTrue(self.lex['agent'].is_defined())
        self.assertTrue(self.lex._lex.is_defined())

        human = self.lex.define('agent', 'human')
        anna = self.lex.define(human, 'anna')
        bart = self.lex.define(human, 'bart')
        like = self.lex.verb('like')
        liking = anna.says(like, bart, 5)

        self.assertTrue(human.is_defined())
        self.assertTrue(anna.is_defined())
        self.assertTrue(bart.is_defined())
        self.assertTrue(like.is_defined())
        self.assertFalse(liking.is_defined())

    # def test_non_verb_undefined_as_function_disallowed(self):
    #     human = self.lex.define('agent', 'human')
    #     anna = self.lex.define(human, 'anna')
    #     bart = self.lex.define(human, 'bart')
    #     like = self.lex.verb('like')
    #
    #     liking = anna.says(like, bart, 5)
    #     with self.assertRaises(TypeError):
    #         liking(bart)
    #     with self.assertRaises(qiki.Word.NonVerbUndefinedAsFunctionException):
    #         liking(bart)

    def test_lex_is_lex(self):
        """Various ways a lex is OR ISN'T a singleton, with it's lex."""
        sys1 = self.lex
        sys2 = self.lex['lex']
        sys3 = self.lex['lex'].lex
        sys4 = self.lex['lex'].lex['lex']
        sys5 = self.lex['lex'].lex['lex'].lex

        with self.assertRaises(TypeError):
            '''The plain jane word lex cannot spawn words.'''
            _ = self.lex['lex']['lex']

        self.assertNotEqual(sys1,     sys2)

        self.assertIs(      sys1,     sys3)

        self.assertNotEqual(sys1,     sys4)
        self.assertEqual(   sys2,     sys4)
        self.assertEqual(   sys2.idn, sys4.idn)
        self.assertIsNot(   sys2,     sys4)

        self.assertIs(      sys1,     sys5)

    def test_idn_setting_not_allowed(self):
        lex = self.lex['lex']
        self.assertEqual(lex.idn, self.lex.IDN_LEX)
        with self.assertRaises(AttributeError):
            lex.idn = 999
        self.assertEqual(lex.idn, self.lex.IDN_LEX)

    def test_idn_suffix(self):
        """Make sure adding a suffix to the lex's idn does not modify lex.idn."""
        lex = self.lex['lex']
        self.assertEqual(lex.idn, self.lex.IDN_LEX)
        suffixed_lex_idn = lex.idn.plus_suffix(3)
        # FIXME:  Crap, this USED to mutate lex.idn!!
        self.assertEqual(lex.idn, self.lex.IDN_LEX)
        self.assertEqual(suffixed_lex_idn, qiki.Number('0q80__030100'))

    # def test_verb_paren_object(self):
    #     """An orphan verb can spawn a sentence.
    #     v = lex['name of a verb']; v(o) is equivalent to lex.v(o).
    #     Lex is the implicit subject."""
    #     some_object = self.lex.noun('some object')
    #     verb = self.lex['verb']
    #     oobleck = verb('oobleck')
    #     self.assertTrue(oobleck.is_a_verb())
    #     with self.assertNewWord():
    #         blob = oobleck(some_object, qiki.Number(42), 'new sentence')
    #     self.assertTrue(blob.exists())
    #     self.assertEqual(blob.sbj, self.lex)
    #     self.assertEqual(blob.vrb, oobleck)
    #     self.assertEqual(blob.obj, some_object)
    #     self.assertEqual(blob.num, qiki.Number(42))
    #     self.assertEqual(blob.txt, "new sentence")

    # def test_verb_paren_object_text_number(self):
    #     """More orphan verb features.  v = lex[...]; v(o,t,n) is also equivalent to lex.v(o,t,n)."""
    #     some_object = self.lex.noun('some object')
    #     verb = self.lex['verb']
    #     oobleck = verb('oobleck')
    #     self.assertTrue(oobleck.is_a_verb())
    #     with self.assertNewWord():
    #         blob = oobleck(some_object, qiki.Number(11), "blob")
    #     self.assertTrue(blob.exists())
    #     self.assertEqual(blob.obj, some_object)
    #     self.assertEqual(blob.num, qiki.Number(11))
    #     self.assertEqual(blob.txt, "blob")

    def test_define_object_type_string(self):
        """Specify the object of a definition by its txt."""
        oobleck = self.lex.define('verb', 'oobleck')
        self.assertTrue(oobleck.exists())
        self.assertEqual(oobleck.sbj, self.lex._lex)
        self.assertEqual(oobleck.vrb, self.lex['define'])
        self.assertEqual(oobleck.obj, self.lex['verb'])
        self.assertEqual(oobleck.num, qiki.Number(1))
        self.assertEqual(oobleck.txt, "oobleck")

    # def test_verb_paren_object_deferred_subject(self):
    #     """A patronized verb can spawn a sentence.
    #     That's a verb such as subject.verb that is generated as if it were an attribute.
    #     x = s.v; x(o) is equivalent to s.v(o).
    #     So a verb word instance can remember its subject for later spawning a new word."""
    #
    #     some_object = self.lex.noun('some object')
    #     self.lex.verb('oobleck')
    #     lex_oobleck = self.lex['oobleck']   # word from an orphan verb
    #
    #     xavier = self.lex.define('agent', 'xavier')
    #     self.assertNotEqual(xavier, self.lex)
    #     xavier_oobleck = xavier.oobleck   # word from a patronized verb
    #
    #     # Weirdness: the verb instances are equal but behave differently
    #     self.assertEqual(lex_oobleck, xavier_oobleck)   # TODO:  Should these be unequal??
    #     self.assertFalse(hasattr(lex_oobleck, '_word_before_the_dot'))
    #     self.assertTrue(hasattr(xavier_oobleck, '_word_before_the_dot'))
    #     # self.assertNotEqual(lex_oobleck._word_before_the_dot, xavier_oobleck._word_before_the_dot)
    #
    #     xavier_blob = xavier_oobleck(some_object, qiki.Number(42), "xavier blob")
    #     self.assertTrue(xavier_blob.exists())
    #     self.assertEqual(xavier_blob.sbj, xavier)
    #     self.assertEqual(xavier_blob.vrb, xavier_oobleck)
    #     self.assertEqual(xavier_blob.obj, some_object)
    #     self.assertEqual(xavier_blob.num, qiki.Number(42))
    #     self.assertEqual(xavier_blob.txt, "xavier blob")

    def test_lex_number(self):
        agent_by_txt = self.lex['agent']
        agent_by_idn = self.lex[qiki.LexSentence.IDN_AGENT]
        self.assertEqual(agent_by_txt, agent_by_idn)
        self.assertEqual('agent', agent_by_idn.txt)
        self.assertEqual(qiki.LexSentence.IDN_AGENT, agent_by_txt.idn)

    def test_num_explicit(self):
        anna = self.lex.define('agent', 'anna')
        hate = self.lex.verb('hate')
        oobleck = self.lex.noun('oobleck')
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
    #     blurt = self.lex.verb('blurt')
    #     self.lex.says(blurt, self.lex, 1, '')
    #     with self.assertRaises(TypeError):
    #         self.lex.says(blurt, self.lex, no_such_keyword_argument=666)
    #     with self.assertRaises(qiki.Word.SentenceArgs):
    #         self.lex.says(blurt, self.lex, no_such_keyword_argument=666)

    # def test_missing_sentence_obj(self):
    #     self.lex.verb('blurt')
    #     with self.assertRaises(TypeError):
    #         self.lex.blurt()
    #     with self.assertRaises(qiki.Word.MissingObj):
    #         self.lex.blurt()

    def test_missing_word_getter(self):
        alf = self.lex.define('agent', 'alf')
        clap = self.lex.verb('clap')
        eve = self.lex.verb('eve')
        with self.assertNewWord():
            alf.says(clap, eve, 55)
        word = alf.said(clap, eve)
        self.assertEqual(55, word.num)
        with self.assertRaises(qiki.Word.NotExist):
            _ = eve.said(clap, alf)

    def test_missing_word_getter_square(self):
        alf = self.lex.define('agent', 'alf')
        clap = self.lex.verb('clap')
        eve = self.lex.verb('eve')
        with self.assertNewWord():
            alf(clap)[eve] = 55
        word = alf.said(clap, eve)
        self.assertEqual(55, word.num)
        with self.assertRaises(qiki.Word.NotExist):
            _ = eve(clap)[alf]

    # def test_missing_lex_getter(self):
    #     with self.assertRaises(qiki.Word.NotExist):
    #         _ = self.lex['defibrillator']

    def test_no_negative_idn(self):
        """This catches a bug where LexInMemory()[-1] returned the same as LexInMemory()[4]"""
        ghost_word = self.lex[-1]
        self.assertFalse(
            ghost_word.exists(),
            "A {lex_class} shouldn't have a word for idn -1".format(lex_class=type_name(self.lex))
        )


class Word0040SentenceTests(WordTests):

    def setUp(self):
        super(Word0040SentenceTests, self).setUp()
        self.sam = self.lex.define('agent', 'sam')
        self.vet = self.lex.verb('vet')
        self.orb = self.lex.noun('orb')

    def assertGoodSentence(self, sentence, the_num=1, the_txt=''):
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
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=42, txt='sentence'), 42, 'sentence')

    def test_sentence_01a_keyword(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=42, txt='sentence'), 42, 'sentence')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=42), 42)
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, txt='sentence'), 1, 'sentence')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb))

    def test_sentence_01b_missing(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb))
        with self.assertRaises(TypeError):   # was six.assertRaisesRegex(self, qiki.Word.SentenceArgs, 'obj'):
            self.assertGoodSentence(self.sam.says(vrb=self.vet))
        with self.assertRaises(TypeError):   # was six.assertRaisesRegex(self, qiki.Word.SentenceArgs, 'vrb'):
            self.assertGoodSentence(self.sam.says(obj=self.orb))

    def test_sentence_02a_positional(self):
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, 42, 'sentence'), 42, 'sentence')
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, 'sentence', 42), 42, 'sentence')
        self.assertGoodSentence(self.sam.says(self.vet, self.orb))
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, 42), 42)
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, True), 1)
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, 'x'), 1, 'x')

    def test_sentence_02b_positional_mix_keyword(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=42, txt='sentence'), 42, 'sentence')
        self.assertGoodSentence(self.sam.says(self.vet, obj=self.orb, num=42, txt='sentence'), 42, 'sentence')
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, num=42, txt='sentence'), 42, 'sentence')
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, 42, txt='sentence'), 42, 'sentence')
        # self.assertGoodSentence(self.sam.says(self.vet, self.orb, 'x', num=42), 42, 'x')
        self.assertGoodSentence(self.sam.says(self.vet, self.orb, 42, txt='x'), 42, 'x')

    def test_sentence_02c_wrong_type(self):
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, some_type))
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, some_type, 1))
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, some_type, ''))
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, 1, some_type))
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, '', some_type))

    def test_sentence_02d_ambiguous_type(self):
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, 42, 42))
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, 'x', 'x'))
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, 'x', txt='x'))
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, 'x', '0q80'))
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, '0q80', 'x'))
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, 'x', '0x80'))
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.assertGoodSentence(self.sam.says(self.vet, self.orb, '0x80', 'x'))

    def test_sentence_by_idn(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet.idn, obj=self.orb.idn, num=42, txt='sentence'), 42, 'sentence')

    def test_sentence_args(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=42, txt='sentence'), 42, 'sentence')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=qiki.Number(42), txt='sentence'), 42, 'sentence')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb))
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=99), 99)
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, txt='flop'), 1, 'flop')

    def test_sentence_use_already(self):
        w1 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt='x'), 9, 'x')
        w2 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt='x'), 9, 'x')
        self.assertLess(w1.idn, w2.idn)

        w3a = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=8, txt='y'), 8, 'y')
        w3b = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=8, txt='y', use_already=True), 8, 'y')
        self.assertEqual(w3a.idn, w3b.idn)

        w4 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=7, txt='z'), 7, 'z')
        w5 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=7, txt='z', use_already=False), 7, 'z')
        self.assertLess(w4.idn, w5.idn)

    def test_sentence_whn(self):
        w1 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt='x'), 9, 'x')
        self.assertSensibleWhen(w1.whn)

        w2 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt='x'), 9, 'x')
        self.assertSensibleWhen(w2.whn)
        self.assertLess(w1.idn, w2.idn)
        self.assertLessEqual(w1.whn, w2.whn)

        w2b = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt='x', use_already=True), 9, 'x')
        self.assertSensibleWhen(w2b.whn)
        self.assertEqual(w2.idn, w2b.idn)
        self.assertEqual(w2.whn, w2b.whn)

        w3 = self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt='x', use_already=False), 9, 'x')
        self.assertSensibleWhen(w3.whn)
        self.assertLess(w2.idn, w3.idn)
        self.assertLessEqual(w2.whn, w3.whn)
    #
    # def test_sentence_bad_positional(self):
    #     with self.assertRaises(qiki.LexSentence.CreateWordError):
    #         self.lex.says(self.sam, self.vet, self.orb, 1, '')
    #     with self.assertRaises(qiki.LexSentence.CreateWordError):
    #         self.lex.says(self.sam, self.vet, self.orb, 1)
    #     with self.assertRaises(qiki.LexSentence.CreateWordError):
    #         self.lex.says(self.sam, self.vet, self.orb)
    #     with self.assertRaises(qiki.LexSentence.CreateWordError):
    #         self.lex.says()

    def test_sentence_bad_args(self):
        # with self.assertRaises(qiki.LexSentence.CreateWordError):
        with self.assertRaises(TypeError):
            self.sam.says(vrb=self.vet, obj=self.orb, no_such_arg=0)

    def test_sentence_num_add(self):
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=9, txt='x'), 9, 'x')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num_add=2, txt='x'), 11, 'x')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num_add=2, txt='x'), 13, 'x')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=None, num_add=2, txt='x'), 15, 'x')
        self.assertGoodSentence(self.sam.says(vrb=self.vet, obj=self.orb, num=8, num_add=None, txt='x'), 8, 'x')

    def test_sentence_conflict_num_num_add(self):
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.sam.says(vrb=self.vet, obj=self.orb, num=99, num_add=-99)

    def test_call_conflict_num_num_add(self):
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.sam.says(self.vet, self.orb, num=99, num_add=-99)
        with self.assertRaises(qiki.LexSentence.CreateWordError):
            self.sam.says(self.vet, self.orb, 99, num_add=-99)
        # with self.assertRaises(qiki.LexSentence.CreateWordError):
        #     self.sam.says(self.vet, self.orb, 99, num=-99)
        # with self.assertRaises(qiki.LexSentence.CreateWordError):
        #     self.sam.says(self.vet, self.orb, 99, num=-99, num_add=999999)


class WordSimpleListingTests(WordTests):

    class SimpleListing(qiki.Listing):
        def lookup(self, index):
            return "{:d}".format(int(index)), index

    def setUp(self):
        super(WordSimpleListingTests, self).setUp()
        self.listing = self.lex.noun('listing')

        meta_simple_listing = self.lex.define(self.listing, 'simple listing')
        self.simple_listing = self.SimpleListing(meta_simple_listing)


class Word0050SimpleListingBasicTests(WordSimpleListingTests):

    def test_simple_listing(self):
        self.assertEqual('0q82_06',              self.simple_listing.meta_word.idn)
        self.assertEqual('0q82_06__82FF_1D0300', self.simple_listing[255].idn)
        self.assertEqual( 255,               int(self.simple_listing[255].num))
        self.assertEqual("255",              str(self.simple_listing[255].txt))

    # noinspection PyStringFormat
    def test_listing_idn_repr(self):
        listing_of_65535 = self.simple_listing[65535]
        self.assertEqual(     '0q82_06', self.simple_listing.meta_word.idn)
        self.assertEqual(     '0q82_06__83FFFF_1D0400', listing_of_65535.idn)
        self.assertEqual("Word(0q82_06__83FFFF_1D0400)", repr(listing_of_65535))

    # noinspection PyStringFormat
    def test_listing_idn_formatting(self):
        listing_of_255 = self.simple_listing[255]
        self.assertEqual(         '0q82_06', self.simple_listing.meta_word.idn)
        self.assertEqual(         '0q82_06__82FF_1D0300', listing_of_255.idn)
        self.assertEqual("Word(idn=0q82_06__82FF_1D0300)", "{:i}".format(listing_of_255))


class WordStudentListingTests(WordTests):

    class StudentRoster(qiki.Listing):

        def __init__(self, grades, *args, **kwargs):
            super(WordStudentListingTests.StudentRoster, self).__init__(*args, **kwargs)
            self.grades = grades

        def lookup(self, index):
            WordStudentListingTests._lookup_call_count += 1
            try:
                return self.grades[int(index)]
            except IndexError:
                raise self.NotFound("There is no student index {}".format(index))

    _lookup_call_count = None   # number of lookups since SetUp

    def setUp(self):
        super(WordStudentListingTests, self).setUp()
        WordStudentListingTests._lookup_call_count = 0
        # self.listing = self.lex['lex']('define', txt='listing')['noun']
        # meta_word = self.lex['lex']('define', txt='student roster')['listing']
        self.listing = self.lex.noun('listing')

        meta_word = self.lex.define(self.listing, 'student roster')
        self.student_roster = self.StudentRoster(
            [
                ("Archie", 4.0),
                ("Barbara", 3.0),
                ("Chad", 3.0),
                ("Deanne", 1.0),
            ],
            meta_word
        )


class Word0051StudentListingBasicTests(WordStudentListingTests):

    def test_listing_word_type(self):
        chad = self.student_roster[qiki.Number(2)]
        self.assertIsInstance(chad, self.student_roster.word_class)
        self.assertIs(type(chad), self.student_roster.word_class)
        self.assertEqual('WordClassJustForThisListing', type_name(chad))

    def test_listing_word_type_unique(self):
        self.assertIsNot(self.student_roster.word_class, type(self.lex['lex']))

    def test_listing_suffix(self):
        # TODO:  Simpler, more granular early listing tests.
        chad = self.student_roster[qiki.Number(2)]

        meta_idn = self.student_roster.meta_word.idn
        suffix = qiki.Suffix(qiki.Suffix.Type.LISTING, qiki.Number(2))
        composite_idn = qiki.Number(meta_idn, suffix)

        self.assertEqual( composite_idn, chad.idn)
        self.assertEqual(qiki.Number(2), chad.index)
        self.assertEqual(        "Chad", chad.txt)
        self.assertEqual(           3.0, chad.num)
        self.assertTrue(chad.exists())

        expected_unsuffixed = self.student_roster.meta_word.idn
        expect_one_suffix = qiki.Suffix(qiki.Suffix.Type.LISTING, qiki.Number(2))
        self.assertEqual(expected_unsuffixed, chad.idn.unsuffixed)
        self.assertEqual([expect_one_suffix], chad.idn.suffixes)

    def test_listing_using_spawn_and_save(self):
        archie = self.student_roster[qiki.Number(0)]
        bless = self.lex.verb('bless')
        blessed_name = self.lex._lex.spawn(
            sbj=self.lex._lex.idn,
            vrb=bless.idn,
            obj=archie.idn,
            txt="mah soul",
            num=qiki.Number(666),
        )
        blessed_name.save()

        blessed_name_too = self.lex._lex.spawn(blessed_name.idn)
        self.assertTrue(blessed_name_too.exists())
        self.assertEqual(blessed_name_too.sbj.idn, qiki.LexSentence.IDN_LEX)
        self.assertEqual(blessed_name_too.vrb, bless)
        self.assertEqual(blessed_name_too.obj, archie)
        self.assertEqual(blessed_name_too.num, qiki.Number(666))
        self.assertEqual(blessed_name_too.txt, "mah soul")

        laud = self.lex.verb('laud')
        thing = self.lex.noun('thing')
        lauded_thing = self.lex._lex.spawn(
            sbj=archie.idn,
            vrb=laud.idn,
            obj=thing.idn,
            txt="most sincerely",
            num=qiki.Number(123456789),
        )
        lauded_thing.save()

    def test_listing_using_method_verb(self):
        archie = self.student_roster[qiki.Number(0)]
        bless = self.lex.verb('bless')
        blessed_name = self.lex._lex.says(vrb=bless, obj=archie, num=qiki.Number(666), txt="mah soul")

        blessed_name_too = self.lex._lex.spawn(blessed_name.idn)
        self.assertTrue(blessed_name_too.exists())
        self.assertEqual(blessed_name_too.sbj.idn, qiki.LexSentence.IDN_LEX)
        self.assertEqual(blessed_name_too.vrb, bless)
        self.assertEqual(blessed_name_too.obj, archie)
        self.assertEqual(blessed_name_too.num, qiki.Number(666))
        self.assertEqual(blessed_name_too.txt, "mah soul")

        laud = self.lex.verb('laud')
        thing = self.lex.noun('thing')
        with self.assertNewWord():
            _ = archie(vrb=laud, num=qiki.Number(123456789), txt="most sincerely")[thing]
            # _ = archie(laud, qiki.Number(123456789), "most sincerely")[thing]
            # archie(laud)[thing] = qiki.Number(123456789), "most sincerely"

    def test_listing_not_found(self):
        """Bogus index raises a Listing.NotFound exception."""
        not_a_student = self.student_roster[qiki.Number(5)]
        with self.assertRaises(qiki.Listing.NotFound):
            _ = not_a_student.txt

    def test_listing_index_Number(self):
        deanne = self.student_roster[qiki.Number(3)]
        self.assertEqual("Deanne", deanne.txt)

    def test_listing_index_int(self):
        deanne = self.student_roster[3]
        self.assertEqual("Deanne", deanne.txt)

    def test_listing_as_nouns(self):
        barbara = self.student_roster[1]
        deanne = self.student_roster[3]
        like = self.lex.verb('like')
        with self.assertNewWords(2):
            # barbara.says(vrb=like, obj=deanne, num=qiki.Number(1))
            # deanne.says(vrb=like, obj=barbara, num=qiki.Number(-1000000000))
            barbara(like)[deanne] = 1
            deanne(like)[barbara] = -1000000000

    def test_listing_by_lex_idn(self):
        """Make sure lex[listing idn, which is a suffixed number] will look up a listing word."""
        chad1 = self.student_roster[2]
        self.assertTrue(chad1.idn.is_suffixed())
        chad2 = self.lex[chad1.idn]
        self.assertTrue(chad2.idn.is_suffixed())
        self.assertEqual(chad1.idn, chad2.idn)
        self.assertEqual("Chad", chad1.txt)
        self.assertEqual("Chad", chad2.txt)
        self.assertEqual(chad1, chad2)

    # def test_listing_by_spawn_idn(self):
    #     """Make sure word.spawn(listing idn) will look up a listing."""
    #     chad1 = self.student_roster[2]
    #     chad2 = self.lex.sbj.spawn(chad1.idn)
    #     self.assertEqual("Chad", chad1.txt)
    #     self.assertEqual("Chad", chad2.txt)
    #     self.assertEqual(chad1, chad2)
    #
    # def test_listing_by_spawn_word_inchoate(self):
    #     """Make sure word.spawn(inchoate listing word) will look up a listing."""
    #     chad1 = self.student_roster[2]
    #     chad2 = self.lex.sbj.spawn(chad1)
    #     self.assertTrue(chad1._is_inchoate)
    #     self.assertTrue(chad2._is_inchoate)
    #     self.assertEqual("Chad", chad1.txt)
    #     self.assertEqual("Chad", chad2.txt)
    #     self.assertFalse(chad1._is_inchoate)
    #     self.assertFalse(chad2._is_inchoate)
    #     self.assertEqual(chad1, chad2)
    #
    # def test_listing_by_spawn_word_choate(self):
    #     """Make sure word.spawn(choate listing word) will look up a listing."""
    #     chad1 = self.student_roster[2]
    #     self.assertEqual("Chad", chad1.txt)
    #     chad2 = self.lex.sbj.spawn(chad1)
    #     self.assertFalse(chad1._is_inchoate)
    #     self.assertTrue(chad2._is_inchoate)
    #     self.assertEqual("Chad", chad2.txt)
    #     self.assertFalse(chad2._is_inchoate)
    #     self.assertEqual(chad1, chad2)



class Word0052StudentListingMultipleTests(WordStudentListingTests):

    class SubStudent(WordStudentListingTests.StudentRoster):
        pass

    class AnotherListing(qiki.Listing):

        def lookup(self, index):
            raise self.NotFound

    def setUp(self):
        super(Word0052StudentListingMultipleTests, self).setUp()
        self.sub_student = self.SubStudent(meta_word=self.lex.noun('sub_student'), grades=[])
        self.another_listing = self.AnotherListing(meta_word=self.lex.noun('another_listing'))
        # TODO:  Shouldn't these be ...define(listing, 'blah') instead of plain nouns?

    def test_singleton_class_dictionary(self):
        self.assertIs(qiki.Listing.listing_dictionary, self.student_roster.listing_dictionary)
        self.assertIs(qiki.Listing.listing_dictionary, self.sub_student.listing_dictionary)
        self.assertIs(qiki.Listing.listing_dictionary, self.another_listing.listing_dictionary)
        # self.lex_report()
        # EXAMPLE:
        #
        # lex_report <-- test_singleton_class_dictionary
        #
        # 0 [lex](define, 'lex')[agent]
        # 1 [lex](define, 'define')[verb]
        # 2 [lex](define, 'noun')[noun]
        # 3 [lex](define, 'verb')[noun]
        # 4 [lex](define, 'agent')[noun]
        # 5 [lex](define, 'listing')[noun]
        # 6 [lex](define, 'student roster')[listing]
        # 7 [lex](define, 'sub_student')[noun]
        # 8 [lex](define, 'another_listing')[noun]
        #
        # 9 ⋅ Word('lex')
        # 9 ⋅ Word('define')
        # 6 ⋅ Word('noun')
        # 1 ⋅ Word('agent')
        # 1 ⋅ Word('verb')
        # 1 ⋅ Word('listing')
        #
        # Mesa lexes
        #     None: LexMemory
        #     0q82_06: student roster -- StudentRoster
        #     0q82_07: sub_student -- SubStudent
        #     0q82_08: another_listing -- AnotherListing

    def test_one_meta_word_per_subclass(self):
        self.assertNotEqual(self.student_roster.meta_word.idn, self.sub_student.meta_word.idn)
        self.assertNotEqual(self.student_roster.meta_word.idn, self.another_listing.meta_word.idn)
        self.assertNotEqual(self.sub_student.meta_word.idn, self.another_listing.meta_word.idn)

    def test_idn_suffixed(self):
        chad = self.student_roster[2]
        deanne = self.student_roster[3]
        self.assertFalse(self.student_roster.meta_word.idn.is_suffixed())
        self.assertFalse(self.sub_student.meta_word.idn.is_suffixed())
        self.assertFalse(self.another_listing.meta_word.idn.is_suffixed())
        self.assertTrue(chad.idn.is_suffixed())
        self.assertTrue(deanne.idn.is_suffixed())

    def test_example_idn(self):
        chad = self.student_roster[2]
        # Serious assumption:  5 words were defined before lex.noun('listing').
        # But this helps to demonstrate Listing meta_word and instance idn contents.
        self.assertEqual('0q82_05', self.listing.idn.qstring())
        self.assertEqual('0q82_06', self.student_roster.meta_word.idn.qstring())   # Number(7)
        self.assertEqual('0q82_06__8202_1D0300', chad.idn.qstring())   # Unsuffixed Number(7), payload Number(2)
        self.assertEqual('0q82_07', self.sub_student.meta_word.idn.qstring())
        self.assertEqual('0q82_08', self.another_listing.meta_word.idn.qstring())

    def test_composite_idn(self):
        self.assertEqual('0q82_06__8222_1D0300', self.student_roster.composite_idn(0x22))
        self.assertEqual('0q82_06__8233_1D0300', self.student_roster.composite_idn(0x33))
        self.assertEqual('0q82_06__8244_1D0300', self.student_roster.composite_idn(0x44))

    def test_listing_instance_from_idn(self):
        chad = self.student_roster[2]
        chad_clone = qiki.Listing.word_from_idn(chad.idn)
        self.assertEqual("Chad", chad.txt)
        self.assertEqual("Chad", chad_clone.txt)
        self.assertEqual(chad, chad_clone)

    def test_listing_instance_from_idn_not_suffixed(self):
        with self.assertRaises(qiki.Listing.NotAListing):
            qiki.Listing.word_from_idn(qiki.Number(666))

    def test_listing_instance_from_idn_wrong_suffixed(self):
        with self.assertRaises(qiki.Listing.NotAListing):
            qiki.Listing.word_from_idn(qiki.Number(666+666j))

    def test_listing_instance_from_idn_not_listing(self):
        chad = self.student_roster[2]
        # (listing_class_idn, suffixes) = chad.idn.parse_suffixes()
        listing_class_idn = chad.idn.unsuffixed
        suffixes = chad.idn.suffixes
        not_a_listing_idn = qiki.Number(listing_class_idn + 666)
        not_a_listing_idn.plus_suffix(suffixes[0])
        with self.assertRaises(qiki.Listing.NotAListing):
            qiki.Listing.word_from_idn(not_a_listing_idn)

    def test_listing_instance_from_idn_type(self):
        chad_clone = qiki.Listing.word_from_idn(self.student_roster[2].idn)
        self.assertIs(type(chad_clone), self.student_roster.word_class)

    def test_listing_instance_from_idn_inchoate(self):
        """Make sure a listing instantiated its idn is inchoate until used."""
        chad_clone = qiki.Listing.word_from_idn(self.student_roster[2].idn)
        self.assertTrue(chad_clone._is_inchoate)
        _ = chad_clone.txt
        self.assertFalse(chad_clone._is_inchoate)

    def test_listing_instance_from_idn_lookup_call(self):
        self.assertEqual(WordStudentListingTests._lookup_call_count, 0)
        chad_clone = qiki.Listing.word_from_idn(self.student_roster[2].idn)
        self.assertEqual(WordStudentListingTests._lookup_call_count, 0)
        _ = chad_clone.txt
        self.assertEqual(WordStudentListingTests._lookup_call_count, 1)

    def test_listing_lex_lookup_type(self):
        chad_clone = self.lex[self.student_roster[2].idn]
        self.assertEqual(self.student_roster[2].idn, chad_clone.idn)
        self.assertEqual("Chad", chad_clone.txt)
        self.assertIs(type(chad_clone), self.student_roster.word_class)

    def test_class_from_meta_idn(self):
        chad = self.student_roster[2]
        chad_listing_idn = chad.idn.unsuffixed
        chad_listing = qiki.Listing.listing_from_meta_idn(chad_listing_idn)

        self.assertEqual(   self.student_roster, chad_listing)
        self.assertIs(      self.student_roster, chad_listing)

        self.assertNotEqual(qiki.Listing,        chad_listing)
        self.assertIsNot(   qiki.Listing,        chad_listing)

        self.assertTrue(isinstance(chad_listing, qiki.Listing))

    def test_listing_instance_from_class_has_a_lex(self):
        chad_from_class = self.student_roster[2]
        self.assertIsNotNone(chad_from_class.lex)
        self.assertIs(chad_from_class.lex.meta_word.lex, self.lex)

    def test_listing_instance_from_lex_has_a_lex(self):
        chad_from_class = self.student_roster[2]
        chad_from_lex = self.lex[chad_from_class.idn]
        self.assertIsNotNone(chad_from_lex.lex)
        self.assertIs(chad_from_lex.lex.meta_word.lex, self.lex)

    def test_class_from_meta_idn_bogus(self):
        some_word = self.lex.noun('some word')
        with self.assertRaises(qiki.Listing.NotAListing):
            qiki.Listing.listing_from_meta_idn(some_word.idn)

    def test_not_a_listing_suffix(self):
        """
        Cannot lex[idn] on a bogus idn, one that's suffixed but not with the Listing suffix.
        """
        with self.assertRaises(qiki.Lex.NotFound):
            _ = self.lex[qiki.Number(1+2j)]

    # def test_uninstalled_listing_instance(self):
    #     """
    #     Cannot lex[idn] on a listing whose class was never installed, e.g. an obsolete listing.
    #
    #     An "obsolete" listing has an idn somewhere in the lex,
    #     but its class has not been installed.
    #     Why does this happen?  If a class has been redefined?  Not expected to be used?
    #     The exception is not raised on instantiation; it happens when/if the word becomes choate.
    #     Unlike a non-listing suffixed word (e.g. complex) this exception is NotAListing.
    #     """
    #     obsolete_listing_meta_word = self.lex.define(self.listing, 'obsolete listing')
    #
    #     class ObsoleteListing(qiki.Listing):
    #         meta_word = obsolete_listing_meta_word
    #
    #         # noinspection PyMethodMayBeStatic,PyUnusedLocal
    #         def lookup(self, index, callback):
    #             callback("foo", qiki.Number(1))
    #
    #     obsolete_listing_instance = ObsoleteListing(42)
    #     # print(obsolete_listing_instance.idn.qstring())
    #     # 0q82_0A__822A_1D0300
    #     instance_clone = self.lex[obsolete_listing_instance.idn]
    #     # print(type(instance_clone).__name__)
    #     # ListingNotInstalled
    #     with self.assertRaises(qiki.Listing.NotAListing):
    #         _ = instance_clone.txt

    def test_listing_inchoate(self):
        """Make sure a listing instantiated from its class & index is inchoate until used."""
        chad = self.student_roster[2]
        self.assertTrue(chad._is_inchoate)
        _ = chad.txt
        self.assertFalse(chad._is_inchoate)

    def test_listing_lookup_call_txt(self):
        self.assertEqual(WordStudentListingTests._lookup_call_count, 0)
        chad = self.student_roster[2]
        self.assertEqual(WordStudentListingTests._lookup_call_count, 0)
        _ = chad.txt
        self.assertEqual(WordStudentListingTests._lookup_call_count, 1)   # w.txt triggers lookup
        _ = chad.txt
        self.assertEqual(WordStudentListingTests._lookup_call_count, 1)   # once
        _ = chad.num
        self.assertEqual(WordStudentListingTests._lookup_call_count, 1)

    def test_listing_lookup_call_num(self):
        self.assertEqual(WordStudentListingTests._lookup_call_count, 0)
        chad = self.student_roster[2]
        self.assertEqual(WordStudentListingTests._lookup_call_count, 0)
        _ = chad.num
        self.assertEqual(WordStudentListingTests._lookup_call_count, 1)   # w.num triggers lookup
        _ = chad.num
        self.assertEqual(WordStudentListingTests._lookup_call_count, 1)   # once
        _ = chad.txt
        self.assertEqual(WordStudentListingTests._lookup_call_count, 1)

    def test_listing_lookup_call_idn(self):
        self.assertEqual(WordStudentListingTests._lookup_call_count, 0)
        chad = self.student_roster[2]
        self.assertEqual(WordStudentListingTests._lookup_call_count, 0)
        _ = chad.idn
        self.assertEqual(WordStudentListingTests._lookup_call_count, 0)   # w.idn doesn't trigger lookup

    # def test_class_from_listing_idn(self):
    #     """Find the class from the listing id."""
    #     chad = self.student_roster[2]
    #     listing_idn = chad.idn
    #     chad_class = qiki.Listing.listing_from_idn(listing_idn)
    #     self.assertIs(chad_class, self.student_roster)
    #
    # def test_class_from_listing_idn_bogus(self):
    #     """Bogus listing id crashes when you try to find its class."""
    #     not_a_listing = self.lex.noun('not a listing')
    #     not_a_listing_idn = not_a_listing.idn
    #     with self.assertRaises(qiki.Listing.NotAListing):
    #         qiki.Listing.listing_from_idn(not_a_listing_idn)
    #
    # def test_class_from_listing_idn_complex(self):
    #     """Suffixed but bogus listing id crashes when you try to find its class."""
    #     not_a_listing_idn = qiki.Number(11+22j)
    #     with self.assertRaises(qiki.Listing.NotAListing):
    #         qiki.Listing.listing_from_idn(not_a_listing_idn)

    def test_read_word_base_lex(self):
        chad1 = self.student_roster[2]
        self.assertEqual("0q82_06__8202_1D0300", chad1.idn.qstring())
        self.assertTrue(chad1.idn.is_suffixed())

        chad2 = self.lex.read_word(chad1.idn)
        self.assertEqual("0q82_06__8202_1D0300", chad2.idn.qstring())

        self.assertIsNot(chad1, chad2)
        self.assertEqual(chad1, chad2)

    def test_read_word_listing(self):
        chad1 = self.student_roster[2]
        self.assertTrue(chad1.idn.is_suffixed())

        chad2 = self.student_roster.read_word(2)

        self.assertIsNot(chad1, chad2)
        self.assertEqual(chad1, chad2)

    def test_read_word_another_listing(self):
        chad1 = self.student_roster[2]
        self.assertTrue(chad1.idn.is_suffixed())

        chad2 = self.another_listing.read_word(chad1.idn)

        self.assertNotEqual(chad1, chad2)
        # NOTE:  chad2 remains inchoate

    def test_read_word_by_definition(self):
        """lex.read_word('blah') is the same as lex('blah')."""
        define1 = self.lex['define']
        define2 = self.lex.read_word('define')
        self.assertIsNot(define1, define2)
        self.assertEqual(define1, define2)

    def test_read_word_by_definition_choate(self):
        """Words read by definition txt are immediately choate."""
        define = self.lex.read_word('define')
        self.assertFalse(define._is_inchoate)

    def test_read_word_by_definition_exists(self):
        define = self.lex.read_word('define')
        self.assertTrue(define.exists())

    def test_read_word_by_definition_not_exists(self):
        gibberish = self.lex.read_word('gibberish')
        self.assertFalse(gibberish.exists())


class Word0060UseAlready(WordTests):

    def setUp(self):
        super(Word0060UseAlready, self).setUp()
        self.narcissus = self.lex.define('agent', 'narcissus')
        self.like = self.lex.verb('like')

    # When txt differs

    def test_use_already_differ_txt_default(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Puddle")

    def test_use_already_differ_txt_false(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Puddle", use_already=False)

    def test_use_already_differ_txt_true(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Puddle", use_already=True)

    # When num differs

    def test_use_already_differ_num_default(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 200, "Mirror")

    def test_use_already_differ_num_false(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 200, "Mirror", use_already=False)

    def test_use_already_differ_num_true(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 200, "Mirror", use_already=True)

    # When num and txt are the same

    def test_use_already_same_default(self):
        with self.assertNewWord():  word1 = self.narcissus.says(self.like, self.narcissus, 100, "Mirror")
        with self.assertNewWord():  word2 = self.narcissus.says(self.like, self.narcissus, 100, "Mirror")
        self.assertEqual(word1.idn+1, word2.idn)

    def test_use_already_same_false(self):
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Mirror")
        with self.assertNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Mirror", use_already=False)

    def test_use_already_same_true(self):
        with self.assertNewWord():    self.narcissus.says(self.like, self.narcissus, 100, "Mirror")
        with self.assertNoNewWord():  self.narcissus.says(self.like, self.narcissus, 100, "Mirror", use_already=True)

    # TODO:  Deal with the inconsistency that when defining a word, use_already defaults to True.


class Word0070FindTests(WordTests):

    def setUp(self):
        super(Word0070FindTests, self).setUp()
        self.apple = self.lex.noun('apple')
        self.berry = self.lex.noun('berry')
        self.curry = self.lex.noun('curry')
        self.fuji = self.lex.define('apple', 'fuji')
        self.gala = self.lex.define('apple', 'gala')
        self.honeycrisp = self.lex.define('apple', 'honeycrisp')
        self.munch = self.lex.verb('munch')
        self.nibble = self.lex.verb('nibble')
        self.dirk = self.lex.define('agent', 'dirk')
        self.fred = self.lex.define('agent', 'fred')

        # WordFindTests's lex:
        #
        # 1 lex.define(verb, 1, 'define')
        # 2 lex.define(noun, 1, 'noun')
        # 3 lex.define(noun, 1, 'verb')
        # 4 lex.define(noun, 1, 'agent')
        # 5 lex.define(agent, 1, 'lex')
        # 6 lex.define(noun, 1, 'apple')
        # 7 lex.define(noun, 1, 'berry')
        # 8 lex.define(noun, 1, 'curry')
        # 9 lex.define(apple, 1, 'fuji')
        # 10 lex.define(apple, 1, 'gala')
        # 11 lex.define(apple, 1, 'honeycrisp')
        # 12 lex.define(verb, 1, 'munch')
        #                          nibble
        #                           dirk
        # 13 lex.define(agent, 1, 'fred')
        #
        # 13 ⋅ Word('lex')
        # 13 ⋅ Word('define')
        # 6 ⋅ Word('noun')
        # 3 ⋅ Word('apple')
        # 2 ⋅ Word('agent')
        # 2 ⋅ Word('verb')

    def test_find_obj(self):
        apple_words = self.lex.find_words(obj=self.apple.idn)
        self.assertEqual(3, len(apple_words))
        self.assertEqual(self.fuji, apple_words[0])
        self.assertEqual(self.gala, apple_words[1])
        self.assertEqual(self.honeycrisp, apple_words[2])
        self.assertEqual([self.fuji, self.gala, self.honeycrisp], apple_words)

    def test_find_obj_word(self):
        self.assertEqual([self.fuji, self.gala, self.honeycrisp], self.lex.find_words(obj=self.apple))

    def test_find_sbj(self):
        self.fred.says(self.munch, self.curry, qiki.Number(1), "Yummy.")
        fred_words = self.lex.find_words(sbj=self.fred.idn)
        self.assertEqual(1, len(fred_words))
        self.assertEqual("Yummy.", fred_words[0].txt)

    def test_find_sbj_word(self):
        fred_word = self.fred.says(self.munch, self.curry, qiki.Number(1), "Yummy.")
        self.assertEqual([fred_word], self.lex.find_words(sbj=self.fred))

    def test_find_vrb(self):
        self.fred.says(self.munch, self.curry, qiki.Number(1), "Yummy.")
        munch_words = self.lex.find_words(vrb=self.munch.idn)
        self.assertEqual(1, len(munch_words))
        self.assertEqual("Yummy.", munch_words[0].txt)

    def test_find_vrb_word(self):
        munch_word = self.fred.says(self.munch, self.curry, qiki.Number(1), "Yummy.")
        self.assertEqual([munch_word], self.lex.find_words(vrb=self.munch))

    def test_find_chronology(self):
        craving_apple = self.fred.says(self.munch, self.apple, qiki.Number(1))
        craving_berry = self.fred.says(self.munch, self.berry, qiki.Number(1))
        craving_curry = self.fred.says(self.munch, self.curry, qiki.Number(1))

        self.assertEqual([craving_apple, craving_berry, craving_curry], self.lex.find_words(sbj=self.fred))
        self.assertEqual([craving_apple, craving_berry, craving_curry], self.lex.find_words(vrb=self.munch))

    def test_find_empty(self):
        self.fred.says(self.munch, self.apple, qiki.Number(1))
        self.fred.says(self.munch, self.berry, qiki.Number(1))
        self.fred.says(self.munch, self.curry, qiki.Number(1))

        self.assertEqual([], self.lex.find_words(sbj=self.munch))
        self.assertEqual([], self.lex.find_words(vrb=self.fred))

    # def test_find_idns(self):
    #     idns = self.lex.find_idns()
    #     for idn in idns:
    #         self.assertIsInstance(idn, qiki.Number)

    def test_find_by_vrb(self):
        munch1 = self.fred.says(self.munch, self.apple, 1)
        munch2 = self.fred.says(self.munch, self.fuji, 10)
        munch3 = self.fred.says(self.munch, self.gala, 0.5)
        self.assertEqual([munch1, munch2, munch3], self.lex.find_words(vrb=self.munch))
        self.assertEqual([munch1, munch2, munch3], self.lex.find_words(vrb=self.munch.idn))
        # self.assertEqual([munch1.idn, munch2.idn, munch3.idn], self.lex.find_idns(vrb=self.munch))
        # self.assertEqual([munch1.idn, munch2.idn, munch3.idn], self.lex.find_idns(vrb=self.munch.idn))

    def test_find_by_vrb_list(self):
        c1 = self.fred.says(self.munch, self.apple, 1)
        c2 = self.fred.says(self.munch, self.fuji, 10)
        retch = self.lex.verb('retch')
        r3 = self.fred.says(retch, self.gala, -1)
        self.assertEqual([c1, c2    ], self.lex.find_words(vrb=[self.munch        ]))
        self.assertEqual([c1, c2, r3], self.lex.find_words(vrb=[self.munch,     retch    ]))
        self.assertEqual([c1, c2, r3], self.lex.find_words(vrb=[self.munch,     retch.idn]))
        self.assertEqual([c1, c2, r3], self.lex.find_words(vrb=[self.munch.idn, retch    ]))
        self.assertEqual([c1, c2, r3], self.lex.find_words(vrb=[self.munch.idn, retch.idn]))
        # self.assertEqual([c1.idn, c2.idn, r3.idn], self.lex.find_idns(vrb=[self.munch    , retch    ]))
        # self.assertEqual([c1.idn, c2.idn, r3.idn], self.lex.find_idns(vrb=[self.munch.idn, retch.idn]))
        # self.assertEqual([                r3.idn], self.lex.find_idns(vrb=[                retch.idn]))

    def test_find_by_txt(self):
        a = self.fred(self.munch, 1, "eat" )[self.apple]
        b = self.fred(self.munch, 1, "math")[self.berry]
        c = self.fred(self.munch, 1, "eat" )[self.curry]

        self.assertEqual([a, c], self.lex.find_words(vrb=self.munch, txt="eat"))
        self.assertEqual([b],    self.lex.find_words(vrb=self.munch, txt="math"))
        self.assertEqual([],     self.lex.find_words(vrb=self.munch, txt="neither"))

    def test_find_words(self):
        words = self.lex.find_words()
        for word in words:
            self.assertIsInstance(word, qiki.Word)

    # def test_find_idns_with_sql(self):
    #     idns = self.lex.find_idns(idn_order='ASC')
    #     self.assertLess(idns[0], idns[-1])
    #     idns = self.lex.find_idns(idn_order='DESC')
    #     self.assertGreater(idns[0], idns[-1])

    def test_find_words_sql(self):
        words = self.lex.find_words(idn_ascending=True)
        self.assertLess(words[0].idn, words[-1].idn)
        words = self.lex.find_words(idn_ascending=False)
        self.assertGreater(words[0].idn, words[-1].idn)

    def test_find_idn(self):
        lex_by_idn = self.lex.find_words(idn=qiki.LexSentence.IDN_LEX)
        self.assertEqual(1, len(lex_by_idn))
        self.assertEqual("lex", lex_by_idn[0].txt)

        # lex_by_idn = self.lex.find_idns(idn=qiki.LexSentence.IDN_LEX)
        # self.assertEqual(1, len(lex_by_idn))
        # self.assertEqual(self.lex._lex.idn, lex_by_idn[0])

    def test_find_idn_word(self):
        lex_by_idn = self.lex.find_words(idn=self.lex._lex)
        self.assertEqual(1, len(lex_by_idn))
        self.assertEqual("lex", lex_by_idn[0].txt)

        # lex_by_idn = self.lex.find_idns(idn=self.lex)
        # self.assertEqual(1, len(lex_by_idn))
        # self.assertEqual(self.lex._lex.idn, lex_by_idn[0])

    def test_find_idn_not(self):
        lex_by_idn = self.lex.find_words(idn=qiki.Number(-42))
        self.assertEqual(0, len(lex_by_idn))

    def test_find_last(self):
        w = self.lex.find_last(obj=self.lex['noun'])
        self.assertEqual(self.curry, w)

    def test_find_last_not(self):
        with self.assertRaises(qiki.Lex.NotFound):
            self.lex.find_last(obj=self.curry)

    def test_find_by_name(self):
        with self.assertNewWords(3):
            w1 = self.lex[self.fred](self.munch, num=11)[self.apple]
            w2 = self.lex[self.dirk](self.munch, num=22)[self.berry]
            w3 = self.lex[self.fred](self.nibble, num=33)[self.curry]

        self.assertEqual(set((w1,   w3,)), set(self.lex.find_words(sbj='fred')))
        self.assertEqual(set((w1,w2,w3,)), set(self.lex.find_words(sbj=('fred', 'dirk'))))
        self.assertEqual(set((w1,w2,   )), set(self.lex.find_words(vrb='munch')))
        self.assertEqual(set((w1,w2,w3,)), set(self.lex.find_words(vrb=('munch', 'nibble'))))
        self.assertEqual(set((   w2,   )), set(self.lex.find_words(obj='berry')))
        self.assertEqual(set((   w2,w3,)), set(self.lex.find_words(obj=('berry', 'curry'))))

        self.assertEqual(set((w1,w2,   )), set(self.lex.find_words(idn=(w1.idn, w2.idn))))
        self.assertEqual(
            set((self.fred, self.dirk, self.berry)),
            set(self.lex.find_words(txt=('fred', 'dirk', 'berry')))
        )


class Cop(object):
    """
    Control thread progress.

    Create a stopping point in one thread that the main thread can make go at a strategic time.
    """
    def __init__(self, description):
        """The lock starts off acquired by the main thread, so the sub-thread .stop() blocks."""
        super(Cop, self).__init__()
        self.description = description
        self.lock = threading.Lock()
        self.lock.acquire()
        self.is_stopped = False   # Are we stuck at the .stop() point?
        self.did_go = False   # Was .go() ever called?  Whether or not .stop() has been called.
        self.timeout = 1.0   # Default 1-second timeout.
        self._all_cops.append(self)

    _all_cops = []

    def stop(self):
        """A sub-thread stops as soon as it calls this."""
        self.is_stopped = True
        self.lock.acquire()
        self.is_stopped = False
        self.lock.release()

    def go(self):
        """Another thread (usually the main thread) un-stops the stopped thread."""
        self.lock.release()
        self.did_go = True


    class DidntStop(Exception):
        """.await_stop() timed out"""

    def await_stop(self, context):
        """Wait for a thread to get to its stopping point."""
        t_start = time.time()
        while True:
            time.sleep(0.0)
            t_elapsed = time.time() - t_start
            if t_elapsed > self.timeout:
                print("{context} {description}, never happened, {elapsed:.3f} sec timeout".format(
                    context=context,
                    description=self.description,
                    elapsed=t_elapsed,
                ))
                raise self.DidntStop(context)
            if self.is_stopped:
                print("{context} {description} after {elapsed:.3f} seconds".format(
                    context=context,
                    description=self.description,
                    elapsed=t_elapsed,
                ))
                return True

    @classmethod
    def let_go_all(cls):
        """Make all stopping points go.  Release all Cop instance locks."""
        for cop in cls._all_cops:
            if not cop.did_go:
                cop.go()


class Word0079Cop(TestBaseClass):
    def test_cop(self):
        """ Verify that Cop controls a thread. """
        # t_start = time.time()
        steps = []

        def step(number):
            steps.append(number)
            # print("test_cop step {number}. {delta:.3f}\n".format(
            #     number=number,
            #     delta=time.time() - t_start
            # ), end="")
            # EXAMPLE:
            #     test_cop step 1. 0.000
            #     test_cop step 2. 0.100
            #     test_cop step 3. 0.200
            #     test_cop step 4. 0.300
            #     test_cop step 5. 0.400

        class Traffic(threading.Thread):
            def __init__(self, this_cop):
                super(Traffic, self).__init__()
                self.cop = this_cop

            def run(self):
                step(2)
                self.cop.stop()   # Thread stops here, until main thread calls .go()
                step(4)

        cop = Cop("trial run")
        traffic = Traffic(cop)
        step(1)
        time.sleep(0.1)
        traffic.start()   # step 2
        time.sleep(0.1)
        step(3)
        time.sleep(0.1)
        cop.go()          # step 4
        time.sleep(0.1)
        step(5)
        self.assertEqual([1,2,3,4,5], steps)


def wait(seconds):
    print("Wait {:.1f} seconds.".format(seconds))


# noinspection PyPep8Naming
class Word0080Threading(TestBaseClass):

    class LexManipulated(qiki.LexMySQL):
        """A lex we can dissect word creation."""
        _credentials = secure.credentials.for_unit_testing_database.copy()
        # _credentials['engine'] = 'InnoDB'
        _credentials.pop('engine', None)
        _credentials['table'] += '_threading'

        def __init__(self, do_lock, do_start):
            super(Word0080Threading.LexManipulated, self).__init__(**self._credentials)
            # THANKS:  Nested class super(), https://stackoverflow.com/a/1825470/673991
            self.do_lock = do_lock
            self.do_start = do_start
            self.cop1 = Cop("ready to lock")
            self.cop2 = Cop("ready to start transaction")
            self.cop3 = Cop("idn has been assigned")

        class _NotALock(object):
            def __enter__(self):
                pass
            def __exit__(self, _, __, ___):
                pass

        def _lock_next_word(self):
            self.cop1.stop()
            if self.do_lock:
                return super(Word0080Threading.LexManipulated, self)._lock_next_word()
            else:
                return self._NotALock()

        def _start_transaction(self):
            self.cop2.stop()
            if self.do_start:
                super(Word0080Threading.LexManipulated, self)._start_transaction()
            else:
                print("Start transaction SHOULD happen, but it won't")

        # noinspection PyMethodMayBeStatic
        def _critical_moment_1(self):
            self.cop3.stop()

        # # noinspection PyMethodMayBeStatic
        # def _critical_moment_2(self):
        #     time.sleep(1)

    class ThreadCreatesNoun(threading.Thread):
        def __init__(self, txt, do_lock, do_start):
            super(Word0080Threading.ThreadCreatesNoun, self).__init__()
            self.txt = txt
            self.do_lock = do_lock
            self.do_start = do_start
            self.word = None
            self.lex = None
            self.did_crash = False

        def run(self):
            self.lex = Word0080Threading.LexManipulated(
                do_lock=self.do_lock,
                do_start=self.do_start
            )
            try:
                self.word = self.lex.noun(self.txt)
            except self.lex.QueryError:
                print("Crash on the {txt} thread!".format(
                    txt=self.txt,
                    # NOTE:  Unfortunately the duplicate idn is not accessible here to brag about,
                    #        because self.word was never assigned.
                ))
                self.did_crash = True
            else:
                print("Successful insert on the {txt} thread, idn = {idn}".format(
                    txt=self.txt,
                    idn=int(self.word.idn),
                ))
            finally:
                self.lex.disconnect()
                self.lex = None

        def await_connect(self):
            """This sub-thread has its own lex object.  Main thread waits for it to instantiate."""
            t_start = time.time()
            while self.lex is None:
                '''Better hope run() starts and then some Cop pauses it.  Else infinite loop.'''
            t_end = time.time()
            print("Connection for {txt} thread took {delta:.3f} seconds.\n".format(
                txt=self.txt,
                delta=t_end - t_start,
            ), end="")

    def test_01_simultaneous_insert(self):
        print("\nDouble-insert expected to work")
        self.simultaneous_insert(do_lock=True, do_start=True)

    def test_02_simultaneous_insert_broken_lock(self):
        print("\nLock broken, expect double-insert to crash")
        self.simultaneous_insert(do_lock=False, do_start=True)

    def test_03_simultaneous_insert_broken_start_transaction(self):
        print("\nStart transaction broken, expect double-insert to crash")
        self.simultaneous_insert(do_lock=True, do_start=False)

    def simultaneous_insert(self, do_lock, do_start):
        """
        Verify whether lock works when creating two new words "simultaneously."

        Even though the tea thread started first, coffee should get the first idn,
        because it was allowed to lock first.

        EXAMPLE:
            Double-insert expected to work
            ___step_1___
            Connection for tea thread took 0.085 seconds.
            tea 1 ready to lock after 0.001 seconds
            Wait 0.1 seconds.
            Connection for coffee thread took 0.125 seconds.
            coffee 1 ready to lock after 0.001 seconds
            ___step_2___
            coffee 2 ready to start transaction after 0.000 seconds
            ___step_3___
            Wait 0.1 seconds.
            ___step_4___
            coffee 4 idn has been assigned after 0.000 seconds
            ___step_5___
            Wait 0.1 seconds.
            ___step_6___
            Successful insert on the coffee thread, idn = 5
            ___step_7___
            tea 7 ready to start transaction after 0.000 seconds
            ___step_8___
            tea 8a idn has been assigned after 0.000 seconds
            Successful insert on the tea thread, idn = 6
            Simultaneous insert worked, coffee idn = 5 tea idn = 6

            Lock broken, expect double-insert to crash
            ___step_1___
            Connection for tea thread took 0.142 seconds.
            tea 1 ready to lock after 0.001 seconds
            Wait 0.1 seconds.
            Connection for coffee thread took 0.225 seconds.
            coffee 1 ready to lock after 0.001 seconds
            ___step_2___
            coffee 2 ready to start transaction after 0.000 seconds
            ___step_3___
            tea 3 ready to start transaction after 0.000 seconds
            ___step_4___
            coffee 4 idn has been assigned after 0.001 seconds
            ___step_5___
            Wait 0.1 seconds.
            tea 5 idn has been assigned after 0.001 seconds
            ___step_6___
            Successful insert on the coffee thread, idn = 5
            ___step_7___
            ___step_8___
            Crash on the tea thread!
            Simultaneous insert broke, coffee idn = 5 tea word is None

            Start transaction broken, expect double-insert to crash
            ___step_1___
            Connection for tea thread took 0.176 seconds.
            tea 1 ready to lock after 0.001 seconds
            Wait 0.1 seconds.
            Connection for coffee thread took 0.115 seconds.
            coffee 1 ready to lock after 0.001 seconds
            ___step_2___
            coffee 2 ready to start transaction after 0.000 seconds
            ___step_3___
            Wait 0.1 seconds.
            ___step_4___
            Start transaction SHOULD happen, but it won't
            coffee 4 idn has been assigned after 0.001 seconds
            ___step_5___
            Wait 0.1 seconds.
            ___step_6___
            Successful insert on the coffee thread, idn = 5
            ___step_7___
            tea 7 ready to start transaction after 0.000 seconds
            ___step_8___
            Start transaction SHOULD happen, but it won't
            tea 8b idn has been assigned after 0.001 seconds
            Crash on the tea thread!
            Simultaneous insert broke, coffee idn = 5 tea word is None
        """
        main_lex = Word0080Threading.LexManipulated(do_lock=True, do_start=True)
        main_lex.cop2.go()
        main_lex.uninstall_to_scratch()
        main_lex.install_from_scratch()
        is_lex_starting_out_empty = main_lex.max_idn() == main_lex.IDN_MAX_FIXED
        assert is_lex_starting_out_empty, "Unexpected " + main_lex.max_idn().qstring()

        max_idn_beforehand = main_lex.max_idn()
        # NOTE:  This USED to free future main_lex.max_idn() calls to have different values:
        #        main_lex._start_transaction()

        thread_tea    = self.ThreadCreatesNoun('tea',    do_lock=do_lock, do_start=do_start)
        thread_coffee = self.ThreadCreatesNoun('coffee', do_lock=do_lock, do_start=do_start)

        def step_1_start_both_threads_but_stop_before_either_locks():
            """That is, some Cop lock stops them, not a Word lock."""
            thread_tea.start()
            thread_tea.await_connect()
            thread_tea.lex.cop1.await_stop("tea 1")
            wait(0.1)
            thread_coffee.start()
            thread_coffee.await_connect()
            thread_coffee.lex.cop1.await_stop("coffee 1")

            self.assertIsNot(thread_tea.lex, thread_coffee.lex)
            self.assertIs   (thread_tea.lex._global_lock, thread_coffee.lex._global_lock)
            # NOTE:  Threads have different lex instances, but share a common lock.
            #        So it won't matter in step 3 which we check is .locked()

            self.assertEqual(max_idn_beforehand, thread_tea.lex.max_idn())
            self.assertEqual(max_idn_beforehand, thread_coffee.lex.max_idn())

        def step_2_let_the_coffee_thread_acquire_the_lock():
            thread_coffee.lex.cop1.go()
            thread_coffee.lex.cop2.await_stop("coffee 2")

            self.assertEqual(max_idn_beforehand, thread_tea.lex.max_idn())
            self.assertEqual(max_idn_beforehand, thread_coffee.lex.max_idn())

        def step_3_let_the_tea_thread_block_on_the_lock():
            thread_tea.lex.cop1.go()
            if do_lock:
                wait(0.1)
                self.assertFalse(thread_tea.lex.cop2.is_stopped)
                # NOTE:  So the tea thread is NOT stuck at cop2.stop().
                #        This means the tea thread has not called ._start_transaction() yet.
                #        Therefore it must be hung up on ._lock_next_word()
                #        As it should be, because the coffee thread acquired the lock.
                self.assertTrue(thread_tea.lex._global_lock.locked())
            else:
                thread_tea.lex.cop2.await_stop("tea 3")
                self.assertTrue(thread_tea.lex.cop2.is_stopped)
                # NOTE:  Because locking is deliberately broken,
                #        the tea thread proceeded to cop2, where it called ._start_transaction()
                #        though the transaction hasn't actually started yet.
                #        (Because LexManipulated._start_transaction() has
                #        yet to call LexMySQL._start_transaction().)

            self.assertEqual(max_idn_beforehand, thread_tea.lex.max_idn())
            self.assertEqual(max_idn_beforehand, thread_coffee.lex.max_idn())

        def step_4_let_the_coffee_thread_inch_ahead_to_where_its_got_max_idn():
            thread_coffee.lex.cop2.go()
            thread_coffee.lex.cop3.await_stop("coffee 4")

            self.assertEqual(max_idn_beforehand, thread_tea.lex.max_idn())
            self.assertEqual(max_idn_beforehand, thread_coffee.lex.max_idn())

        def step_5_tea_thread_should_be_locked():
            wait(0.1)
            if do_lock:
                self.assertFalse(thread_tea.lex.cop2.is_stopped)
            else:
                self.assertTrue(thread_tea.lex.cop2.is_stopped)
                thread_tea.lex.cop2.go()
                thread_tea.lex.cop3.await_stop("tea 5")
                # NOTE:  With locking broken, the tea thread goes all the way
                #        to where it gets an idn assigned.
                #        That's the same point where we've held up the coffee thread.
                #        So they should get the same idn.
                #        And whichever creates its word second will crash.

            self.assertEqual(max_idn_beforehand, main_lex.max_idn())
            self.assertEqual(max_idn_beforehand, thread_tea.lex.max_idn())
            self.assertEqual(max_idn_beforehand, thread_coffee.lex.max_idn())

        def step_6_let_the_coffee_thread_create_its_word_first():
            self.assertEqual(max_idn_beforehand, thread_tea.lex.max_idn())
            thread_coffee.lex.cop3.go()

            thread_coffee.join()

            self.assertIsNone(thread_coffee.lex)
            self.assertEqual(max_idn_beforehand, thread_tea.lex.max_idn())

            self.assertFalse(thread_coffee.did_crash)

        def step_7_now_tea_thread_should_proceed_to_just_before_start_transaction():
            if do_lock:
                thread_tea.lex.cop2.await_stop("tea 7")
                self.assertTrue(thread_tea.lex.cop2.is_stopped)
            else:
                self.assertTrue(thread_tea.lex.cop3.is_stopped)
                # NOTE:  Except if locks are deliberately broken,
                #        it has already gone past _start_transaction(),
                #        and moved on to where it's gotten an idn assigned.

        def step_8_let_the_tea_thread_create_its_word_second():
            if not do_lock:
                # NOTE:  LexManipulated._lock_next_word() was deliberately broken.
                #        So an unrestrained tea thread has already gotten its idn assigned,
                #        which is a fatal duplicate of the idn assigned to the coffee word.
                thread_tea.lex.cop3.go()
                thread_tea.join()                          # crash creating tea word, duplicate idn
                self.assertTrue(thread_tea.did_crash, "No lock - should have crashed")
            elif not do_start:
                # NOTE:  _lock_next_word() works, but _start_transaction() was deliberately broken.
                #        So the tea thread can't see the coffee thread's insert.
                self.assertEqual(max_idn_beforehand, thread_tea.lex.max_idn())
                self.assertTrue(thread_tea.lex.cop2.is_stopped)
                thread_tea.lex.cop2.go()
                thread_tea.lex.cop3.await_stop("tea 8b")
                thread_tea.lex.cop3.go()
                thread_tea.join()                          # tea word creation should crash, dup idn
                self.assertTrue(thread_tea.did_crash, "No start transaction - should have crashed")
            else:
                # NOTE:  Because locks are working, the tea thread will just now be getting its idn.
                self.assertTrue(thread_tea.lex.cop2.is_stopped)
                thread_tea.lex.cop2.go()
                thread_tea.lex.cop3.await_stop("tea 8a")
                thread_tea.lex.cop3.go()
                thread_tea.join()                          # tea word successfully created
                self.assertFalse(thread_tea.did_crash, "Should NOT have crashed")

        def s(n):
            print("___step_{}___\n".format(n), end="")

        try:
            s(1); step_1_start_both_threads_but_stop_before_either_locks()
            s(2); step_2_let_the_coffee_thread_acquire_the_lock()
            s(3); step_3_let_the_tea_thread_block_on_the_lock()
            s(4); step_4_let_the_coffee_thread_inch_ahead_to_where_its_got_max_idn()
            s(5); step_5_tea_thread_should_be_locked()
            s(6); step_6_let_the_coffee_thread_create_its_word_first()
            s(7); step_7_now_tea_thread_should_proceed_to_just_before_start_transaction()
            s(8); step_8_let_the_tea_thread_create_its_word_second()
        except Cop.DidntStop as e:
            self.fail("Cop didn't get to its stopping point: " + str(e))
        else:
            if do_lock and do_start:
                print(
                    "Simultaneous insert worked,",
                    thread_coffee.word.txt, "idn =", int(thread_coffee.word.idn),
                    thread_tea.word.txt,    "idn =", int(thread_tea.word.idn),
                )

                self.assertEqual(max_idn_beforehand + 1, thread_coffee.word.idn)
                self.assertEqual(max_idn_beforehand + 2, thread_tea.word.idn)

                self.assertEqual(max_idn_beforehand    , main_lex.max_idn())
                main_lex._start_transaction()
                self.assertEqual(max_idn_beforehand + 2, main_lex.max_idn())
            else:
                print(
                    "Simultaneous insert broke,",
                    thread_coffee.txt, "idn =", int(thread_coffee.word.idn),
                    thread_tea.txt, "word is", repr(thread_tea.word),
                )
                self.assertIsNone(thread_tea.word)
                self.assertEqual(max_idn_beforehand + 1, thread_coffee.word.idn)

                self.assertEqual(max_idn_beforehand    , main_lex.max_idn())
                main_lex._start_transaction()
                self.assertEqual(max_idn_beforehand + 1, main_lex.max_idn())
        finally:
            Cop.let_go_all()
            thread_tea.join()
            thread_coffee.join()
            main_lex.uninstall_to_scratch()
            main_lex.disconnect()


class WordQoolbarSetup(WordTests):

    def setUp(self):
        super(WordQoolbarSetup, self).setUp()

        self.qoolbar = qiki.QoolbarSimple(self.lex)
        self.qool = self.lex.verb('qool')
        self.iconify = self.lex.verb('iconify')
        self.like = self.lex.verb('like')
        self.delete = self.lex.verb('delete')

        # self.lex.says(self.qool, self.like, qiki.Number(1))
        # self.lex.says(self.qool, self.delete, qiki.Number(1))
        self.anna = self.lex.define('agent', 'anna')
        self.bart = self.lex.define('agent', 'bart')
        self.youtube = self.lex.noun('youtube')
        self.zigzags = self.lex.noun('zigzags')

        self.anna_like_youtube = self.anna.says(self.like, self.youtube, 1)
        self.bart_like_youtube = self.bart.says(self.like, self.youtube, 10)
        self.anna_like_zigzags = self.anna.says(self.like, self.zigzags, 2)
        self.bart_delete_zigzags = self.bart.says(self.delete, self.zigzags, 1)

        qool_declarations = self.lex.find_words(vrb=self.qool.idn)
        self.qool_idns = [w.obj.idn for w in qool_declarations]


class WordQoolbarTests(WordQoolbarSetup):

    def disable_test_lex_report(self):
        """
        lex_report <-- test_lex_report

        0 [lex](define, 'lex')[agent]
        1 [lex](define, 'define')[verb]
        2 [lex](define, 'noun')[noun]
        3 [lex](define, 'verb')[noun]
        4 [lex](define, 'agent')[noun]
        5 [lex](define, 'qool')[verb]
        6 [lex](define, 'iconify')[verb]
        7 [lex](define, 'delete')[verb]
        8 [lex](qool)[delete]
        9 [lex](iconify, 16, 'https://tool.qiki.info/icon/delete_16.png')[delete]
        10 [lex](define, 'like')[verb]
        11 [lex](qool)[like]
        12 [lex](iconify, 16, 'https://tool.qiki.info/icon/thumbsup_16.png')[like]
        13 [lex](define, 'anna')[agent]
        14 [lex](define, 'bart')[agent]
        15 [lex](define, 'youtube')[noun]
        16 [lex](define, 'zigzags')[noun]
        17 [anna](like)[youtube]
        18 [bart](like, 10)[youtube]
        19 [anna](like, 2)[zigzags]
        20 [bart](delete)[zigzags]

        17 ⋅ Word('lex')
        13 ⋅ Word('define')
        5 ⋅ Word('verb')
        5 ⋅ Word('noun')
        5 ⋅ Word('like')
        3 ⋅ Word('agent')
        3 ⋅ Word('delete')
        2 ⋅ Word('qool')
        2 ⋅ Word('iconify')
        2 ⋅ Word('anna')
        2 ⋅ Word('youtube')
        2 ⋅ Word('bart')
        2 ⋅ Word('zigzags')

        Mesa lexes
            None: LexMemory
        """
        self.lex_report()

    def test_get_all_qool_verbs(self):
        """Make sure the qool verbs were found."""
        self.assertEqual({self.like.idn, self.delete.idn}, set(self.qool_idns))

    def test_find_qool_verbed_words(self):
        """Find words with qool verbs."""
        qool_uses = self.lex.find_words(vrb=self.qool_idns)
        self.assertEqual(4, len(qool_uses))
        self.assertEqual(qool_uses[0].sbj, self.anna)
        self.assertEqual(qool_uses[1].sbj, self.bart)
        self.assertEqual(qool_uses[2].sbj, self.anna)
        self.assertEqual(qool_uses[3].sbj, self.bart)

    def test_find_qool_verbed_words_with_particular_object(self):
        """Find words with qool verbs and a specific object."""
        qool_uses = self.lex.find_words(vrb=self.qool_idns, obj=self.youtube)
        self.assertEqual(2, len(qool_uses))
        self.assertEqual(qool_uses[0].sbj, self.anna)
        self.assertEqual(qool_uses[0].num, qiki.Number(1))
        self.assertEqual(qool_uses[1].sbj, self.bart)
        self.assertEqual(qool_uses[1].num, qiki.Number(10))

    def test_find_qool_verbed_words_with_particular_subject(self):
        """Find words with qool verbs and a specific subject."""
        qool_uses = self.lex.find_words(vrb=self.qool_idns, sbj=self.bart)
        self.assertEqual(2, len(qool_uses))
        self.assertEqual(qool_uses[0].obj, self.youtube)
        self.assertEqual(qool_uses[0].num, qiki.Number(10))
        self.assertEqual(qool_uses[1].obj, self.zigzags)
        self.assertEqual(qool_uses[1].num, qiki.Number(1))

    def test_lex_from_idn(self):
        word = self.lex._lex.spawn()
        self.lex.populate_word_from_idn(word, self.zigzags.idn)
        self.assertEqual(self.zigzags.idn, word.idn)
        self.assertEqual(self.zigzags.sbj, word.sbj)
        self.assertEqual(self.zigzags.vrb, word.vrb)
        self.assertEqual(self.zigzags.obj, word.obj)
        self.assertEqual(self.zigzags.num, word.num)
        self.assertEqual(self.zigzags.txt, word.txt)
        self.assertEqual(self.zigzags.whn, word.whn)

    def test_lex_from_definition(self):
        word = self.lex._lex.spawn()
        self.lex.populate_word_from_definition(word, self.zigzags.txt)
        self.assertEqual(self.zigzags.idn, word.idn)
        self.assertEqual(self.zigzags.sbj, word.sbj)
        self.assertEqual(self.zigzags.vrb, word.vrb)
        self.assertEqual(self.zigzags.obj, word.obj)
        self.assertEqual(self.zigzags.num, word.num)
        self.assertEqual(self.zigzags.txt, word.txt)
        self.assertEqual(self.zigzags.whn, word.whn)

    def test_lex_from_sbj_vrb_obj_idns(self):
        word = self.lex._lex.spawn()
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
        word = self.lex._lex.spawn()
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
        word = self.lex._lex.spawn()
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
        word = self.lex._lex.spawn()
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

    def test_find_words(self):
        nouns = self.lex.find_words(obj=self.lex.noun())
        self.assertEqual(5, len(nouns))
        self.assertEqual('noun', nouns[0].txt)
        self.assertEqual('verb', nouns[1].txt)
        self.assertEqual('agent', nouns[2].txt)
        self.assertEqual('youtube', nouns[3].txt)
        self.assertEqual('zigzags', nouns[4].txt)

    def test_find_words_jbo(self):
        nouns = self.lex.find_words(obj=self.lex.noun(), jbo_vrb=self.qool_idns)
        self.assertEqual([
            'noun',
            'verb',
            'agent',
            'youtube',
            'zigzags',
        ], [noun.txt for noun in nouns])

        self.assertEqual([], nouns[0].jbo)
        self.assertEqual([], nouns[1].jbo)
        self.assertEqual([], nouns[2].jbo)
        self.assertEqual([self.anna_like_youtube, self.bart_like_youtube], nouns[3].jbo)
        self.assertEqual([self.anna_like_zigzags, self.bart_delete_zigzags], nouns[4].jbo)

        self.assertIsInstance(nouns[4].jbo[0].num, qiki.Number)
        self.assertIsInstance(nouns[4].jbo[0].txt, qiki.Text)   # (This was broken once.)

    def test_find_words_jbo_inner(self):
        nouns = self.lex.find_words(obj=self.lex.noun(), jbo_vrb=self.qool_idns, jbo_strictly=True)
        self.assertEqual([
            'youtube',
            'zigzags',
        ], [noun.txt for noun in nouns])

        self.assertEqual([self.anna_like_youtube, self.bart_like_youtube], nouns[0].jbo)
        self.assertEqual([self.anna_like_zigzags, self.bart_delete_zigzags], nouns[1].jbo)

    def test_jbo_single_verb_word(self):
        deleted_things = self.lex.find_words(jbo_vrb=self.delete, jbo_strictly=True)
        self.assertEqual({
            'zigzags'
        }, {thing.txt for thing in deleted_things})

    def test_jbo_single_verb_idn(self):
        deleted_things = self.lex.find_words(jbo_vrb=self.delete.idn, jbo_strictly=True)
        self.assertEqual({
            'zigzags'
        }, {thing.txt for thing in deleted_things})

    def test_jbo_two_verbs(self):
        """jbo_vrb specifying multiple words and/or idns"""
        deleted_and_qooled = self.lex.find_words(jbo_vrb=[self.delete, self.qool.idn], jbo_strictly=True)
        self.assertEqual({
            'delete',
            'like',
            'zigzags',
        }, {thing.txt for thing in deleted_and_qooled})

        deleted_and_qooled = self.lex.find_words(jbo_vrb=[self.delete.idn, self.like], jbo_strictly=True)
        self.assertEqual({
            'youtube',
            'zigzags',
        }, {thing.txt for thing in deleted_and_qooled})

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

    def test_qoolbar_verbs(self):
        verbs = list(self.qoolbar.get_verbs())
        self.assertEqual({self.like, self.delete}, set(verbs))

    def test_qoolbar_verb_dicts(self):
        verb_dicts = list(self.qoolbar.get_verb_dicts())
        self.assertEqual({
            self.like.idn.qstring(),
            self.delete.idn.qstring()
        }, {d['idn'] for d in verb_dicts})
        self.assertEqual({
            self.like.txt,
            self.delete.txt
        }, {d['name'] for d in verb_dicts})

    def test_qoolbar_verbs_qool_iconify(self):
        """Verbs that are qool and iconified show up in the qoolbar."""
        bleep = self.lex.verb('bleep')
        self.lex._lex(self.qool)[bleep] = 1
        self.lex._lex(self.iconify)[bleep] = 'https://example.com/bleep.png'

        verbs = self.qoolbar.get_verbs()
        self.assertEqual({self.lex['like'], self.lex['delete'], self.lex['bleep']}, set(verbs))

    def test_qoolbar_verbs_qool_without_iconify(self):
        """Verbs only need to be qool to show up in the qoolbar."""
        bleep = self.lex.verb('bleep')
        self.lex._lex(self.qool)[bleep] = 1

        verbs = self.qoolbar.get_verbs()
        self.assertEqual({self.lex['like'], self.lex['delete'], self.lex['bleep']}, set(verbs))

    def test_qoolbar_verbs_iconify_without_qool(self):
        """Iconified verbs aren't necessarily qool."""
        bleep = self.lex.verb('bleep')
        self.lex._lex(self.iconify)[bleep] = 'https://example.com/bleep.png'

        verbs = self.qoolbar.get_verbs()
        self.assertEqual({self.lex['like'], self.lex['delete']}, set(verbs))

    def test_qoolbar_verbs_one_more(self):
        bleep = self.lex.verb('bleep')
        self.lex._lex(self.qool)[bleep] = 1
        self.lex._lex(self.iconify)[bleep] = 'https://example.com/bleep.png'

        verbs = self.qoolbar.get_verbs()
        self.assertEqual({self.lex['like'], self.lex['delete'], self.lex['bleep']}, set(verbs))

    # def test_nums(self):
    #     nums = self.qoolbar.nums(self.youtube)
    #     self.assertEqual({
    #         self.like: {
    #             self.anna: {'num': qiki.Number(1)},
    #             self.bart: {'num': qiki.Number(10)},
    #         }
    #     }, nums)

    def test_qoolbar_verb_started_off_deleted(self):
        bleep = self.lex.verb('bleep')
        with self.assertNewWord():
            self.lex._lex(self.qool)[bleep] = 0

        verbs = self.qoolbar.get_verbs()
        self.assertEqual({self.lex['like'], self.lex['delete'], self.lex['bleep']}, set(verbs))

        non_deleted_verbs = {v for v in verbs if v.qool_num != 0}
        self.assertEqual({self.lex['like'], self.lex['delete']}, set(non_deleted_verbs))

    def test_qoolbar_verb_later_deleted(self):
        bleep = self.lex.verb('bleep')
        with self.assertNewWord():
            self.lex._lex(self.qool)[bleep] = 1
        with self.assertNewWord():
            self.lex._lex(self.qool)[bleep] = 0

        verbs = self.qoolbar.get_verbs()
        self.assertEqual({self.lex['like'], self.lex['delete'], self.lex['bleep']}, set(verbs))

        non_deleted_verbs = {v for v in verbs if v.qool_num != 0}
        self.assertEqual({self.lex['like'], self.lex['delete']}, set(non_deleted_verbs))

    def test_qoolbar_verb_undeleted(self):
        bleep = self.lex.verb('bleep')
        with self.assertNewWord():
            self.lex._lex(self.qool)[bleep] = 1
        with self.assertNewWord():
            self.lex._lex(self.qool)[bleep] = 0
        with self.assertNewWord():
            self.lex._lex(self.qool)[bleep] = 1

        verbs = self.qoolbar.get_verbs()
        self.assertEqual({self.lex['like'], self.lex['delete'], self.lex['bleep']}, set(verbs))

    def test_qoolbar_jbo(self):
        self.assertFalse(hasattr(self.youtube, 'jbo'))
        youtube_words = self.lex.find_words(idn=self.youtube, jbo_vrb=self.qoolbar.get_verbs())
        self.assertFalse(hasattr(self.youtube, 'jbo'))

        youtube_word = youtube_words[0]
        youtube_jbo = youtube_word.jbo

        self.assertEqual({self.anna_like_youtube, self.bart_like_youtube}, set(youtube_jbo))

        self.assertEqual(self.youtube, youtube_word)
        self.assertIsNot(self.youtube, youtube_word, "Whoa, youtube is a singleton.")

    def test_lex_jbo(self):
        """
        Test for the find_words() jbo lex bug.

        find_words() returns a list of words.  The jbo_vrb parameter makes each of those words contain
        a jbo property, a list of words whose object is each found word.
        This tests for a bug where the self.lex singleton object gets a jbo stuck on it
        as a side effect.
        """
        self.anna(self.like)[self.lex._lex] = 1,"strangely enough"
        self.bart(self.like)[self.lex._lex] = -1,"not really at all"
        # print("Lex members", self.lex.__dict__)
        # EXAMPLE:
        #     Lex members {'lex': Word('lex'), '_idn': Number('0q80'), 'words': [Word('lex'), Word('define'),
        #     Word('noun'), Word('verb'), Word('agent'), Word('qool'), Word('iconify'), Word('delete'), Word(8),
        #     Word(9), Word('like'), Word(11), Word(12), Word('anna'), Word('bart'), Word('youtube'),
        #     Word('zigzags'), Word(17), Word(18), Word(19), Word(20), Word(21), Word(22)], '_exists': True,
        #     '_fields': {'sbj': Word('lex'), 'vrb': Word('define'), 'obj': Word('agent'),
        #     'num': Number('0q82_01'), 'txt': 'lex', 'whn': Number('0q85_5B494F5CFC3758')},
        #     '_noun': Word('noun'), '_verb': Word('verb')}
        self.assertFalse(hasattr(self.lex, 'jbo'))
        lex_words = self.lex.find_words(idn=self.lex._lex, jbo_vrb=[self.like])
        self.assertEqual(
            {
                self.anna(self.like)[self.lex._lex],
                self.bart(self.like)[self.lex._lex]
            },
            set(lex_words[0].jbo)
        )
        self.assertFalse(hasattr(self.lex, 'jbo'), "Whoops, lex has a .jbo property!?!")

    def test_lex_singleton_found(self):
        lexes_found = self.lex.find_words(idn=self.lex._lex)
        self.assertEqual(1, len(lexes_found))
        lex_found = lexes_found[0]
        self.assertEqual(self.lex._lex.idn, lex_found.idn)
        self.assertEqual(self.lex._lex, lex_found)
        self.assertIsNot(self.lex._lex, lex_found, "Whoa, lex returned by find_words() is a singleton.")


class WordSuperSelectTest(WordQoolbarSetup):

    def __init__(self, *args, **kwargs):
        super(WordSuperSelectTest, self).__init__(*args, **kwargs)
        self.only_sql_flavors()

    def test_lex_table_not_writable(self):
        with self.assertRaises(AttributeError):
            # noinspection PyPropertyAccess
            self.lex.table = 'something'

    def test_super_select_idn(self):
        self.assertEqual([{'txt': 'define'},], list(self.lex.super_select(
            'SELECT txt FROM',
            self.lex.table,
            'WHERE idn =',
            qiki.LexSentence.IDN_DEFINE
        )))

    def test_super_select_word(self):
        define_word = self.lex['define']
        self.assertEqual([{'txt': 'define'},], list(self.lex.super_select(
            'SELECT txt FROM',
            self.lex.table,
            'WHERE idn =',
            define_word
            # NOTE:  Sad, so sad, this conversion can't be automagic.
        )))

    def test_super_select_txt(self):
        self.assertEqual([{'idn': qiki.LexSentence.IDN_DEFINE},], list(self.lex.super_select(
            'SELECT idn FROM',
            self.lex.table,
            'WHERE txt =',
            qiki.Text('define')
        )))

    def test_super_select_with_none(self):
        """To concatenate two strings of literal SQL code, intersperse a None."""
        self.assertEqual([{'txt': 'define'}], list(self.lex.super_select(
            'SELECT txt', None, 'FROM',
            self.lex.table,
            'WHERE', None, 'idn =',
            qiki.LexSentence.IDN_DEFINE
        )))

    def test_super_select_string_concatenate_alternatives(self):
        """Showcase of all the valid ways one might concatenate strings with super_select().

        That is, strings that make up SQL.  Not the content of fields, e.g. txt."""
        def good_super_select(*args):
            self.assertEqual([{'txt':'define'}], list(self.lex.super_select(*args)))

        def bad_super_select(*args):
            with self.assertRaises(qiki.LexMySQL.SuperSelectStringString):
                list(self.lex.super_select(*args))
        txt = 'txt'

        good_super_select('SELECT          txt          FROM', self.lex.table, 'WHERE idn=',qiki.LexSentence.IDN_DEFINE)
        good_super_select('SELECT '       'txt'       ' FROM', self.lex.table, 'WHERE idn=',qiki.LexSentence.IDN_DEFINE)
        good_super_select('SELECT '   +   'txt'   +   ' FROM', self.lex.table, 'WHERE idn=',qiki.LexSentence.IDN_DEFINE)
        good_super_select('SELECT', None, 'txt', None, 'FROM', self.lex.table, 'WHERE idn=',qiki.LexSentence.IDN_DEFINE)
        good_super_select('SELECT '   +    txt    +   ' FROM', self.lex.table, 'WHERE idn=',qiki.LexSentence.IDN_DEFINE)
        good_super_select('SELECT', None,  txt , None, 'FROM', self.lex.table, 'WHERE idn=',qiki.LexSentence.IDN_DEFINE)

        bad_super_select( 'SELECT',       'txt',       'FROM', self.lex.table, 'WHERE idn=',qiki.LexSentence.IDN_DEFINE)
        bad_super_select( 'SELECT',        txt ,       'FROM', self.lex.table, 'WHERE idn=',qiki.LexSentence.IDN_DEFINE)

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
        self.lex.super_select('SELECT * FROM', self.lex.table, 'WHERE txt=', qiki.Text('define'))

    def test_super_select_null(self):
        self.assertEqual([{'x': None}], list(self.lex.super_select('SELECT NULL as x')))
        self.assertEqual([{'x': None}], list(self.lex.super_select('SELECT', None, 'NULL as x')))

    def test_super_select_type_error(self):
        class ExoticType(object):
            pass

        with self.assertRaises(qiki.LexMySQL.SuperSelectTypeError):
            list(self.lex.super_select(ExoticType))

    def test_super_select_idn_list(self):
        anna_and_bart = list(self.lex.super_select(
            'SELECT txt FROM', self.lex.table,
            'WHERE idn IN (', [
                self.anna.idn,
                self.bart.idn
            ], ')'
        ))
        self.assertEqual([
            {'txt': 'anna'},
            {'txt': 'bart'},
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
            {'txt': 'anna'},
            {'txt': 'bart'},
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
            {'txt': 'anna'},
            {'txt': 'bart'},
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
            {'txt': 'anna'},
            {'txt': 'bart'},
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
            {'txt': 'anna'},
            {'txt': 'bart'},
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
            {'txt': 'anna'},
            {'txt': 'bart'},
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
            {'txt': 'anna'},
            {'txt': 'bart'},
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






class WordInternalTests(WordTests):

    def test_is_iterable_basic_types(self):
        self.assertTrue(is_iterable([]))
        self.assertTrue(is_iterable(()))
        self.assertTrue(is_iterable({}))
        self.assertTrue(is_iterable(set()))
        self.assertTrue(is_iterable(dict()))
        self.assertTrue(is_iterable(range(10)))
        self.assertTrue(is_iterable(bytearray()))

        self.assertFalse(is_iterable(None))
        self.assertFalse(is_iterable(Ellipsis))
        self.assertFalse(is_iterable(NotImplemented))
        self.assertFalse(is_iterable(Exception))
        self.assertFalse(is_iterable(True))
        self.assertFalse(is_iterable(str()))
        self.assertFalse(is_iterable(''))
        self.assertFalse(is_iterable(''))
        self.assertFalse(is_iterable(1))
        self.assertFalse(is_iterable(1.0))
        self.assertFalse(is_iterable(1.0 + 2.0j))

    # noinspection PyArgumentList
    def test_is_iterable_ambiguous(self):
        """is_iterable() is ambiguous about byte-strings -- Python 3 yes, Python 2 no."""
        if six.PY2:
            self.assertFalse(is_iterable(b'abc'))
            self.assertFalse(is_iterable(bytes('abc')))

            assert bytes is str
            self.assertEqual('a', bytes('abc')[0])
            self.assertIs(str, type(bytes('abc')[0]))
        else:
            self.assertTrue(is_iterable(b'abc'))
            self.assertTrue(is_iterable(bytes('abc', 'ascii')))
            # XXX:  These should be False in Python 3.

            assert bytes is not str
            self.assertEqual(97, bytes('abc', 'ascii')[0])
            self.assertIs(int, type(bytes('abc', 'ascii')[0]))

    def test_is_iterable_classes(self):
        self.assertFalse(is_iterable(object))
        self.assertFalse(is_iterable(object()))

        class OldStyleClass:
            def __init__(self):
                pass

        class NewStyleClass(object):
            pass

        self.assertFalse(is_iterable(OldStyleClass))
        self.assertFalse(is_iterable(NewStyleClass))

        old_style_instance = OldStyleClass()
        new_style_instance = NewStyleClass()
        self.assertFalse(is_iterable(old_style_instance))
        self.assertFalse(is_iterable(new_style_instance))

    def test_is_iterable_generator_function(self):

        def regular_function():
            return 0

        def generator_function():
            yield 0

        self.assertFalse(is_iterable(regular_function))
        self.assertFalse(is_iterable(generator_function))
        self.assertFalse(is_iterable(regular_function()))

        self.assertTrue(is_iterable(generator_function()))

        self.assertEqual('generator', type(generator_function()).__name__)

    def test_is_iterable_generator_expression(self):
        self.assertTrue(is_iterable((i for i in (1,2,3,4) if i % 2)))

        self.assertEqual('generator', type((i for i in (1,2,3,4) if i % 2)).__name__)

    def test_is_iterable_comprehension(self):
        self.assertTrue(is_iterable([i   for i in (1,2,3,4)]))
        self.assertTrue(is_iterable({i   for i in (1,2,3,4)}))
        self.assertTrue(is_iterable({i:i for i in (1,2,3,4)}))

        self.assertIs(list, type([i   for i in (1,2,3,4)]))
        self.assertIs(set,  type({i   for i in (1,2,3,4)}))
        self.assertIs(dict, type({i:i for i in (1,2,3,4)}))

    def test_is_iterable_by_next(self):
        # THANKS:  Iterative object, http://stackoverflow.com/a/7542261/673991

        class IteratorByNext:

            def __init__(self, some_list):
                self.some_list = some_list
                self.index = 0

            def __iter__(self):
                return self

            def __next__(self):
                try:
                    result = self.some_list[self.index]
                except IndexError:
                    raise StopIteration
                else:
                    self.index += 1
                    return result

            next = __next__
        self.assertEqual([1,2,3], list(IteratorByNext([1,2,3])))

        self.assertTrue(is_iterable(IteratorByNext([1,2,3])))

        self.assertEqual(py23(b'instance', 'IteratorByNext'), type(IteratorByNext([1,2,3])).__name__)

    def test_is_iterable_by_getitem(self):
        # THANKS:  Iterative object, http://stackoverflow.com/a/7542261/673991

        class IteratorByGetItem:

            def __init__(self, some_list):
                self.some_list = some_list

            def __getitem__(self, index):
                return self.some_list[index]

        self.assertEqual([1,2,3], list(IteratorByGetItem([1,2,3])))

        self.assertTrue(is_iterable(IteratorByGetItem([1,2,3])))

        self.assertEqual(py23(b'instance', 'IteratorByGetItem'), type(IteratorByGetItem([1,2,3])).__name__)

    def test_word_presentable(self):
        self.assertEqual("42", qiki.Word.presentable(qiki.Number(42)))
        self.assertEqual("4.75", qiki.Word.presentable(qiki.Number(4.75)))
        self.assertEqual("0q82_2A__7E0100", qiki.Word.presentable(qiki.Number(
            42,
            qiki.Suffix(qiki.Suffix.Type.TEST)
        )))
        self.assertEqual("0qFF_81", qiki.Word.presentable(qiki.Number.POSITIVE_INFINITY))
        self.assertEqual("0q00_7F", qiki.Word.presentable(qiki.Number.NEGATIVE_INFINITY))
        self.assertEqual("0q", qiki.Word.presentable(qiki.Number.NAN))

    def test_lex(self):
        self.assertFalse(is_iterable(self.lex))
        self.assertFalse(is_iterable(self.lex[self.lex]))


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
    #     class UnExpected(object):
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


def py23(if2, if3_or_greater):
    """
    Python-2-specific value.  Versus Python-3-or-later-specific value.

    Sensibly returns a value that stands a reasonable chance of not breaking on Python 4,
    if there ever is such a thing.  That is, assumes Python 4 will be more like 3 than 2.
    SEE:  https://astrofrog.github.io/blog/2016/01/12/stop-writing-python-4-incompatible-code/
    """
    if six.PY2:
        return if2
    else:
        return if3_or_greater


class SomeType(object):
    pass
some_type = SomeType()


if __name__ == '__main__':
    # NOTE:  PyCharm Unittests doesn't run this part
    import unittest

    unittest.main(verbosity=2)
    # NOTE:  Most verbose level 2, https://stackoverflow.com/a/1322648/673991


# TODO:  Convert to pytest, https://docs.pytest.org/en/latest/getting-started.html#grouping-multiple-tests-in-a-class
