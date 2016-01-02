"""
A qiki Word is defined by a three-word subject-verb-object
"""

from __future__ import print_function
import re
import time

import mysql.connector
import six

from qiki import Number


@six.python_2_unicode_compatible
class Word(object):
    """
    A qiki Word is a subject-verb-object triplet of other words (sbj, vrb, obj).

    A word is identified by a qiki Number (idn).
    A word may be elaborated by a Number (num) and a string (txt).
    A word remembers the time it was created (whn).

    Each of these seven components of a word has a 3-letter symbol.
    (idn, sbj, vrb, obj, num, txt, whn)
    This helps a little in searching for the symbol, and avoiding Python reserved words.

    A word is fundamentally, uniquely, and forever defined by its idn,
    within the context of its Lex,
    as long as it has been saved (exists is true).

    :type content: six.string_types | Word | instancemethod

    :type sbj: Number | Word
    :type vrb: Number | instancemethod
    :type obj: Number | Word
    :type num: Number
    :type txt: six.string_types or six.binary_type, in other words:
               unicode or str (utf8) in Python 2, e.g. u'noun' or 'noun'
               str or bytes (utf8) in Python 3, e.g. 'noun' or b'noun'
    :type lex: Word

    Note:  instantiation.txt is always Unicode
    """

    def __init__(self, content=None, sbj=None, vrb=None, obj=None, num=None, txt=None, lex=None):
        self.lex = lex
        self.exists = False
        self._idn = None
        self._word_before_the_dot = None
        if isinstance(content, self.TXT_TYPES):
            # e.g. Word('agent')
            # assert isinstance(self._connection, mysql.connector.MySQLConnection), "Not connected."
            self._from_definition(content)
        elif isinstance(content, Number):
            # Word(idn)
            # assert isinstance(self._connection, mysql.connector.MySQLConnection), "Not connected."
            self._from_idn(content)
            assert self.exists
        elif isinstance(content, type(self)):
            # Word(some_other_word)
            # assert isinstance(self._connection, mysql.connector.MySQLConnection), "Not connected."
            self._from_word(content)
        elif content is None:
            # Word(sbj=s, vrb=v, obj=o, num=n, txt=t)
            # TODO:  If this is only used via spawn(), then move this code there somehow?
            self.sbj = sbj
            self.vrb = vrb
            self.obj = obj
            self.num = num
            if isinstance(txt, (six.text_type, type(None))):
                self.txt = txt
            else:
                self.txt = six.text_type(txt.decode('utf-8'))
        else:
            typename = type(content).__name__
            if typename == 'instance':
                typename = content.__class__.__name__
            # raise TypeError('Word(%s) is not supported' % typename)
            raise TypeError("{outer}({inner}) is not supported".format(
                outer=type(self).__name__,
                inner=typename,
            ))

    _ID_DEFINE = Number(1)
    _ID_NOUN   = Number(2)
    _ID_VERB   = Number(3)
    _ID_AGENT  = Number(4)
    _ID_LEX    = Number(5)

    _ID_MAX_FIXED = Number(5)

    TXT_TYPES = (six.string_types, six.binary_type)

    def __getattr__(self, noun_txt):
        assert hasattr(self, 'lex'), "No lex, can't x.{noun}".format(noun=noun_txt)
        return_value = self.lex(noun_txt)
        # FIXME:  catch NotExist: raise NoSuchAttribute (a gross internal error)
        return_value._word_before_the_dot = self   # In s.v(o) this is how v remembers the s.
        return return_value

    def __call__(self, *args, **kwargs):
        if self.is_lex():   # Get a word by its text:  lex(t)  e.g.  lex('anna')
            # lex(t) in English:  Lex defines a word named t.
            # lex('text') - find a word by its txt
            existing_word = self.spawn(*args, **kwargs)
            # FIXME:  if not exists: raise NotExist
            assert existing_word.exists, "{word} has no property {name}".format(
                word=repr(self),
                name=repr(args[0]),
            )
            if existing_word.idn == self.idn:
                return self   # lex is a singleton.  Why is this important?
            else:
                return existing_word
        elif self.is_a_verb(reflexive=False):   # Quintessential word creation:  s.v(o)  e.g. anna.like(bart)
            # (But not s.verb(o) -- the 'verb' word is not a verb.)
            assert hasattr(self, 'lex')
            assert self.lex.exists
            assert self.lex.is_lex()

            # TODO:  s.v(o,t)
            # TODO:  s.v(o,t,n)
            # DONE:  s.v(o)
            # DONE:  s.v(o,n)
            # DONE:  s.v(o,n,t)
            # DONE:  o(t) -- shorthand for lex.define(o,1,t)
            # DONE:  x = s.v; x(o...) -- s.v(o...) with an intermediate variable
            # TODO:  Disallow s.v(o,t,n,etc)

            # TODO:  Avoid ambiguity of s.v(o, '0q80', '0q82_01') -- which is txt, which is num?
            # TODO:  Disallow positional n,t?  Keyword-only num=n,txt=t would have flexible order.
            # SEE:  https://www.python.org/dev/peps/pep-3102/
            # SEE:  http://code.activestate.com/recipes/577940-emulate-keyword-only-arguments-in-python-2/
            # TODO:  Keyword arguments would look like:
            # TODO:  s.v(o,num=n)
            # TODO:  s.v(o,txt=t)
            # TODO:  s.v(o,num=n,txt=t)
            # TODO:  s.v(o,txt=t,num=n)
            # TODO:  v(o,n,t) -- lex is the implicit subject

            assert len(args) >= 1
            obj = args[0]
            try:
                num = Number(args[1])
            except IndexError:
                num = Number(1)
            try:
                txt = args[2]
            except IndexError:
                txt=''
            assert self._word_before_the_dot is not None, "A verb can't (yet) be called without a preceding subject."
            # TODO:  allow  v(t)?  In English:  Lex defines a v named t.  And v is a verb.
            if len(args) == 1:   # subject.verb(object) <-- getter only
                existing_word = self.spawn(sbj=self._word_before_the_dot.idn, vrb=self.idn, obj=obj.idn)
                existing_word._from_sbj_vrb_obj()
                assert existing_word.exists, "The form subject.verb(object) is a getter, not a setter."
            else:   # subject.verb(object, number)        \ <-- these are getter or setter
                    # subject.verb(object, number, text)  /
                if kwargs.get('use_already', False):
                    existing_word = self.spawn(
                        sbj=self._word_before_the_dot.idn,
                        vrb=self.idn,
                        obj=obj.idn,
                        num=num,
                        txt=txt,
                    )
                    existing_word._from_sbj_vrb_obj_num_txt()
                    if not existing_word.exists:
                        existing_word = self.sentence(
                            sbj=self._word_before_the_dot,
                            vrb=self,
                            obj=obj,
                            num=num,
                            txt=txt,
                        )
                else:
                    existing_word = self.sentence(
                        sbj=self._word_before_the_dot,
                        vrb=self,
                        obj=obj,
                        num=num,
                        txt=txt,
                    )
            self._word_before_the_dot = None   # TODO:  This enforced SOME single use, but is it enough?
            # EXAMPLE:  Should the following work??  x = s.v; x(o)
            return existing_word
        elif self.is_defined():   # Implicit define, e.g.  beth = lex.agent('beth'); like = lex.verb('like')
            # o(t) in English:  Lex defines an o named t.  And o is a noun.
            # object('text') ==> lex.define(object, Number(1), 'text')
            assert hasattr(self, 'lex')
            assert self.lex.exists
            assert self.lex.is_lex()
            existing_or_new_word = self.lex.define(self, *args, **kwargs)
            return existing_or_new_word
        else:
            raise self.NonVerbUndefinedAsFunctionException(
                "Word {idn} cannot be used as a function -- it's neither a verb nor a definition.".format(
                    idn=int(self.idn)
                )
            )

    def define(self, obj, txt, num=Number(1)):
        possibly_existing_word = self.spawn(txt)
        # How to handle "duplications"
        # TODO:  Shouldn't this be spawn(sbj=lex, vrb=define, txt)?
        # TODO:  use_already option?
        # But why would anyone want to duplicate a definition with the same txt and num?
        if possibly_existing_word.exists:
            return possibly_existing_word
        new_word = self.sentence(sbj=self, vrb=self.lex('define'), obj=obj, txt=txt, num=num)
        return new_word

    def spawn(self, *args, **kwargs):
        """
        Construct a Word() using the same lex as another word.

        The constructed word may exist in the database already.
        Otherwise it will be prepared to .save().
        """
        assert hasattr(self, 'lex')
        kwargs['lex'] = self.lex
        return Word(*args, **kwargs)

    def sentence(self, sbj, vrb, obj, txt, num):
        """
        Construct a new sentence from a 3-word subject-verb-object.

        Differences between Word.sentence() and Word.spawn():
            sentence takes a Word-triple, spawn takes an idn-triple.
            sentence saves the new word.
            spawn can take in idn or other ways to indicate an existing word.
        Differences between Word.sentence() and Word.define():
            sentence takes a Word-triple,
            define takes only one word for the object (sbj and vrb are implied)
            sentence requires an explicit num, define defaults to 1

        """
        # TODO:  Move use_already option to here, from __call__()?
        # Then define() could just call sentence() without checking spawn() first?
        # Only callers to sentence() are __call__() and define().
        assert isinstance(sbj, Word),           "sbj cannot be a {type}".format(type=type(sbj).__name__)
        assert isinstance(vrb, Word),           "vrb cannot be a {type}".format(type=type(vrb).__name__)
        assert isinstance(obj, Word),           "obj cannot be a {type}".format(type=type(obj).__name__)
        assert isinstance(txt, self.TXT_TYPES), "txt cannot be a {type}".format(type=type(txt).__name__)
        assert isinstance(num, Number),         "num cannot be a {type}".format(type=type(num).__name__)
        new_word = self.spawn(sbj=sbj.idn, vrb=vrb.idn, obj=obj.idn, num=num, txt=txt)
        new_word.save()
        return new_word

    class MissingFromLex(Exception):
        pass

    def _from_idn(self, idn):
        """
        Construct a Word from its idn.

        :type idn: Number
        """
        assert isinstance(idn, Number)
        if idn.is_suffixed():
            listed_instance = Listing.word_lookup(idn)
            self.txt = listed_instance.txt
            self.exists = True
        else:
            # TODO:  Move this part to Lex
            self._load_row(
                "SELECT * FROM `{table}` WHERE `idn` = ?"
                .format(
                    table=self.lex._table,
                ),
                (
                    idn.raw,
                )
            )
            if not self.exists:
                raise self.MissingFromLex

    def _from_definition(self, txt):
        """Construct a Word from its txt, but only when it's a definition."""
        # TODO:  Move to Lex
        assert isinstance(txt, self.TXT_TYPES)
        self._load_row(
            "SELECT * FROM `{table}` "
                "WHERE   `vrb` = ? "
                    "AND `txt` = ?"
            .format(
                table=self.lex._table,
            ),
            (
                self._ID_DEFINE.raw,
                txt,
            )
        )
        if not self.exists:
            self.txt = txt

    def _from_word(self, word):
        if word.is_lex():
            raise ValueError   # lex is a singleton.  TODO:  Explain why this should be.
        assert word.exists
        self.lex = word.lex
        self._from_idn(word.idn)
        # if word.exists:
        #     self._from_idn(word.idn)
        # else:
        #     self._from_definition(word.txt)

    def _from_sbj_vrb_obj(self):
        """Construct a word from its subject-verb-object."""
        # TODO:  Move to Lex
        assert isinstance(self.sbj, Number)
        assert isinstance(self.vrb, Number)
        assert isinstance(self.obj, Number)
        self._load_row(
            "SELECT * FROM `{table}` "
                "WHERE   `sbj` = ? "
                    "AND `vrb` = ? "
                    "AND `obj` = ? "
                "ORDER BY `idn` DESC "
                "LIMIT 1"
            .format(
                table=self.lex._table,
            ),
            (
                self.sbj.raw,
                self.vrb.raw,
                self.obj.raw,
            )
        )

    def _from_sbj_vrb_obj_num_txt(self):
        """Construct a word from its subject-verb-object and its num and txt."""
        # TODO:  Move to Lex
        assert isinstance(self.sbj, Number)
        assert isinstance(self.vrb, Number)
        assert isinstance(self.obj, Number)
        assert isinstance(self.num, Number)
        assert isinstance(self.txt, six.string_types)
        self._load_row(
            "SELECT * FROM `{table}` "
                "WHERE   `sbj` = ? "
                    "AND `vrb` = ? "
                    "AND `obj` = ? "
                    "AND `num` = ? "
                    "AND `txt` = ? "
                "ORDER BY `idn` DESC "
                "LIMIT 1"
            .format(
                table=self.lex._table,
            ),
            (
                self.sbj.raw,
                self.vrb.raw,
                self.obj.raw,
                self.num.raw,
                self.txt,
            )
        )

    def _load_row(self, sql, parameters):
        """Flesh out a word object from a single row of the word table.

        Same parameters as cursor.execute,
        namely a MySQL string and a tuple of ?-value parameters.
        """
        # TODO:  Move to Lex.  Along with every function that calls it.
        cursor = self.lex._connection.cursor(prepared=True)
        cursor.execute(sql, parameters)
        tuple_row = cursor.fetchone()
        assert cursor.fetchone() is None
        if tuple_row is not None:
            self.exists = True
            dict_row = dict(zip(cursor.column_names, tuple_row))
            self._idn = Number.from_mysql(dict_row['idn'])
            self.sbj = Number.from_mysql(dict_row['sbj'])
            self.vrb = Number.from_mysql(dict_row['vrb'])
            self.obj = Number.from_mysql(dict_row['obj'])
            self.num = Number.from_mysql(dict_row['num'])
            self.txt = six.text_type(dict_row['txt'].decode('utf-8'))
            self.whn = Number.from_mysql(dict_row['whn'])
        cursor.close()

    def is_a(self, word, reflexive=True, recursion=10):
        assert recursion >= 0
        if reflexive and self.idn == word.idn:
            return True
        if recursion <= 0:
            return False
        if self.vrb != self._ID_DEFINE:
            return False
        if self.obj == word.idn:
            return True
        parent = self.spawn(self.obj)
        if parent.idn == self.idn:
            return False
        return parent.is_a(word, reflexive=reflexive, recursion=recursion-1)   # TODO:  limit recursion

    def is_a_noun(self, reflexive=True, **kwargs):
        assert hasattr(self, 'lex')
        return self.is_a(self.lex.noun, reflexive=reflexive, **kwargs)

    def is_a_verb(self, reflexive=False, **kwargs):
        assert hasattr(self, 'lex')
        return self.is_a(self.lex.verb, reflexive=reflexive, **kwargs)

    def is_define(self):
        return self.idn == self._ID_DEFINE

    def is_defined(self):
        """Test whether a word is the product of a definition.

        That is, whether the sentence that creates it uses the verb 'define'."""
        return self.vrb == self._ID_DEFINE

    def is_noun(self):
        return self.idn == self._ID_NOUN

    def is_verb(self):
        """Not to be confused with is_a_verb().

        is_a_verb() -- is this word in a []-(define)-[verb] sentence, recursively.
        is_verb() -- is this the one-and-only "verb" word, i.e. [lex]-(define)-[noun]"verb", i.e. id == _ID_VERB
        """
        return self.idn == self._ID_VERB

    def is_agent(self):
        return self.idn == self._ID_AGENT

    def is_lex(self):
        return self.idn == self._ID_LEX

    def description(self):
        sbj = self.spawn(self.sbj)
        vrb = self.spawn(self.vrb)
        obj = self.spawn(self.obj)
        return "{sbj}.{vrb}({obj}, {num}{maybe_txt})".format(
            sbj=str(sbj),
            vrb=str(vrb),
            obj=str(obj),
            num=self.presentable(self.num),
            maybe_txt=(", " + repr(self.txt)) if self.txt != '' else "",
        )

    @staticmethod
    def presentable(num):
        if num.is_whole():
            return str(int(num))
        else:
            return str(float(num))

    def __repr__(self):
        if self.exists:
            if self.is_defined() and self.txt:
                return "Word('{}')".format(self.txt)
            else:
                return "Word({})".format(int(self.idn))
        elif (
            hasattr(self, 'sbj') and
            hasattr(self, 'vrb') and
            hasattr(self, 'obj') and
            hasattr(self, 'txt') and
            hasattr(self, 'num') and
            isinstance(self.sbj, Number) and
            isinstance(self.vrb, Number) and
            isinstance(self.obj, Number) and
            isinstance(self.txt, six.string_types) and
            isinstance(self.num, Number)
        ):
            return("Word(sbj={sbj}, vrb={vrb}, obj={obj}, txt={txt}, num={num})".format(
                sbj=self.sbj.qstring(),
                vrb=self.vrb.qstring(),
                obj=self.obj.qstring(),
                txt=repr(self.txt),
                num=self.num.qstring(),
            ))
        else:
            return "Word(in a strange state)"

        # if hasattr(self, 'txt') and self.is_defined():
        #     return "Word('{0}')".format(self.txt)
        # elif self.exists:
        #     return "Word(Number({idn_qstring}))".format(idn_qstring=self.idn.qstring())
        # else:
        #     return("Word(sbj={sbj}, vrb={vrb}, obj={obj}, txt={txt}, num={num})".format(
        #         sbj=self.sbj.qstring(),
        #         vrb=self.vrb.qstring(),
        #         obj=self.obj.qstring(),
        #         txt=repr(self.txt),
        #         num=self.num.qstring(),
        #     ))

    def __str__(self):
        if hasattr(self, 'txt'):
            return self.txt
        else:
            return repr(self)

    def __eq__(self, other):
        # TODO:  Should this if self._word_before_the_dot != other._word_before_the_dot return False ?
        return self.exists and other.exists and self.idn == other.idn

    @property
    def idn(self):
        return Number(self._idn)   # Copy constructor so e.g. w.idn.suffix(n) won't modify w.idn.
                                   # TODO:  but then what about w.sbj.add_suffix(n), etc.?
                                   # So this passing through Number() is a bad idea.
                                   # Plus this makes x.idn fundamentally differ from x._idn, burdening debug.

    @idn.setter
    def idn(self, value):
        raise RuntimeError("Cannot set a Word's idn")

    def save(self, override_idn=None):
        if override_idn is not None:
            self._idn = override_idn
        assert isinstance(self.idn, (Number, type(None)))
        assert isinstance(self.sbj, Number)
        assert isinstance(self.vrb, Number)
        assert isinstance(self.obj, Number), "{obj} is not a Number".format(obj=repr(self.obj))
        assert isinstance(self.num, Number)
        assert isinstance(self.txt, six.string_types)
        assert not self.exists
        if self._idn is None:
            self._idn = self.lex.max_idn().inc()   # AUTO sorta INCREMENT
            # TODO:  Race condition?  Make max_idn and insert_word part of a transaction.
            # Or store latest idn in another table
            # SEE:  http://stackoverflow.com/questions/3292197/emulate-auto-increment-in-mysql-innodb
            assert not self.idn.is_nan()
        assert isinstance(self.idn, Number)
        self.lex.insert_word(self)

    # noinspection PyClassHasNoInit
    class DefineDuplicateException(Exception):
        pass

    # noinspection PyClassHasNoInit
    class NonVerbUndefinedAsFunctionException(Exception):
        pass


