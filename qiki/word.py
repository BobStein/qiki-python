"""
A qiki Word is defined by a three-word subject-verb-object
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import re
import threading
import time

# noinspection PyPackageRequirements
import mysql.connector
import six

from qiki import Number, Suffix
from qiki.number import type_name


# TODO:  Move mysql stuff to lex_mysql.py?


HORRIBLE_MYSQL_CONNECTOR_WORKAROUND = True
# SEE:  https://stackoverflow.com/q/52759667/673991#comment99030618_55150960
# SEE:  https://stackoverflow.com/questions/49958723/cant-insert-blob-image-using-python-via-stored-procedure-mysql
# SEE:  https://stackoverflow.com/questions/51657097/how-can-i-retrieve-binary-data-using-mysql-python-connector
# Problem:  VARBINARY fields are decoded as if their contents were text
#           'utf8' codec can't decode ... invalid start byte
#           0q80 == lex.idn, and '\x80' can never be a valid utf8 string
#           Started happening between connector versions 2.2.2 and 8.0.16
# Workaround:  character encoding latin1 across whole table
#              qiki.Number fields work because latin1 can never fail to decode
#              qiki.Text field (txt) fake stores utf8 when it thinks it's latin1, yuk

# max_idn_lock = threading.Lock()


# noinspection PyAttributeOutsideInit
class Word(object):
    """
    A qiki Word is a subject-verb-object triplet of other words (sbj, vrb, obj).

    A word is identified by a qiki Number (idn).
    A word may be elaborated by a Number (num) and a string (txt).
    A word remembers the time it was created (whn).

    Each of these seven components of a word has a 3-letter symbol.
    (idn, sbj, vrb, obj, num, txt, whn)
    This helps a little in searching for the symbol, and avoiding reserved words.

    A word is fundamentally, uniquely, and forever defined by its idn,
    within the context of its Lex,
    as long as it has been saved (exists is true).

    :type content: Text.is_valid() | Word | instancemethod

    :type sbj: Number | Word
    :type vrb: Number | instancemethod
    :type obj: Number | Word
    :type num: Number
    :type txt: Unicode string in either Python 2 or 3
    """

    lex = None   # This is probably overwritten by the Lex base constructor.

    def __init__(self, content=None, sbj=None, vrb=None, obj=None, num=None, txt=None):
        if Text.is_valid(content):          # Word('agent')
            self._from_definition(content)
        elif isinstance(content, Number):   # Word(idn)
            self._inchoate(content)
        elif isinstance(content, Word):     # Word(another_word)
            self._from_word(content)
        elif content is None:               # Word(sbj=s, vrb=v, obj=o, num=n, txt=t)
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
            need_unicode = type_name(content) in ('str', 'bytes', 'bytearray')
            raise TypeError("{outer}({inner}) is not supported{etc}".format(
                outer=type_name(self),
                inner=type_name(content),
                etc=" -- use unicode instead" if need_unicode else ""
            ))

    def _inchoate(self, idn):
        """
        Initialize an inchoate word.

        Definition of "inchoate"
        ------------------------
        An inchoate word is frugal with resources.  It's a ghost, barely there.
        All that is known about an inchoate word is its idn.
        Maybe that's all we ever need to know about it.
        But, if anything substantive is asked of it, then the word is made choate.
        For example, getting these properties forces the word to become choate:
            word.sbj
            word.vrb
            word.vrb
            word.num
            word.txt
            word.whn
            word.exists()   (does it exist in the lex, NOT is it choate)

        The following also have the side-effect of making a word choate,
        because they use one of the above properties:
            str(word)
            repr(word)
            hasattr(word, 'txt')
            ...a lot more

        But the following actions do not make a word choate.  If it was inchoate it stays so:
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
        # CAUTION:  But Word(content=None) is a choate word, because it populates self._fields.
        #           Listing relies on all this so it may need to be refactored.
        #           (This is weird because Word(idn) is inchoate.)
        self.set_idn_if_you_really_have_to(idn)

    def set_idn_if_you_really_have_to(self, idn):
        self._idn = idn

    def _choate(self):
        """
        Transform an inchoate word into a not-inchoate word.

        That is, from a mere container of an idn to a fleshed-out word
        with num and txt (and if not a Listing, sbj, vrb, obj).
        This in preparation to use one of its properties, sbj, vrb, obj, txt, num, whn.
        """
        if self._is_inchoate:
            self._from_idn(self._idn)

            # assert not self._is_inchoate
            # TODO:  Why the f does asserting that break everything?

            if self._is_inchoate:
                self._fields = dict()

        assert not self._is_inchoate

    # TODO:  @property?
    def exists(self):
        """"
        Does this word exist?  Is it stored in a Lex?

        This is a bigger question than being choate.
        Choate is more a concept of what we know about the word so far.
        Exist is more a concept of what the world manifests about the word.
        """
        # TODO:  What about Listing words?
        self._choate()
        return hasattr(self, '_exists') and self._exists   # WTF is not hasattr() enough?

    def _now_it_exists(self):
        """Declare that a word "exists"."""
        self._exists = True

    # NOTE:  lex and define words may be very common and benefit from a short idn (0q80 and 0q82)

    @property
    def _is_inchoate(self):
        return not hasattr(self, '_fields')

    @property
    def sbj(self):
        return self._get_field('sbj')

    @property
    def vrb(self):
        return self._get_field('vrb')

    @property
    def obj(self):
        return self._get_field('obj')

    @property
    def num(self):
        return self._get_field('num')

    @property
    def txt(self):
        return self._get_field('txt')

    @property
    def whn(self):
        return self._get_field('whn')

    @whn.setter
    def whn(self, new_whn):
        self._set_field('whn', new_whn)

    def _set_field(self, field_name, new_value):
        self._choate()
        self._fields[field_name] = new_value

    def _get_field(self, field_name):
        self._choate()
        try:
            return self._fields[field_name]
        except KeyError:
            return None

    @property
    def do_not_call_in_templates(self):
        # THANKS:  for this Django flag, maybe http://stackoverflow.com/a/21711308/673991
        return True

    class NotExist(Exception):
        pass

    def __call__(self, vrb, *args, **kwargs):
        """
        Part way to the square-bracket sentence.

        This is the result of the curried expression:

            lex[s](v)

        Which is just before the [o] part.
        """
        if isinstance(vrb, six.binary_type):
            raise TypeError("Verb name must be unicode, not " + repr(vrb))
        return SubjectedVerb(self, vrb, *args, **kwargs)
        # NOTE:  sbj=self

    def said(self, vrb, obj):
        return self(vrb)[obj]

    @classmethod
    def txt_num_swap(cls, a1, a2):
        """
        Swap num and txt if necessary.

        Either could be None
        """
        # TODO:  This is a poor stand-in for extract_txt_num().  Or vice versa.
        if (
            (a2 is None or Text.is_valid(a2)) and
            (a1 is None or Number.is_number(a1))
        ):
            return a2, a1
        else:
            return a1, a2

    def says(self, vrb, obj, num=None, txt=None, num_add=None, use_already=False):

        # return self(vrb, *args, **kwargs)[obj]
        # NOTE:  The above way is not quite aggressive enough.
        #        If num and txt were missing it would passively find a word by s,v,o,
        #        as opposed to making a new ('',1) word, as create_word below would do.

        txt, num = self.txt_num_swap(num, txt)   # in case they were specified positionally

        return self.lex.create_word(
            sbj=self,
            vrb=vrb,
            obj=obj,
            num=num,
            txt=txt,
            num_add=num_add,
            use_already=use_already,
        )

    def spawn(self, *args, **kwargs):
        """
        Construct a Word() using the same lex as another word.
        """

        if len(args) == 1 and isinstance(args[0], (Number, Word)):
            return self.lex.root_lex[args[0]]

        try:
            idn = self.lex.idn_ify(args[0])
        except IndexError:                        # args is empty (kwargs probably is not)
            pass
        except TypeError:                         # args[0] is neither a Word nor a Number
            pass
        else:
            try:
                return Listing.word_from_idn(idn)
            # except Listing.NotAListingRightNow:
            #     return ListingNotInstalled(idn)   # args[0] is a listing, but its class was not installed
            except Listing.NotAListing:
                pass                              # args[0] is not a listing word

            if idn.is_suffixed():
                raise self.NotAWord("Do not know how to spawn this suffixed idn " + idn.qstring())

        assert hasattr(self, 'lex')
        # XXX:  Why did PY2 need this to be a b'lex'?!  And why does it not now??
        # Otherwise hasattr(): attribute name must be string
        assert isinstance(self.lex, Lex)
        # kwargs['lex'] = self.lex
        return type(self)(*args, **kwargs)
        # NOTE:  This should be the only call to the Word constructor.
        # (Except of course from derived class constructors that call their super().)
        # Enforce?  Refactor somehow?
        # (The chicken/egg problem is resolved by the first Word being instantiated
        # via the derived class Lex (e.g. LexMySQL).)

        #     else:
        #         return listing_class.word_from_idn(args[0].idn)
        # else:
        #     kwargs['lex'] = self.lex
        #     return Word(*args, **kwargs)
        #
        # if len(args) >= 1 and isinstance(args[0], Number):
        #     idn = args[0]
        #     if idn.is_suffixed():
        #         try:
        #             listing_class = Listing.class_from_listing_idn(idn)
        #             # TODO:  Instead, listed_instance = Listing.word_from_idn(idn)
        #         except Listing.NotAListing:   # as e:
        #             return ListingNotInstalled(idn)
        #             # raise self.NotAWord("Listing identifier {q} exception: {e}".format(
        #             #     q=idn.qstring(),
        #             #     e=str(e)
        #             # ))
        #         else:
        #             assert issubclass(listing_class, Listing), repr(listing_class)
        #             return listing_class.word_from_idn(idn)
        #             # _, hack_index = Listing.split_compound_idn(idn)
        #             # return listing_class(hack_index)
        #         # pieces = idn.parse_suffixes()
        #         # assert len(pieces) == 1 or isinstance(pieces[1], Suffix)
        #         # if len(pieces) == 2 and pieces[1].
        #
        # assert hasattr(self, 'lex')
        # # Otherwise hasattr(): attribute name must be string
        # assert isinstance(self.lex, Lex)
        # kwargs['lex'] = self.lex
        # return Word(*args, **kwargs)
        # # NOTE:  This should be the only call to the (base) Word constructor.  Enforce?  Refactor somehow?
        # # (The chicken/egg problem is resolved by the first Word being instantiated
        # # via the derived class Lex (e.g. LexMySQL).)

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
        self.lex.populate_word_from_idn(self, idn)
        # TODO:  Do something with return value?
        # NOTE:  If this returned True, it already called populate_from_word()
        #        and so the word now exists()

    def _from_definition(self, txt):
        """
        Construct a Word from its name, aka its definition txt.

        That is, look for a word with
            sbj=lex
            vrb=define
            obj=(can be anything)
            txt=whatever

        """
        assert Text.is_valid(txt)
        assert isinstance(self.lex, LexSentence)
        if not self.lex.populate_word_from_definition(self, txt):
            self._fields = dict(
                txt=Text(txt)
            )

    def _from_word(self, other):
        assert isinstance(other, Word)   # Not necessarily type(self)
        assert self.lex == other.lex
        assert self.lex is other.lex
        assert isinstance(self, other.lex.word_class)
        assert isinstance(other, self.lex.word_class)
        # noinspection PyProtectedMember
        if other._is_inchoate:
            self._inchoate(other.idn)
        else:
            assert other.exists()
            self.set_idn_if_you_really_have_to(other.idn)
            self._from_idn(other.idn)
            # TODO:  Why not copy-construct a choate other into an inchoate self?
            #        (Find out whether this populated self is now choate.)

    def _from_sbj_vrb_obj(self):
        """Construct a word by looking up its subject-verb-object."""
        assert isinstance(self.sbj, Word)
        assert isinstance(self.vrb, Word)
        assert isinstance(self.obj, Word)
        self.lex.populate_word_from_sbj_vrb_obj(
            self,
            self.sbj,
            self.vrb,
            self.obj
        )

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
        # return self.spawn(self.idn)
        return self.lex[self.idn]

    def populate_from_word(self, word):
        word_dict = dict(
            idn=word.idn,
            sbj=word.sbj.idn,
            vrb=word.vrb.idn,
            obj=word.obj.idn,
            num=word.num,
            txt=word.txt,
            whn=word.whn,
        )
        self.populate_from_row(word_dict)

    def populate_from_row(self, row, prefix=''):
        assert isinstance(row[prefix + 'idn'], Number)
        assert isinstance(row[prefix + 'sbj'], Number), type_name(row[prefix + 'sbj'])
        assert isinstance(row[prefix + 'vrb'], Number)
        assert isinstance(row[prefix + 'obj'], Number)
        assert isinstance(row[prefix + 'num'], Number)
        assert isinstance(row[prefix + 'txt'], Text)
        assert isinstance(row[prefix + 'whn'], Number)
        self.set_idn_if_you_really_have_to(row[prefix + 'idn'])
        self._now_it_exists()   # Must come before spawn(sbj) for lex's sake.
        self._fields = dict(
            sbj=self.lex[row[prefix + 'sbj']],
            vrb=self.lex[row[prefix + 'vrb']],
            obj=self.lex[row[prefix + 'obj']],
            num=row[prefix + 'num'],
            txt=row[prefix + 'txt'],
            whn=row[prefix + 'whn'],
        )

    def populate_from_num_txt(self, num, txt):
        assert isinstance(txt, Text), "Need Text, not a {t}: `{r}'".format(
            t=type_name(txt),
            r=repr(txt)
        )
        assert isinstance(num, Number)
        self._now_it_exists()
        self._fields = dict(
            num=num,
            txt=txt,
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
        if self.vrb.idn != self.lex.IDN_DEFINE:
            return False
        if self.obj == word:
            return True
        # parent = self.spawn(self.obj)
        parent = self.lex[self.obj]
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
        return self.idn == self.lex.IDN_DEFINE

    def is_defined(self):
        """
        Test whether a word is the product of a definition.

        That is, whether the sentence that creates it uses the verb 'define'.
        """
        return self.vrb is not None and self.vrb.idn == self.lex.IDN_DEFINE

    def is_noun(self):
        return self.idn == self.lex.IDN_NOUN

    def is_verb(self):
        """
        Not to be confused with is_a_verb().

        is_a_verb() -- is this word in a []-(define)-[verb] sentence, recursively.
        is_verb() -- is this the one-and-only "verb" word,
                     i.e. [lex](define, "verb")[noun],
                     i.e. idn == IDN_VERB
        """
        return self.idn == self.lex.IDN_VERB

    def is_agent(self):
        return self.idn == self.lex.IDN_AGENT

    def is_lex(self):
        # return isinstance(self, Lex) and self.exists() and self.idn == self.lex.IDN_LEX
        return self.exists() and self.idn == self.lex.IDN_LEX

    def description(self):
        return u"[{sbj}]({vrb}{maybe_num}{maybe_txt})[{obj}]".format(
            sbj=str(self.sbj),
            vrb=str(self.vrb),
            obj=str(self.obj),
            # TODO:  Would str(x) cause infinite recursion?  Not if str() does not call description()
            maybe_num=(", " + self.presentable(self.num)) if self.num != 1   else "",
            maybe_txt=(", " + repr(self.txt))             if self.txt != u'' else "",
        )

    def to_json(self):
        d = dict(
            idn=self.idn,
            sbj=self.sbj.idn,
            vrb=self.vrb.idn,
            obj=self.obj.idn,
            whn=float(self.whn),
        )

        if self.txt != "":
            d['txt'] = self.txt

        if self.num != 1:
            d['num'] = self.num

        if hasattr(self, 'jbo') and len(self.jbo) > 0:
            d['jbo'] = self.jbo

        return d

    @staticmethod
    def presentable(num):
        if num.is_suffixed() or not num.is_reasonable():
            return num.qstring()
        try:
            is_it_whole = num.is_whole()
        except TypeError:   # Number.WholeError:
            return num.qstring()
        else:
            if is_it_whole:
                return str(int(num))
            else:
                return str(float(num))

    def __format__(self, format_spec):
        # THANKS:  format > repr > str, https://stackoverflow.com/a/40600544/673991
        if format_spec == '':
            return repr(self)
        else:
            return "Word({})".format(",".join(self._word_attributes(format_spec)))

    def _word_attributes(self, format_spec):
        for c in format_spec:
            if   c == 'i':  yield "idn={}".format(self.presentable(self.idn))
            elif c == 's':  yield "sbj={}".format(str(self.sbj))
            elif c == 'v':  yield "vrb={}".format(str(self.vrb))
            elif c == 'o':  yield "obj={}".format(str(self.obj))
            elif c == 't':  yield "txt='{}'".format(str(self.txt))
            elif c == 'n':  yield "num={}".format(self.presentable(self.num))
            elif c == 'w':  yield "whn={}".format(str(TimeLex()[self.whn].txt))
            else:
                raise ValueError("'{}' unknown in .format(word)".format(c))

    def __repr__(self):
        # THANKS:  repr() conventions, https://codingkilledthecat.wordpress.com/2012/06/03/please-dont-abuse-repr/
        if self.exists():
            if self.is_defined() and self.txt:

                # TODO:  Undo comma_num (WTF is this?)

                if self.num == Number(1):
                    comma_num = ""
                else:
                    comma_num = ", num={num}".format(num=repr(self.num))

                # TODO:  comma_idn -- Show idn if txt,num is not the latest

                return "Word('{txt}'{comma_num})".format(
                    comma_num=comma_num,
                    txt=self.txt
                )
            else:
                return "Word({})".format(self.presentable(self.idn))
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
        elif Text.is_valid(self.txt):
            return "Word(undefined {})".format(repr(self.txt))
        else:
            try:
                idn_repr = repr(self.idn)
            except ValueError:
                if self.txt:
                    return "Word(nonexistent {})".format(repr(self.txt))   # TODO:  unit test
                else:
                    return "Word(in a corrupt state)"   # can't show idn nor txt  TODO: unit test this?
            else:
                return "Word(unidentified {})".format(idn_repr)

    def __str__(self):
        if hasattr(self, 'txt') and self.txt is not None:
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
        try:
            return Number(self._idn)   # Copy constructor so e.g. w.idn.suffix(n) will not modify w.idn.
                                   # TODO:  but then what about w.sbj.add_suffix(n), etc.?
                                   #        (But there's no more add_suffix, only new-number-generating plus_suffix)
                                   # So this passing through Number() is a bad idea.
                                   # Plus this makes x.idn a different object from x._idn, burdening debug.
        except AttributeError:
            return Number.NAN

    def save(self, override_idn=None):
        # TODO:  Move to Lex?  It's only ever called by create_word() anyway...
        assert isinstance(self.idn, Number)
        assert isinstance(self.sbj, Word)
        assert isinstance(self.vrb, Word)
        assert isinstance(self.obj, Word), "{obj} is not a Word".format(obj=repr(self.obj))
        assert isinstance(self.num, Number)
        assert isinstance(self.txt, Text)
        if override_idn is None:
            self.lex.insert_next_word(self)
        else:
            self.set_idn_if_you_really_have_to(override_idn)
            self.lex.insert_word(self)


class SubjectedVerb(object):
    # TODO:  Move this to inside Word?  Or LexSentence!??
    """
    This is the currying intermediary, the "x" in x = s(v) and x[o].  Thus allowing:  s(v)[o].

    So this is the Python-object that is "returned" when you "call" a subject and pass it a verb.
    In that function call, which is actually the constructor for this class,
    other parameters (besides the verb) can be passed in the form of args and kwargs to modify the instance.
    Those modifiers are txt and num in flexible order.  Oh wait are they?
    Maybe they're just num_add and use_already.
    """
    def __init__(self, sbj, vrb, *args, **kwargs):
        self._subjected = sbj
        self._verbed = self._subjected.lex.root_lex[vrb]   # TODO:  Move to ... (?)
        self._args = list(args)
        self._kwargs = kwargs

    def __setitem__(self, key, value):
        """
        Square-bracket sentence insert (the C in CRUD).

        This is the result of the curried expression:

            lex[s](v)[o] = n,t

        Specifically, the assignment combined with the right-most square-bracket operator.
        """
        # objected = self._subjected.spawn(key)
        objected = self._subjected.lex.root_lex[key]

        txt, num = self.extract_txt_num(value, dict())

        # num_and_or_txt = value
        # if isinstance(num_and_or_txt, numbers.Number):
        #     # TODO:  instead Number.is_number()?  But it shouldn't accept q-strings!  Or '3'!
        #     num = num_and_or_txt
        #     txt = u""
        # elif Text.is_valid(num_and_or_txt):
        #     # TODO:  rename Text.is_text()?
        #     txt = num_and_or_txt
        #     num = Number(1)
        # else:
        #     num = Number(1)
        #     txt = Text(u"")
        #     num_count = 0
        #     txt_count = 0
        #     if is_iterable(num_and_or_txt):
        #         for num_or_txt in num_and_or_txt:
        #             if isinstance(num_or_txt, numbers.Number):
        #                 num = num_or_txt
        #                 num_count += 1
        #             elif Text.is_valid(num_or_txt):
        #                 txt = num_or_txt
        #                 txt_count += 1
        #             else:
        #                 raise self._subjected.SentenceArgs("Expecting num or txt, got " + repr(num_or_txt))
        #     else:
        #         raise self._subjected.SentenceArgs("Expecting num and/or txt, got " + repr(num_and_or_txt))
        #     if num_count > 1:
        #         raise self._subjected.SentenceArgs("Expecting 1 number not {n}: {arg}".format(
        #             n=num_count,
        #             arg=repr(num_and_or_txt)
        #         ))
        #     if txt_count > 1:
        #         raise self._subjected.SentenceArgs("Expecting 1 text not {n}: {arg}".format(
        #             n=txt_count,
        #             arg=repr(num_and_or_txt)
        #         ))

        self._subjected.lex.root_lex.create_word(
            sbj=self._subjected,
            vrb=self._verbed,
            obj=objected,
            num=num,
            txt=txt,
            *self._args,
            **self._kwargs
        )

    def __getitem__(self, item):
        """
        Square-bracket sentence extraction from its lex (the R in CRUD).

        This is the result of the curried expression:

            w = lex[s](v)[o]

        Specifically, the right-most square-bracket operator.

        So o can be:
            an object word
            idn of an object
            txt of a defined object

        This also handles the creation of a new word (the C in CRUD).

            w = lex[s](v, t, n)[o]

        Without the assignment there may be a warning about code having no effect.
        """
        if isinstance(item, six.binary_type):
            raise TypeError("Object name must be unicode, not " + repr(item))
        objected = self._subjected.lex.root_lex[item]
        if self._args or self._kwargs:
            txt, num = self.extract_txt_num(self._args, self._kwargs)

            # self._kwargs.pop('txt', None)
            # self._kwargs.pop('num', None)
            # XXX:  WTF Why were these here, aren't they SUPPOSED to be removed
            #       by extract_txt_num??

            return self._subjected.lex.root_lex.create_word(
                sbj=self._subjected,
                vrb=self._verbed,
                obj=objected,
                num=num,
                txt=txt,
                *self._args,
                **self._kwargs
            )
        else:
            existing_word = self._subjected.lex.word_class()
            does_exist = self._subjected.lex.populate_word_from_sbj_vrb_obj(
                existing_word,
                sbj=self._subjected,
                vrb=self._verbed,
                obj=objected,
            )
            if not does_exist:
                raise self._subjected.NotExist(
                    "There is no word type '{word}' such that:\n"
                    "    sbj={sbj}\n"
                    "    vrb={vrb}\n"
                    "    obj={obj}\n"
                    "in this {lex} (python id {lex_python_id})".format(
                        word=self._subjected.lex.word_class.__name__,
                        sbj=self._subjected,
                        vrb=self._verbed,
                        obj=objected,
                        lex=repr(self._subjected.lex),
                        lex_python_id=id(repr(self._subjected.lex)),
                    )
                )
            return existing_word
            # return self._subjected.said(self._verbed, objected)

    @classmethod
    def extract_txt_num(cls, a, k):   # aka (args, kwargs)
        """
        Get num and/or txt from positional-arguments, and keyword-arguments.

        This is the <etc> part of lex[s](v, <etc>)[o]

        Or at least part of it.
        It's meant to remove from <etc> the num and txt if they're there.
        whether they're keyword-arguments or not.
        But also leave behind other keyword arguments to pass through to
        TypeError if ambiguous or unsupportable.
        Examples that will raise TypeError:
            extract_txt_num('text', 'more text')
            extract_txt_num(1, 42)
            extract_txt_num(neither_text_nor_number)

        Expects a (args) is a list, not a tuple, so it can be modified in-place.

        :return:  (txt, num)
        """
        # TODO:  It was silly to expect a (args) to be a list.
        #        Only k (kwargs) can have surplus parameters.
        #        If this function doesn't generate an exception,
        #        then it used up all of a (args) anyway.

        if isinstance(a, tuple):
            a = list(a)   # A tuple turns into a list. (Oh well, can't know what wasn't absorbed.)
        elif isinstance(a, list):
            a = a         # A list stays the same, that's what we expected, ala args
        else:
            a = [a]       # Anything else is stuffed INTO a list

        for arg in a:
            if isinstance(arg, six.binary_type):
                raise TypeError("Expecting unicode not " + repr(arg))

        for name, value in k.items():
            if isinstance(value, six.binary_type):
                raise TypeError("Expecting " + repr(name) + " to be unicode not " + repr(value))

        def type_code(x):
            return 'n' if Number.is_number(x) else 't' if Text.is_valid(x) else 'x'

        pats = ''.join(type_code(arg) for arg in a)   # pats:  Positional-Argument Types
        t = 'txt' in k
        n = 'num' in k

        def type_failure():
            return TypeError("Expecting a num and a txt, not {} {} {} {} {}".format(
                repr(a), repr(k), pats, t, n
            ))

        if   pats == ''   and not t and not n:  r = ''          , 1
        elif pats == 'n'  and not t and not n:  r = ''          , a[0]        ; del a[0]
        elif pats == 't'  and not t and not n:  r = a[0]        , 1           ; del a[0]
        elif pats == ''   and     t and not n:  r = k.pop('txt'), 1
        elif pats == ''   and not t and     n:  r = ''          , k.pop('num')
        elif pats == 'tn' and not t and not n:  r = a[0]        , a[1]        ; del a[0:2]
        elif pats == 'nt' and not t and not n:  r = a[1]        , a[0]        ; del a[0:2]
        elif pats == 't'  and not t and     n:  r = a[0]        , k.pop('num'); del a[0]
        elif pats == 'n'  and     t and not n:  r = k.pop('txt'), a[0]        ; del a[0]
        elif pats == ''   and     t and     n:  r = k.pop('txt'), k.pop('num')
        else:
            raise type_failure()

        try:
            return Text(r[0]),  Number(r[1])
        except ValueError:
            raise type_failure()


class Lex(object):
    """
    Collection of Numbered Words.

    idn is the qiki Number that identifies the word.
    The words are instantiations of a subclass of qiki Word.

    meta_idn is the number that identifies the Lex collection itself, in some parent Lex.
    Meta and mesa are opposites, up and down the hierarchy of lexes.
    (this is not an inheritance hierarchy)
    This hierarchy was invented so a Listing can reconstruct the suffixed idn
    needed in the LexSentence words that REFER to Listing words.

    """

    def __init__(self, meta_word=None, word_class=None, **_):
        super(Lex, self).__init__()
        # NOTE:  Blow off unused kwargs here, which might be sql credentials.
        #        Guess we do this here so sql credentials could contain word_class=Something.

        if word_class is None:

            class WordClassJustForThisLex(Word):
                pass

            word_class = WordClassJustForThisLex
        self.word_class = word_class
        self.word_class.lex = self
        self.meta_word = meta_word
        self.mesa_lexes = dict()
        # SEE:  mesa, opposite of meta, https://english.stackexchange.com/a/22805/18673
        root_lexes = self.root_lex.mesa_lexes
        if meta_word in root_lexes:
            raise self.LexMetaError(
                "Meta Word {this_word} already used for {that_class}. "
                "Not available for this {this_class}".format(
                    this_word=repr(meta_word),
                    that_class=repr(root_lexes[meta_word]),
                    this_class=repr(self)
                )
            )
        meta_idn = None if meta_word is None else meta_word.idn
        root_lexes[meta_idn] = self

    class LexMetaError(TypeError):
        """Something is wrong with Lex meta words, e.g. two sub-lexes use the same meta word."""

    def __repr__(self):
        """
        EXAMPLE:  GoogleQikiListing Word('google user')
        EXAMPLE:  AnonymousQikiListing Word('anonymous')
        """
        if self.meta_word is None:
            return type_name(self)
        else:
            return type_name(self) + " " + repr(self.meta_word)

    def __getitem__(self, item):
        """
        Square-bracket Word instantiation.

        This gets called when you do any of these
            lex[idn]
            lex[word]  (for copy construction)
        """
        return self.read_word(item)

    class NotFound(Exception):
        pass

    @property
    def root_lex(self):
        return self._root_lex()

    def _root_lex(self):
        if self.meta_word is None:
            return self
        if self.meta_word.lex is None:
            return self
        else:
            # noinspection PyProtectedMember
            is_potential_infinite_loop = (
                self.meta_word.lex           is self or
                self.meta_word.lex._root_lex is self._root_lex
            )
            if is_potential_infinite_loop:
                # NOTE:  This kind of self-reference should never happen.  Avoid infinite loop anyway.
                raise RuntimeError("{} meta_word refers to itself".format(type_name(self)))
            else:
                return self.meta_word.lex.root_lex

    def word_from_word_or_number(self, x):
        return self.root_lex[x]

    def read_word(self, idn_or_word_or_none):
        if idn_or_word_or_none is None:
            return self.word_class(None)

        idn = self.idn_ify(idn_or_word_or_none)
        assert isinstance(idn, Number)

        if idn is None:
            return self.word_class(idn_or_word_or_none)

        if idn.is_suffixed():
            try:
                meta_idn, index = Listing.split_compound_idn(idn)
                # TODO:  Don't just try unsuffixed.  Try all sub-suffixed numbers.
                #        Allowing nested lexes.
            except (Listing.NotAListing, KeyError) as e:
                raise Lex.NotFound("{q} is not a Listing idn: {e}".format(
                    q=idn.qstring(),
                    e=type_name(e) + " - " + str(e),
                ))
            else:
                try:
                    lex = self.root_lex.mesa_lexes[meta_idn]
                except KeyError as ke:
                    new_word = limbo_listing.word_class(u"{q} is not a Listing idn: {e}".format(
                        q=idn.qstring(),
                        e=type_name(ke) + " - " + str(ke),
                    ))
                    new_word.set_idn_if_you_really_have_to(idn)
                    return new_word
                    # raise Lex.NotFound("{q} is not a Listing idn: {e}".format(
                    #     q=idn.qstring(),
                    #     e=type_name(ke) + " - " + str(ke),
                    # ))

            return lex.read_word(index)
        else:
            return self.word_class(idn)

    def populate_word_from_idn(self, word, idn):
        # TODO:  Be consistent with this method, either return true/false and USE it.
        #        Or raise exceptions and
        raise NotImplementedError()

    def idn_ify(self, x):
        """
        Helper for functions that take either idn or word.

        Or for a LexSentence, return its idn for itself!

        CAUTION:  This will of course NOT be the idn that OTHER lexes use
                  to refer to this lex.

        :param x:  - an idn or a word or a lex (LexSentence)
        :return:   - an idn, nor None for undefined name ()
        """
        # TODO:  Support idn_ify('0q82_2A') q-strings?
        if isinstance(x, Word):
            assert isinstance(x.idn, Number)
            return x.idn
        elif isinstance(x, Number):
            return x
        elif isinstance(x, (int, float)):
            return Number(x)
        elif isinstance(x, LexSentence):
            assert isinstance(x.IDN_LEX, Number)
            return x.IDN_LEX
        else:
            if isinstance(x, six.binary_type):
                raise TypeError("The name of a qiki Word must be unicode, not " + repr(x))
            elif Text.is_valid(x):
                w = self.word_class(x)
                if w.exists():
                    return w.idn
                else:
                    raise ValueError("No definition for '{txt}' in this {lex}".format(
                        txt=x,
                        lex=type_name(self),
                    ))
            else:
                raise TypeError(
                    "{the_type} is not supported here.  "
                    "Expecting the idn or name of a word, a word itself, or a lex.\n"
                    "    You passed:  {repr}".format(
                        the_type=type_name(x),
                        repr=repr(x),
                    )
                )


class Listing(Lex):
    # TODO:  Listing(ProtoWord) -- derived from an abstract base class?
    # TODO:  Or maybe Listing(Lex) or Lookup(Lex)

    """
    Listing was born of the need for a qiki Word to refer to data stored somewhere by index.

    For example, a database record with integer id.
    A suffixed word refers to both the storage and the record.  They each have an idn.
    A composite idn contains both:  Number(idn_storage, Suffix(Suffix.Type.LISTING, idn_record))

    idn_storage is the idn of a Word in the system Lex, corresponding to the listing.
    idn_record doesn't mean anything to qiki, just to the storage system.
    """
    listing_dictionary = dict()   # Table of Listing instances, indexed by meta_word.idn

    SUFFIX_TYPE = Suffix.Type.LISTING

    def __init__(self, meta_word, word_class=None, **kwargs):
        """
        self.index - The index is an integer or Number that's opaque to qiki.
                     It is unique to whatever is represented by the ListingSubclass instance.
                     (So two ListingSubclass instances with the same index can be said to be equal.
                     Just as two words with the same idns are equal.  Which in fact they also are.)
                     This index is passed to the ListingSubclass constructor, and to it's lookup() method.
        self.idn - The identifier is a suffixed number:
                   unsuffixed part - meta_idn for the ListingSubclass,
                                     the idn of the meta_word that defined the ListingSubclass
                   suffix type - Type.LISTING
                   suffix payload - the index
        """

        if word_class is None:

            class WordClassJustForThisListing(WordListed):
                pass

            word_class = WordClassJustForThisListing

        super(Listing, self).__init__(meta_word=meta_word, word_class=word_class, **kwargs)
        assert isinstance(meta_word, Word)
        assert not isinstance(meta_word, self.word_class)   # meta_word is NOT a listing word,
                                                            # that's self-referentially nuts
        self.listing_dictionary[meta_word.idn] = self
        self.meta_word = meta_word
        self.suffix_type = Suffix.Type.LISTING

    def lookup(self, index):
        raise NotImplementedError("Subclass must def lookup(index): return txt, num ")
        # THANKS:  Classic abstract method, http://stackoverflow.com/a/4383103/673991

    def composite_idn(self, index):
        return Number(self.meta_word.idn, Suffix(Suffix.Type.LISTING, Number(index)))

    def read_word(self, index):
        word = self.word_class(self.composite_idn(index))
        # noinspection PyProtectedMember
        assert word._is_inchoate
        return word

    def populate_word_from_idn(self, word, idn):
        _, index = self.split_compound_idn(idn)
        (txt, num) = self.lookup(index)
        word.populate_from_num_txt(Number(num), Text(txt))
        return True

    class NotAListing(Exception):
        pass

    @classmethod
    def word_from_idn(cls, idn):
        """
        Turn a suffixed-Number identifier into a (word) instance of some subclass of Listing.
        The ListingSubclass constructor is like an instance_from_index() converter.

        So it's a double-lookup.
        First we look up which class this idn is for.
        That's determined by the unsuffixed (root) part of the idn.
        This class will be a subclass of Listing.
        Second we call that class's lookup on the suffix (payload) part of the idn.
        """

        meta_idn, index = cls.split_compound_idn(idn)
        listing = cls.listing_from_meta_idn(meta_idn)
        listed_instance = listing[index]
        # TODO:  Support non-Number suffix payloads?  The Listing index must now be a Number.
        return listed_instance

    @classmethod
    def listing_from_meta_idn(cls, meta_idn):
        """Listing subclass instance, from the listing's meta-idn."""
        # print(repr(cls.listing_dictionary))
        try:
            listing = cls.listing_dictionary[meta_idn]
        except KeyError:
            raise cls.NotAListing("Not a meta_word for any listing: " + meta_idn.qstring())
        assert isinstance(listing, cls), repr(listing) + " is not a subclass of " + repr(cls)
        assert listing.meta_word.idn == meta_idn
        return listing

    @classmethod
    def split_compound_idn(cls, idn):
        """Return (meta_idn, index) from a listing word's idn.  Or raise NotAListing."""
        try:
            return idn.unsuffixed, idn.suffix(cls.SUFFIX_TYPE).number
        except (AttributeError, Suffix.RawError, Suffix.NoSuchType) as e:
            raise cls.NotAListing("Not a Listing idn: " + type_name(idn) + " - " + six.text_type(e))


class WordListed(Word):
    """Base class of all Listing words."""
    @property
    def index(self):
        return self.idn.suffix(Suffix.Type.LISTING).number


class ListingLimbo(Lex):
    """
    Singleton for legacy Listing.

    It's composite idn is in the database.
    But it's meta_idn is not in Listing.listing_dictionary.
    Presumably, the meta_word was never passed to a Listing constructor.
    """
    def populate_word_from_idn(self, word, idn):
        return False
    #
    # # noinspection PyMethodMayBeStatic
    # def populate_word_from_definition(self, _, __):   # word, define_txt):
    #     """Used by Lex.read_word().  define_txt will be the txt of a nonexistent limbo word"""
    #     return False


limbo_listing = ListingLimbo()


class Pythonic:
    """
    Python-specific features.

    Python-platform arcana is supposed to start going here.
    This may ease porting of other classes to other languages.
    """
    @classmethod
    def unix_epoch_now(cls):
        if six.PY2:
            unix_epoch = time.time()
        else:
            unix_epoch = datetime.datetime.timestamp(datetime.datetime.now(datetime.timezone.utc))
            # THANKS:  Python 3.3 unix epoch, https://stackoverflow.com/a/30156392/673991
        # TODO:  Use arrow module instead of time?  https://github.com/crsmithdev/arrow
        assert isinstance(unix_epoch, float)
        return unix_epoch

    @classmethod
    def time_format_yyyy_mmdd_hhmm_ss(cls, unix_epoch):
        """
        Format a unix timestamp (seconds since 1970 UTC) into a string.

        EXAMPLE:  assert "1999.1231.2359.59" == time_local_yyyy_mmdd_hhmm_ss(946684799.0)
        EXAMPLE:  assert "2000.0101.0000.00" == time_local_yyyy_mmdd_hhmm_ss(946684800.0)
        """
        assert isinstance(unix_epoch, float)
        time_tuple_thingie = time.gmtime(unix_epoch)

        yyyy_mmdd_hhmm_ss_str = time.strftime('%Y.%m%d.%H%M.%S', time_tuple_thingie)
        # NOTE:  No Unicode for you.  Another way timekeeping is stuck in 1970.
        # THANKS:  https://stackoverflow.com/q/2571515/673991

        yyyy_mmdd_hhmm_ss_unicode = cls._unicode_from_str(yyyy_mmdd_hhmm_ss_str)
        return yyyy_mmdd_hhmm_ss_unicode

    @classmethod
    def _unicode_from_str(cls, string):
        assert isinstance(string, str)
        if six.PY2:
            # noinspection PyUnresolvedReferences
            string = string.decode('utf-8')
        assert isinstance(string, six.text_type)
        return string


class TimeLex(Lex):
    """
    Factory for words whose idn == num == whn are all a time code, seconds since 1970 UTC.

    Each word represents an instant in time.  Or an interval between times.

    time_lex = TimeLex()
    t_now = time_lex[Number.NAN]   # "now" -- the time it was referenced.
    t_i = time_lex[i]              # any other time, i seconds since 1970 UTC

    t_1 = time_lex[unix_timestamp_1]
    t_2 = time_lex[unix_timestamp_2]
    t_delta = time_lex[t_1]('differ')[t_2]   # seconds between any two times
    """

    _DIFFER = 'differ'
    _POWER_VERBS = [_DIFFER]

    def __init__(self, word_class=None, **kwargs):
        """
        This is cosmetics, just to name the word_class TimeWord.

        :param word_class: - or something else, but probably None
        :param kwargs: - could contain Lex() constructor stuff I guess
        """
        if word_class is None:

            class TimeWord(Word):
                pass

            word_class = TimeWord

        super(TimeLex, self).__init__(word_class=word_class, **kwargs)

    def now_word(self):
        """
        A qiki.Word representing the time this function was called.

        Actually it's a TimeWord, a subclass of qiki.Word.

        Suitable for comparing with other TimeWord's.

        Not to be confused with LexSentence.now_number(), a qiki.Number
        """
        return self[Number.NAN]

    def read_word(self, idn_ish):
        if Text.is_valid(idn_ish):
            txt = Text(idn_ish)
            if txt in self._POWER_VERBS:
                new_word = self.word_class(None)
                new_word.populate_from_num_txt(Number.NAN, txt)
                return new_word
                # NOTE:  This TimeLex word doesn't represent a time OR an interval.
                #        It represents the ABSTRACTION of a time interval.
                #        This word defines the verb whose txt='differ'.
                #        Then all time interval words have this word as their vrb.
            else:
                raise ValueError("TimeLex can't identify " + repr(idn_ish))
        else:
            new_word = super(TimeLex, self).read_word(idn_ish)
            new_word.exists()
            # NOTE:  This is a sneaky way to make new_word choate, so idn of NAN becomes now.
            #        This fixes time_lex[time_lex[NAN]] which also should be now.
            return new_word

    # noinspection PyMethodMayBeStatic
    def differ(self, word, sbj, vrb, obj):
        difference = obj.whn - sbj.whn
        word.populate_from_row(dict(
            idn=difference,
            num=difference,
            whn=difference,
            sbj=sbj.idn,
            vrb=vrb.idn,
            obj=obj.idn,
            txt=Text("fake-time-difference"),   # TODO:  e.g. "3.2 minutes" ?
        ))
        return True

    def populate_word_from_sbj_vrb_obj(self, word, sbj, vrb, obj):
        if vrb.txt == self._DIFFER:
            # XXX:  This is a cute hijack of qiki sentences, but clumsy as musher fudge.
            #       Subtraction, i.e. time_word.__sub__() might be a lot less muddy.
            return self.differ(word, sbj, vrb, obj)
        return False

    def populate_word_from_idn(self, word, idn):
        assert isinstance(word, Word)
        assert isinstance(idn, Number)
        if idn.is_nan():
            # TODO:  Should this weird special NAN=now case be somehow achieved by the
            #        same (weird) mechanism that LexMySQL auto increments when inserting a new word?
            #        Kind of a lex.next_available_idn() method or something?
            unix_epoch = Pythonic.unix_epoch_now()
            num = Number(unix_epoch)
            word.set_idn_if_you_really_have_to(num)
        else:
            try:
                unix_epoch = float(idn)
            except ValueError:
                unix_epoch = None
                num = Number.NAN
            else:
                num = idn

        if unix_epoch is None:
            txt = Text("((indeterminate time))")
        else:
            txt = Text(Pythonic.time_format_yyyy_mmdd_hhmm_ss(unix_epoch))
        word.populate_from_num_txt(
            num=num,
            txt=txt,
        )
        word.whn = word.num
        # NOTE:  Yes, idn == num == whn
        #        This breaks the rules for whn,
        #        which is supposed to indicate when the word became choate,
        #        e.g. was inserted into a LexMySQL record.
        #        But maybe that rule should only apply to a LexSentence word.
        #        Anyway, here it will facilitate creating a TimeLex word
        #        that represents a time difference.
        #        Because then you can check the difference
        #        between a TimeLex word (representing a moment in time)
        #        and any other word (representing anything)
        #        because only the whn fields will be compared.
        #        For example,
        #            t = TimeLex()
        #            now_word = t.now_word()
        #        and                                     v--- These fields represent time:  idn == num == whn
        #            how_old_is_word_w = t[w]('differ')[now_word]
        #                                  ^--- in word w, only the whn field has a time
        #        in case w.num represents a time, you can:
        #            t[w.num]('differ')[now_word]
        return True

    # TODO:  TimeLex()[t1:t2] could be a time interval shorthand??  D'oh!


class LexSentence(Lex):
    # rename candidates:  Site, Book, Server, Domain, Dictionary, Qorld, Lex, Lexicon
    #                     Station, Repo, Repository, Depot, Log, Tome, Manuscript,
    #                     Diary, Heap, Midden, Scribe, Stow (but it's a verb), Stowage,
    # Eventually, this will encapsulate other word repositories
    # Or should it simply be a sibling of e.g. Listing (List)?
    # This could encapsulate the idea of a container of sbj-vrb-obj words
    #     a sentence that defines a word.
    # Yeesh, should Word be an abstract base class, and derived classes
    #     have sbj,vrb,obj members, and other derivations that don't?
    #     class Sentence(Word)?
    # Make Lex formally an abstract base class

    """
    LexSentence is a collection of Sentences.

    A Sentence is a Numbered Word that is defined by a triplet of Words:  subject, verb, object

    LexSentence is the abstract base class for this kind of Word collector and factory.

    Instantiate a derived class of Lex for a database or other collection of word definitions.
    The word_class property is the class of words unique to this Lex instance.
                            If one is not supplied to this constructor,
                            as in LexSubClass(word_class=WordSubClass),
                            then such a class will be created for you.
    The _lex property is a bit mind-bending.
                      It is the word in the lex that's an abstraction for the lex.
                      See, each lex needs a way to refer to itself.
                      A pale shadow of the way it can refer to another lex, also.
                      That reference (to an abstraction of itself)
                      is usually in the sbj or obj of a word in the lex.
                      If `lex` is an instance of a Lex subclass,
                      Then lex._lex is a word that represents that lex.
                      lex._lex is an instance of lex.word_class
                      Boy for all that mind-bending it sure isn't used for much.
                      It's used in Word.define as a default for the sbj=None parameter.
                      It's used in LexMySQL.__init__() as a hint the lex is new and empty.
    """
    # TODO:  class WordForLexSentence base class, ala WordListed for Listing.

    def populate_word_from_idn(self, word, idn):
        raise NotImplementedError

    def __init__(self, **kwargs):
        super(LexSentence, self).__init__(**kwargs)
        self._lex = None
        self._noun = None
        self._verb = None
        self._define = None
        self._duplicate_definition_callback_functions = []

    def duplicate_definition_notify(self, f):
        # XXX:  Sure is a drastic, totalitarian solution.
        #       But duplicate defines have in the past wasted a lot of time.
        self._duplicate_definition_callback_functions.append(f)

    class ConnectError(Exception):
        pass

    # Hard-code the idns of the fundamental words.
    IDN_LEX    = Number(0)
    IDN_DEFINE = Number(1)
    IDN_NOUN   = Number(2)
    IDN_VERB   = Number(3)
    IDN_AGENT  = Number(4)

    IDN_MAX_FIXED = Number(4)

    # TODO:  Why did this start at 1 before?
    # TODO:  Why does this start at 0 now?

    def install_from_scratch(self):
        raise NotImplementedError()

    def uninstall_to_scratch(self):
        raise NotImplementedError()

    def _install_all_seminal_words(self):
        """
        Insert the five fundamental sentences into the Lex database.  (Unless already there.)
        Each sentence uses verbs and nouns defined in some of the other seminal sentences.

        The five seminal sentences:
              lex = lex.define(agent, 'lex')
                    lex.define(verb, 'define')
             noun = lex.define(noun, 'noun')
             verb = lex.define(noun, 'verb')
            agent = lex.define(noun, 'agent')

        At least that's how they'd be defined if forward references were not a problem.
        """
        def seminal_word(_idn, _obj, _txt):
            """Subject is always 'lex'.  Verb is always 'define'."""
            word = self[_idn]
            if not word.exists():
                self._install_one_seminal_word(_idn, _obj, _txt)
                word = self[_idn]
            assert word.exists()

        __crazy_idea_define_lex_first__ = True
        # TODO:  Haha, the order of idns is defined by the constants.  Rearrange them, e.g. Word.IDN_LEX
        if __crazy_idea_define_lex_first__:
            #                                                           forward,reflexive references
            seminal_word(self.IDN_LEX,    self.IDN_AGENT, u'lex')     # 2,1    0,+1,+4
            seminal_word(self.IDN_DEFINE, self.IDN_VERB,  u'define')  # 1,1   -1, 0,+2
            seminal_word(self.IDN_NOUN,   self.IDN_NOUN,  u'noun')    # 0,1   -2,-1, 0
            seminal_word(self.IDN_VERB,   self.IDN_NOUN,  u'verb')    # 0,0   -3,-2,-1
            seminal_word(self.IDN_AGENT,  self.IDN_NOUN,  u'agent')   # 0,0   -4,-3,-2
                                                                        # ---
                                                                        # 3,3
        else:
            #                                                           forward,reflexive references
            seminal_word(self.IDN_DEFINE, self.IDN_VERB,  u'define')  # 2,1   +4, 0,+2
            seminal_word(self.IDN_NOUN,   self.IDN_NOUN,  u'noun')    # 1,1   +3,-1, 0
            seminal_word(self.IDN_VERB,   self.IDN_NOUN,  u'verb')    # 1,0   +2,-2,-1
            seminal_word(self.IDN_AGENT,  self.IDN_NOUN,  u'agent')   # 1,0   +1,-3,-2
            seminal_word(self.IDN_LEX,    self.IDN_AGENT, u'lex')     # 0,1    0,-4,-1
                                                                        # ---
                                                                        # 5,3

    def _install_one_seminal_word(self, _idn, _obj, _txt):
        self.create_word(
            override_idn=_idn,
            sbj=self.IDN_LEX,
            vrb=self.IDN_DEFINE,
            obj=_obj,
            num=Number(1),
            txt=_txt,
        )

    def insert_word(self, word):
        raise NotImplementedError()

    def populate_word_from_definition(self, word, define_txt):
        raise NotImplementedError()

    def populate_word_from_sbj_vrb_obj(self, word, sbj, vrb, obj):
        raise NotImplementedError()

    def populate_word_from_sbj_vrb_obj_num_txt(self, word, sbj, vrb, obj, num, txt):
        raise NotImplementedError()

    def noun(self, name=None):
        if name is None:
            return self._noun
        else:
            return self.define(self._noun, name)

    def verb(self, name=None):   # was , sbj=None):
        if name is None:
            return self._verb
        else:
            return self.define(self._verb, name)   # was: , sbj=sbj)

    class DefinitionMustBeUnicode(TypeError):
        """In a word definition, the name (txt) must be Unicode."""

    def define(self, obj, txt):   # was , sbj=None):  --- is this needed any more?
        obj_could_be_many_types = obj

        # sbj_could_be_none = sbj
        # sbj = sbj_could_be_none or self._lex

        sbj = self._lex
        vrb = self._define
        obj = self[obj_could_be_many_types]

        if not Text.is_valid(txt):
            raise self.DefinitionMustBeUnicode(
                "Definition must have unicode name, not " + repr(txt)
            )

        try:
            old_definition = self[txt]
        except ValueError:
            '''txt must not be defined yet.'''
        else:
            if old_definition.exists():
                # TODO:  Use create_word's use_already option instead?
                #        Oops, cannot!
                #        define() goes to EARLIEST definition
                #        create_word(use_already=True) goes to LATEST definition
                if len(self._duplicate_definition_callback_functions) > 0:
                    duplicate_words = self.find_words(vrb=self._define, txt=txt, sbj=sbj)
                    if len(duplicate_words) != 1:
                        for function in self._duplicate_definition_callback_functions:
                            function(
                                txt,
                                "Trying to define a {obj} called '{txt}', "
                                "but there are already {count} definitions for '{txt}': {word}".format(
                                    obj=str(obj),
                                    count=len(duplicate_words),
                                    txt=txt,
                                    word=", ".join("{idn}:{txt}".format(
                                        idn=w.idn.qstring(),
                                        txt=str(w.obj),
                                    ) for w in duplicate_words),
                                )
                            )
                return old_definition
        return self.create_word(sbj=sbj, vrb=vrb, obj=obj, txt=txt)

    def find_words(self, **kwargs):
        raise NotImplementedError()

    outer = 0   # HACK
    inner = 0   # HACK

    _global_lock = threading.Lock()

    def _lock_next_word(self):
        """
        Make the auto-increment simulation thread-safe.

        Derived class may override the class variable _global_lock,
        by mimicking the above line exactly,
        so that it referees among all instances of that class,
        (but only that class, not among sibling class instances)
        e.g. to keep thread-specific instances of that class from racing one another.

        Or the derived class may override the instance method _lock_next_word(),
        so that each instance of that class has its own lock.
        This might make sense if a single instance could be shared by multiple threads.
        Wouldn't work with LexMySQL because apparently one mysql.connector.connect()
        object cannot be shared by multiple threads.

        By default all instances of all derived classes use the singleton LexSentence._global_lock
        (Only applies to instances running on the same host of course.)
        """
        return self._global_lock

    def insert_next_word(self, word):
        # global max_idn_lock

        # noinspection PyUnusedLocal
        def droid(step):
            """
            Probe droid for debugging the browse storm bugs.

            EXAMPLE:
                INSERT_A b'shrubbery' 0 1 unlock 54423720 0q82_04
                INSERT_B b'shrubbery' 1 1 LOCKED 54423720 0q82_04
                INSERT_C b'shrubbery' 1 1 LOCKED 54423720 0q82_05
                INSERT_D b'shrubbery' 0 1 unlock 54423720 0q82_05
            """
            # print(
            #     step + " " +
            #     str(word.txt.encode('ascii', 'ignore')).replace(" ", "_") + " " +
            #     str(LexSentence.inner) + " " +
            #     str(LexSentence.outer) + " " +
            #     ("LOCKED " if self._global_lock.locked() else "unlock ") +
            #     str(id(self._global_lock)) + " " +
            #     self.max_idn().qstring() +
            #     "\n", end=""
            # )

        try:
            LexSentence.outer += 1
            droid("INSERT_A")
            with self._lock_next_word():   # test_word.Word0080Threading.LexManipulated.cop1
                try:
                    LexSentence.inner += 1
                    droid("INSERT_B")
                    self._start_transaction()   # test_word.Word0080Threading.LexManipulated.cop2

                    idn_of_new_word = self.next_idn()
                    self._critical_moment_1()   # test_word.Word0080Threading.LexManipulated.cop3
                    word.set_idn_if_you_really_have_to(idn_of_new_word)
                    self._critical_moment_2()
                    self.insert_word(word)
                finally:
                    droid("INSERT_C")
                    LexSentence.inner -= 1
            # TODO:  Unit test this lock, with "simultaneous" inserts on multiple threads.
        finally:
            droid("INSERT_D")
            LexSentence.outer -= 1
        
    def _critical_moment_1(self):
        """For testing, hold up this step to raise a duplicate IDN error."""

    def _critical_moment_2(self):
        """For testing, hold up this step to raise a duplicate IDN error."""

    def _start_transaction(self):
        """Whatever needs to happen just before getting the next idn.  Do nothing by default."""

    def next_idn(self):
        return self.max_idn().inc()   # Crude reinvention of AUTO_INCREMENT

    def max_idn(self):
        raise NotImplementedError()

    def server_version(self):
        return "(not implemented)"

    def disconnect(self):
        raise NotImplementedError()

    def find_last(self, **kwargs):
        # TODO:  In LexMySQL, do this more efficiently:
        #        limit find_words() to latest using sql LIMIT.
        # TODO:  Who should make sure idn_ascending is True?
        bunch = self.find_words(**kwargs)
        try:
            return bunch[-1]
        except IndexError:
            raise self.NotFound

    # def read_word(self, txt_or_idn_etc):
    #     if Text.is_valid(txt_or_idn_etc):
    #         # word = self.word_class(txt=txt_or_idn_etc)  <-- well that was dumb ... OR NOT
    #         word = self.word_class(txt_or_idn_etc)
    #         # word = self[txt_or_idn_etc]  <--- haha no, that is infinite recursion
    #         # word._from_definition(txt_or_idn_etc)
    #         # FIXME:  Should verify that lex defined it.
    #         #         Maybe eventually the user can define it himself.
    #         # word = self.lex.find_words(sbj=self.lex, vrb='define', txt=txt_or_idn_etc)
    #
    #         # self.populate_word_from_definition(word, txt_or_idn_etc)   # TODO:  redundant??
    #         return word
    #     else:
    #         return super(LexSentence, self).read_word(txt_or_idn_etc)

    def read_word(self, txt_or_idn_etc):
        if Text.is_valid(txt_or_idn_etc):
            word = self.word_class(txt_or_idn_etc)
            return word
        else:
            return super(LexSentence, self).read_word(txt_or_idn_etc)

    class CreateWordError(ValueError):
        """LexSentence.create_word() argument error."""

    def create_word(
        self,
        sbj,
        vrb,
        obj,
        num=None,
        txt=None,
        num_add=None,
        use_already=False,
        override_idn=None
    ):
        """
        Construct a new sentence from a 3-word subject-verb-object.
        """
        # TODO:  Disallow num,txt positionally, unlike Word.says()

        # TODO:  Allow sbj=lex
        assert isinstance(sbj, (Word, Number, type(u''))), "sbj cannot be a {type}".format(type=type_name(sbj))
        assert isinstance(vrb, (Word, Number, type(u''))), "vrb cannot be a {type}".format(type=type_name(vrb))
        assert isinstance(obj, (Word, Number, type(u''))), "obj cannot be a {type}".format(type=type_name(obj))

        # if isinstance(txt, numbers.Number) or Text.is_valid(num):
        #     # TODO:  Why `or` not `and`?
        #     (txt, num) = (num, txt)

        if num is not None and num_add is not None:
            raise self.CreateWordError("{self_type}.create_word() cannot specify both num and num_add.".format(
                self_type=type_name(self),
            ))

        num = num if num is not None else 1
        txt = txt if txt is not None else u''

        if not Number.is_number(num):
            # TODO:  Allow q-strings for num.  I.e. raise this exception on Number(num) error.
            raise self.CreateWordError("Wrong type for {self_type}.create_word(num={num_type})".format(
                self_type=type_name(self),
                num_type=type_name(num),
            ))
        if not Text.is_valid(txt):
            raise self.CreateWordError("Wrong type for {self_type}.create_word(txt={txt_type})".format(
                self_type=type_name(self),
                txt_type=type_name(txt),
            ))

        new_word = self.word_class(
            sbj=sbj,
            vrb=vrb,
            obj=obj,
            num=Number(num),
            txt=txt,
        )
        if num_add is not None:
            assert Number.is_number(num_add)
            self.populate_word_from_sbj_vrb_obj(new_word, sbj, vrb, obj)
            if new_word.exists():
                # noinspection PyProtectedMember
                new_word._fields['num'] += Number(num_add)
                new_word.set_idn_if_you_really_have_to(Number.NAN)
            else:
                # noinspection PyProtectedMember
                new_word._fields['num'] = Number(num_add)
            new_word.save()
        elif use_already:
            old_word = self.word_class(
                sbj=sbj,
                vrb=vrb,
                obj=obj
            )
            self.populate_word_from_sbj_vrb_obj(old_word, sbj, vrb, obj)
            if not old_word.exists():
                new_word.save()
            elif (
                old_word.txt == new_word.txt and
                old_word.num == new_word.num
            ):
                # NOTE:  There was an identical sentence already (same s,v,o,t,n).
                #        (And it was the latest word matching (s,v,o).)
                #        Fetch it so new_word.exists().
                #        This is the only path through create_word()
                #        where no new sentence is created.
                #        That is, where new_word is an old word.
                # NOTE:  It only happens when the old_word is the NEWEST of its kind (s,v,o)
                #        This was a problem with multiple explanations on a word.
                self.populate_word_from_sbj_vrb_obj_num_txt(new_word, sbj, vrb, obj, Number(num), txt)
                assert new_word.idn == old_word.idn, "Race condition {old} to {new}".format(
                    old=old_word.idn.qstring(),
                    new=new_word.idn.qstring()
                )
            else:
                new_word.save()
        else:
            new_word.save(override_idn=override_idn)
        return new_word

    @classmethod
    def now_number(cls):
        """
        Returns a qiki.Number suitable for the whn field:  seconds since 1970 UTC.

        Not to be confused with qiki.TimeLex.now_word() which is a qiki.Word
        an abstraction representing the current time.
        """
        return TimeLex().now_word().num


def native_num(num):
    if num.is_suffixed():
        # TODO:  Complex?
        return num.qstring()
    elif not num.is_reasonable():
        # THANKS:  JSON is a dummy about NaN, inf,
        #          https://stackoverflow.com/q/1423081/673991#comment52764219_1424034
        # THANKS:  None to nul, https://docs.python.org/library/json.html#py-to-json-table
        return None
    elif num.is_whole():
        return int(num)
    else:
        # TODO:  Ludicrous numbers should become int.
        return float(num)


# import json
#
#
# class WordEncoder(json.JSONEncoder):
#     def default(self, o):
#         if isinstance(o, Word):
#             return repr(o)
#         else:
#             return super(WordEncoder, self).default(o)


class LexInMemory(LexSentence):
    """In-memory lex.  Always start empty."""

    def __init__(self, **kwargs):
        super(LexInMemory, self).__init__(**kwargs)
        # TODO:  new_lex_memory = LexMemory(old_lex_memory)?

        self.words = None
        self.install_from_scratch()

    def insert_word(self, word):
        assert not word.idn.is_nan()
        word.whn = self.now_number()

        self.words.append(word)

        assert int(word.idn) == len(self.words) - 1
        # NOTE:   Crude expectation word insertion order 0,1,2,...

        # noinspection PyProtectedMember
        word._now_it_exists()

    def disconnect(self):
        pass

    def install_from_scratch(self):
        self.words = []
        # NOTE:  Assume zero-starting idns

        self._lex = self.word_class(self.IDN_LEX)

        self._install_all_seminal_words()
        self._lex = self.words[int(self.IDN_LEX)]
        self._noun = self.words[int(self.IDN_NOUN)]
        self._verb = self.words[int(self.IDN_VERB)]
        self._define = self.words[int(self.IDN_DEFINE)]

    def uninstall_to_scratch(self):
        del self.words

    def populate_word_from_idn(self, word, idn):
        try:
            word_source = self.words[int(idn)]
        except (
            IndexError,   # e.g. (what?)
            ValueError    # e.g. Word(NAN) - ValueError: Not-A-Number cannot be represented by integers.
        ):
            return False
        else:
            word.populate_from_word(word_source)
            return True

    def populate_word_from_definition(self, word, define_txt):
        """Flesh out a word by its txt.  sbj=lex, vrb=define only."""
        for word_source in self.words:
            if (
                word_source.sbj.idn == self.IDN_LEX and
                word_source.vrb.idn == self.IDN_DEFINE and
                word_source.txt == Text(define_txt)
            ):
                word.populate_from_word(word_source)
                return True
        return False

    def populate_word_from_sbj_vrb_obj(self, word, sbj, vrb, obj):
        for word_source in reversed(self.words):
            # NOTE:  reversed() to prefer the LATEST word that matches s,v,o
            if word_source.sbj == sbj and word_source.vrb == vrb and word_source.obj == obj:
                word.populate_from_word(word_source)
                return True
        return False

    def populate_word_from_sbj_vrb_obj_num_txt(self, word, sbj, vrb, obj, num, txt):
        for word_source in reversed(self.words):
            if (
                word_source.sbj == sbj and
                word_source.vrb == vrb and
                word_source.obj == obj and
                word_source.num == num and
                word_source.txt == txt
            ):
                word.populate_from_word(word_source)
                return True
        return False

    def max_idn(self):
        try:
            return self.words[-1].idn
        except (AttributeError, IndexError):   # whether self.words is missing or empty
            return Number(0)

    def find_words(
        self,
        idn=None,
        sbj=None,
        vrb=None,
        obj=None,
        txt=None,
        # TODO: num
        idn_ascending=True,
        jbo_ascending=True,
        jbo_vrb=(),
        jbo_strictly=False,
        debug=False
    ):
        found_words = []
        for word_source in self.words if idn_ascending else reversed(self.words):
            hit = True
            if idn is not None and not self.word_match(word_source.idn, idn):   #
                # was word_source.idn != self.idn_ify(idn):
                # TODO:  Why does word_match(word_source.idn, idn) fail in one test?
                hit = False
            if sbj is not None and not self.word_match(word_source.sbj, sbj):
                hit = False
            if vrb is not None and not self.word_match(word_source.vrb, vrb):
                hit = False
            if obj is not None and not self.word_match(word_source.obj, obj):
                hit = False
            if txt is not None and not self.txt_match(word_source.txt, txt):
                # was word_source.txt != Text(txt):
                hit = False
            if hit:
                found_words.append(self[word_source])   # copy constructor

        if jbo_vrb:
            restricted_found_words = []
            for found_word in found_words:
                jbo = []
                for other_word in self.words:
                    if (
                        self.word_match(other_word.obj, found_word.idn) and
                        self.word_match(other_word.vrb, jbo_vrb)
                    ):
                        jbo.append(other_word)

                new_word = self[found_word]
                assert new_word is not found_word

                new_word.jbo = jbo
                # FIXME:  Whoa this could add a jbo to the in-memory lex object couldn't it!
                #         Same bug exists with LexMySQL instance maybe!
                #         Maybe this is a reason NOT to enforce a lex being a singleton.
                #         Or if this bug does NOT happen
                #             it blows a hole in the idea lex ever was a singleton.
                #             I don't see where Word._from_word() enforces that.
                # TODO:  Test whether lex[lex] is lex -- Oh it is in test_08_lex_square_lex

                if jbo or not jbo_strictly:
                    restricted_found_words.append(new_word)
            return restricted_found_words
        else:
            return found_words

    def word_match(self, word_1, word_or_words_2):
        """
        Is a word equal to another word (or any of a nested collection of words)?

        Actually they can be idns too.
        """
        assert not is_iterable(word_1)
        if is_iterable(word_or_words_2):
            for word_2 in word_or_words_2:
                if self.word_match(word_1, word_2):
                    return True
            return False
        else:
            return self.idn_ify(word_1) == self.idn_ify(word_or_words_2)

    def txt_match(self, txt_1, txt_or_txts_2):
        """
        Is a txt equal to another txt (or any of a nested collection of txt)?
        """
        # TODO:  D.R.Y. with word_match()
        assert not is_iterable(txt_1)
        if is_iterable(txt_or_txts_2):
            for txt_2 in txt_or_txts_2:
                if self.txt_match(txt_1, txt_2):
                    return True
            return False
        else:
            return txt_1 == txt_or_txts_2


# noinspection SqlDialectInspection,SqlNoDataSourceInspection
class LexMySQL(LexSentence):
    """
    Store a Lex in a MySQL table.
    """
    # TODO:  Move LexMySQL to lex_mysql.py?

    def __init__(self, **kwargs):
        """
        Create or initialize the table, as necessary.

        kwargs parameters:
            language - must be 'MySQL' (required)
            table - e.g. 'word' (required)
            engine - MySQL ENGINE, defaults to InnoDB
            txt_type - MySQL type of txt, defaults to VARCHAR(10000)
        """

        language = kwargs.pop('language')
        assert language == 'MySQL'
        self._table = kwargs.pop('table')
        self._engine = kwargs.pop('engine', 'InnoDB')
        self._connection = None
        default_txt_type = 'VARCHAR(10000)'   if self._engine.upper() == 'MEMORY' else   'TEXT'
        # VARCHAR(65536):  ProgrammingError: 1074 (42000): Column length too big for column 'txt'
        #                  (max = 16383); use BLOB or TEXT instead
        # VARCHAR(16383):  ProgrammingError: 1118 (42000): Row size too large. The maximum row size
        #                  for the used table type, not counting BLOBs, is 65535. This includes
        #                  storage overhead, check the manual. You have to change some columns to
        #                  TEXT or BLOBs
        # SEE:  VARCHAR versus TEXT, https://stackoverflow.com/a/2023513/673991
        self._txt_type = kwargs.pop('txt_type', default_txt_type)

        kwargs_sql = { k: v for k, v in kwargs.items() if k     in self.APPROVED_MYSQL_CONNECT_ARGUMENTS }
        kwargs_etc = { k: v for k, v in kwargs.items() if k not in self.APPROVED_MYSQL_CONNECT_ARGUMENTS }

        super(LexMySQL, self).__init__(**kwargs_etc)

        def do_connect():
            return mysql.connector.connect(**kwargs_sql)

        def do_connect_with_and_without_use_pure():
            """
            MySQL Connector compatibility.

            MySQL Python Connector version 8.0.16 requires use_pure=True.
            MySQL Python Connector version 2.2.2b1 doesn't support use_pure.
            """

            kwargs_sql['use_pure'] = True
            # THANKS:  Disable CEXT because it doesn't support prepared statements
            #          https://stackoverflow.com/a/50535647/673991

            try:
                return do_connect()
            except AttributeError as attribute_error:
                if str(attribute_error) == "Unsupported argument 'use_pure'":
                    del kwargs_sql['use_pure']
                    return do_connect()
                else:
                    print("Unknown Attribute Error:", str(attribute_error))
                    raise

        try:
            self._connection = do_connect_with_and_without_use_pure()
        except mysql.connector.Error as exception:
            raise self.ConnectError(exception.__class__.__name__ + " - " + str(exception))
            # EXAMPLE:  (mysqld is down)
            #     InterfaceError - 2003: Can't connect to MySQL server on 'localhost:33073'
            #     (10061 No connection could be made because the target machine actively refused it)
            # EXAMPLE:  (maybe wrong password)
            #     ProgrammingError

        try:
            if HORRIBLE_MYSQL_CONNECTOR_WORKAROUND:
                self._connection.set_charset_collation(str('latin1'))
            else:
                self._connection.set_charset_collation(str('utf8'))

            # self.super_query('SET TRANSACTION ISOLATION LEVEL READ COMMITTED')
            # # NOTE:  Required for max_idn() to keep up with latest insertions (created words).
            # # THANKS:  Isolation level, https://stackoverflow.com/a/17589234/673991
            # # SEE:  SET TRANSACTION, https://dev.mysql.com/doc/refman/en/set-transaction.html
            # # SEE:  READ COMMITTED, https://dev.mysql.com/doc/refman/en/innodb-transaction-isolation-levels.html#isolevel_read-committed
            # # DONE:  Would still rather make max_idn() alone do this,
            # #        but "FROM SHARE" was a syntax error.
            # #        Maybe "FOR UPDATE" in the max_idn() SELECT statement,
            # #        plus a commit in super_select() would do the trick?
            # #        (Or maybe in insert_next_word())
            # # SEE:  FOR UPDATE, https://dev.mysql.com/doc/refman/en/select.html

            self._lex = self.word_class(self.IDN_LEX)
            try:
                # noinspection PyProtectedMember
                self._lex._choate()   # Get the word out of this Lex that represents the Lex itself.
            except self.QueryError as exception:   # was mysql.connector.ProgrammingError as exception:
                exception_message = str(exception)
                if re.search(r"Table .* doesn't exist", exception_message):
                    # TODO:  Better detection of automatic table creation opportunity.
                    self.install_from_scratch()
                    # TODO:  Do not super() twice -- cuz it's not D.R.Y.
                    # TODO:  Do not install in unit tests if we're about to uninstall.
                    super(LexMySQL, self).__init__(**kwargs_etc)
                    self._lex = self.word_class(self.IDN_LEX)   # because base constructor sets it to None
                else:
                    raise self.ConnectError(str(exception))

            if self._lex is None or not self._lex.exists():
                self._install_all_seminal_words()

            self._lex = self[self.IDN_LEX]
            self._noun = self[self.IDN_NOUN]
            self._verb = self[self.IDN_VERB]
            self._define = self[self.IDN_DEFINE]
            assert self._connection.is_connected()

        except BaseException:
            # SEE:  Exception vs BaseException vs bare except, https://stackoverflow.com/a/7161517/673991
            # NOTE:  Prevent ConnectError: OperationalError - 1040 (08004): Too many connections
            self.disconnect()
            raise
    APPROVED_MYSQL_CONNECT_ARGUMENTS = {
        'user',
        'password',
        'database',
        'host',
        'port',
        'charset',
        'collation',
        'ssl_ca',
        'ssl_cert',
        'ssl_key',
    }
    # SEE:  https://dev.mysql.com/doc/connector-python/en/connector-python-connectargs.html

    def disconnect(self):
        # noinspection SpellCheckingInspection
        """
        Prevent lots of ResourceWarning messages in test_word.py in Python 3.5

        EXAMPLE:
            .../qiki-python/number.py:180: ResourceWarning: unclosed
            <socket.socket fd=532, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM,
            proto=6, laddr=(...), raddr=(...)>

        SEE:  Closing aggregated connection (using flawed __del__),
              https://softwareengineering.stackexchange.com/a/200529/56713
        """

        # noinspection PyBroadException
        try:
            name_error = NameError
        except Exception:
            '''Severe inability to close'''
            # EXAMPLE:  NameError: name 'NameError' is not defined
            raise
        else:
            try:
                need_to_close = hasattr(self, '_connection') and self._connection is not None
            except name_error:
                '''Dying session, give up trying to close gracefully.'''
                # EXAMPLE:  NameError: name 'hasattr' is not defined
                # THANKS:  Safely ignore, https://stackoverflow.com/a/44940341/673991
            else:
                if need_to_close:
                    if self._connection.is_connected():
                        # NOTE:  Prevent `TypeError: 'NoneType'` deep in MySQL Connector code.
                        self._connection.close()
                    self._connection = None

    def __del__(self):
        self.disconnect()

    def install_from_scratch(self):
        """Create database table and insert words.  Or do nothing if table and/or words already exist."""
        if not re.match(self._ENGINE_NAME_VALIDITY, self._engine):
            raise self.IllegalEngineName("Not a valid table name: " + repr(self._engine))

        with self._cursor() as cursor:
            if HORRIBLE_MYSQL_CONNECTOR_WORKAROUND:
                txt_specs = "CHARACTER SET latin1"
            else:
                txt_specs = "CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            query = """
                CREATE TABLE IF NOT EXISTS `{table}` (
                    `idn` VARBINARY(255) NOT NULL,
                    `sbj` VARBINARY(255) NOT NULL,
                    `vrb` VARBINARY(255) NOT NULL,
                    `obj` VARBINARY(255) NOT NULL,
                    `num` VARBINARY(255) NOT NULL,
                    `txt` {txt_type} {txt_specs} NOT NULL,
                    `whn` VARBINARY(255) NOT NULL,
                    PRIMARY KEY (`idn`)
                )
                    ENGINE = `{engine}`
                ;
            """.format(
                table=self.table,
                txt_type=self._txt_type,
                txt_specs=txt_specs,
                engine=self._engine,
            )

            # Graveyard:
                    # DEFAULT CHARACTER SET = utf8mb4
                    # DEFAULT COLLATE = utf8mb4_general_ci
                    # `txt` {txt_type}
                    #     CHARACTER SET utf8mb4
                    #     COLLATE utf8mb4_general_ci
                    #     NOT NULL,

            # cursor.execute(query)
            self._execute(cursor, query)
            # TODO:  other keys?  sbj-vrb?   obj-vrb?
        self._install_all_seminal_words()

    def _install_one_seminal_word(self, _idn, _obj, _txt):
        try:
            super(LexMySQL, self)._install_one_seminal_word(_idn, _obj, _txt)
        except mysql.connector.ProgrammingError as exception:
            exception_message = str(exception)
            if re.search(r"INSERT command denied to user", exception_message):
                print("GRANT INSERT ON db TO user@host?")
                raise
            else:
                print(exception_message)
                raise
        except mysql.connector.IntegrityError:
            # TODO:  What was I thinking should happen here?
            raise
        except mysql.connector.Error:
            # TODO:  What could happen here?
            raise

    def uninstall_to_scratch(self):
        """Deletes table.  Opposite of install_from_scratch()."""
        try:
            self.super_query('DELETE FROM', self.table)
        except self.QueryError:
            '''Not a problem if MySQL user doesn't have the DELETE privilege'''
        self.super_query('DROP TABLE IF EXISTS', self.table)
        # self._now_it_doesnt_exist()   # So install will insert the lex sentence.
        # After this, we can only install_from_scratch() or disconnect()

    # noinspection SpellCheckingInspection
    def insert_word(self, word):
        whn = self.now_number()
        # TODO:  Enforce whn uniqueness?
        # SEE:  https://docs.python.org/library/time.html#time.time
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

        names = []
        values = []

        if not word.idn.is_nan():
            names += ['idn']
            values += [word.idn]

        names +=  [    'sbj',    'vrb',    'obj',    'num',    'txt', 'whn']
        values += [word.sbj, word.vrb, word.obj, word.num, word.txt,   whn ]

        last_row_id = self.super_query(
            'INSERT INTO', self.table,
            '(' + ','.join(names) + ') ' +
            'VALUES (', values, ')')
        # TODO:  named substitutions with NON-prepared statements??
        # THANKS:  https://dev.mysql.com/doc/connector-python/en/connector-python-api-mysqlcursor-execute.html
        # THANKS:  About prepared statements, http://stackoverflow.com/a/31979062/673991
        self._connection.commit()
        word.whn = whn
        # noinspection PyProtectedMember
        word._now_it_exists()
        return last_row_id

    def _start_transaction(self):
        """
        Akin to MySQL START TRANSACTION.

        Ironically, start a new transaction by ending the (apparently auto-started) old one.

        This prevents the following exception when multi-threaded requests generate new words:
            mysql.connector.errors.ProgrammingError: Transaction already in progress
        """
        self._connection.commit()
        # NOTE:  self._connection.start_transaction() generates:
        #        ProgrammingError: Transaction already in progress

    class Cursor(object):
        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            try:
                self.the_cursor = self.connection.cursor(prepared=True)
                # NOTE:  Exception here if we don't connect with use_pure=True:
                #        NotImplementedError: Alternative: Use connection.MySQLCursorPrepared
            except mysql.connector.OperationalError:
                self.connection.connect()
                self.the_cursor = self.connection.cursor(prepared=True)
            return self.the_cursor

        # noinspection PyUnusedLocal
        def __exit__(self, exc_type, exc_val, exc_tb):
            try:
                self.the_cursor.close()
            except mysql.connector.DatabaseError as e:
                # NOTE:  Avoid this exception masking another, while a cursor is alive.
                # EXAMPLE:  InternalError: Unread result found
                #           This can happen if an exception is raised inside a with-cursor clause
                #           when selecting multiple rows.
                print("Error closing cursor", str(e))

    def _cursor(self):
        return self.Cursor(self._connection)

    def _simulate_connection_neglect(self):
        """
        For testing, simulate what happens when the MySQL connection is idle for too long.

        This is easy to achieve, just close the connection.
        The symptom is the same:
            mysql.connector.errors.OperationalError: MySQL Connection not available.
        I originally thought this had something to do with the connection_timeout
        option aka socket.settimeout(), but it does not.
        """
        self._connection.close()

    def populate_word_from_idn(self, word, idn):
        rows = self.super_select(
            'SELECT * FROM', self.table,
            'WHERE idn =', idn
        )
        return self._populate_from_one_row(word, rows)

    def populate_word_from_definition(self, word, define_txt):
        """Flesh out a word by its txt.  sbj=lex, vrb=define only."""
        rows = self.super_select(
            'SELECT * FROM', self.table, 'AS w '
            'WHERE sbj =', self.IDN_LEX,
            'AND vrb =', self.IDN_DEFINE,
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
            return    # oops, fewer than 1 row
        else:
            word.populate_from_row(row)
            try:
                next(rows)
            except StopIteration:
                return True
            else:
                assert False, "Cannot populate from unexpected extra rows."
                # noinspection PyUnreachableCode
                return False   # oops, more than 1 row (it is reachable, with python -O)

    # TODO:  Study JOIN with LIMIT 1 in 2 SELECTS, http://stackoverflow.com/a/28853456/673991
    # Maybe also http://stackoverflow.com/questions/11885394/mysql-join-with-limit-1/11885521#11885521

    def find_words(
        self,
        idn=None,
        sbj=None,
        vrb=None,
        obj=None,
        txt=None,
        # TODO: num
        idn_ascending=True,
        jbo_ascending=True,
        jbo_vrb=(),
        jbo_strictly=False,
        debug=False
    ):
        # TODO:  Lex.find()  It should return inchoate words.  Best of both find_words and find_idns.
        """
        Select words by subject, verb, and/or object.

        Return a list of choate words.

        idn,sbj,vrb,obj each restrict the list of returned words.
        Except when they're None or empty, then they don't restrict.

        The "jbo" concept means that, in addition to the words we find,
        we're also interested in words whose OBJECT is a found word.
        Get it, "jbo" is "obj" backwards?
        We call those jbo words objectifiers.
        the jbo of a word w contains words that objectify w.

        jbo_vrb is a container of verbs to restrict those objectifiers.
        It contains either words or idns (but not txts).
        So jbo_vrb=[like] means glom onto found words the words that like them.

        jbo_vrb is not restrictive it's elaborative (note 1).
        If jbo_vrb is a container of verbs, each returned word has a jbo attribute
        that is, a list of choate words whose object is the word.
        It gloms onto each word the words that point to it (using approved verbs).
        jbo_vrb cannot be a generator's iterator, because super_select()
        will probably need two passes on it anyway.

        The order of words is chronological.
        idn_ascending=False for reverse-chronological.
        The order of jbo words is always chronological.

        jbo_strictly means only include words that are the objects of jbo_vrb verbs.

        If jbo_strictly is True and jbo_vrb contains multiple verbs, then an OR
        relationship can be expected.  That is, words will be included if they
        are objectified by ANY of the jbo_vrb verbs.

        (note 1) If jbo_strictly is True, then jbo_vrb IS restrictive.
        and words are excluded that would otherwise have an empty jbo.
        """
        if isinstance(jbo_vrb, (Word, Number)):
            jbo_vrb = (jbo_vrb,)
        if jbo_vrb is None:
            jbo_vrb = ()
        assert isinstance(idn, (Number, Word, type(None)))            or is_iterable(idn)
        assert isinstance(sbj, (Number, Word, type(None), type(u''))) or is_iterable(sbj)   # TODO: Allow LexSentence?
        assert isinstance(vrb, (Number, Word, type(None), type(u''))) or is_iterable(vrb)
        assert isinstance(obj, (Number, Word, type(None), type(u''))) or is_iterable(obj)
        assert isinstance(txt, (Text,         type(None), type(u''))) or is_iterable(txt)
        assert isinstance(jbo_vrb, (list, tuple, set)), "jbo_vrb is a " + type_name(jbo_vrb)
        assert hasattr(jbo_vrb, '__iter__')
        idn_order = 'ASC' if idn_ascending else 'DESC'
        jbo_order = 'ASC' if jbo_ascending else 'DESC'
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
                join, self.table, 'AS jbo ' +
                    'ON jbo.obj = w.idn ' +
                        'AND jbo.vrb in (', jbo_vrb, ')',
                None
            ]

        query_args += ['WHERE TRUE', None]
        query_args += self._and_clauses(idn, sbj, vrb, obj, txt)

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
                # NOTE:  This violates the singleton lex object idea!
                word.jbo = []
                words.append(word)   # To be continued, we may append to word.jbo later.
                # So yield would not work here -- because word continues to be modified after
                # it gets appended to words.  Similarly new_jbo after appended to word.jbo.
                # No wait, new_jbo is final, and not modified after appended to word.jbo.
                # But wait a minute, who's to say an object cannot be modified after yielded?
                # It could, but that could lead to ferociously complicated bugs!
                # Upshot:  append not yield
            jbo_idn = row.get('jbo_idn', None)
            if jbo_idn is not None:
                new_jbo = self[None]
                new_jbo.populate_from_row(row, prefix='jbo_')
                word.jbo.append(new_jbo)
        return words

    # def find_idns(self, idn=None, sbj=None, vrb=None, obj=None, idn_order='ASC'):
    #     """
    #     Select word identifiers by subject, verb, and/or object.
    #
    #     Return list of idns.
    #     """
    #     query_args = ['SELECT idn FROM', self.table, 'AS w WHERE TRUE', None]
    #     query_args += self._and_clauses(idn, sbj, vrb, obj)
    #     query_args += ['ORDER BY idn ' + idn_order]
    #     rows_of_idns = self.super_select(*query_args)
    #     idns = [row['idn'] for row in rows_of_idns]
    #     return idns

    MAX_ITERABLE = 1000


    class OverflowIterable(ValueError):
        """find_words() can take iterables, but not too big."""


    # @staticmethod
    def _and_clauses(self, idn, sbj, vrb, obj, txt):
        assert isinstance(idn, (Number, Word, type(None),          )) or is_iterable(idn)
        assert isinstance(sbj, (Number, Word, type(None), type(u''))) or is_iterable(sbj)
        assert isinstance(vrb, (Number, Word, type(None), type(u''))) or is_iterable(vrb)
        assert isinstance(obj, (Number, Word, type(None), type(u''))) or is_iterable(obj)
        assert isinstance(txt, (Text,         type(None), type(u''))) or is_iterable(txt)

        def clause(value_or_values, name, conversion_function):
            """
            Format field value(s) into an AND clause, suitable for super_select().

            EXAMPLE:
                ['AND w.txt IN (', Text('a'), ',', Text('b'), ')', None] ==
                    list(clause([       'a',            'b'], 'txt', lambda: Text(x)))

            :param value_or_values: what
            :param name:
            :param conversion_function:
            :return:
            """
            if value_or_values is not None:
                if is_iterable(value_or_values):
                    almost_values = value_or_values
                else:
                    almost_values = [value_or_values]

                # values = [conversion_function(x) for x in almost_values]
                # NOTE:  Prevent infinite loop
                values = []
                for x in almost_values:
                    values.append(conversion_function(x))
                    if len(values) > self.MAX_ITERABLE:
                        raise self.OverflowIterable("find_words({name} = contains more than {max} things)".format(
                            name=name,
                            max=self.MAX_ITERABLE,
                        ))

                if len(values) < 1:
                    '''part=[] and part=None mean no restriction'''
                elif len(values) == 1:
                    yield 'AND w.{name} ='.format(name=name)
                    yield values[0]
                else:
                    yield 'AND w.{name} IN ('.format(name=name)
                    yield values[0]
                    for value in values[1 : ]:
                        yield ','
                        yield value
                    yield ')'
                    yield None

        query_args = []

        query_args += list(clause(idn, 'idn', lambda x: self.idn_ify(x)))
        query_args += list(clause(sbj, 'sbj', lambda x: self.idn_ify(x)))
        query_args += list(clause(vrb, 'vrb', lambda x: self.idn_ify(x)))
        query_args += list(clause(obj, 'obj', lambda x: self.idn_ify(x)))
        query_args += list(clause(txt, 'txt', lambda x: Text(x)))
        return query_args

    def server_version(self):
        return Text.decode_if_you_must(self.super_select_one('SELECT VERSION()')[0])

    def super_select_one(self, *query_args, **kwargs):
        """
        Read one row.  Return None if it's not there.

        Unlike super_select() this does not convert the returned row to Number, Text.
        """
        query, parameters = self._super_parse(*query_args, **kwargs)
        with self._cursor() as cursor:
            self._execute(cursor, query, parameters)
            return cursor.fetchone()

    class QueryError(Exception):
        """
        super_query() or super_select() had a MySQL exception.
        Report query string, parameter lengths, error message.
        """

    def super_query(self, *query_args, **kwargs):
        """
        Non-SELECT SQL statement:  INSERT, DROP, etc.  Alternate syntax with data.

        Returns last inserted id (as qiki Number) if INSERT and auto_increment.
        """
        query, parameters = self._super_parse(*query_args, **kwargs)
        with self._cursor() as cursor:
            self._execute(cursor, query, parameters)
            return Number(cursor.lastrowid)

    def super_select(self, *query_args, **kwargs):
        """
        SQL statement that generates rows.  Alternate syntax with data or symbol.

        Usually SELECT.  Also SHOW.

        EXAMPLE:
            rows = super_select('SELECT * FROM ', TableName('Order'), 'WHERE id = ', Number(42))

        :param query_args:  Alternate SQL syntax string with any of:
                            Text, SuperIdentifier, Number, Word, None, int
        :param kwargs: - e.g. debug=True
        :return: - generator yielding row-dictionaries
        """
        debug = kwargs.get('debug', False)
        query, parameters = self._super_parse(*query_args, **kwargs)
        with self._cursor() as cursor:
            self._execute(cursor, query, parameters)
            for row in cursor:
                field_dictionary = dict()
                if debug:  print(end='\t')
                for field, name in zip(row, cursor.column_names):
                    if field is None:
                        value = None
                    elif name.endswith('txt'):   # including jbo_txt
                        value = self.text_from_mysql(field)
                    else:
                        value = self.number_from_mysql(field)
                    field_dictionary[name] = value
                    if debug:  print(name, repr(value), end='; ')
                yield field_dictionary
                if debug:  print()

    def _execute(self, cursor, query, parameters=()):
        """
        SQL execute with informative error message.

        Cannot make the cursor here, because the caller may need it (e.g. SELECT).
        """
        try:
            cursor.execute(query, parameters)
        except mysql.connector.Error as e:
            # EXAMPLE:
            #     ProgrammingError: 1142 (42000): DELETE command denied to user
            #     'qiki_unit_tester'@'localhost' for table 'word_3f054d67009e44cebu4dd5c1ff605faf'
            # EXAMPLE:
            #     ProgrammingError: 1055 (42000): Expression #1 of SELECT list is not in GROUP BY clause
            #     and contains non-aggregated column 'qiki_unit_tested.w.idn'
            #     which is not functionally dependent on columns in GROUP BY clause;
            #     this is incompatible with sql_mode=only_full_group_by
            # EXAMPLE:
            #     QueryError: 1055 (42000): Expression #2 of SELECT list is not in GROUP BY clause
            #     and contains non-aggregated column 'qiki_unit_tested.w.idn'
            #     which is not functionally dependent on columns in GROUP BY clause;
            #     this is incompatible with sql_mode=only_full_group_by
            #     on query:
            #     SELECT w.obj AS obj, w.idn AS idn, w.sbj AS sbj, w.vrb AS vrb, w.num AS num,
            #     w.txt AS txt, w.whn AS whn  FROM `word` AS w  WHERE TRUE  AND w.vrb = ?
            #     GROUP BY obj  ORDER BY w.idn ASC ;
            #     parameter lengths 2
            #     parameters = ['\x82\x05']
            # EXAMPLE:
            #     qiki.word.LexMySQL.QueryError: 1062 (23000): Duplicate entry '\x83\x08\xB2'
            #     for key 'PRIMARY' on query: INSERT INTO `word_local`
            #     (idn,sbj,vrb,obj,num,txt,whn) VALUES ( ?,?,?,?,?,?,? ) ;
            #     parameter lengths 3,8,3,3,2,9,8

            def str_len(x):
                try:
                    return str(len(x))
                except TypeError:
                    return "-"

            raise self.QueryError(
                str(e) +
                " on query:\n" +
                query +
                ";\n" +
                "parameter lengths " +
                ",".join(str_len(p) for p in parameters)

                # "parameters: " +
                # ",".join(repr(p) for p in parameters)
                # NOTE:  Not showing parameter values, they may be binary, or big.
            )

    def _super_parse(self, *query_args, **kwargs):
        """
        Build a prepared statement query from a list of sql statement fragments
        interleaved with data parameters.

        Return a tuple of the two parameters for cursor.execute(),
        Namely (query, parameters) where query is a string with ? placeholders.
        """
        # TODO:  Recursive query_args?
        # So super_select(*args) === super_select(args) === super_select([args]) etc.
        # Say, then this could work, super_select('SELECT *', ['FROM table'])
        # Instead of                 super_select('SELECT +', None, 'FROM table')

        debug = kwargs.pop('debug', False)
        query = ''
        parameters = []
        for index, (arg_previous, arg_next) in enumerate(zip(query_args[:-1], query_args[1:])):
            if (
                    isinstance(arg_previous, six.string_types) and
                not isinstance(arg_previous, (Text, self.SuperIdentifier)) and
                    isinstance(arg_next, six.string_types) and
                not isinstance(arg_next, (Text, self.SuperIdentifier))
            ):
                # NOTE:  if consecutive strings that aren't Text or SuperIdentifier
                raise self.SuperSelectStringString(
                    "Consecutive super_select() arguments should not be strings.  " +
                    "Pass string fields through qiki.Text().  " +
                    "Pass identifiers through SuperIdentifier().  " +
                    "Or concatenate actual plaintext strings with + or intersperse None.\n"
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
                # And I'm getting tired of all the Nones to separate strings that are not parameters.
        for index_zero_based, query_arg in enumerate(query_args):
            if isinstance(query_arg, Text):
                query += '?'
                parameters.append(self.mysql_from_text(query_arg))
            elif isinstance(query_arg, self.SuperIdentifier):
                query += '`' + six.text_type(query_arg) + '`'
            elif isinstance(query_arg, six.string_types):   # Must come after Text and Lex.SuperIdentifier tests.
                query += query_arg
            elif isinstance(query_arg, Number):
                query += '?'
                parameters.append(query_arg.raw)
            elif isinstance(query_arg, int):
                query += '?'
                parameters.append(query_arg)
            elif isinstance(query_arg, Word):
                query += '?'
                parameters.append(query_arg.idn.raw)
            # elif isinstance(query_arg, (list, tuple, set)):
            # TODO:  Dictionary for INSERT or UPDATE syntax SET c=z, c=z, c=z, ...
            elif is_iterable(query_arg):
                # TODO:  query_arg should probably be passed through list() here, so
                #        that a generated iterable could be supported.
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
                # TODO:  Make these embedded iterables recursive.  Or flatten query_args.
                # TODO:  D.R.Y. the above elif clauses and the ones in _parametric_forms())
            elif query_arg is None:
                '''
                None is ignored.  This is useful if you want consecutive plaintext query_args,
                which would otherwise raise a SuperSelectStringString exception.  
                Interspersing None avoids this false alarm.
                '''
            else:
                raise self.SuperSelectTypeError(
                    "super_select() argument {index_one_based} of {n} type {type} is not supported.".format(
                        index_one_based=index_zero_based+1,
                        n=len(query_args),
                        type=type_name(query_arg)
                    )
                )
            query += ' '
        if debug:
            print("Query", query)
            print("Parameters", ", ".join([repr(parameter) for parameter in parameters]))
        return query, parameters

    class SuperSelectTypeError(TypeError):
        """super_select() or super_query() cannot parse this type."""

    class SuperSelectStringString(TypeError):
        """super_select() or super_query() require alternating syntax and data."""

    class SuperIdentifier(six.text_type):
        """Identifier in an SQL super-query that could go in `back-ticks`."""

    class TableName(SuperIdentifier):
        """Name of a MySQL table in a super-query"""

    @classmethod
    def number_from_mysql(cls, mysql_cell):
        if HORRIBLE_MYSQL_CONNECTOR_WORKAROUND:
            try:
                return Number.from_mysql(mysql_cell.encode('latin1'))
            except AttributeError:
                return Number.from_mysql(mysql_cell)   # for 2.2.2b1 MySQL connector
        else:
            return Number.from_mysql(mysql_cell)

    @classmethod
    def text_from_mysql(cls, mysql_cell):
        if HORRIBLE_MYSQL_CONNECTOR_WORKAROUND:
            try:
                return Text(mysql_cell.encode('latin1').decode('utf8'))
            except AttributeError:
                return Text.decode_if_you_must(mysql_cell)   # for 2.2.2b1 MySQL connector
        else:
            return Text.decode_if_you_must(mysql_cell)

    @classmethod
    def mysql_from_text(cls, text):
        if HORRIBLE_MYSQL_CONNECTOR_WORKAROUND:
            return text.encode('utf8').decode('latin1')
        else:
            return text.unicode()

    @classmethod
    def _parametric_forms(cls, sub_args):
        """
        Convert objects into the form MySQL expects for its data parameters.

        Return a value that could be passed as the 2nd parameter to cursor.execute().
        Raises TypeError if sub_args is not iterable, or contains unrecognized objects.
        """
        for sub_arg in sub_args:
            if isinstance(sub_arg, Text):
                yield cls.mysql_from_text(sub_arg)
            elif isinstance(sub_arg, Number):
                yield sub_arg.raw
            elif isinstance(sub_arg, int):
                yield sub_arg
            elif isinstance(sub_arg, Word):
                yield sub_arg.idn.raw
            else:
                raise TypeError("contains a " + type_name(sub_arg))
                # NOTE:  If type is 'str' this MIGHT mean two strings were consecutive
                #        in the sub_args, and this wasn't caught by SuperSelectStringString.
                #        Either data or a SuperIdentifier or None must intervene.

    def max_idn(self):
        # TODO:  Store max_idn in a singleton table?
        #        Or a parallel 1-column AUTO_INCREMENT?
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


def is_iterable(x):
    """
    Yes for (tuple) or [list] or {set} or {dictionary keys}.
    No for strings.

    Ask permission before using in a for-loop.

    This implementation is better than either of:
        return hasattr(x, '__getitem__')
        return hasattr(x, '__iter__')
    SEE:  http://stackoverflow.com/a/36154791/673991
    SEE:  is_iterable_not_string(), https://stackoverflow.com/q/1055360/673991

    CAUTION:  This will likely break a generator's iterator.
    It may consume some or all of it's elements.

    """
    # XXX:  Fix is_iterable(b'')  (false in Python 2, true in Python 3)
    # try:
    #     0 in x
    # except TypeError as e:
    #     assert e.__class__ is TypeError   # A subclass of TypeError raised by comparison operators?  No thanks.
    #     return False
    # else:
    #     return True

    # THANKS:  https://stackoverflow.com/a/36230057/673991
    # if (
    #         hasattr(obj, '__iter__') and
    #         # hasattr(obj, 'next') and      # or __next__ in Python 3
    #         callable(obj.__iter__) and
    #         obj.__iter__() is obj
    #     ):
    #     return True
    # else:
    #     return False
    # PHOOEY, it likes strings

    # TODO:  Rejigger this to return true if iter(x) doesn't raise an exception.
    #        IOW to include strings.
    #        But then define is_container() := is_iterable and not is_string()
    #        Or, fuck it, maybe just test things for whatever ELSE is expected and as a last resort
    #        use it in a for-statement and recurse if it doesn't raise a TypeError
    #        Or call this is_recursable()?

    # THANKS:  rule-out-string then duck-type, https://stackoverflow.com/a/1835259/673991
    if isinstance(x, six.string_types):
        return False
    if isinstance(x, (Lex, Word)):
        # NOTE:  Having a __getitme__ that doesn't raise an IndexError makes iter() digest a lex.
        #        We don't want that.  (It once treated self=lex like an infinitude of words)
        return False
    try:
        iter(x)
    except TypeError as e:
        assert e.__class__ is TypeError   # A subclass of TypeError raised by comparison operators?  No thanks.
        return False
    else:
        return True


assert is_iterable(['a', 'list', 'is', 'iterable'])
assert not is_iterable('a string is not')


class Text(six.text_type):   # always Unicode
    # TODO:  Move this to inside Word?
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
            # NOTE:  Unexpected Argument warning started PyCharm 2018.2
            # noinspection PyArgumentList
            return six.text_type.__new__(cls, the_string)
        else:
            raise TypeError("Text({value} type {type}) is not supported".format(
                value=repr(the_string),
                type=type_name(the_string)
            ))

    @classmethod
    def decode_if_you_must(cls, x):
        # TODO:  Rename from_str()?
        """
        Interpret a MySQL txt field.  (Possibly the only use remaining in word.py.)

        How evil is this?  What's the better way?

        Was once used by Word.__getattr__() on its name argument, when lex.word_name was a thing.
        (Now we do lex[u'word_name'] instead.)
        """
        # TODO:  Better to if six.PY2 ... else six.PY3?
        # and call the method from_str()
        # so the constructor is implicitly a from_unicode()
        try:
            # noinspection PyArgumentList
            return cls(x)   # This works in Python 3.  It raises an exception in Python 2.
        except TypeError:
            # noinspection PyArgumentList
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
        return isinstance(x, type(u''))


class Qoolbar(object):
    pass


class QoolbarSimple(Qoolbar):
    def __init__(self, lex):
        # TODO:  __init__(self, qool, iconify)
        assert isinstance(lex, LexSentence)
        self.lex = lex
        self.say_initial_verbs()
        # TODO:  Cache get_verbs().

    def say_initial_verbs(self):
        qool = self.lex.verb(u'qool')
        iconify = self.lex.verb(u'iconify')

        delete = self.lex.verb(u'delete')
        self.lex.create_word(
            sbj=self.lex['lex'], vrb=qool, obj=delete,
            use_already=True
        )
        self.lex.create_word(
            sbj=self.lex['lex'], vrb=iconify, obj=delete,
            use_already=True,
            num=16, txt=u'http://tool.qiki.info/icon/delete_16.png'
        )

        like = self.lex.verb(u'like')
        self.lex.create_word(
            sbj=self.lex['lex'], vrb=qool, obj=like,
            use_already=True
        )
        self.lex.create_word(
            sbj=self.lex['lex'], vrb=iconify, obj=like,
            use_already=True,
            num=16, txt=u'http://tool.qiki.info/icon/thumbsup_16.png'
        )

    def get_verb_dicts(self, debug=False):
        """
        Generate dictionaries about qoolbar verbs:
            idn - qstring of the verb's idn
            name - txt of the verb, e.g. 'like'
            icon_url - txt from the most recent iconify sentence (or None if there weren't any)
            qool_num - native integer for verb's num field (0 means user deleted it)

        :param debug: bool - print() SQL (to log) and other details.
        :rtype: collections.Iterable[dict[string, string]]
        """
        # TODO:  Make Qoolbar json serializable, http://stackoverflow.com/a/3768975/673991
        # SEE:  Also, patching json module, http://stackoverflow.com/a/32225623/673991
        # Then we would not have to translate verbs to verb_dicts:
        verbs = self.get_verbs(debug)
        for verb in verbs:
            yield dict(
                idn=verb.idn.qstring(),
                name=verb.txt,
                icon_url=verb.icon_url,
                qool_num=int(verb.qool_num),
            )

    def get_verbs(self, debug=False):
        qool_idn = self.lex['qool'].idn
        iconify_idn = self.lex['iconify'].idn
        qool_verbs = self.lex.find_words(
            vrb='define',
            # obj=self.lex['verb'],    # Ignore whether object is lex[verb] or lex[qool]
                                       # Because qiki playground did [lex](define][qool] = 'like'
                                       # but now we always do        [lex](define][verb] = 'like'
                                       # so we only care if some OTHER word declares it qool.  And nonzero.
            jbo_vrb=(qool_idn, iconify_idn),
            jbo_strictly=True,
            debug=debug
        )
        verbs = []
        for qool_verb in qool_verbs:
            has_qool = False
            newest_iconify_url = None
            qool_verb.qool_num = None
            for aux in qool_verb.jbo:
                if aux.vrb.idn == qool_idn:
                    has_qool = True
                    qool_verb.qool_num = aux.num   # Remember num from newest qool sentence.
                elif aux.vrb.idn == iconify_idn:
                    newest_iconify_url = aux.txt
            if has_qool:   # and newest_iconify_url is not None:
                # NOTE:  We used to insist that qool verbs have an icon.
                # NOTE:  We don't usually catch ourselves using the royal we.
                qool_verb.icon_url = newest_iconify_url
                verbs.append(qool_verb)
                # NOTE:  yield is not used here because find_word(jbo_vrb) does not handle
                #        a generator's iterator well.  Can that be done in one pass anyway?
                #        Probably not because of super_select() -- the MySQL version of which
                #        needs to pass a list of its values and know its length anyway.
        return verbs

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
    # The set of words whose subject is word.
# word.brv?  The set of definitions and qualifiers supporting this verb??
    # No, that would be word.jbo.  word.brv is the set of sentences that use word as their verb!

# TODO:  Word iterators and iterables.
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
#     lex-define-noun "" <-- this is the path word
#     lex-name-path "path"   <-- this is how you find it
#     lex-browse-path "/root"
# That way the uniqueness thing would be confined to vrb=name words
# (instead of vrb=define words)
# And there could be defined nouns that did not have a name, known only by their idn
# Or maybe rewinding to the first method, an unnamed define would have a blank txt
# And that did not have to be unique, and could never be Word(txt) searched for.
# This could help multilingual implementation by defining a different verb.
#     lex.nombre-path "calle"
# Or the word might be named in a computer language for reference by code.
# Not so much language but application
#     lex-apacheName-path "pth"

# TODO:  lex[x] is exactly one word (or an exception) but how about:
#        lex(x) is a COLLECTION of words, same as lex.find_words(x)
#        lex(vrb='like') is all the words with lex['like'] as their vrb
#        lex(obj=lex(vrb=browse, obj=path)) is all the hits on a path
