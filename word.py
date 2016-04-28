"""
A qiki Word is defined by a three-word subject-verb-object
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import numbers
import re
import time

import mysql.connector
import six

from qiki import Number


# noinspection PyAttributeOutsideInit
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

    :type content: Text.is_valid() | Word | instancemethod

    :type sbj: Number | Word
    :type vrb: Number | instancemethod
    :type obj: Number | Word
    :type num: Number
    :type txt: Unicode in either Python 2 or 3
    :type lex: Word

    Note:  instantiation.txt is always Unicode
    """

    def __init__(self, content=None, sbj=None, vrb=None, obj=None, num=None, txt=None, lex=None):
        self.lex = lex
        if Text.is_valid(content):   # e.g. Word('agent')
            self._from_definition(content)
        elif isinstance(content, Number):   # Word(idn)
            self._inchoate(content)
        elif isinstance(content, Word):   # Word(some_other_word)
            self._from_word(content)
        elif content is None:   # Word(sbj=s, vrb=v, obj=o, num=n, txt=t)
            # TODO:  If this is only used via spawn(), then move this code there somehow?
            self._fields = dict(
                sbj=None if sbj is None else self.lex.word_from_word_or_number(sbj),
                vrb=None if vrb is None else self.lex.word_from_word_or_number(vrb),
                obj=None if obj is None else self.lex.word_from_word_or_number(obj),
                num=num,
                txt=None if txt is None else Text(txt),
                whn=None,
            )
        else:
            typename = type(content).__name__
            if typename == 'instance':
                typename = content.__class__.__name__
            if typename in ('str', 'bytes', 'bytearray'):
                etc = " -- use unicode instead"
            else:
                etc = ""
            raise TypeError("{outer}({inner}) is not supported{etc}".format(
                outer=type(self).__name__,
                inner=typename,
                etc=etc,
            ))

    def _inchoate(self, idn):
        """
        Initialize an inchoate word.

        Definition of "inchoate"
        ------------------------
        An inchoate word is frugal with resources.
        All that is known about an inchoate word is its idn.
        Maybe that's all we ever need to know about it.
        But, if almost anything else is asked of it, then the word is made choate.
        Such as:
            word.sbj
            word.vrb
            word.vrb
            word.num
            word.txt
            word.whn
            word.exists()

        These also make a word choate, but they do so implicitly
        because they use one of the above members:
            str(word)
            repr(word)
            hasattr(word, 'txt')
            ...a lot more

        But these actions do not make a word choate.  If it was inchoate it stays so:
            word.idn
            word.lex
            hash(word)
            word == word2
            word2 = lex(word)
            word2 = word.spawn(word)
            word2 = word.inchoate_copy()

        This makes it possible to dereference the parts of a sentence dynamically,
        only when they're needed, e.g.

            word.obj.obj.obj.obj.txt

        It also makes it possible to work with a list of words
        in a way that's almost as resource-efficient as a list of idns.
        """
        self._idn = idn
        self._is_inchoate = True
        assert self.lex is not None

    def _choate(self):
        """
        Transform an inchoate word into a not-inchoate word.

        This in preparation to use one of its properties, sbj, vrb, obj, txt, num, whn.
        """
        if self._is_inchoate:
            del self._is_inchoate
            self._from_idn(self._idn)

    def exists(self):
        self._choate()
        return self._exists

    def _now_it_exists(self):
        self._exists = True

    _IDN_DEFINE = Number(1)
    _IDN_NOUN   = Number(2)
    _IDN_VERB   = Number(3)
    _IDN_AGENT  = Number(4)
    _IDN_LEX    = Number(5)

    _IDN_MAX_FIXED = Number(5)

    class NoSuchAttribute(AttributeError):
        pass

    class NoSuchKwarg(TypeError):
        pass

    class MissingObj(TypeError):
        pass

    def __getattr__(self, attribute_name):
        if attribute_name.startswith('_'):
            # What about ('_exists', '_is_inchoate', '_idn', '_word_before_the_dot', '_fields')
            # return None
            if attribute_name in ('_exists', '_is_inchoate', '_idn'):
                return None
            # XXX:  More pythonic to raise AttributeError
            raise AttributeError("Verbs starting with underscore can't use the subject.verb syntax: " + attribute_name)
        if attribute_name in ('sbj', 'vrb', 'obj', 'num', 'txt', 'whn'):
            self._choate()
            # if self._fields is None:
            #     return None
            #     # XXX:  More pythonic to raise AttributeError
            try:
                return self._fields[attribute_name]
            except KeyError:   # Why don't I need AttributeError here too for _fields?
                return None
                # XXX:  More pythonic to raise AttributeError
        if attribute_name == 'do_not_call_in_templates':
            # THANKS:  for this Django flag, maybe http://stackoverflow.com/a/21711308/673991
            return True

        raise RuntimeError("Neither is this implemented any more")

    class NotExist(Exception):
        pass

    def __call__(self, *args, **kwargs):
        """subject(verb)"""
        that = SubjectedVerb(self, *args, **kwargs)
        return that

    def define(self, obj, txt):
        """
        Define a word.  Name it txt.  Its type or class is obj.

        Example:
            agent = lex('agent')
            lex.define(agent, 'fred')

        The obj may be identified by its txt, example:
            lex.define('agent', 'fred')
        """
        if Text.is_valid(obj):   # Meta definition:  s.define('x') is equivalent to s.define(lex['x'])
            obj = self.spawn(obj)
        # TODO:  Move the above logic to says()?  Similarly for SubjectedVerb, and its calls to spawn()

        assert isinstance(obj, Word)
        assert Text.is_valid(txt), "define() txt cannot be a {}".format(type(txt).__name__)

        # How to handle "duplications"

        # TODO:  Shouldn't this be spawn(sbj=lex, vrb=define, txt)?
        # Maybe someone else will define a word.
        # Then everyone who tries to define that word will use that first person's definition.
        # Anything interesting about the first definer of a word?  Maybe not much.
        # What's important is consistency.
        # And anyway, anyone could theoretically imbue the word with their own meaning,
        # applicable to their uses.

        # TODO:  Implement define() via says() with a use_earliest option?
        # Not really, more subtle than that. Selecting uniqueness on txt and not on sbj.

        # Who cares about num (yet)?  Used to, but now abolished.

        # So anyway, this attempts to find the earliest definition by anybody of the same word:
        possibly_existing_word = self.spawn(txt)
        if possibly_existing_word.exists():
            return possibly_existing_word
        new_word = self.says(vrb=self.lex[u'define'], obj=obj, txt=txt)
        return new_word

    def said(self, vrb, obj):
        assert isinstance(vrb, (Word, Number)), "vrb cannot be a {type}".format(type=type(vrb).__name__)
        assert isinstance(obj, (Word, Number)), "obj cannot be a {type}".format(type=type(obj).__name__)
        existing_word = self.spawn(
            sbj=self,
            vrb=vrb,
            obj=obj
        )
        existing_word._from_sbj_vrb_obj()
        if not existing_word.exists():
            raise self.NotExist
        return existing_word

    def says(self, vrb, obj, num=None, txt=None, num_add=None, use_already=False):
        """
        Construct a new sentence from a 3-word subject-verb-object.

        Subject is self.

        use_already makes a difference if the same word with the same num and txt
        exists already AND is the newest word with that sbj-vrb-obj combination.
        In that case no new sentence is created, the old one is returned.

        Either num or num_add may be specified.

        Differences between Word.sentence() and Word.spawn():
            sentence takes a Word-triple, spawn takes an idn-triple.
            sentence saves the new word.
            spawn can take in idn or other ways to indicate an existing word.
        Differences between Word.sentence() and Word.define():
            sentence takes a Word-triple,
            define takes only one word for the object (sbj and vrb are implied)
            sentence requires an explicit num, define defaults to 1
        """
        # TODO:  rewrite this docstring

        assert isinstance(vrb, (Word, Number)), "vrb cannot be a {type}".format(type=type(vrb).__name__)
        assert isinstance(obj, (Word, Number)), "obj cannot be a {type}".format(type=type(obj).__name__)
        if isinstance(txt, numbers.Number) or Text.is_valid(num):
            # TODO:  Why `or` not `and`?
            (txt, num) = (num, txt)

        if num is not None and num_add is not None:
            raise self.SentenceArgs("Word.says() cannot specify both num and num_add.")

        num = num if num is not None else 1
        txt = txt if txt is not None else u''

        if not isinstance(num, numbers.Number) or not Text.is_valid(txt):
            raise self.SentenceArgs("Wrong types for Word.says() num or txt")

        new_word = self.spawn(
            sbj=self,
            vrb=vrb,
            obj=obj,
            num=Number(num),
            txt=txt
        )
        if num_add is not None:
            new_word._from_sbj_vrb_obj()
            assert isinstance(num_add, numbers.Number)
            if new_word.exists():
                new_word._fields['num'] += Number(num_add)
            else:
                new_word._fields['num'] = Number(num_add)
            new_word.save()
        elif use_already:
            old_word = self.spawn(
                sbj=self,
                vrb=vrb,
                obj=obj
            )
            old_word._from_sbj_vrb_obj()
            if not old_word.exists():
                new_word.save()
            elif old_word.txt != new_word.txt or old_word.num != new_word.num:
                new_word.save()
            else:
                # There was an identical sentence already.  Fetch it so new_word.exists().
                # This is the only path through says() where no new sentence is created.
                new_word._from_sbj_vrb_obj_num_txt()
                assert new_word.idn == old_word.idn, "Race condition {old} to {new}".format(
                    old=old_word.idn.qstring(),
                    new=new_word.idn.qstring()
                )
        else:
             new_word.save()
        return new_word

    class SentenceArgs(TypeError):
        pass

    def spawn(self, *args, **kwargs):
        """
        Construct a Word() using the same lex as another word.
        """
        assert hasattr(self, 'lex')
        kwargs['lex'] = self.lex
        return Word(*args, **kwargs)

    class NotAVerb(Exception):
        pass

    class NotAWord(Exception):
        pass

    def _from_idn(self, idn):
        """
        Construct a Word from its idn.

        :type idn: Number
        """
        assert isinstance(idn, Number)
        if idn.is_suffixed():
            try:
                listed_instance = Listing.word_lookup(idn)
            except Listing.NotAListing:
                raise self.NotAWord("Not a Word identifier: " + idn.qstring())
            else:
                assert listed_instance.exists()
                self._fields = dict(txt=listed_instance.txt)
                self._now_it_exists()
                # TODO:  This was a fudge. Word(suffixed idn) should return a Listing instance
                # i.e. something like self = listed_instance
                # or self.__class__ = Listing subclass
                # SEE:  http://stackoverflow.com/a/3209240/673991
        else:
            self._idn = idn
            self.lex.populate_word_from_idn(self, idn)

    def _from_definition(self, txt):
        """Construct a Word from its txt, but only when it's a definition."""
        assert Text.is_valid(txt)
        assert isinstance(self.lex, Lex)
        if not self.lex.populate_word_from_definition(self, txt):
            self._fields = dict(txt=Text(txt))

    def _from_word(self, word):
        # if word.is_lex():
        #     raise ValueError("Lex is a singleton, so it cannot be copied.")
        #     # TODO:  Explain why this should be.
        #     # TODO:  Resolve inconsistency:  spawn(lex.idn) will clone lex
        #     # And this ability may be needed anyway in the murk of LexMySQL.__init__()
        assert isinstance(word, Word)   # Instead of type(self)
        self.lex = word.lex
        if word._is_inchoate:
            self._idn         = word._idn
            self._is_inchoate = word._is_inchoate
        else:
            assert word.exists()
            self._from_idn(word.idn)

    def _from_sbj_vrb_obj(self):
        """Construct a word by looking up its subject-verb-object."""
        assert isinstance(self.sbj, Word)
        assert isinstance(self.vrb, Word)
        assert isinstance(self.obj, Word)
        self.lex.populate_word_from_sbj_vrb_obj(self, self.sbj, self.vrb, self.obj)

    def _from_sbj_vrb_obj_num_txt(self):
        """Construct a word by looking up its subject-verb-object and its num and txt."""
        assert isinstance(self.sbj, Word)
        assert isinstance(self.vrb, Word)
        assert isinstance(self.obj, Word)
        assert isinstance(self.num, Number)
        assert isinstance(self.txt, Text)
        self.lex.populate_word_from_sbj_vrb_obj_num_txt(
            self,
            self.sbj,
            self.vrb,
            self.obj,
            self.num,
            self.txt
        )

    def inchoate_copy(self):
        """
        Word clones itself but the copy is inchoate.

        Useful for words as dictionary keys.
        """
        return self.spawn(self.idn)

    def populate_from_row(self, row, prefix=''):
        self._idn = row[prefix + 'idn']
        self._now_it_exists()   # Must come before spawn(sbj) for lex's sake.
        self._fields = dict(
            sbj=self.spawn(row[prefix + 'sbj']),
            vrb=self.spawn(row[prefix + 'vrb']),
            obj=self.spawn(row[prefix + 'obj']),
            num=row[prefix + 'num'],
            txt=row[prefix + 'txt'],
            whn=row[prefix + 'whn'],
        )

    def is_a(self, word, reflexive=True, recursion=10):
        assert recursion >= 0
        if reflexive and self.idn == word.idn:
            return True
        if recursion <= 0:
            return False
        if not self.exists():
            return False
        if not hasattr(self, 'vrb'):
            return False
        if self.vrb.idn != self._IDN_DEFINE:
            return False
        if self.obj == word:
            return True
        parent = self.spawn(self.obj)
        if parent.idn == self.idn:
            return False
        return parent.is_a(word, reflexive=reflexive, recursion=recursion-1)

    def is_a_noun(self, reflexive=True, **kwargs):
        """Noun is a noun.  Really, everything is a noun."""
        assert hasattr(self, 'lex')
        return self.is_a(self.lex.noun(), reflexive=reflexive, **kwargs)

    def is_a_verb(self, reflexive=False, **kwargs):
        """Verb is not a verb.  But anything defined as a verb is a verb."""
        assert hasattr(self, 'lex')
        return self.is_a(self.lex.verb(), reflexive=reflexive, **kwargs)

    def is_define(self):
        """Is this word the one and only verb (whose txt is) 'define'."""
        return self.idn == self._IDN_DEFINE

    def is_defined(self):
        """
        Test whether a word is the product of a definition.

        That is, whether the sentence that creates it uses the verb 'define'.
        """
        return self.vrb.idn == self._IDN_DEFINE

    def is_noun(self):
        return self.idn == self._IDN_NOUN

    def is_verb(self):
        """
        Not to be confused with is_a_verb().

        is_a_verb() -- is this word in a []-(define)-[verb] sentence, recursively.
        is_verb() -- is this the one-and-only "verb" word, i.e. [lex]-(define)-[noun]"verb", i.e. id == _IDN_VERB
        """
        return self.idn == self._IDN_VERB

    def is_agent(self):
        return self.idn == self._IDN_AGENT

    def is_lex(self):
        return isinstance(self, Lex) and self.exists() and self.idn == self._IDN_LEX

    def description(self):
        return u"[{sbj}]({vrb}{maybe_num}{maybe_txt})[{obj}]".format(
            sbj=str(self.sbj),
            vrb=str(self.vrb),
            obj=str(self.obj),
            # TODO:  Would str(x) cause infinite recursion?  Not if str() doesn't call description()
            maybe_num=(", " + self.presentable(self.num)) if self.num != 1   else "",
            maybe_txt=(", " + repr(self.txt))             if self.txt != u'' else "",
        )

    @staticmethod
    def presentable(num):
        if num.is_whole():
            return str(int(num))
        else:
            return str(float(num))

    def __repr__(self):
        if self.exists():
            if self.is_defined() and self.txt:
                return "Word(u'{}')".format(self.txt)
            else:
                return "Word({})".format(int(self.idn))
        elif (
            isinstance(self.sbj, Word) and
            isinstance(self.vrb, Word) and
            isinstance(self.obj, Word) and
            isinstance(self.txt, Text) and
            isinstance(self.num, Number)
        ):
            return("Word(sbj={sbj}, vrb={vrb}, obj={obj}, txt={txt}, num={num})".format(
                sbj=self.sbj.idn.qstring(),
                vrb=self.vrb.idn.qstring(),
                obj=self.obj.idn.qstring(),
                txt=repr(self.txt),
                num=self.num.qstring(),
            ))
        else:
            try:
                repr_idn = repr(int(self.idn))
            except ValueError:
                repr_idn = repr(self.idn)
            return "Word(in a strange state, idn {})".format(repr_idn)

    def __str__(self):
        if hasattr(self, 'txt'):
            return self.txt.native()
        else:
            return repr(self)
            # TODO:  Should this be encoded for PY2?

    def __unicode__(self):
        if hasattr(self, 'txt'):
            assert isinstance(self.txt, Text)
            return self.txt.unicode()
        else:
            return repr(self)

    def __hash__(self):
        return hash(self.idn)

    def __eq__(self, other):
        try:
            return self.idn == other.idn
        except AttributeError:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def idn(self):
        return Number(self._idn)   # Copy constructor so e.g. w.idn.suffix(n) won't modify w.idn.
                                   # TODO:  but then what about w.sbj.add_suffix(n), etc.?
                                   # So this passing through Number() is a bad idea.
                                   # Plus this makes x.idn fundamentally differ from x._idn, burdening debug.

    @idn.setter
    def idn(self, value):
        raise AttributeError("Cannot set a Word's idn.")
    # TODO:  Omit this?

    def save(self, override_idn=None):
        if override_idn is not None:
            self._idn = override_idn
        assert isinstance(self.idn, (Number, type(None)))
        assert isinstance(self.sbj, Word)
        assert isinstance(self.vrb, Word)
        assert isinstance(self.obj, Word), "{obj} is not a Word".format(obj=repr(self.obj))
        assert isinstance(self.num, Number)
        assert isinstance(self.txt, Text)
        if self.exists() or self._idn is None:
            self._idn = self.lex.max_idn().inc()   # AUTO sorta INCREMENT
            # TODO:  Race condition?  Make max_idn and insert_word part of a transaction.
            # Or store latest idn in another table
            # SEE:  http://stackoverflow.com/questions/3292197/emulate-auto-increment-in-mysql-innodb
            assert not self.idn.is_nan()
        assert isinstance(self.idn, Number)
        self.lex.insert_word(self)

    class DefineDuplicateException(Exception):
        pass

    class NonVerbUndefinedAsFunctionException(TypeError):
        pass