class Listing(Word):
    meta_word = None   # This is the Word associated with Listing,
                       # or the Word associated with each derived class,
                       # in both cases assigned by install().
                       # Listing.meta_word.idn is an unsuffixed qiki.Number.
                       # Subclass.meta_word.idn is another unsuffixed qiki.Number.
                       # An instance_of_subclass.idn is a suffixed qiki.Number
                       # and the root of that idn is its class's meta_word.idn.
                       # See examples in test_example_idn().
    class_dictionary = dict()   # Master list of derived classes, indexed by meta_word.idn

    def __init__(self, index):
        super(Listing, self).__init__()
        assert isinstance(index, (int, Number))   # TODO:  Support a non-Number index.
        assert self.meta_word is not None
        self.index = Number(index)
        self._idn = Number(self.meta_word.idn).add_suffix(Number.Suffix.TYPE_LISTING, self.index)
        self.num = None
        self.txt = None
        self.lookup(self.index, self.lookup_callback)
        self.lex = self.meta_word.lex

    # TODO:  @abstractmethod
    def lookup(self, index, callback):
        raise NotImplementedError("Subclasses of Listing must define a lookup() method.")

    def lookup_callback(self, txt, num):
        self.num = num
        self.txt = txt
        self.exists = True

    @classmethod
    def install(cls, meta_word):
        """
        Associate the class with a (simple) word in the database.
        That word's idn will be the root of the idn for all instances.

        This must be called before any instantiations.
        """
        assert isinstance(meta_word, Word)
        assert isinstance(meta_word.idn, Number)
        # TODO:  Make sure if already defined that it's the same class.
        cls.class_dictionary[meta_word.idn] = cls
        cls.meta_word = meta_word

    @classmethod
    def word_lookup(cls, idn):
        """
        Turn a suffixed Number identifier into a (word) instance of some subclass of Listing.

        So it's a double-lookup.
        First we look up which class this idn is for.
        That's determined by the root of the idn.
        (The root is the Number part without any suffix.)
        This class will be a subclass of Listing.
        Second we call that class's lookup on the suffix of the idn.
        """
        (identifier, suffix) = idn.parse_suffixes()
        assert isinstance(identifier, Number)
        assert isinstance(suffix, Number.Suffix)
        subclass = cls.class_from_meta_idn(identifier)
        listed_instance = subclass(suffix.payload_number())
        # TODO:  Support non-Number suffixes?  The Listing index must now be a Number.
        return listed_instance

    @classmethod
    def class_from_meta_idn(cls, meta_idn):
        # print(repr(cls.class_dictionary))
        return_value = cls.class_dictionary[meta_idn]
        assert issubclass(return_value, cls), repr(return_value) + " is not a subclass of " + repr(cls)
        assert return_value.meta_word.idn == meta_idn
        return return_value

    class NotFound(Exception):
        pass


