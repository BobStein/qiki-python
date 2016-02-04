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
        self.whn = None
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
            # TODO:  Should this be Word instead of type(self)?
            # As it stands with type(self) DerivedWord(Word) would TypeError, not copy.
            # For example Lex(Word).  Is that desirable or not?
            # WTF, should Lex by Word's meta-class??
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

    _IDN_DEFINE = Number(1)
    _IDN_NOUN   = Number(2)
    _IDN_VERB   = Number(3)
    _IDN_AGENT  = Number(4)
    _IDN_LEX    = Number(5)

    _IDN_MAX_FIXED = Number(5)

    TXT_TYPES = (six.string_types, six.binary_type)

    class NoSuchAttribute(AttributeError):
        pass

    def __getattr__(self, noun_txt):
        assert hasattr(self, 'lex'), "No lex, can't x.{noun}".format(noun=noun_txt)
        assert self.lex is not None, "Lex is None, can't x.{noun}".format(noun=noun_txt)
        assert self.lex.exists, "Lex doesn't exist yet, can't x.{noun}".format(noun=noun_txt)
        # Testing lex.exists prevents infinity.
        # This would happen below where lex(noun_txt) would call Word.__call__()
        # But in very early conditions lex.is_lex() is false before it's read its row from the database.
        # (By the way why does is_lex() depend on exists? There was probably some reason.)
        # So it asks instead if lex is a verb, which calls .is_a()
        # which comes right back here for reasons I never did figure out (because there IS a Word.is_a()).
        # This madness would happen e.g. when Lex.populate_from_idn() called a bogus function:
        #     return self.populate_from_one_row_misnamed_or_something(word, one_row)
        assert self.lex.is_lex(), "Lex isn't a lex, can't x.{noun}".format(noun=noun_txt)
        assert hasattr(self.lex, '__call__'), "Lex isn't callable, can't x.{noun}".format(noun=noun_txt)
        return_value = self.lex(noun_txt)
        # FIXME:  catch NotExist: raise NoSuchAttribute (a gross internal error)
        if not return_value.exists:
            raise self.NoSuchAttribute("Word has no attribute {name}".format(
                # word=repr(self),   # Infinity:  repr() calls hasattr() tries __getattr__()...
                name=repr(noun_txt)
            ))
        return_value._word_before_the_dot = self   # In s.v(o) this is how v remembers the s.
        return return_value

    def __call__(self, *args, **kwargs):
        if self.is_lex():   # Get a word by its text:  lex(t)  e.g.  lex('anna')
            # lex(t) in English:  Lex defines a word named t.
            # lex('text') - find a word by its txt
            existing_word = self.spawn(*args, **kwargs)
            # FIXME:  if not exists: raise NotExist
            if existing_word.idn == self.idn:
                return self   # lex is a singleton.  Why is this important?
            else:
                return existing_word
        elif self.is_a_verb(reflexive=False):   # Quintessential word creation:  s.v(o)  e.g. anna.like(bart)
            # (But not s.verb(o) -- the 'verb' word is not itself a verb.)
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
            if self._word_before_the_dot is None:
                sbj = self.lex   # Lex can be the implicit subject. Renounce?
            else:
                sbj = self._word_before_the_dot
            # assert self._word_before_the_dot is not None, "A verb can't (yet) be called without a preceding subject."
            # TODO:  allow  v(t)?  In English:  Lex defines a v named t.  And v is a verb.
            # But this looks a lot like v(o) where o could be identified by a string, so maybe support neither?
            # In other words, don't v(t), instead lex.define(v,n,t)
            # And no v(object_name), instead s.v(lex(object_name),n,t)
            if len(args) == 1:   # subject.verb(object) <-- getter only
                existing_word = self.spawn(sbj=sbj.idn, vrb=self.idn, obj=obj.idn)
                existing_word._from_sbj_vrb_obj()
                assert existing_word.exists, "The form s.v(o) is a getter.  A setter looks like: s.v(o,1,'')"
            else:   # subject.verb(object, number)        \ <-- these are getter or setter
                    # subject.verb(object, number, text)  /
                if kwargs.get('use_already', False):
                    existing_word = self.spawn(
                        sbj=sbj.idn,
                        vrb=self.idn,
                        obj=obj.idn,
                        num=num,
                        txt=txt,
                    )
                    existing_word._from_sbj_vrb_obj_num_txt()
                    if not existing_word.exists:
                        existing_word = self.sentence(
                            sbj=sbj,
                            vrb=self,
                            obj=obj,
                            num=num,
                            txt=txt,
                        )
                else:
                    existing_word = self.sentence(
                        sbj=sbj,
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
            # And in this o(t) form you can't supply a num.
            assert self.lex.is_lex()
            txt = kwargs.get('txt', args[0] if len(args) > 0 else None)
            assert isinstance(txt, self.TXT_TYPES), "Defining a new noun, but txt is a " + type(txt).__name__
            try:
                existing_or_new_word = self.lex.define(self, *args, **kwargs)
            except TypeError:
                raise
                # FIXME:  Problems with the o(t) format:
                # - similar to s.v(o) and so error messages are likely to be confusing
                # - haven't thought of a simpler way to do lex.define(o,t) than o(t) yet.
                # - But if o(t) is acceptable, allow s.o(t) shorthand for s.define(o,t), yuck
            return existing_or_new_word
        else:
            raise self.NonVerbUndefinedAsFunctionException(
                "Word {idn} cannot be used as a function -- it's neither a verb nor a definition.".format(
                    idn=int(self.idn)
                )
            )

    def define(self, obj, txt, num=Number(1)):
        # One of the only cases where txt comes before num.  Are there others?
        """Define a word.  Name it txt.  Its type or class is obj.

        Example:
            agent = lex('agent')
            lex.define(agent, 'fred')

        The obj may be identified by its txt, example:
            lex.define('agent', 'fred')
        """
        assert isinstance(obj, (Word, self.TXT_TYPES))
        assert isinstance(txt, self.TXT_TYPES), "define() txt cannot be a {}".format(type(txt).__name__)
        assert isinstance(num, Number)
        possibly_existing_word = self.spawn(txt)
        # How to handle "duplications"
        # TODO:  Shouldn't this be spawn(sbj=lex, vrb=define, txt)?
        # TODO:  use_already option?
        # But why would anyone want to duplicate a definition with the same txt and num?
        if possibly_existing_word.exists:
            # TODO:  Create a new word if the num's are different?
            return possibly_existing_word
        if isinstance(obj, self.TXT_TYPES):   # Meta definition:  s.define('x') is equivalent to s.define(lex('x'))
            obj = self.spawn(obj)
        new_word = self.sentence(sbj=self, vrb=self.lex('define'), obj=obj, num=num, txt=txt)
        return new_word

    def sentence(self, sbj, vrb, obj, num, txt):
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
        assert isinstance(num, Number),         "num cannot be a {type}".format(type=type(num).__name__)
        assert isinstance(txt, self.TXT_TYPES), "txt cannot be a {type}".format(type=type(txt).__name__)
        if not vrb.is_a_verb():
            raise self.NotAVerb("Sentence verb {} is not a verb.".format(vrb.qstring()))
            # NOTE:  Rare error, because sentence() almost always comes from s.v(o).
        new_word = self.spawn(sbj=sbj.idn, vrb=vrb.idn, obj=obj.idn, num=num, txt=txt)
        new_word.save()
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

    class NotAVerb(Exception):
        pass

    class MissingFromLex(Exception):
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
                self.txt = listed_instance.txt
                self.exists = True
        else:
            self._idn = idn
            if not self.lex.populate_word_from_idn(self, idn):
                raise self.MissingFromLex

    def _from_definition(self, txt):
        """Construct a Word from its txt, but only when it's a definition."""
        assert isinstance(txt, self.TXT_TYPES)
        if not self.lex.populate_word_from_definition(self, txt):
            self.txt = txt

    def _from_word(self, word):
        if word.is_lex():
            raise ValueError   # lex is a singleton.  TODO:  Explain why this should be.
        assert word.exists
        self.lex = word.lex
        self._from_idn(word.idn)

    def _from_sbj_vrb_obj(self):
        """Construct a word from its subject-verb-object."""
        assert isinstance(self.sbj, Number)
        assert isinstance(self.vrb, Number)
        assert isinstance(self.obj, Number)
        self.lex.populate_word_from_sbj_vrb_obj(self, self.sbj, self.vrb, self.obj)

    def _from_sbj_vrb_obj_num_txt(self):
        """Construct a word from its subject-verb-object and its num and txt."""
        assert isinstance(self.sbj, Number)
        assert isinstance(self.vrb, Number)
        assert isinstance(self.obj, Number)
        assert isinstance(self.num, Number)
        assert isinstance(self.txt, six.string_types)
        self.lex.populate_word_from_sbj_vrb_obj_num_txt(
            self,
            self.sbj,
            self.vrb,
            self.obj,
            self.num,
            self.txt
        )

    def populate_from_row(self, row):
        self._idn = row['idn']
        self.sbj = row['sbj']
        self.vrb = row['vrb']
        self.obj = row['obj']
        self.num = row['num']
        self.txt = row['txt']
        self.whn = row['whn']
        self.exists = True

    def is_a(self, word, reflexive=True, recursion=10):
        assert recursion >= 0
        if reflexive and self.idn == word.idn:
            return True
        if recursion <= 0:
            return False
        if not self.exists:
            return False
        if not hasattr(self, 'vrb'):
            return False
        if self.vrb != self._IDN_DEFINE:
            return False
        if self.obj == word.idn:
            return True
        parent = self.spawn(self.obj)
        if parent.idn == self.idn:
            return False
        return parent.is_a(word, reflexive=reflexive, recursion=recursion-1)

    def is_a_noun(self, reflexive=True, **kwargs):
        """Noun is a noun.  Really, everything is a noun."""
        assert hasattr(self, 'lex')
        return self.is_a(self.lex.noun, reflexive=reflexive, **kwargs)

    def is_a_verb(self, reflexive=False, **kwargs):
        """Verb is not a verb.  But anything defined as a verb is a verb."""
        assert hasattr(self, 'lex')
        return self.is_a(self.lex.verb, reflexive=reflexive, **kwargs)

    def is_define(self):
        """Is this word the one and only verb (whose txt is) 'define'."""
        return self.idn == self._IDN_DEFINE

    def is_defined(self):
        """Test whether a word is the product of a definition.

        That is, whether the sentence that creates it uses the verb 'define'."""
        return self.vrb == self._IDN_DEFINE

    def is_noun(self):
        return self.idn == self._IDN_NOUN

    def is_verb(self):
        """Not to be confused with is_a_verb().

        is_a_verb() -- is this word in a []-(define)-[verb] sentence, recursively.
        is_verb() -- is this the one-and-only "verb" word, i.e. [lex]-(define)-[noun]"verb", i.e. id == _IDN_VERB
        """
        return self.idn == self._IDN_VERB

    def is_agent(self):
        return self.idn == self._IDN_AGENT

    def is_lex(self):
        return isinstance(self, Lex) and self.exists and self.idn == self._IDN_LEX

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

    def __str__(self):
        if hasattr(self, 'txt'):
            return self.txt
        else:
            return repr(self)

    class Incomparable(TypeError):
        pass

    def __eq__(self, other):
        # TODO:  if self._word_before_the_dot != other._word_before_the_dot return False ?
        # I think so, but I wonder if this would throw off other things.
        # Because the "identity" of a word should be fully contained in its idn.
        # And yet a patronized word (s.v) behaves differently from an orphan word (lex('v')).
        if other is None:
            return False   # Needed for a particular word == none comparison in Python 3
            # Mystery:  Why isn't that test needed in Python 2?
            # The actual distinction is comparing two word's _word_before_the_dot members when one is None.
            # That should be a comparison of a word instance with None.
            # Yet a simple Word() == None does seem to come here.
            # See test_word.py test_verb_paren_object_deferred_subject()
        try:
            other_exists = other.exists
            other_idn = other.idn
        except AttributeError:
            raise self.Incomparable("Words cannot be compared with a " + type(other).__name__)
        else:
            return self.exists and other_exists and self.idn == other_idn

    @property
    def idn(self):
        return Number(self._idn)   # Copy constructor so e.g. w.idn.suffix(n) won't modify w.idn.
                                   # TODO:  but then what about w.sbj.add_suffix(n), etc.?
                                   # So this passing through Number() is a bad idea.
                                   # Plus this makes x.idn fundamentally differ from x._idn, burdening debug.

    @idn.setter
    def idn(self, value):
        raise AttributeError("Cannot set a Word's idn.")

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
        # Another case where txt comes before num, the exception.
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


class Lex(Word):   # rename candidates:  Site, Book, Server, Domain, Dictionary, Qorld, Lex, Lexicon
                      #                     Station, Repo, Repository, Depot, Log, Tome, Manuscript, Diary,
                      #                     Heap, Midden, Scribe, Stow (but it's a verb), Stowage,
                      # Eventually, this will encapsulate other word repositories
                      # Make this an abstract base class

    class TableName(str):
        pass


class LexMySQL(Lex):
    def __init__(self, **kwargs):
        language = kwargs.pop('language')
        assert language == 'MySQL'
        self._table = kwargs.pop('table')
        self._engine = kwargs.pop('engine', 'InnoDB')
        self._txt_type = kwargs.pop('txt_type', 'TEXT')
        self._connection = mysql.connector.connect(**kwargs)
        self.lex = self
        self.last_inserted_whn = None
        try:
            super(LexMySQL, self).__init__(self._IDN_LEX, lex=self)
        except mysql.connector.ProgrammingError as exception:
            exception_message = str(exception)
            if re.search(r"Table .* doesn't exist", exception_message):
                # TODO:  Better detection of automatic table creation opportunity.
                self.install_from_scratch()
                # TODO:  Don't super() twice -- cuz it's not D.R.Y.
                # TODO:  Don't install in unit tests if we're about to uninstall.
                super(LexMySQL, self).__init__(self._IDN_LEX, lex=self)
            else:
                assert False, exception_message
        except Word.MissingFromLex:
            self._install_seminal_words()

        assert self.exists
        cursor = self._cursor()
        cursor.execute('SET NAMES utf8mb4 COLLATE utf8mb4_general_ci')
        # THANKS:  http://stackoverflow.com/a/27390024/673991
        cursor.close()
        assert self.is_lex()
        assert self._connection.is_connected()

    def install_from_scratch(self):
        """Create database table and insert words.  Or do nothing if table and/or words already exist."""
        cursor = self._cursor()
        query = """
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
                ENGINE = `{engine}`
                DEFAULT CHARACTER SET = utf8mb4
                DEFAULT COLLATE = utf8mb4_general_ci
            ;
        """.format(
            table=self._table,
            txt_type=self._txt_type,   # But using this is a hard error:  <type> expected found '{'
            engine=self._engine,
        )
        query = query.replace('TEXT', self._txt_type)   # Workaround for hard error using {txt_type}
        cursor.execute(query)
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
        self._seminal_word(self._IDN_DEFINE, self._IDN_VERB,  u'define')
        self._seminal_word(self._IDN_NOUN,   self._IDN_NOUN,  u'noun')
        self._seminal_word(self._IDN_VERB,   self._IDN_NOUN,  u'verb')
        self._seminal_word(self._IDN_AGENT,  self._IDN_NOUN,  u'agent')
        self._seminal_word(self._IDN_LEX,    self._IDN_AGENT, u'lex')


        if not self.exists:
            self._from_idn(self._IDN_LEX)
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
            sbj = self._IDN_LEX,
            vrb = self._IDN_DEFINE,
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

    _default_find_sql = 'ORDER BY idn ASC'
    # TODO:  Start and number parameters, for LIMIT clause.

    def populate_word_from_idn(self, word, idn):
        one_row = self.super_select("SELECT * FROM", self.table, "WHERE idn =", idn)
        return self.populate_from_one_row(word, one_row)

    def populate_word_from_definition(self, word, define_txt):
        one_row = self.super_select(
            "SELECT * FROM",
            self.table,
            "WHERE vrb =",
            Word._IDN_DEFINE,
            "AND txt =",
            Text(define_txt)
        )
        return self.populate_from_one_row(word, one_row)

    def populate_word_from_sbj_vrb_obj(self, word, sbj, vrb, obj):
        one_row = self.super_select(
            "SELECT * FROM",
            self.table,
            "WHERE sbj =",
            sbj,
            "AND vrb =",
            vrb,
            "AND obj =",
            obj,
            "ORDER BY `idn` DESC LIMIT 1"
        )
        return self.populate_from_one_row(word, one_row)


    def populate_word_from_sbj_vrb_obj_num_txt(self, word, sbj, vrb, obj, num, txt):
        one_row = self.super_select(
            "SELECT * FROM",
            self.table,
            "WHERE sbj =",
            sbj,
            "AND vrb =",
            vrb,
            "AND obj =",
            obj,
            "AND num =",
            num,
            "AND txt =",
            Text(txt),
            "ORDER BY `idn` DESC LIMIT 1"
        )
        return self.populate_from_one_row(word, one_row)

    @staticmethod
    def populate_from_one_row(word, one_row):
        assert len(one_row) in (0,1), "Populating from unexpectedly {} rows.".format(len(one_row))
        if len(one_row) > 0:
            row = one_row[0]
            word.populate_from_row(row)
            return True
        return False

    def find_words(self, sbj=None, vrb=None, obj=None, sql=_default_find_sql):
        """Select words by subject, verb, and/or object.

        Return list of words."""
        idns = self.find_idns(sbj,vrb,obj, sql)
        return self. words_from_idns(idns)
        # TODO:  More efficient to do one SELECT-* than one SELECT-* plus a buncha SELECT-idns

    def find_idns(self, sbj=None, vrb=None, obj=None, sql=_default_find_sql):
        """Select words by subject, verb, and/or object.

        Return list of idns."""
        query_args = ['SELECT idn FROM', self.table, 'WHERE TRUE', None]
        if sbj is not None:
            query_args += ['AND sbj=', idn_from_word_or_number(sbj)]
        if vrb is not None:
            try:
                verbs = [idn_from_word_or_number(v) for v in vrb]
            except TypeError:
                verbs = [idn_from_word_or_number(vrb)]
            if len(verbs) < 1:
                pass
            elif len(verbs) == 1:
                query_args += ['AND vrb =', verbs[0]]
            else:
                query_args += ['AND vrb IN (', verbs[0]]
                for v in verbs[1:]:
                    query_args += [',', v]
                query_args += [')', None]
        if obj is not None:
            query_args += ['AND obj=', idn_from_word_or_number(obj)]
        query_args += [sql]
        rows_of_idns = self.super_select(*query_args)
        idns = [row['idn'] for row in rows_of_idns]
        return idns

    class SuperSelectTypeError(TypeError):
        pass

    class SuperSelectStringString(TypeError):
        pass

    def super_select(self, *query_args, **kwargs):
        # TODO:  Recursive lists in query_args?
        debug = kwargs.pop('debug', False)
        query = ""
        parameters = []
        for arg_previous, arg_next in zip(query_args[:-1], query_args[1:]):
            if (
                    isinstance(arg_previous, six.string_types) and
                not isinstance(arg_previous, (Text, Lex.TableName)) and
                    isinstance(arg_next, six.string_types) and
                not isinstance(arg_next, (Text, Lex.TableName))
            ):
                raise self.SuperSelectStringString(
                    "Consecutive super_select() arguments shouldn't be strings.  " +
                    "Pass string fields through qiki.Text().  " +
                    "Or make a class to encapsulate "
                )
                # TODO:  Complete report of all the query_args types
                # TODO:  Or maybe this can all just go away...
                # Main purpose was to detect mistakes like this:
                #     super_select('SELECT * in word WHERE txt=', 'define')
                # Which could be an SQL injection bug.
                # But that would break anyway (unless searching for .e.g 'txt').
                # And I'm getting tired of all the Nones.
        for index_zero_based, query_arg in enumerate(query_args):
            if isinstance(query_arg, Text):
                query += '?'
                parameters.append(query_arg.the_string)
            elif isinstance(query_arg, Lex.TableName):
                query += '`' + query_arg + '`'
            elif isinstance(query_arg, six.string_types):   # Must come after Text and Lex.TableName tests.
                query += query_arg
            elif isinstance(query_arg, Number):
                query += '?'
                parameters.append(query_arg.raw)
            elif isinstance(query_arg, Word):
                query += '?'
                parameters.append(query_arg.idn.raw)
            elif isinstance(query_arg, (list, tuple)):
                query += ','.join(['?']*len(query_arg))
                parameters += [idn_from_word_or_number(x).raw for x in query_arg]
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
        cursor = self.lex._connection.cursor(prepared=True)
        if debug:
            print("Query", query)
        cursor.execute(query, parameters)
        rows_of_fields = []
        for row in cursor:
            field_dictionary = dict()
            if debug:
                print(end='\t')
            for field, name in zip(row, cursor.column_names):
                if field is None:
                    value = None
                elif name == 'txt':
                    # TODO:  If name ends in 'txt'?
                    value = six.text_type(field.decode('utf-8'))
                else:
                    value = Number.from_mysql(field)
                field_dictionary[name] = value
                if debug:
                    print(name, repr(value), end='; ')
            rows_of_fields.append(field_dictionary)
            if debug:
                print()
        return rows_of_fields

    def words_from_idns(self, idns):
        words = []
        for idn in idns:
            word = self(idn)
            # This calls Word._from_idn(), which calls Word._load_row().
            # TODO:  Move them here.
            words.append(word)
        return words

    @classmethod
    def raws_from_idns(cls, idns):
        raws = []
        for idn in idns:
            raws.append(idn.raw)
        return raws

    def max_idn(self):
        # TODO:  Store max_idn in a singleton table?
        one_row_one_col = self.super_select('SELECT MAX(idn) AS max_idn FROM', self.table)
        if len(one_row_one_col) < 1:
            return Number(0)
        return_value = one_row_one_col[0]['max_idn']
        assert not return_value.is_nan()
        assert return_value.is_whole()
        return return_value

    @property
    def table(self):
        """For super_select()"""
        return self.TableName(self._table)




def idn_from_word_or_number(x):
    if isinstance(x, Word):
        return x.idn
    elif isinstance(x, Number):
        return x
    else:
        raise TypeError("idn_from_word_or_number({}) is not supported, only Word or Number.".format(
            type(x).__name__,
        ))



class Text(object):
    """The only use of qiki.Text() so far is for identifying txt field values to Lex.super_select()."""
    # This can't simply derive from six.text_type
    # Because in Python 3 that's str
    # And str(u'string'.encode('utf-8')) == "b'string'"
    # That's right, a doubly-encoded string!  Just like repr()

    def __init__(self, the_string):
        """Accept either Unicode or UTF-8-encoded string in either Python 2 or 3.

        Actually it's the MySQL Connector that encapsulates both these flexibilities."""
        self.the_string = the_string


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