class SubjectedVerb(object):
    """
    This is the result of s(v).

    That is, when you subscript a subject by a verb.
    """
    def __init__(self, sbj, vrb, *args, **kwargs):
        self._subjected = sbj
        self._verbed = self._subjected.spawn(vrb)   # TODO:  Move to
        self._args = args
        self._kwargs = kwargs

    def __setitem__(self, key, value):
        objected = self._subjected.spawn(key)
        num_and_or_txt = value
        if isinstance(num_and_or_txt, numbers.Number):
            num = num_and_or_txt
            txt = u""
        elif Text.is_valid(num_and_or_txt):
            txt = num_and_or_txt
            num = Number(1)
        else:
            num = Number(1)
            txt = Text(u"")
            if is_iterable(num_and_or_txt):
                for num_or_txt in num_and_or_txt:
                    if isinstance(num_or_txt, numbers.Number):
                        num = num_or_txt
                    elif Text.is_valid(num_or_txt):
                        txt = num_or_txt
                    else:
                        raise Word.SentenceArgs("Expecting num or txt, got " + repr(num_or_txt))
            else:
                raise Word.SentenceArgs("Expecting num and/or txt, got " + repr(num_and_or_txt))

        self._subjected.says(self._verbed, objected, num, txt, *self._args, **self._kwargs)

    def __getitem__(self, item):
        objected = item
        return self._subjected.said(self._verbed, objected)


