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
        elif isinstance(content, type(self)):   # Word(some_other_word)
            # TODO:  Should this be Word instead of type(self)?
            # As it stands with type(self), DerivedWord(Word) would TypeError, not copy.
            # For example Lex(Word).  Is that desirable or not?
            # Perhaps yes, we may not know how to handle DerivedWord here.
            # And if it wants to clone it should do so in its own __init__().
            # Perhaps no, we could try to handle it; it's easy to override.
            # WTF, should Lex be Word's meta-class??
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

    def _now_it_doesnt_exist(self):
        self._exists = False

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
            # e.g. ('_not_exists', '_is_inchoate', '_idn', '_word_before_the_dot')
            return None
            # XXX:  More pythonic to raise AttributeError
        if attribute_name in ('sbj', 'vrb', 'obj', 'num', 'txt', 'whn'):
            self._choate()
            if self._fields is None:
                return None
                # XXX:  More pythonic to raise AttributeError
            try:
                return self._fields[attribute_name]
            except KeyError:
                return None
                # XXX:  More pythonic to raise AttributeError
        if attribute_name == 'do_not_call_in_templates':
            # THANKS:  for this Django flag, maybe http://stackoverflow.com/a/21711308/673991
            return True
        noun_txt = Text.decode_if_desperate(attribute_name)
        assert hasattr(self, 'lex'), "No lex, can't x.{noun}".format(noun=noun_txt)
        assert self.lex is not None, "Lex is None, can't x.{noun}".format(noun=noun_txt)
        assert self.lex.exists(), "Lex doesn't exist yet, can't x.{noun}".format(noun=noun_txt)

        # Testing lex.exists() prevents infinity.
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
        if not return_value.exists():
            raise self.NoSuchAttribute("Word has no attribute {name}".format(
                # word=repr(self),   # Infinity:  repr() calls hasattr() tries __getattr__()...
                name=repr(noun_txt)
            ))
        return_value._word_before_the_dot = self   # In s.v(o) this is how v remembers the s.
        # TODO:  Better way?  Descriptor, decorator, or metaclass?
        # Or maybe before we do s.v(o) we have to s.verb('v') to declare that v is a verb?
        # Might be safer somehow.
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
            # DONE:  s.v(o,num=n)
            # DONE:  s.v(o,num_add=n)
            # DONE:  s.v(o,n,t)
            # DONE:  o(t) -- shorthand for lex.define(o,1,t)
            # DONE:  x = s.v; x(o...) -- s.v(o...) with an intermediate variable
            # TODO:  Disallow s.v(o,t,n,etc)

            # TODO:  Avoid ambiguity of s.v(o, '0q80', '0q82_01') -- which is txt, which is num?
            # TODO:  Disallow positional n,t?  Keyword-only num=n,txt=t would have flexible order.
            # SEE:  https://www.python.org/dev/peps/pep-3102/
            # SEE:  http://code.activestate.com/recipes/577940-emulate-keyword-only-arguments-in-python-2/

            # TODO:  Keyword arguments would look like:
            # TODO:  s.v(o,txt=t)
            # TODO:  s.v(o,num=n,txt=t)
            # TODO:  s.v(o,txt=t,num=n)

            # TODO:  More weirdos:
            # TODO:  v(o,n,t) -- lex is the implicit subject
            # TODO:  s.v(o,num_multiply=n)

            # TODO:  Groan, what follows should be simpler...

            if self._word_before_the_dot is None:
                sbj = self.lex   # Lex can be the implicit subject. Renounce?
            else:
                sbj = self._word_before_the_dot
                del self._word_before_the_dot
                # TODO:  This enforces SOME single use, but is it enough?
                # TODO:  And would this be too much if for example s.v([o1,o2,o3]) needed the sbj multiple times?

            try:
                obj = args[0]
            except IndexError:
                raise self.MissingObj("Calling a verb method requires an object.")

            # XXX:  Refactor the following num/num_add logic
            # Separate these tasks:  (1) getter or setter (2) num by position or keyword
            # This will get worse after (3) txt by keyword
            is_getter = False
            try:
                num = args[1]
            except IndexError:
                if 'num' not in kwargs and 'num_add' not in kwargs:
                    is_getter = True
            else:
                if 'num' in kwargs:
                    raise self.SentenceArgs("Twice specified num, by the 2nd position and by keyword.")
                elif num is not None:
                    kwargs['num'] = num

            if is_getter:   # s.v(o) flavor -- with no num or num_add -- this is a getter
                if len(kwargs) != 0:
                    raise self.NoSuchKwarg("Unrecognized keywords in s.v(o) call: " + repr(kwargs))
                existing_word = self.spawn(sbj=sbj, vrb=self, obj=obj)
                existing_word._from_sbj_vrb_obj()
                if not existing_word.exists():
                    raise self.MissingFromLex(
                        "The form s.v(o) is a getter.  "
                        "So that word must exist already.  "
                        "A setter would need a num or num_add, e.g.:  s.v(o,1)"
                    )
                return existing_word
            else:   # s.v(o, num or num_add, maybe txt, etc.) flavor -- this is a setter or adder
                try:
                    kwargs['txt'] = args[2]
                except IndexError:
                    kwargs['txt'] = u''
                return self.sentence(
                    sbj=sbj,
                    vrb=self,
                    obj=obj,
                    **kwargs
                )

        elif self.is_defined():   # Implicit define, e.g.  beth = lex.agent('beth'); like = lex.verb('like')
            # o(t) in English:  Lex defines an o named t.  And o is a noun.
            # object('text') ==> lex.define(object, Number(1), 'text')
            # And in this o(t) form you can't supply a num.
            assert self.lex.is_lex()
            txt = kwargs.get('txt', args[0] if len(args) > 0 else None)
            assert Text.is_valid(txt), "Defining a new noun, but txt is a " + type(txt).__name__
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
        if Text.is_valid(obj):   # Meta definition:  s.define('x') is equivalent to s.define(lex('x'))
            obj = self.spawn(obj)
        assert isinstance(obj, Word)
        assert Text.is_valid(txt), "define() txt cannot be a {}".format(type(txt).__name__)
        assert isinstance(num, Number)
        possibly_existing_word = self.spawn(txt)
        # How to handle "duplications"
        # TODO:  Shouldn't this be spawn(sbj=lex, vrb=define, txt)?
        # TODO:  use_already option?
        # But why would anyone want to duplicate a definition with the same txt and num?
        if possibly_existing_word.exists():
            # TODO:  Create a new word if the num's are different?
            return possibly_existing_word
        new_word = self.sentence(sbj=self, vrb=self.lex(u'define'), obj=obj, num=num, txt=txt)
        return new_word

    def sentence(self, *args, **kwargs):
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
        original_kwargs = kwargs.copy()
        try:
            sbj = kwargs.pop('sbj')
            vrb = kwargs.pop('vrb')
            obj = kwargs.pop('obj')
        except KeyError:
            raise self.SentenceArgs("Word.sentence() requires sbj, vrb, and obj arguments." + repr(original_kwargs))

        try:
            if kwargs['num'] is not None and kwargs['num_add'] is not None:
                raise self.SentenceArgs("Word.sentence() cannot specify both num and num_add.")
        except KeyError:
            pass

        num = kwargs.pop('num', Number(1))
        txt = kwargs.pop('txt', u'')
        use_already = kwargs.pop('use_already', False)
        num_add = kwargs.pop('num_add', None)
        if len(args) != 0:
            raise self.SentenceArgs("Word.sentence() requires keyword arguments, not positional: " + repr(args))
        if len(kwargs) != 0:
            raise self.SentenceArgs("Word.sentence() doesn't understand these arguments: " + repr(kwargs))
        # DONE:  Moved use_already option to here, from __call__()?
        # Then define() could just call sentence() without checking spawn() first?
        # Only callers to sentence() are __call__() and define().
        assert isinstance(sbj, (Word, Number)), "sbj cannot be a {type}".format(type=type(sbj).__name__)
        assert isinstance(vrb, (Word, Number)), "vrb cannot be a {type}".format(type=type(vrb).__name__)
        assert isinstance(obj, (Word, Number)), "obj cannot be a {type}".format(type=type(obj).__name__)
        assert Text.is_valid(txt),              "txt cannot be a {type}".format(type=type(txt).__name__)
        new_word = self.spawn(
            sbj=sbj,
            vrb=vrb,
            obj=obj,
            num=Number(num),
            txt=txt
        )
        if num_add is not None:
            new_word._from_sbj_vrb_obj()
            if new_word.exists():
                new_word._fields['num'] += Number(num_add)
            else:
                new_word._fields['num'] = Number(num_add)
            new_word.save()
        elif use_already:
            assert isinstance(num, numbers.Number), "num cannot be a {type}".format(type=type(num).__name__)
            new_word._from_sbj_vrb_obj_num_txt()
            if not new_word.exists():
                new_word.save()
        else:
            assert isinstance(num, numbers.Number), \
                "Invalid for num to be a {num_type} while num_add is a {num_add_type}".format(
                    num_type=type(num).__name__,
                    num_add_type=type(num_add).__name__,
                )
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

    class MissingFromLex(Exception):
        """Looking up a word by a nonexistent idn or other criteria."""
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
            # if not self.lex.populate_word_from_idn(self, idn):
            #     raise self.MissingFromLex

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
        """Word clones itself but the copy is inchoate.

        Useful for words as dictionary keys."""
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
        return self.vrb.idn == self._IDN_DEFINE

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
        return isinstance(self, Lex) and self.exists() and self.idn == self._IDN_LEX

    def description(self):
        sbj = self.spawn(self.sbj.idn)
        vrb = self.spawn(self.vrb.idn)
        obj = self.spawn(self.obj.idn)
        return u"{sbj}.{vrb}({obj}, {num}{maybe_txt})".format(
            sbj=str(sbj),
            vrb=str(vrb),
            obj=str(obj),
            # TODO:  Would str(x) cause infinite recursion?  Not if str() doesn't call description()
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
        # if not self.exists():
        #     raise TypeError("A Word must exist to be hashable.")   WRONG!  It can be inchoate.
        return hash(self.idn)

    # class Incomparable(TypeError):
    # class Incomparable(Exception):
    #     pass

    def __eq__(self, other):
        # TODO:  if self._word_before_the_dot != other._word_before_the_dot return False ?
        try:
            return self.idn == other.idn
        except AttributeError:
            return False


    def __ne__(self, other):
        return not self.__eq__(other)

        # # I think so, but I wonder if this would throw off other things.
        # # Because the "identity" of a word should be fully contained in its idn.
        # # And yet a patronized word (s.v) behaves differently from an orphan word (lex('v')).
        # if other is None:
        #     return False   # Needed for a particular word == none comparison in Python 3
        #     # Mystery:  Why isn't that test needed in Python 2?
        #     # The actual distinction is comparing two word's _word_before_the_dot members when one is None.
        #     # That should be a comparison of a word instance with None.
        #     # Yet a simple Word() == None does seem to come here.
        #     # See test_word.py test_verb_paren_object_deferred_subject()
        #
        # try:
        #     other_is_inchoate = other._is_inchoate
        #     self_is_inchoate = self._is_inchoate
        # except AttributeError:
        #     return False
        #
        #
        #
        # try:
        #     other_exists = other.exists()
        #     other_idn = other.idn
        # except AttributeError:
        #     return False
        #     # It was not pythonic to raise an exception on comparing words and numbers.
        #     # That is just plain simply False.
        #     # For one thing, it flummoxed is_iterable(), which did `0 in x` and if x was a tuple
        #     # containing words, it raised Incomparable, and since Incomparable was a TypeError,
        #     # is_iterable() returned False.  Falsely so!
        #     # What used to be here:
        #     #     raise self.Incomparable("Words cannot be compared with a " + type(other).__name__)
        # else:
        #     return self.exists() and other_exists and self.idn == other_idn

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

    # noinspection PyClassHasNoInit
    class DefineDuplicateException(Exception):
        pass

    # noinspection PyClassHasNoInit
    class NonVerbUndefinedAsFunctionException(TypeError):
        pass


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
        # self.num = None
        # self.txt = None
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


class Lex(Word):   # rename candidates:  Site, Book, Server, Domain, Dictionary, Qorld, Lex, Lexicon
                      #                     Station, Repo, Repository, Depot, Log, Tome, Manuscript, Diary,
                      #                     Heap, Midden, Scribe, Stow (but it's a verb), Stowage,
                      # Eventually, this will encapsulate other word repositories
                      # Make this an abstract base class

    class TableName(str):
        pass

    class NotFound(Exception):
        pass

    class ConnectError(Exception):
        pass


# noinspection SqlDialectInspection
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

        assert self.exists()
        cursor = self._cursor()
        cursor.execute('SET NAMES utf8mb4 COLLATE utf8mb4_general_ci')
        # THANKS:  http://stackoverflow.com/a/27390024/673991
        cursor.close()
        assert self.is_lex()
        assert self._connection.is_connected()

    def install_from_scratch(self):
        """Create database table and insert words.  Or do nothing if table and/or words already exist."""
        if not re.match(self._ENGINE_NAME_VALIDITY, self._engine):
            raise self.IllegalEngineName("Not a valid table name: " + repr(self._engine))

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
            table=self.table,
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
        def seminal_word(_idn, _obj, _txt):
            x1 = repr(self._exists)
            """Subject is always 'lex'.  Verb is always 'define'."""
            word = self.spawn(_idn)
            if not word.exists():
                self._install_word(_idn, _obj, _txt)
                word = self.spawn(_idn)
            assert self.max_idn() >= _idn, repr(self) + "\n" + repr(self.__dict__) + "\n" + x1
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
        cursor = self._cursor()
        try:
            cursor.execute("DELETE FROM `{table}`".format(table=self.table))
        except mysql.connector.ProgrammingError:
            pass
        cursor.execute("DROP TABLE IF EXISTS `{table}`".format(table=self.table))
        cursor.close()
        # self._now_it_doesnt_exist()   # So install will insert the lex sentence.
        # After this, we can only install_from_scratch() or disconnect()

    def disconnect(self):
        self._connection.close()

    # noinspection SpellCheckingInspection
    def insert_word(self, word):
        cursor = self._cursor()
        assert not word.idn.is_nan()
        whn = Number(time.time())
        # TODO:  Enforce uniqueness?
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

        # If any of the SQL in this module generates an error in PyCharm like one of these:
        #     <comma join expression> expected, unexpected end of file
        #                 <reference> expected, unexpected end of file
        #     '(', <reference>, GROUP, HAVING, UNION, WHERE or '{' expected, got '{'
        # Then a work-around is to disable SQL inspection:
        #     Settings | Editor | Language Injections | (uncheck) python: "SQL select/delete/insert/update/create"
        # Sadly the SQL syntax highlighting is lost.
        # SEE:  http://i.imgur.com/l61ARUX.png
        # SEE:  PyCharm bug report, https://youtrack.jetbrains.com/issue/PY-18367

        self.super_select(
            'INSERT INTO', self.table,
                   '(         idn,      sbj,      vrb,      obj,      num,      txt, whn) '
            'VALUES (', (word.idn, word.sbj, word.vrb, word.obj, word.num, word.txt, whn), ')')
        # TODO:  named substitutions with NON-prepared statements??
        # THANKS:  https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursor-execute.html
        # THANKS:  http://stackoverflow.com/questions/1947750/does-python-support-mysql-prepared-statements/31979062#31979062
        self._connection.commit()
        cursor.close()
        word.whn = whn
        # noinspection PyProtectedMember
        word._now_it_exists()

    def _cursor(self):
        return self._connection.cursor(prepared=True)

    def populate_word_from_idn(self, word, idn):
        rows = self.super_select("SELECT * FROM", self.table, "WHERE idn =", idn)
        return self._populate_from_one_row(word, rows)

    def populate_word_from_definition(self, word, define_txt):
        rows = self.super_select(
            'SELECT * FROM', self.table, 'AS w '
            'WHERE vrb =', Word._IDN_DEFINE,
            'AND txt =', Text(define_txt)
        )
        return self._populate_from_one_row(word, rows)

    def populate_word_from_sbj_vrb_obj(self, word, sbj, vrb, obj):
        rows = self.super_select(
            'SELECT * FROM', self.table, 'AS w '
            "WHERE sbj =", sbj,
            "AND vrb =", vrb,
            "AND obj =", obj,
            "ORDER BY `idn` DESC LIMIT 1"
        )
        return self._populate_from_one_row(word, rows)


    def populate_word_from_sbj_vrb_obj_num_txt(self, word, sbj, vrb, obj, num, txt):
        rows = self.super_select(
            'SELECT * FROM', self.table, 'AS w '
            "WHERE sbj =", sbj,
            "AND vrb =", vrb,
            "AND obj =", obj,
            "AND num =", num,
            "AND txt =", Text(txt),
            "ORDER BY `idn` DESC LIMIT 1"
        )
        return self._populate_from_one_row(word, rows)

    @staticmethod
    def _populate_from_one_row(word, rows):
        assert len(rows) in (0,1), "Populating from unexpectedly {} rows.".format(len(rows))
        if len(rows) > 0:
            row = rows[0]
            word.populate_from_row(row)
            return True
        return False

    def find_last(self, **kwargs):
        bunch = self.find_words(**kwargs)
        # TODO:  Limit find_words() to latest using sql LIMIT.
        try:
            return bunch[-1]
        except IndexError:
            raise self.NotFound

    # TODO:  Study JOIN with LIMIT 1 in 2 SELECTS, http://stackoverflow.com/a/28853456/673991
    # Maybe also http://stackoverflow.com/questions/11885394/mysql-join-with-limit-1/11885521#11885521

    def find_words(self, idn=None, sbj=None, vrb=None, obj=None, idn_order='ASC', jbo_vrb=None):
        # TODO:  Lex.find()
        """Select words by subject, verb, and/or object.

        Return a list of choate words.

        idn,sbj,vrb,obj all restrict the list of returned words.
        jbo_vrb is not restrictive, it's elaborative.
        'jbo' being 'obj' backwards, it represents a reverse reference.
        If jbo_vrb is an iterable of verbs, each returned word has a jbo attribute
        that is a list of inchoate words whose object is the word.
        In other words, it gloms onto each word the words that point to it.

        The order of words is chronological.
        idn_order='DESC' for reverse-chronological.
        The order of jbo words is always chronological.
        """

        assert isinstance(idn, (Number, Word, type(None)))
        assert isinstance(sbj, (Number, Word, type(None)))
        assert isinstance(vrb, (Number, Word, type(None))) or is_iterable(vrb)
        assert isinstance(obj, (Number, Word, type(None)))
        assert idn_order in (None, 'ASC', 'DESC')
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
        if jbo_vrb is not None:
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
        if jbo_vrb is not None:
            query_args += [
                'LEFT JOIN', self.table, 'AS jbo '
                    'ON jbo.obj = w.idn '
                        'AND jbo.vrb in (', jbo_vrb, ')',
                None
            ]
        query_args += ['WHERE TRUE', None]
        query_args += self._find_where(idn, sbj, vrb, obj)
        order_clause = 'ORDER BY w.idn ' + idn_order
        if jbo_vrb is not None:
            order_clause += ', jbo.idn ASC'
        query_args += [order_clause]
        rows = self.super_select(*query_args)
        words = []
        word = None
        for row in rows:
            if word is None or row['idn'] != word.idn:
                word = self()
                word.populate_from_row(row)
                word.jbo = []
                words.append(word)   # To be continued, we may append to word.jbo later.
            jbo_idn = row.get('jbo_idn', None)
            if jbo_idn is not None:
                new_jbo = self()
                new_jbo.populate_from_row(row, prefix='jbo_')
                word.jbo.append(new_jbo)
        return words


    def find_idns(self, idn=None, sbj=None, vrb=None, obj=None, idn_order='ASC'):
        """Select word identifiers by subject, verb, and/or object.

        Return list of idns."""
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
            query_args += ['AND w.idn=', idn_from_word_or_number(idn)]
        if sbj is not None:
            query_args += ['AND w.sbj=', idn_from_word_or_number(sbj)]
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
            query_args += ['AND w.obj=', idn_from_word_or_number(obj)]
        return query_args

    class SuperSelectTypeError(TypeError):
        pass

    class SuperSelectStringString(TypeError):
        pass

    def super_select(self, *query_args, **kwargs):
        """Build a prepared statement query from a list of sql strings and data parameters."""
        # TODO:  Recursive query_args?
        # So super_select(*args) === super_select(args) === super_select([args]) etc.
        # Say, then this could work, super_select('SELECT *', ['FROM table'])
        debug = kwargs.pop('debug', False)
        query = ""
        parameters = []
        for index, (arg_previous, arg_next) in enumerate(zip(query_args[:-1], query_args[1:])):
            if (
                    isinstance(arg_previous, six.string_types) and
                not isinstance(arg_previous, (Text, Lex.TableName)) and
                    isinstance(arg_next, six.string_types) and
                not isinstance(arg_next, (Text, Lex.TableName))
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
                    # TODO:  If name ends in 'txt' also?
                    value = Text.decode_if_desperate(field)
                else:
                    value = Number.from_mysql(field)
                field_dictionary[name] = value
                if debug:
                    print(name, repr(value), end='; ')
            rows_of_fields.append(field_dictionary)
            if debug:
                print()
        return rows_of_fields

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
        raise TypeError("idn_from_word_or_number({}) is not supported, only Word or Number.".format(
            type(x).__name__,
        ))


def is_iterable(x):
    # return hasattr(x, '__getitem__')
    # return hasattr(x, '__iter__')
    try:
        0 in x
    except TypeError as e:
        assert e.__class__ is TypeError   # A subclass of TypeError raised by comparison operators?  No thanks.
        return False
    else:
        return True


class Text(six.text_type):
    """The class for the Word txt field.

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
    def decode_if_desperate(cls, x):
        """For __getattr__() name argument."""
        try:
            return cls(x)
        except TypeError:
            return cls(x.decode('utf-8'))

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