class Lex(Word):   # rename candidates:  Site, Book, Server, Domain, Dictionary, Qorld, Lex, Lexicon
                      #                     Station, Repo, Repository, Depot, Log, Tome, Manuscript, Diary,
                      #                     Heap, Midden, Scribe, Stow (but it's a verb), Stowage,
                      # Eventually, this will encapsulate other word repositories
                      # Make this an abstract base class
    pass


class LexMySQL(Lex):
    def __init__(self, **kwargs):
        language = kwargs.pop('language')
        assert language == 'MySQL'
        self._table = kwargs.pop('table')
        self._connection = mysql.connector.connect(**kwargs)
        self.lex = self
        self.last_inserted_whn = None
        try:
            super(LexMySQL, self).__init__(self._ID_LEX, lex=self)
            assert self.exists
        except mysql.connector.ProgrammingError as exception:
            exception_message = str(exception)
            if re.search(r"Table .* doesn't exist", exception_message):
                # TODO:  Better detection of automatic table creation opportunity.
                self.install_from_scratch()
                # TODO:  Don't super() twice -- cuz it's not D.R.Y.
                # TODO:  Don't install in unit tests if we're about to uninstall.
                super(LexMySQL, self).__init__(self._ID_LEX, lex=self)
            else:
                assert False, exception_message
        except Word.MissingFromLex:
            self._install_seminal_words()

        assert self.exists
        cursor = self._cursor()
        cursor.execute('SET NAMES utf8mb4 COLLATE utf8mb4_general_ci')
        cursor.close()
        # THANKS:  http://stackoverflow.com/a/27390024/673991
        assert self.is_lex()
        assert self._connection.is_connected()

    def install_from_scratch(self):
        """Create database table and insert words.  Or do nothing if table and/or words already exist."""
        cursor = self._cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `{table}` (
                `idn` VARBINARY(255) NOT NULL,
                `sbj` VARBINARY(255) NOT NULL,
                `vrb` VARBINARY(255) NOT NULL,
                `obj` VARBINARY(255) NOT NULL,
                `num` VARBINARY(255) NOT NULL,
                `txt` TEXT NOT NULL,
                `whn` VARBINARY(255) NOT NULL,
                PRIMARY KEY (`idn`)
            )
                ENGINE = InnoDB
                DEFAULT CHARACTER SET = utf8mb4
                DEFAULT COLLATE = utf8mb4_general_ci
            ;
        """.format(table=self._table))
        # TODO:  other keys?  sbj-vrb?   obj-vrb?
        cursor.close()
        self._install_seminal_words()

    def _install_seminal_words(self):
        """
        Insert the five fundamental sentences into the Lex database.
        Each sentence uses verbs and nouns defined in some of the other seminal sentences.

        The five seminal sentences:
                    lex.define(verb, 'define')
             noun = lex.define(noun, 'noun')
             verb = lex.define(noun, 'verb')
            agent = lex.define(noun, 'agent')
                    lex.define(agent, 'lex')

        At least that's how they'd be defined if forward references were not a problem.
        """
        self._seminal_word(self._ID_DEFINE, self._ID_VERB, u'define')
        self._seminal_word(self._ID_NOUN, self._ID_NOUN, u'noun')
        self._seminal_word(self._ID_VERB, self._ID_NOUN, u'verb')
        self._seminal_word(self._ID_AGENT, self._ID_NOUN, u'agent')
        self._seminal_word(self._ID_LEX, self._ID_AGENT, u'lex')


        if not self.exists:
            self._from_idn(self._ID_LEX)
        assert self.exists
        assert self.is_lex()

    def _seminal_word(self, _idn, _obj, _txt):
        """Insert important, fundamental word into the table, if it's not already there.

        Subject is always 'lex'.  Verb is always 'define'."""
        try:
            word = self.spawn(_idn)
        except Word.MissingFromLex:
            self._install_word(_idn, _obj, _txt)
            word = self.spawn(_idn)
        # if not word.exists:   # TODO:  is this really necessary any longer?
        #     self._install_word(_idn, _obj, _txt)
        #     word = self.spawn(_idn)
        assert word.exists

    def _install_word(self, _idn, _obj, _txt):
        word = self.spawn(
            sbj = self._ID_LEX,
            vrb = self._ID_DEFINE,
            obj = _obj,
            num = Number(1),
            txt = _txt,
        )
        try:
            word.save(override_idn=_idn)
        except mysql.connector.IntegrityError:
            # TODO:  What was I thinking should happen here?
            raise
        except mysql.connector.ProgrammingError as exception:
            exception_message = str(exception)
            if re.search(r"INSERT command denied to user", exception_message):
                print("GRANT INSERT ON db TO user@host?")
                raise
            else:
                print(exception_message)
                raise

    def uninstall_to_scratch(self):
        """Deletes table.  Opposite of install_from_scratch()."""
        cursor = self._cursor()
        try:
            cursor.execute("DELETE FROM `{table}`".format(table=self._table))
        except mysql.connector.ProgrammingError:
            pass
        cursor.execute("DROP TABLE IF EXISTS `{table}`".format(table=self._table))
        cursor.close()
        # After this, we can only install_from_scratch() or disconnect()

    def disconnect(self):
        self._connection.close()

    def get_all_idns(self):
        """Return an array of all word ids in the database."""
        # TODO:  Start and number parameters, for LIMIT clause.
        cursor = self._cursor()
        cursor.execute("SELECT idn FROM `{table}` ORDER BY idn ASC".format(table=self._table))
        idns = []
        for row in cursor:
            idn = Number.from_mysql(row[0])
            idns.append(idn)
        cursor.close()
        return idns

    # noinspection SpellCheckingInspection
    def insert_word(self, word):
        cursor = self._cursor()
        assert not word.idn.is_nan()
        whn = Number(time.time())
        cursor.execute(
            "INSERT INTO `{table}` "
                   "(idn, sbj, vrb, obj, num, txt, whn) "
            "VALUES (  ?,   ?,   ?,   ?,   ?,   ?,   ?)"
            .format(
                table=self._table,
            ),
            (
                word.idn.raw,
                word.sbj.raw,
                word.vrb.raw,
                word.obj.raw,
                word.num.raw,
                word.txt,
                whn.raw,
            )
        )
        # TODO:  named substitutions with NON-prepared statements??
        # THANKS:  https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursor-execute.html
        # THANKS:  http://stackoverflow.com/questions/1947750/does-python-support-mysql-prepared-statements/31979062#31979062
        self._connection.commit()
        cursor.close()
        word.whn = whn
        word.exists = True

    def _cursor(self):
        return self._connection.cursor(prepared=True)

    def find(self, sbj=None, vrb=None, obj=None):
        query = "SELECT idn FROM " + self._table + " WHERE 1 "
        parameters = []
        if sbj is not None:   query += " AND sbj=? ";   parameters.append(sbj.raw)
        if vrb is not None:   query += " AND vrb=? ";   parameters.append(vrb.raw)
        if obj is not None:   query += " AND obj=? ";   parameters.append(obj.raw)
        query += " ORDER BY idn "
        return self._select_words(query, parameters)

    # noinspection SpellCheckingInspection
    def _select_words(self, sql, parameters):
        """
        Read an array of words based on an SELECT idn FROM {table} query.

        Same parameters as cursor.execute,
        namely a MySQL string and a tuple of ?-value parameters.
        """
        cursor = self.lex._connection.cursor(prepared=True)
        # TODO:  Give up prepared=True so we can buffered=True so we can have one for-loop below?
        # Another reason to use prepared=False:  http://stackoverflow.com/a/24842296/673991
        # Or use cursor(cursor_class=MySQLCursorPrepared) - see last line of:
        # https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursorprepared.html
        cursor.execute(sql, parameters)
        idns = []
        for row in cursor:
            assert len(row) == 1, "Expecting 1 column only, got " + repr(row)
            idn = Number.from_mysql(row[0])
            # word = self(idn)   # Doing this raises InternalError: Unread result found.
            # NOTE:  Apparently, multiple cursors do NOT support multiple query-results.
            # SEE:  http://stackoverflow.com/a/17268389/673991
            # And a cursor can't be both prepared and buffered.
            idns.append(idn)
        words = []
        for idn in idns:
            word = self(idn)
            words.append(word)
        cursor.close()
        return words

    def max_idn(self):
        # TODO:  Store max_idn in a singleton table.
        cursor = self._connection.cursor()
        cursor.execute("SELECT MAX(idn) FROM `{table}`".format(table=self._table))
        max_idn_sql_row = cursor.fetchone()
        if max_idn_sql_row is None:
            return Number(0)
        max_idn_sql = max_idn_sql_row[0]
        if max_idn_sql is None:
            return Number(0)
        return_value = Number.from_mysql(max_idn_sql)
        assert not return_value.is_nan()
        assert return_value.is_whole()
        return return_value


# DONE:  Combine connection and table?  We could subclass like so:  Lex(MySQLConnection)
# DONE:  ...No, make them properties of Lex.  And make all Words refer to a Lex
# DONE:  ...So combine all three.  Maybe Lex shouldn't subclass Word?
# DONE:  Or make a class LexMysql(Lex)
# DONE:  MySQL decouple -- reinvent some db abstraction class?  (Lex)

# TODO:  Do not raise built-in classes, raise subclasses of built-in exceptions
# TODO:  Word attributes sbj,vrb,obj might be more convenient as Words, not Numbers.
# TODO:  ...If so they would need to be dynamic properties.
# TODO:  ......And avoid infinite recursion!  That is, e.g. sbj.vrb.vrb.vrb.obj....
# TODO:  ...One way to do this might be x = Word(idn) would not generate database activity
# TODO:  ......unless some other method were called, e.g. x.vrb
# TODO:  ...Perhaps they could stay numbers until treated as words
# TODO:  ......and then "become" (i.e. by a database read and some shenanigans) words?
# TODO:  Singleton pattern, so e.g. Word('noun') is Word('noun')
# TODO:  Logging callbacks

# TODO:  Exotic syntax?
#        (s)[v](o)
#        (s)[v](o, 2)
#        (s)[v](o, "why")
#    Or:
#        [s](v)[o]
#        [s](v, 2)[o]
#        [s](v, "why")[o]

# TODO:  Implement use_already as a "verb property".  Aka "adverb"??
# lex.noun('adverb')
# lex.adverb('use_already')
# like = lex.verb('like')
# lex.use_already(like, 0 for defaults-to-False or 1 for True)
# alice.like(bob, "but just as a friend")   # use_already=True unnecessary
# lex.use_already(lex.define, 1)