# noinspection PyAttributeOutsideInit
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
        self.lookup(self.index, self.lookup_callback)
        self.lex = self.meta_word.lex

    # TODO:  @abstractmethod
    def lookup(self, index, callback):
        raise NotImplementedError("Subclasses of Listing must define a lookup() method.")

    def lookup_callback(self, txt, num):
        # Another case where txt comes before num, the exception.
        self.num = num
        self.txt = Text(txt)
        self._now_it_exists()

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

    class NotAListing(Exception):
        pass

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
        pieces = idn.parse_suffixes()
        try:
            (identifier, suffix) = pieces
        except ValueError:
            raise cls.NotAListing("Not a Listing identifier: " + idn.qstring())
        assert isinstance(identifier, Number)
        assert isinstance(suffix, Number.Suffix)
        subclass = cls.class_from_meta_idn(identifier)
        listed_instance = subclass(suffix.payload_number())
        # TODO:  Support non-Number suffixes?  The Listing index must now be a Number.
        return listed_instance

    @classmethod
    def class_from_meta_idn(cls, meta_idn):
        # print(repr(cls.class_dictionary))
        try:
            return_value = cls.class_dictionary[meta_idn]
        except KeyError:
            raise cls.NotAListing("Not a Listing class identifier: " + meta_idn.qstring())
        assert issubclass(return_value, cls), repr(return_value) + " is not a subclass of " + repr(cls)
        assert return_value.meta_word.idn == meta_idn
        return return_value

    class NotFound(Exception):
        pass


class Lex(Word):    # rename candidates:  Site, Book, Server, Domain, Dictionary, Qorld, Lex, Lexicon
                    #                     Station, Repo, Repository, Depot, Log, Tome, Manuscript, Diary,
                    #                     Heap, Midden, Scribe, Stow (but it's a verb), Stowage,
                    # Eventually, this will encapsulate other word repositories
                    # Make this an abstract base class

    class SuperIdentifier(str):
        """Identifier in an SQL super-query that could go in `back-ticks`."""
        pass

    # noinspection PyClassHasNoInit
    class TableName(SuperIdentifier):
        pass

    class NotFound(Exception):
        pass

    class ConnectError(Exception):
        pass


# noinspection SqlDialectInspection,SqlNoDataSourceInspection
class LexMySQL(Lex):
    def __init__(self, **kwargs):
        language = kwargs.pop('language')
        assert language == 'MySQL'
        self._table = kwargs.pop('table')
        self._engine = kwargs.pop('engine', 'InnoDB')
        self._txt_type = kwargs.pop('txt_type', 'TEXT')
        try:
            self._connection = mysql.connector.connect(**kwargs)
        except mysql.connector.ProgrammingError as exception:
            raise self.ConnectError(str(exception))
        self.lex = self
        self.last_inserted_whn = None

        super(LexMySQL, self).__init__(self._IDN_LEX, lex=self)
        try:
            self._choate()
        except mysql.connector.ProgrammingError as exception:
            exception_message = str(exception)
            if re.search(r"Table .* doesn't exist", exception_message):
                # TODO:  Better detection of automatic table creation opportunity.
                self.install_from_scratch()
                # TODO:  Don't super() twice -- cuz it's not D.R.Y.
                # TODO:  Don't install in unit tests if we're about to uninstall.
                super(LexMySQL, self).__init__(self._IDN_LEX, lex=self)
            else:
                raise self.ConnectError(str(exception))

        if not self.exists():
            self._install_seminal_words()

        self._noun = self[self._IDN_NOUN]
        self._verb = self[self._IDN_VERB]

        assert self.exists()

        self.super_query('SET NAMES utf8mb4 COLLATE utf8mb4_general_ci')
        # THANKS:  http://stackoverflow.com/a/27390024/673991
        assert self.is_lex()
        assert self._connection.is_connected()

    def __getitem__(self, item):

        existing_word = self.spawn(item)
        # if not existing_word.exists():
        #     raise self.NotExist
        # No because inchoate words become choate by virtue of calling .exists().
        # And it's just not (yet) the Word way of doing things.
        #     That is, lots of code asks permission rather than forgiveness.
        #     But even moreso, the whole inchoate scheme falls apart if we have to ask,
        #     at this point, whether the word exists or not.

        if existing_word.idn == self.idn:
            return self   # lex is a singleton.  Why is this important?
        else:
            return existing_word

    def noun(self, name=None):
        if name is None:
            return self._noun
        else:
            return self.define(self._noun, name)

    def verb(self, name=None):
        if name is None:
            return self._verb
        else:
            return self.define(self._verb, name)

    def install_from_scratch(self):
        """Create database table and insert words.  Or do nothing if table and/or words already exist."""
        if not re.match(self._ENGINE_NAME_VALIDITY, self._engine):
            raise self.IllegalEngineName("Not a valid table name: " + repr(self._engine))

        with self._cursor() as cursor:
            query = """
                CREATE TABLE IF NOT EXISTS `{table}` (
                    `idn` VARBINARY(255) NOT NULL,
                    `sbj` VARBINARY(255) NOT NULL,
                    `vrb` VARBINARY(255) NOT NULL,
                    `obj` VARBINARY(255) NOT NULL,
                    `num` VARBINARY(255) NOT NULL,
                    `txt` {txt_type} NOT NULL,
                    `whn` VARBINARY(255) NOT NULL,
                    PRIMARY KEY (`idn`)
                )
                    ENGINE = `{engine}`
                    DEFAULT CHARACTER SET = utf8mb4
                    DEFAULT COLLATE = utf8mb4_general_ci
                ;
            """.format(
                table=self.table,
                txt_type=self._txt_type,   # But using this is a hard error:  <type> expected found '{'
                engine=self._engine,
            )

            cursor.execute(query)
            # TODO:  other keys?  sbj-vrb?   obj-vrb?
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
        def seminal_word(_idn, _obj, _txt):
            """Subject is always 'lex'.  Verb is always 'define'."""
            word = self.spawn(_idn)
            if not word.exists():
                self._install_word(_idn, _obj, _txt)
                word = self.spawn(_idn)
            assert word.exists()
                                                                    # forward, reflexive references
        seminal_word(self._IDN_DEFINE, self._IDN_VERB,  u'define')  # 2,1   +4, 0,+2
        seminal_word(self._IDN_NOUN,   self._IDN_NOUN,  u'noun')    # 1,1   +3,-1, 0
        seminal_word(self._IDN_VERB,   self._IDN_NOUN,  u'verb')    # 1,0   +2,-2,-1
        seminal_word(self._IDN_AGENT,  self._IDN_NOUN,  u'agent')   # 1,0   +1,-3,-2
        seminal_word(self._IDN_LEX,    self._IDN_AGENT, u'lex')     # 0,1    0,-4,-1
                                                                    #-----
                                                                    # 5,3
        return
        # noinspection PyUnreachableCode
        # TODO:  If lex were moved to the first idn:
                                                                    # forward, reflexive references
        seminal_word(self._IDN_LEX,    self._IDN_AGENT, u'lex')     # 2,1    0,+1,+4
        seminal_word(self._IDN_DEFINE, self._IDN_VERB,  u'define')  # 1,1   -1, 0,+2
        seminal_word(self._IDN_NOUN,   self._IDN_NOUN,  u'noun')    # 0,1   -2,-1, 0
        seminal_word(self._IDN_VERB,   self._IDN_NOUN,  u'verb')    # 0,0   -3,-2,-1
        seminal_word(self._IDN_AGENT,  self._IDN_NOUN,  u'agent')   # 0,0   -4,-3,-2
                                                                    #-----
                                                                    # 3,3

        if not self.exists():
            self._from_idn(self._IDN_LEX)
        assert self.exists()
        assert self.is_lex()

    def _install_word(self, _idn, _obj, _txt):
        word = self.spawn(
            sbj=self._IDN_LEX,
            vrb=self._IDN_DEFINE,
            obj=_obj,
            num=Number(1),
            txt=_txt,
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
        try:
            self.super_query('DELETE FROM', self.table)
        except mysql.connector.ProgrammingError:
            pass
        self.super_query('DROP TABLE IF EXISTS', self.table)
        # self._now_it_doesnt_exist()   # So install will insert the lex sentence.
        # After this, we can only install_from_scratch() or disconnect()

    def disconnect(self):
        self._connection.close()

    # noinspection SpellCheckingInspection
    def insert_word(self, word):
        assert not word.idn.is_nan()
        whn = Number(time.time())
        # TODO:  Enforce whn uniqueness?
        # SEE:  https://docs.python.org/2/library/time.html#time.time
        #     "Note that even though the time is always returned as a floating point number,
        #     not all systems provide time with a better precision than 1 second.
        #     While this function normally returns non-decreasing values,
        #     it can return a lower value than a previous call
        #     if the system clock has been set back between the two calls."
        # Unfortunately, monotonic.monotonic() is seconds since boot, not since 1970.
        # TODO:  Construct a hybrid?  Get an offset at startup then record offset + monotonic()?
        # That would mean a time change requires restart.
        # Groan, invent a qiki.Time() class?  Oh where does it end.
        # Might as well make classes qiki.Wheel() and qiki.KitchenSink().

        # NOTE:  If any of the SQL in this module generates an error in PyCharm like one of these:
        #     <comma join expression> expected, unexpected end of file
        #                 <reference> expected, unexpected end of file
        #     '(', <reference>, GROUP, HAVING, UNION, WHERE or '{' expected, got '{'
        # Then a work-around is to disable SQL inspection:
        #     Settings | Editor | Language Injections | (uncheck) python: "SQL select/delete/insert/update/create"
        # Sadly the SQL syntax highlighting is lost.
        # SEE:  http://i.imgur.com/l61ARUX.png
        # SEE:  PyCharm bug report, https://youtrack.jetbrains.com/issue/PY-18367

        self.super_query(
            'INSERT INTO', self.table,
                   '(         idn,      sbj,      vrb,      obj,      num,      txt, whn) '
            'VALUES (', (word.idn, word.sbj, word.vrb, word.obj, word.num, word.txt, whn), ')')
        # TODO:  named substitutions with NON-prepared statements??
        # THANKS:  https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursor-execute.html
        # THANKS:  About prepared statements, http://stackoverflow.com/a/31979062/673991
        self._connection.commit()
        word.whn = whn
        # noinspection PyProtectedMember
        word._now_it_exists()

    class Cursor(object):
        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            try:
                self.the_cursor = self.connection.cursor(prepared=True)
            except mysql.connector.OperationalError:
                self.connection.connect()
                self.the_cursor = self.connection.cursor(prepared=True)
            return self.the_cursor

        # noinspection PyUnusedLocal
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.the_cursor.close()

    def _cursor(self):
        return self.Cursor(self._connection)

    def _simulate_connection_neglect(self):
        """
        For testing, simulate what happens when the MySQL connection is idle for too long.

        This is easy to achieve, just close the connection.
        The symptom is the same:
            mysql.connector.errors.OperationalError: MySQL Connection not available.
        I originally thought this had something to do with the connection_timeout
        option aka socket.settimeout(), but it doesn't.
        """
        self._connection.close()

    def populate_word_from_idn(self, word, idn):
        rows = self.super_select('SELECT * FROM', self.table, 'WHERE idn =', idn)
        return self._populate_from_one_row(word, rows)

    def populate_word_from_definition(self, word, define_txt):
        rows = self.super_select(
            'SELECT * FROM', self.table, 'AS w '
            'WHERE vrb =', Word._IDN_DEFINE,
            'AND txt =', Text(define_txt),
            'ORDER BY `idn` ASC LIMIT 1'   # select the EARLIEST definition, so it's the most universal.
        )
        return self._populate_from_one_row(word, rows)

    def populate_word_from_sbj_vrb_obj(self, word, sbj, vrb, obj):
        rows = self.super_select(
            'SELECT * FROM', self.table, 'AS w '
            'WHERE sbj =', sbj,
            'AND vrb =', vrb,
            'AND obj =', obj,
            'ORDER BY `idn` DESC LIMIT 1'
        )
        return self._populate_from_one_row(word, rows)

    def populate_word_from_sbj_vrb_obj_num_txt(self, word, sbj, vrb, obj, num, txt):
        rows = self.super_select(
            'SELECT * FROM', self.table, 'AS w '
            'WHERE sbj =', sbj,
            'AND vrb =', vrb,
            'AND obj =', obj,
            'AND num =', num,
            'AND txt =', Text(txt),
            'ORDER BY `idn` DESC LIMIT 1'
        )
        return self._populate_from_one_row(word, rows)

    @staticmethod
    def _populate_from_one_row(word, rows):
        # assert len(rows) in (0, 1), "Populating from unexpectedly {} rows.".format(len(rows))
        try:
            row = next(rows)
        except StopIteration:
            return False
        else:
            word.populate_from_row(row)
            try:
                next(rows)
            except StopIteration:
                return True
            else:
                assert False, "Populating unexpected extra rows."

    def find_last(self, **kwargs):
        bunch = self.find_words(**kwargs)
        # TODO:  Limit find_words() to latest using sql LIMIT.
        try:
            return bunch[-1]
        except IndexError:
            raise self.NotFound

    # TODO:  Study JOIN with LIMIT 1 in 2 SELECTS, http://stackoverflow.com/a/28853456/673991
    # Maybe also http://stackoverflow.com/questions/11885394/mysql-join-with-limit-1/11885521#11885521

    def find_words(
        self,
        idn=None,
        sbj=None,
        vrb=None,
        obj=None,
        idn_order='ASC',
        jbo_order='ASC',
        jbo_vrb=(),
        obj_group=False,
        jbo_strictly=False,
        debug=False
    ):
        # TODO:  Lex.find()
        """
        Select words by subject, verb, and/or object.

        Return a list of choate words.

        idn,sbj,vrb,obj all restrict the list of returned words.
        jbo_vrb is not restrictive, it's elaborative.
        'jbo' being 'obj' backwards, it represents a reverse reference.
        If jbo_vrb is an iterable of verbs, each returned word has a jbo attribute
        that is a list of choate words whose object is the word.
        In other words, it gloms onto each word the words that point to it (using approved verbs).

        The order of words is chronological.
        idn_order='DESC' for reverse-chronological.
        The order of jbo words is always chronological.

        obj_group=True to collapse by obj.
        jbo_strictly means only words that are glommed.
        """

        assert isinstance(idn, (Number, Word, type(None)))
        assert isinstance(sbj, (Number, Word, type(None)))
        assert isinstance(vrb, (Number, Word, type(None))) or is_iterable(vrb)
        assert isinstance(obj, (Number, Word, type(None)))
        assert idn_order in ('ASC', 'DESC')
        assert jbo_order in ('ASC', 'DESC')
        assert isinstance(jbo_vrb, (Number, Word, type(None))) or is_iterable(jbo_vrb)
        query_args = [
            'SELECT '
            'w.idn AS idn, '
            'w.sbj AS sbj, '
            'w.vrb AS vrb, '
            'w.obj AS obj, '
            'w.num AS num, '
            'w.txt AS txt, '
            'w.whn AS whn',
            None
        ]
        if any(jbo_vrb):
            query_args += [
                ', jbo.idn AS jbo_idn'
                ', jbo.sbj AS jbo_sbj'
                ', jbo.vrb AS jbo_vrb'
                ', jbo.obj AS jbo_obj'
                ', jbo.num AS jbo_num'
                ', jbo.txt AS jbo_txt'
                ', jbo.whn AS jbo_whn',
                None
            ]
        query_args += 'FROM', self.table, 'AS w', None,
        if any(jbo_vrb):
            join = 'JOIN' if jbo_strictly else 'LEFT JOIN'
            query_args += [
                join, self.table, 'AS jbo '
                    'ON jbo.obj = w.idn '
                        'AND jbo.vrb in (', jbo_vrb, ')',
                None
            ]

        query_args += ['WHERE TRUE', None]
        query_args += self._find_where(idn, sbj, vrb, obj)

        if obj_group:
            query_args += ['GROUP BY obj', None]


        order_clause = 'ORDER BY w.idn ' + idn_order
        if any(jbo_vrb):
            order_clause += ', jbo.idn ' + jbo_order
        query_args += [order_clause]

        rows = self.super_select(*query_args, debug=debug)

        words = []
        word = None
        for row in rows:
            if word is None or row['idn'] != word.idn:
                word = self[None]
                word.populate_from_row(row)
                word.jbo = []
                words.append(word)   # To be continued, we may append to word.jbo later.
                # (So yield would not work here -- because word continues to be modified after
                # it gets appended to words.  Similarly new_jbo after appended to word.jbo.
                # No wait, that part is final.)
            jbo_idn = row.get('jbo_idn', None)
            if jbo_idn is not None:
                new_jbo = self[None]
                new_jbo.populate_from_row(row, prefix='jbo_')
                word.jbo.append(new_jbo)
        return words

    def find_idns(self, idn=None, sbj=None, vrb=None, obj=None, idn_order='ASC'):
        """
        Select word identifiers by subject, verb, and/or object.

        Return list of idns.
        """
        query_args = ['SELECT idn FROM', self.table, 'AS w WHERE TRUE', None]
        query_args += self._find_where(idn, sbj, vrb, obj)
        query_args += ['ORDER BY idn ' + idn_order]
        rows_of_idns = self.super_select(*query_args)
        idns = [row['idn'] for row in rows_of_idns]
        return idns

    @staticmethod
    def _find_where(idn, sbj, vrb, obj):
        assert isinstance(idn, (Number, Word, type(None)))
        assert isinstance(sbj, (Number, Word, type(None)))
        assert isinstance(vrb, (Number, Word, type(None))) or is_iterable(vrb)
        assert isinstance(obj, (Number, Word, type(None)))
        query_args = []
        if idn is not None:
            query_args += ['AND w.idn =', idn_from_word_or_number(idn)]
        if sbj is not None:
            query_args += ['AND w.sbj =', idn_from_word_or_number(sbj)]
        if vrb is not None:
            try:
                verbs = [idn_from_word_or_number(v) for v in vrb]
            except TypeError:
                verbs = [idn_from_word_or_number(vrb)]
            if len(verbs) < 1:
                pass
            elif len(verbs) == 1:
                query_args += ['AND w.vrb =', verbs[0]]
            else:
                query_args += ['AND w.vrb IN (', verbs[0]]
                for v in verbs[1:]:
                    query_args += [',', v]
                query_args += [')', None]
        if obj is not None:
            # TODO:  obj could be a list also.  Would help e.g. find qool verb icons.
            query_args += ['AND w.obj =', idn_from_word_or_number(obj)]
        return query_args

    class SuperSelectTypeError(TypeError):
        pass

    class SuperSelectStringString(TypeError):
        pass

    def _super_parse(self, *query_args, **kwargs):
        """
        Build a prepared statement query from a list of sql statement fragments
        interleaved with data parameters.

        Return the two parameters to cursor.execute(), namely a tuple of query and parameters.
        """
        # TODO:  Recursive query_args?
        # So super_select(*args) === super_select(args) === super_select([args]) etc.
        # Say, then this could work, super_select('SELECT *', ['FROM table'])

        debug = kwargs.pop('debug', False)
        query = ''
        parameters = []
        for index, (arg_previous, arg_next) in enumerate(zip(query_args[:-1], query_args[1:])):
            if (
                    isinstance(arg_previous, six.string_types) and
                not isinstance(arg_previous, (Text, Lex.SuperIdentifier)) and
                    isinstance(arg_next, six.string_types) and
                not isinstance(arg_next, (Text, Lex.SuperIdentifier))
            ):
                raise self.SuperSelectStringString(
                    "Consecutive super_select() arguments shouldn't be strings.  " +
                    "Pass string fields through qiki.Text().  " +
                    "Or concatenate with +, or intersperse a None.\n"
                    "Argument #{n1}: '{arg1}\n"
                    "Argument #{n2}: '{arg2}".format(
                        n1=index+1,
                        n2=index+2,
                        arg1=arg_previous,
                        arg2=arg_next
                    )
                )
                # TODO:  Report all the query_args types in this error message.
                # TODO:  Or maybe this clunky for-loop can all just go away...
                # Main purpose was to detect mistakes like this:
                #     super_select('SELECT * in word WHERE txt=', 'define')
                # Which could be an SQL injection bug.
                # But that would break anyway (unless searching for .e.g 'txt').
                # And I'm getting tired of all the Nones.
        for index_zero_based, query_arg in enumerate(query_args):
            if isinstance(query_arg, Text):
                query += '?'
                parameters.append(query_arg.unicode())
            elif isinstance(query_arg, Lex.SuperIdentifier):
                query += '`' + query_arg + '`'
            elif isinstance(query_arg, six.string_types):   # Must come after Text and Lex.SuperIdentifier tests.
                query += query_arg
            elif isinstance(query_arg, Number):
                query += '?'
                parameters.append(query_arg.raw)
            elif isinstance(query_arg, Word):
                query += '?'
                parameters.append(query_arg.idn.raw)
            # elif isinstance(query_arg, (list, tuple, set)):
            # TODO:  Dictionary for INSERT or UPDATE syntax SET c=z, c=z, c=z, ...
            elif is_iterable(query_arg):
                query += ','.join(['?']*len(query_arg))
                try:
                    parameters += self._parametric_forms(query_arg)
                except TypeError as e:
                    raise self.SuperSelectTypeError(
                        "super_select() argument {index_one_based} of {n} {what}.".format(
                            index_one_based=index_zero_based+1,
                            n=len(query_args),
                            what=str(e)
                        )
                    )
                # TODO: make these embedded iterables recursive
            elif query_arg is None:
                pass
            else:
                raise self.SuperSelectTypeError(
                    "super_select() argument {index_one_based} of {n} type {type} is not supported.".format(
                        index_one_based=index_zero_based+1,
                        n=len(query_args),
                        type=type(query_arg).__name__
                    )
                )
            query += ' '
        if debug:
            print("Query", query)
        return query, parameters

    def super_query(self, *query_args, **kwargs):
        query, parameters = self._super_parse(*query_args, **kwargs)
        with self._cursor() as cursor:
            cursor.execute(query, parameters)

    def super_select(self, *query_args, **kwargs):
        debug = kwargs.get('debug', False)
        query, parameters = self._super_parse(*query_args, **kwargs)
        if debug:
            print("Parameters", ", ".join([repr(parameter) for parameter in parameters]))
        with self._cursor() as cursor:
            cursor.execute(query, parameters)
            for row in cursor:
                field_dictionary = dict()
                if debug:
                    print(end='\t')
                for field, name in zip(row, cursor.column_names):
                    if field is None:
                        value = None
                    elif name.endswith('txt'):   # including jbo_txt
                        value = Text.decode_if_you_must(field)
                    else:
                        value = Number.from_mysql(field)
                    field_dictionary[name] = value
                    if debug:
                        print(name, repr(value), end='; ')
                yield field_dictionary
                if debug:
                    print()

    @staticmethod
    def _parametric_forms(sub_args):
        """Convert objects into MySQL parameters, ready to be substituted for '?'s."""
        for sub_arg in sub_args:
            if isinstance(sub_arg, Text):
                yield sub_arg.unicode()
            elif isinstance(sub_arg, Number):
                yield sub_arg.raw
            elif isinstance(sub_arg, Word):
                yield sub_arg.idn.raw
            else:
                raise TypeError("contains a " + type(sub_arg).__name__)

    # def words_from_idns(self, idns):
    #     # TODO:  Generator?  Is this even used anywhere??
    #     words = []
    #     for idn in idns:
    #         word = self[idn]
    #         words.append(word)
    #     return words

    # @classmethod
    # def raws_from_idns(cls, idns):
    #     # TODO:  Generator?  Is this even used anywhere??
    #     raws = []
    #     for idn in idns:
    #         raws.append(idn.raw)
    #     return raws

    def max_idn(self):
        # TODO:  Store max_idn in a singleton table?
        one_row_one_col = list(self.super_select('SELECT MAX(idn) AS max_idn FROM', self.table))
        if len(one_row_one_col) < 1:
            return Number(0)
        return_value = one_row_one_col[0]['max_idn']
        assert not return_value.is_nan()
        assert return_value.is_whole()
        return return_value

    @property
    def table(self):
        """For super_select() and for continuous validation of table name."""
        if not re.match(self._TABLE_NAME_VALIDITY, self._table):
            raise self.IllegalTableName("Not a valid table name: " + repr(self._table))
        return self.TableName(self._table)

    _TABLE_NAME_VALIDITY = r'^[A-Za-z_][A-Za-z_0-9]*$'
    _ENGINE_NAME_VALIDITY = r'^[A-Za-z_][A-Za-z_0-9]*$'

    class IllegalTableName(Exception):
        pass

    class IllegalEngineName(Exception):
        pass

    def word_from_word_or_number(self, x):
        if isinstance(x, Word):
            return x
        elif isinstance(x, Number):
            return Word(x, lex=self)
        else:
            raise TypeError("idn_from_word_or_number({}) is not supported, only Word or Number.".format(
                type(x).__name__,
            ))


def idn_from_word_or_number(x):
    if isinstance(x, Word):
        return x.idn
    elif isinstance(x, Number):
        return x
    else:
        raise TypeError(
            "idn_from_word_or_number({}) is not supported, "
            "only Word or Number.".format(
                type(x).__name__,
            )
        )


def is_iterable(x):
    """
    Yes for (tuple) or [list] or {set} or {dictionary keys}.
    No for strings.

    Ask permission before using in a for-loop.

    This implementation is better than either of:
        return hasattr(x, '__getitem__')
        return hasattr(x, '__iter__')
    SEE:  http://stackoverflow.com/a/36154791/673991
    """
    try:
        0 in x
    except TypeError as e:
        assert e.__class__ is TypeError   # A subclass of TypeError raised by comparison operators?  No thanks.
        return False
    else:
        return True
assert is_iterable(['a', 'list', 'is', 'iterable'])
assert not is_iterable('a string is not')


class Text(six.text_type):
    """
    The class for the Word txt field.

    The main use of qiki.Text() is for identifying txt field values to Lex.super_select().
    Note the only mention of UTF-8 in this module other than this class is in MySQL configuration.
    And this .utf8() method may never actually be needed anywhere anyway,
    because the MySQL connector takes unicode values in prepared statements just fine.

    Constructor accepts only Unicode in either Python 2 or 3.
        t = Text(x)
    To get unicode out:
        t.unicode()
    To get the utf8 out:
        t.utf8()
    """
    # THANKS:  Modifying a unicode/str on construction with __new__, http://stackoverflow.com/a/7255782/673991
    def __new__(cls, the_string):
        if cls.is_valid(the_string):
            return six.text_type.__new__(cls, the_string)
        else:
            raise TypeError("Text({value} type {type}) is not supported".format(
                value=repr(the_string),
                type=type(the_string).__name__
            ))

    @classmethod
    def decode_if_you_must(cls, x):
        """
        Interpret a MySQL txt field.  (Possibly the only use left.)

        Was once used by Word.__getattr__() on its name argument, when lex.word_name was a thing.
        (Now we do lex[u'word_name'] instead.)
        """
        try:
            return cls(x)   # This works in Python 3.  It raises an exception in Python 2.
        except TypeError:
            return cls(x.decode('utf-8'))   # This happens in Python 2.

    def unicode(self):
        return six.text_type(self)

    def utf8(self):
        return self.encode('utf-8')

    def native(self):
        if six.PY2:
            return self.utf8()
        else:
            return self.unicode()

    @staticmethod
    def is_valid(x):
        return isinstance(x, six.text_type)


class Qoolbar(object):
    pass


class QoolbarSimple(Qoolbar):
    def __init__(self, lex):
        assert isinstance(lex, Lex)
        self.lex = lex
        self.say_initial_verbs()
        # TODO:  Cache get_verbs().

    def say_initial_verbs(self):
        qool = self.lex.verb(u'qool')
        iconify = self.lex.verb(u'iconify')

        delete = self.lex.verb(u'delete')
        self.lex(qool, use_already=True)[delete] = 1
        self.lex(iconify, use_already=True)[delete] = 16, u'http://tool.qiki.info/icon/delete_16.png'

        like = self.lex.verb(u'like')
        self.lex(qool, use_already=True)[like] = 1
        self.lex(iconify, use_already=True)[like] = 16, u'http://tool.qiki.info/icon/thumbsup_16.png'

    def get_verbs_new(self, debug=False):
        qool_verbs = self.lex.find_words(
            vrb=self.lex[u'define'],
            # obj=self.lex[u'verb'],   # Ignore whether object is lex[verb] or lex[qool]
                                       # Because qiki playground did [lex](define][qool] = 'like'
                                       # but now we always do        [lex](define][verb] = 'like'
            jbo_vrb=(self.lex[u'iconify'], self.lex[u'qool']),
            jbo_strictly=True,
            debug=debug
        )
        verbs = []
        qool = self.lex[u'qool']
        iconify = self.lex[u'iconify']
        for qool_verb in qool_verbs:
            has_qool = False
            last_iconify_url = None
            for aux in qool_verb.jbo:
                if aux.vrb == qool:
                    has_qool = True
                elif aux.vrb == iconify:
                    last_iconify_url = aux.txt
            if has_qool and last_iconify_url is not None:
                qool_verb.icon_url = last_iconify_url
                verbs.append(qool_verb)
        return verbs

    def get_verbs(self, debug=False):
        return self.get_verbs_new(debug)

    def get_verb_dicts(self, debug=False):
        """
        Generate dictionaries about qoolbar verbs:
            idn - qstring of the verb's idn
            name - txt of the verb, e.g. 'like'
            icon_url - txt from the iconify sentence
        """
        # TODO:  Make Word json serializable, http://stackoverflow.com/a/3768975/673991
        # Then we wouldn't have to translate verbs to verb_dicts:
        verbs = self.get_verbs(debug)
        for verb in verbs:
            yield dict(
                idn=verb.idn.qstring(),
                name=verb.txt,
                icon_url=verb.icon_url
            )

    def get_verbs_old(self, debug=False):
        qoolifications = self.lex.find_words(vrb=self.lex[u'qool'], obj_group=True, debug=debug)
        verbs = []
        for qoolification in qoolifications:
            qool_verb = qoolification.obj
            icons = self.lex.find_words(vrb=self.lex[u'iconify'], obj=qool_verb, debug=debug)
            try:
                icon = icons[-1]
            except IndexError:
                pass
            else:
                qool_verb.icon_url = icon.txt
                verbs.append(qool_verb)
        return verbs

    def nums(self, obj):   # TODO:  Obsolete?
        jbo = self.lex.find_words(idn=obj, jbo_vrb=self.get_verbs())[0].jbo
        return_dict = dict()
        for word in jbo:
            icon_entry = return_dict.setdefault(word.vrb, dict())
            icon_entry[word.sbj] = dict(num=word.num)
        return return_dict

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

# TODO:  Implement use_already as a "verb property".  Aka "adverb"??
# lex.noun('adverb')
# lex.adverb('use_already')
# like = lex.verb('like')
# lex.use_already(like, 0 for defaults-to-False or 1 for True)
# alice.like(bob, "but just as a friend")   # use_already=True unnecessary
# lex.use_already(lex.define, 1)

# TODO:  w=lex(idn) etc. should start out as a phantom Word,
# which does, not read the database until or unless needed, e.g. w.sbj is used.
# That way when w.sbj is used, its members can become phantom Words themselves instead of mere Numbers
# until and unless they are used, e.g. w.sbj.sbj
# There should be __init_shallow() for Word(idn) and __init_deep() for everything else.
# And __init_deep() is called when a shallow/phantom word is used for any other purpose.
# So a shallow Word needs only properties ._idn and .lex

# TODO:  Maybe this is a use for a meta-class!
# We could get rid of the .lex property.
# Word would be abstract, and subclassed by each database (aka Lex aka Listing).
# For a word in one database to point to (to have an idn for) a word in another database,
# the idn would be suffixed.
# class Word(object); class WordInMySQL(Word); class WordQiki(WordInMySQL); class WordDjango(Word);
# Duh, Lex already IS kinda the metaclass for Word.

# TODO:  define
# Rename:  is, meta, make, be
# num
        # could mean 1=meta, 0=identical.  No because identical should itself have shades of gray.
        # could mean 1=reflexive, 0=not.  The way noun is a noun but verb is not a verb.
        # could inform the is_a() hierarchy bubbling

# TODO:  word.jbo a "soft" property that refers to the set of words whose object is word.
# Or w.jbo(vrb=qool_verbs) could filter that set down to the words whose verbs were in the iterator qool_verbs
# Maybe it should always be a method.
# Similarly word.jbs.
# word.brv?  The set of definitions and qualifiers supporting this verb??

# TODO:  Word iterators and iteratables.
# These will be needed for large sets, or sets that take a long time to determine, E.g.
    # The verbs in a qoolbar
    # A user's current qoolbar for a particular context.
    # The verbs likely of interest to a new user.
# SEE:  http://stackoverflow.com/a/24377/673991

# TODO:  The way lex comes into existence is still spooky.
# For example, why does it work if uninstall leaves lex._exists True?
# It seems to rely on non-singleton lexes (that is,
# more than one word instance that is also a LexMySQL instance)
# for the database record to be written at the birth of a lex.

# TODO:  define imbues a word with a string name, by which it can be found.  Another way?
# Better to do that with a "name" verb?
# So instead of:
#     lex-define-noun "path"
#     lex-browse-path "/root"
# it could be:
#     lex-define-noun  <-- this is the path word
#     lex-name-path "path"   <-- this is how you find it
#     lex-browse-path "/root"
# That way the uniqueness thing would be confined to vrb=name words
# And there could be defined nouns that didn't have a name, known only by their idn
# Or maybe rewinding to the first method, an unnamed define would have a blank txt
# And that didn't have to be unique, and could never be Word(txt) searched for.
