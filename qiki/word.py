"""
A qiki Word is defined by a three-word subject-verb-object
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

try:
    import collections.abc as collections_abc
except ImportError:
    import collections as collections_abc
    # THANKS:  six-ish collections.abc, https://stackoverflow.com/a/53978543/673991

import numbers
import re
import time

import mysql.connector
import six

from qiki import Number, Suffix
from qiki.number import type_name


# TODO:  Move mysql stuff to lex_mysql.py?


HORRIBLE_MYSQL_CONNECTOR_WORKAROUND = True
# SEE:  https://stackoverflow.com/questions/52759667/properly-getting-blobs-from-mysql-database-with-mysql-connector-in-python#comment99030618_55150960
# SEE:  https://stackoverflow.com/questions/49958723/cant-insert-blob-image-using-python-via-stored-procedure-mysql
# SEE:  https://stackoverflow.com/questions/51657097/how-can-i-retrieve-binary-data-using-mysql-python-connector
# Problem:  VARBINARY fields are decoded as if their contents were text
#           'utf8' codec can't decode ... invalid start byte
#           0q80 == lex.idn, and '\x80' can never be a valid utf8 string
#           Started happening between connector versions 2.2.2 and 8.0.16
# Workaround:  character encoding latin1 across whole table
#              qiki.Number fields work because latin1 can never fail to decode
#              qiki.Text field (txt) fake stores utf8 when it thinks its latin1, yuk


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

    @property
    def lex(self):
        raise NotImplementedError()

    def __init__(self, content=None, sbj=None, vrb=None, obj=None, num=None, txt=None):
        # assert isinstance(lex, (Lex, type(None)))
        # self.lex = lex
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
        An inchoate word is frugal with resources.
        All that is known about an inchoate word is its idn.
        Maybe that's all we ever need to know about it.
        But, if almost anything else is asked of it, then the word is made choate.
        For example, getting these properties requires the word to become choate first:
            word.sbj
            word.vrb
            word.vrb
            word.num
            word.txt
            word.whn
            word.exists()

        The following also make a word choate, and they also do so implicitly
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
        # DONE:  Refactor _is_inchoate property to check for the existence of self._fields instead.
        # CAUTION:  But Word(content=None) is a choate word.  Because it populates self._fields.
        #           Listing relies on all this so it may need to be refactored.
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
        """subject(verb, ...)"""
        return SubjectedVerb(self, vrb, *args, **kwargs)

    def define(self, obj, txt):
        # TODO:  WTF, D.R.Y. violation with LexSentence.define().  One should use the other or sumpin.
        """
        Define a word.  Name it txt.  Its type or class is obj.

        Example:
            agent = lex['agent']
            lex.define(agent, 'fred')
        Or:
            lex.define('agent', 'fred')

        The obj may be identified by its txt, example:
            lex.define('agent', 'fred')
        """
        if Text.is_valid(obj):   # Meta definition:  s.define('x') is equivalent to s.define(lex['x'])
            # obj = self.spawn(obj)
            obj = self.lex.read_word(obj)
        # TODO:  Move the above logic to says()?  Similarly for SubjectedVerb, and its calls to spawn()

        assert isinstance(obj, Word)
        assert Text.is_valid(txt), "define() txt cannot be a {}".format(type_name(txt))

        # How to handle "duplications"

        # TODO:  Should not this be spawn(sbj=lex, vrb=define, txt)?
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
        # possibly_existing_word = self.spawn(txt)
        possibly_existing_word = self.lex[txt]
        if possibly_existing_word.exists():
            return possibly_existing_word
        # new_word = self.says(vrb=self.lex[u'define'], obj=obj, txt=txt)
        new_word = self(vrb=self.lex[u'define'], txt=txt)[obj]
        return new_word

    def said(self, vrb, obj):
        return self(vrb)[obj]

        # assert isinstance(vrb, (Word, Number)), "vrb cannot be a {type}".format(type=type_name(vrb))
        # assert isinstance(obj, (Word, Number)), "obj cannot be a {type}".format(type=type_name(obj))
        # existing_word = self.spawn(
        #     sbj=self,
        #     vrb=vrb,
        #     obj=obj
        # )
        # existing_word._from_sbj_vrb_obj()
        # if not existing_word.exists():
        #     raise self.NotExist
        # return existing_word

    def says(self, vrb, obj, num=None, txt=None, num_add=None, use_already=False):

        # return self(vrb, *args, **kwargs)[obj]
        # NOTE:  The above way is not quite aggressive enough.
        #        If num and txt were missing it would passively find a word by s,v,o,
        #        as opposed to making a new ('',1) word, as create_word below would do.

        return self.lex.create_word(
            sbj=self,
            vrb=vrb,
            obj=obj,
            num=num,
            txt=txt,
            num_add=num_add,
            use_already=use_already,
        )

        # """
        # Construct a new sentence from a 3-word subject-verb-object.
        #
        # Subject is self.
        #
        # use_already makes a difference if the same word with the same num and txt
        # exists already AND is the newest word with that sbj-vrb-obj combination.
        # In that case no new sentence is created, the old one is returned.
        #
        # Either num or num_add may be specified.
        #
        # Differences between Word.sentence() and Word.spawn():
        #     sentence takes a Word-triple, spawn takes an idn-triple.
        #     sentence saves the new word.
        #     spawn can take in idn or other ways to indicate an existing word.
        # Differences between Word.sentence() and Word.define():
        #     sentence takes a Word-triple,
        #     define takes only one word for the object (sbj and vrb are implied)
        #     sentence requires an explicit num, define defaults to 1
        # """
        # # TODO:  rewrite this docstring
        # # TODO:  say()?
        #
        # assert isinstance(vrb, (Word, Number)), "vrb cannot be a {type}".format(type=type_name(vrb))
        # assert isinstance(obj, (Word, Number)), "obj cannot be a {type}".format(type=type_name(obj))
        # if isinstance(txt, numbers.Number) or Text.is_valid(num):
        #     # TODO:  Why `or` not `and`?
        #     (txt, num) = (num, txt)
        #
        # if num is not None and num_add is not None:
        #     raise self.SentenceArgs("Word.says() cannot specify both num and num_add.")
        #
        # num = num if num is not None else 1
        # txt = txt if txt is not None else u''
        #
        # if not isinstance(num, numbers.Number):
        #     raise self.SentenceArgs("Wrong type for Word.says(num={})".format(type_name(num)))
        #
        # if not Text.is_valid(txt):
        #     raise self.SentenceArgs("Wrong type for Word.says(txt={})".format(type_name(txt)))
        #
        # new_word = self.spawn(
        #     sbj=self,
        #     vrb=vrb,
        #     obj=obj,
        #     num=Number(num),
        #     txt=txt
        # )
        # if num_add is not None:
        #     new_word._from_sbj_vrb_obj()
        #     assert isinstance(num_add, numbers.Number)
        #     if new_word.exists():
        #         # noinspection PyProtectedMember
        #         new_word._fields['num'] += Number(num_add)
        #     else:
        #         # noinspection PyProtectedMember
        #         new_word._fields['num'] = Number(num_add)
        #     new_word.save()
        # elif use_already:
        #     old_word = self.spawn(
        #         sbj=self,
        #         vrb=vrb,
        #         obj=obj
        #     )
        #     old_word._from_sbj_vrb_obj()
        #     if not old_word.exists():
        #         new_word.save()
        #     elif old_word.txt != new_word.txt or old_word.num != new_word.num:
        #         new_word.save()
        #     else:
        #         # There was an identical sentence already.  Fetch it so new_word.exists().
        #         # This is the only path through says() where no new sentence is created.
        #         new_word._from_sbj_vrb_obj_num_txt()
        #         assert new_word.idn == old_word.idn, "Race condition {old} to {new}".format(
        #             old=old_word.idn.qstring(),
        #             new=new_word.idn.qstring()
        #         )
        # else:
        #     new_word.save()
        # return new_word

    class SentenceArgs(TypeError):
        """Arguments to Word.says() (or intended for Word.says()) are wrong."""
        # TODO:  SayError?

    def spawn(self, *args, **kwargs):
        """
        Construct a Word() using the same lex as another word.
        """

        if len(args) == 1 and isinstance(args[0], (Number, Word)):
            return self.lex.root_lex[args[0]]

        try:
            idn = idn_from_word_or_number(args[0])
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
        # assert not idn.is_suffixed()
        self._idn = idn
        self.lex.populate_word_from_idn(self, idn)
        # NOTE:  If this returned True, it already called populate_from_word()
        #        and so the word now exists()

    def _from_definition(self, txt):
        """Construct a Word from its txt, but only when it's a definition."""
        assert Text.is_valid(txt)
        assert isinstance(self.lex, Lex)
        if not self.lex.populate_word_from_definition(self, txt):
            self._fields = dict(txt=Text(txt))

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
            self._from_idn(other.idn)

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
        self._idn = row[prefix + 'idn']
        self._now_it_exists()   # Must come before spawn(sbj) for lex's sake.
        self._fields = dict(
            # sbj=self.spawn(row[prefix + 'sbj']),
            # vrb=self.spawn(row[prefix + 'vrb']),
            # obj=self.spawn(row[prefix + 'obj']),
            sbj=self.lex[row[prefix + 'sbj']],
            vrb=self.lex[row[prefix + 'vrb']],
            obj=self.lex[row[prefix + 'obj']],
            num=row[prefix + 'num'],
            txt=row[prefix + 'txt'],
            whn=row[prefix + 'whn'],
        )

    def populate_from_num_txt(self, num, txt):
        assert isinstance(txt, Text)
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

    @staticmethod
    def presentable(num):
        if num.is_whole():
            return str(int(num))
        elif not num.is_suffixed():
            return str(float(num))
        else:
            return num.qstring()

    def __format__(self, format_spec):
        # THANKS:  format > repr > str, https://stackoverflow.com/a/40600544/673991
        if format_spec == '':
            return str(self)
        else:
            return "Word({})".format(",".join(self._word_attributes(format_spec)))

    def _word_attributes(self, format_spec):
        for c in format_spec:
            if   c == 'i': yield "idn={}".format(self.presentable(self.idn))
            elif c == 's': yield "sbj={}".format(str(self.sbj))
            elif c == 'v': yield "vrb={}".format(str(self.vrb))
            elif c == 'o': yield "obj={}".format(str(self.obj))
            elif c == 't': yield "txt='{}'".format(str(self.txt))
            elif c == 'n': yield "num={}".format(self.presentable(self.num))
            elif c == 'w': yield "whn={}".format(self.presentable(self.whn))
            else:
                raise ValueError("'{}' unknown in .format(word)".format(c))

    def __repr__(self):
        # THANKS:  repr() conventions, https://codingkilledthecat.wordpress.com/2012/06/03/please-dont-abuse-repr/
        if self.exists():
            if self.is_defined() and self.txt:
                # TODO:  Undo comma_num
                if self.num == Number(1):
                    comma_num = ""
                else:
                    comma_num = ", num={num}".format(num=repr(self.num))
                return "Word('{txt}'{comma_num})".format(
                    comma_num=comma_num,
                    txt=self.txt
                )
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
                idn_int = repr(int(self.idn))
            except ValueError:
                if self.txt:
                    return "Word(undefined {})".format(repr(self.txt))
                else:
                    return "Word(in a strange state, idn {})".format(repr(self.idn))
            else:
                return "Word(in a strange state, idn {})".format(idn_int)

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
        try:
            return Number(self._idn)   # Copy constructor so e.g. w.idn.suffix(n) will not modify w.idn.
                                   # TODO:  but then what about w.sbj.add_suffix(n), etc.?
                                   #        (But there's no more add_suffix, only new-number-generating plus_suffix)
                                   # So this passing through Number() is a bad idea.
                                   # Plus this makes x.idn a different object from x._idn, burdening debug.
        except AttributeError:
            return Number.NAN

    @idn.setter
    def idn(self, value):
        raise AttributeError("Cannot set a Word's idn.")
    # TODO:  Omit this?  Does this happen for free anyway?

    def save(self, override_idn=None):
        if override_idn is not None:
            self._idn = override_idn
        assert isinstance(self.idn, (Number, type(None)))
        assert isinstance(self.sbj, Word)
        assert isinstance(self.vrb, Word)
        assert isinstance(self.obj, Word), "{obj} is not a Word".format(obj=repr(self.obj))
        assert isinstance(self.num, Number)
        assert isinstance(self.txt, Text)
        if self.exists() or self.idn == Number.NAN:
            self._idn = self.lex.max_idn().inc()   # AUTO sorta INCREMENT
            # TODO:  Race condition?  Make max_idn and insert_word part of an atomic transaction.
            # Or store latest idn in another table
            # SEE:  http://stackoverflow.com/questions/3292197/emulate-auto-increment-in-mysql-innodb
            assert not self.idn.is_nan()
        assert isinstance(self.idn, Number)
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
            num_count = 0
            txt_count = 0
            if is_iterable(num_and_or_txt):
                for num_or_txt in num_and_or_txt:
                    if isinstance(num_or_txt, numbers.Number):
                        num = num_or_txt
                        num_count += 1
                    elif Text.is_valid(num_or_txt):
                        txt = num_or_txt
                        txt_count += 1
                    else:
                        raise self._subjected.SentenceArgs("Expecting num or txt, got " + repr(num_or_txt))
            else:
                raise self._subjected.SentenceArgs("Expecting num and/or txt, got " + repr(num_and_or_txt))
            if num_count > 1:
                raise self._subjected.SentenceArgs("Expecting 1 number not {n}: {arg}".format(
                    n=num_count,
                    arg=repr(num_and_or_txt)
                ))
            if txt_count > 1:
                raise self._subjected.SentenceArgs("Expecting 1 text not {n}: {arg}".format(
                    n=txt_count,
                    arg=repr(num_and_or_txt)
                ))
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
        objected = self._subjected.lex.root_lex[item]
        if self._args or self._kwargs:
            num, txt = self.extract_txt_num(self._args, self._kwargs)
            self._kwargs.pop('txt', None)
            self._kwargs.pop('num', None)
            # return self._subjected.says(self._verbed, objected, num=num, txt=txt, **self._kwargs)
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
                raise self._subjected.NotExist
            return existing_word
            # return self._subjected.said(self._verbed, objected)

    @classmethod
    def extract_txt_num(cls, a, k):   # aka (args, kwargs)
        """
        Pop num and/or txt from positional-arguments, and keyword-arguments.

        TypeError if ambiguous or unsupportable.
        Examples that will raise TypeError:
            extract_txt_num('text', 'more text')
            extract_txt_num(1, 42)
            extract_txt_num(neither_text_nor_number)

        Expects a (args) is a list, not a tuple, so it can be modified in-place.

        """
        # TODO:  It was silly to expect a (args) to be a list.
        #        Only k (kwargs) can have surplus parameters.
        #        If this function doesn't generate an exception,
        #        then it used up all of a (args) anyway.

        def type_code(x):
            return 'n' if isinstance(x, numbers.Number) else 't' if Text.is_valid(x) else 'x'

        pats = ''.join(type_code(arg) for arg in a)   # pats:  positional-argument types
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

    idn is the number that identifies the word.
    meta_idn is the number that identifies the Lex collection.
    """

    def __init__(self, meta_word=None, word_class=None, **_):
        """

        :param meta_word:
        :type meta_word Word:
        :param word_class:
        :param _:
        """
        super(Lex, self).__init__()
        # NOTE:  Blow off unused kwargs here, which might be sql credentials.
        #        Guess we do this here so sql credentials could contain word_class=Something.

        if word_class is None:

            class WordClassJustForThisLex(Word):
                lex = None

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
        meta_word_report = "" if self.meta_word is None else " " + repr(self.meta_word)
        return type_name(self) + meta_word_report

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

        idn = idn_from_word_or_number(idn_or_word_or_none)
        assert isinstance(idn, Number)

        if idn.is_suffixed():
            try:
                meta_idn, index = Listing.split_compound_idn(idn)
                lex = self.root_lex.mesa_lexes[meta_idn]
                # TODO:  Don't just try unsuffixed.  Try all sub-suffixed numbers.
                #        Allowing nested lexes.
            except (Listing.NotAListing, KeyError):
                raise Lex.NotFound("{q} is not a Listing idn".format(
                    q=idn.qstring(),
                ))
            return lex.read_word(index)
        else:
            return self.word_class(idn)

    def populate_word_from_idn(self, word, idn):
        raise NotImplementedError()


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

    # meta_word = None   # This class variable is a Word associated with a Listing subclass.
    #                    # It is assigned by install().
    #                    # ListingSubclass.meta_word.idn is an unsuffixed qiki.Number.
    #                    # If x is an instance of a ListingSubclass, then x.idn is a suffixed qiki.Number.
    #                    # The unsuffixed part of x.idn is its class's meta_word.idn.
    #                    # I.e. x.idn.unsuffixed == x.meta_word.idn
    #                    # See examples in test_example_idn().
    #                    # By convention meta_word.obj.txt == 'listing' but nothing enforces that.
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

            class WordClassJustForThisListing(Word):
                lex = None

                @property
                def index(self):
                    return self.idn.suffix(Suffix.Type.LISTING).number

                # def __call__(self, vrb, *a, **k):
                #     return SubjectedVerb(self.idn, vrb, *a, **k)

            word_class = WordClassJustForThisListing

        super(Listing, self).__init__(meta_word=meta_word, word_class=word_class, **kwargs)
        assert isinstance(meta_word, Word)
        assert not isinstance(meta_word, self.word_class)   # meta_word is NOT a listing word,
                                                            # that's self-referentially nuts
        self.listing_dictionary[meta_word.idn] = self
        self.meta_word = meta_word
        self.suffix_type = Suffix.Type.LISTING

        # assert isinstance(index, (int, Number))   # TODO:  Support a non-int, non-Number index.
        # assert self.meta_word is not None, (
        #     "Class {c} must be installed with its meta_word before it can be instantiated".format(
        #         c=type_name(self)
        #     )
        # )
        # self.index = Number(index)
        #
        # if lex is None:
        #     lex = self.meta_word.lex
        # super(Listing, self).__init__()
        #
        # idn = Number(self.meta_word.idn, Suffix(self.SUFFIX_TYPE, self.index))
        # # FIXME:  Holy crap, the above line USED to mutate self.meta_word.idn.  What problems did THAT create??
        # # Did that morph a class property into an instance property?!?

        # self._inchoate(idn)
        # self.__is_inchoate = True

        # self.lookup(self.index, self.lookup_callback)
        # self.lex = self.meta_word.lex

    # @property
    # def _is_inchoate(self):
    #     # TODO:  Instead override base class property with a member boolean self._is_inchoate?
    #     #        Otherwise, self._is_choate is better than self.__is_inchoate, avoiding double-underscore.
    #     return self.__is_inchoate

    # def _from_idn(self, idn):
    #     assert idn.is_suffixed()
    #     assert idn.unsuffixed == self.meta_word.idn
    #     assert idn.suffix(self.SUFFIX_TYPE) == Suffix(self.SUFFIX_TYPE, self.index)
    #     self.lookup(self.index, self.lookup_callback)
    #     self.__is_inchoate = False

    # TODO:  @abstractmethod
    # TODO:  No parameters for lookup()?  Do not pass index, and just return txt and num?
    # Or was the callback some kind of async feature, in case looking up took a while?
    # Because I'm doubtful that would work anyway.
    def lookup(self, index):
        raise NotImplementedError("Subclass must def lookup(index): return txt, num ")
        # THANKS:  Classic abstract method, http://stackoverflow.com/a/4383103/673991

    # def __getitem__(self, index):
    #     return self.read_word(index)

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

    # def lookup_callback(self, txt, num):
    #     # Another case where txt comes before num, the exception.
    #     # XXX:  Wait, WHY does lookup need a callback?  Can it just RETURN (txt, num)??
    #     # It could even return a flexible tuple (n), (t), (n,t), (t,n), dict(num=n, txt=t)
    #     # Oh wait, there's that pesky fact that the word should not "exist" until num,txt are populated.
    #     # But maybe lookup should populate those fields instead.
    #     # The lookup's caller could check that they were populated, then call _now_it_exists()
    #     # Listing is just a burbling cauldron of refactoring need.
    #     # self.num = num
    #     # self.txt = Text(txt)
    #     self._fields = dict(
    #         num=num,
    #         txt=Text(txt)
    #     )
    #     # self._now_it_exists()

    # @classmethod
    # def install(cls, meta_word):
    #     """
    #     ListingSubclass.meta_word is a word in the lex that represents the subclass.
    #     That meta-word should already exist, and it will (probably) have no suffix.
    #     The meta-word's idn will be the unsuffixed part of the idn for all instances of the subclass.
    #     Each instance idn will have a unique suffix, whose payload is the index for that instance.
    #     This suffixed word is conceptually created each time the class is instantiated with a unique index.
    #
    #     This must be called before any instantiations.
    #     """
    #     assert isinstance(meta_word, Word)
    #     assert isinstance(meta_word.idn, Number)
    #     # TODO:  Make sure if already defined that it's the same class.
    #     cls.class_dictionary[meta_word.idn] = cls
    #     cls.meta_word = meta_word

    class NotAListing(Exception):
        pass

    # # noinspection PyClassHasNoInit
    # class NotAListingRightNow(NotAListing):
    #     pass

    @classmethod
    def word_from_idn(cls, idn):
        """
        Turn a suffixed Number identifier into a (word) instance of some subclass of Listing.
        The ListingSubclass constructor is like an instance_from_index() converter.

        So it's a double-lookup.
        First we look up which class this idn is for.
        That's determined by the unsuffixed part of the idn.
        This class will be a subclass of Listing.
        Second we call that class's lookup on the suffix of the idn.
        """
        # pieces = idn.parse_suffixes()
        # try:
        #     (identifier, suffix) = pieces
        # except ValueError:
        #     raise cls.NotAListing("Not a Listing identifier: " + idn.qstring())
        # assert isinstance(identifier, Number)
        # assert isinstance(suffix, Suffix)

        meta_idn, index = cls.split_compound_idn(idn)
        listing = cls.listing_from_meta_idn(meta_idn)
        listed_instance = listing[index]
        # TODO:  Support non-Number suffix payloads?  The Listing index must now be a Number.
        return listed_instance

    # @classmethod
    # def listing_from_idn(cls, idn):
    #     """"""
    #     meta_idn, index = cls.split_compound_idn(idn)
    #     listing_subclass = cls.listing_from_meta_idn(meta_idn)
    #     return listing_subclass

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

        # try:
        #     identifier = idn.unsuffixed
        #     suffixes = idn.suffixes
        # except (AttributeError, Suffix.RawError):
        #     raise cls.NotAListing("Not a Number: " + type(idn).__name__)
        # if len(suffixes) != 1:
        #     raise cls.NotAListing("Not a suffixed Number: " + idn.qstring())
        # suffix = suffixes[0]
        # if suffix.type_ != cls.SUFFIX_TYPE:
        #     raise cls.NotAListing("Not a Listing suffix: 0x{:02X}".format(suffix.type_))
        #
        # assert isinstance(identifier, Number)
        # assert isinstance(suffix, Suffix)
        # meta_idn = identifier
        # index = suffix.payload_number()
        # return meta_idn, index


# class ListingNotInstalled(Listing):
#     """
#     Smelly class where spawn() can dump uninstalled Listings.
#
#     To defer raising NotAWord until it becomes choate.
#     So the spawn() calls in Word.populate_from_row() can meekly go about their inchoate business.
#     And exceptions are raised only if those words try to become choate.
#     All this so we do not have to install obsolete listing classes,
#     but we can still instantiate the no-longer-used words that refer to them.
#     """
#     # noinspection PyUnresolvedReferences
#     meta_idn = Number.NAN
#
#     # noinspection PyMissingConstructor
#     def __init__(self, idn):
#         self.index = None
#         # self._inchoate(idn)   # Smelly way this doomed instance will raise an exception only if it becomes choate.
#
#     # def _choate(self):
#     #     assert self.idn.is_suffixed()
#     #     raise Listing.NotAListing(
#     #         "Listing identifier {idn} has meta_idn {meta_idn} "
#     #         "which was not installed to a class.".format(
#     #             idn=self.idn,
#     #             meta_idn=self.idn.unsuffixed,
#     #         )
#     #     )
#
#     def lookup(self, index, callback):
#         raise self.NotAListing


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
                      See each lex needs a way to refer to itself.  Just as it can refer to another lex.
                      That reference is usually in the sbj or obj of a word in the lex.
                      If `lex` is an instance of a Lex subclass,
                      Then lex._lex is an instance of the word that represents that lex.
                      lex._lex is an instance of lex.word_class
    """

    def populate_word_from_idn(self, word, idn):
        raise NotImplementedError

    def __init__(self, **kwargs):
        super(LexSentence, self).__init__(**kwargs)
        self._lex = None
        self._noun = None
        self._verb = None
        self._define = None

    # def __getitem__(self, item):
    #     """
    #     Square-bracket Word instantiation.
    #
    #     This is the result of
    #         lex[idn]
    #         lex[txt]  (for a definition)
    #         lex[word]  (for copy construction)
    #     """
    #     return self.read_word(item)
    #
    #     existing_word = self._lex.spawn(item)
    #     # existing_word = self.word_class(item)
    #     # Oops can't use word_class here. The class depends on the item. That's what spawn does.
    #
    #     # if not existing_word.exists():
    #     #     raise self.NotExist
    #     # No, because inchoate words become choate by virtue of calling .exists().
    #     # And it's just not (yet) the Word way of doing things.
    #     #     That is, lots of code asks permission rather than forgiveness.
    #     #     But even moreso, the whole inchoate scheme falls apart if we have to ask,
    #     #     at this point, whether the word exists or not.
    #
    #     # if existing_word.idn == self.idn:
    #     #     return self   # lex is a singleton, i.e. assert lex[lex] is lex
    #
    #     # TODO:  Explain, why is this important?
    #     #        Why is the Lex's word for the Lex itself only instantiated once.
    #     #        And why aren't other words in the Lex also a singleton.,
    #     # Ok, one reason it makes sense is only a LexMySQL instantiated object (which is also a Word)
    #     # can perform database actions like .find_words() or .populate_word_from_idn().
    #     # There should be only one instance of a Lex for a given lex.
    #     # Otherwise there'd be multiple connections or shared connections and chaos would reign.
    #     # But is there any problem with there being a Word('lex') that isn't a Lex?
    #     # Equal but not identical.  Not so weird.
    #     # You couldn't do any lex-like things to Word('lex').
    #     # Maybe the lesson here is that Lex should not derive Word at all.
    #     # Possibly go further and make Lex the metaclass of Word.
    #     # Is that just abstraction-confusion?  Lex is really a CONTAINER of Words.
    #     # Maybe lex should be a class object of Word.  And it should point to
    #     # whatever generates words.
    #     #
    #     #     class MyWord(Word):
    #     #         pass
    #     #
    #     #     MyWord.lex = LexMySQL(**my_credentials, word_class=MyWord)
    #
    #     return existing_word

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

    def _install_all_seminal_words(self):
        """
        Insert the five fundamental sentences into the Lex database.
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
            # word = self._lex.spawn(_idn)
            word = self[_idn]
            if not word.exists():
                self._install_one_seminal_word(_idn, _obj, _txt)
                # word = self._lex.spawn(_idn)
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

        # assert not self.exists()
        # if not self.exists():     # XXX:  Does this make sense??
                                    # Why should from_idn() cause lex to "exist" if it "did not" already?
                                    # Could lex just start out inchoate and that would take care of this??!??

        # self._from_idn(self.IDN_LEX)

        # assert self.exists()
        # assert self.is_lex()

    def _install_one_seminal_word(self, _idn, _obj, _txt):
        # word = self._lex.spawn(
        #     sbj=self.IDN_LEX,
        #     vrb=self.IDN_DEFINE,
        #     obj=_obj,
        #     num=Number(1),
        #     txt=_txt,
        # )
        # word.save(override_idn=_idn)
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

    # def noun(self, name=None):
    #     raise NotImplementedError()
    #
    # def verb(self, name=None):
    #     raise NotImplementedError()

    def noun(self, name=None):
        if name is None:
            return self._noun
        else:
            return self.define(self._noun, name)

    def verb(self, name=None, sbj=None):
        if name is None:
            return self._verb
        else:
            return self.define(self._verb, name, sbj=sbj)

    def define(self, obj, txt, sbj=None):
        old_definition = self[txt]
        if old_definition.exists():
            # TODO:  Use create_word's use_already option instead.
            return old_definition
        sbj = sbj or self._lex
        vrb = self._define
        obj = self[obj]
        return self.create_word(sbj=sbj, vrb=vrb, obj=obj, txt=txt)

    def find_words(self, **kwargs):
        raise NotImplementedError()

    def max_idn(self):
        raise NotImplementedError()

    def server_version(self):
        return "(not implemented)"

    def uninstall_to_scratch(self):
        raise NotImplementedError()

    def disconnect(self):
        raise NotImplementedError()

    def find_last(self, **kwargs):
        # TODO:  In LexMySQL, limit find_words() to latest using sql LIMIT.
        bunch = self.find_words(**kwargs)
        try:
            return bunch[-1]
        except IndexError:
            raise self.NotFound

    class CreateWordError(Exception):
        """LexSentence.create_word() argument error."""

    def read_word(self, txt_or_idn_etc):
        if Text.is_valid(txt_or_idn_etc):
            word = self.word_class(txt=txt_or_idn_etc)
            self.populate_word_from_definition(word, txt_or_idn_etc)
            return word
        else:
            return super(LexSentence, self).read_word(txt_or_idn_etc)

    def create_word(
        self,
        sbj, vrb, obj,
        num=None,
        txt=None,
        num_add=None,
        use_already=False,
        override_idn=None
    ):
        """
        Construct a new sentence from a 3-word subject-verb-object.
        """
        assert isinstance(sbj, (Word, Number)), "vrb cannot be a {type}".format(type=type_name(sbj))
        assert isinstance(vrb, (Word, Number)), "vrb cannot be a {type}".format(type=type_name(vrb))
        assert isinstance(obj, (Word, Number)), "obj cannot be a {type}".format(type=type_name(obj))
        if isinstance(txt, numbers.Number) or Text.is_valid(num):
            # TODO:  Why `or` not `and`?
            (txt, num) = (num, txt)

        if num is not None and num_add is not None:
            raise self.CreateWordError("{self_type}.create_word() cannot specify both num and num_add.".format(
                self_type=type_name(self),
            ))

        num = num if num is not None else 1
        txt = txt if txt is not None else u''

        if not isinstance(num, numbers.Number):
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
            assert isinstance(num_add, numbers.Number)
            self.populate_word_from_sbj_vrb_obj(new_word, sbj, vrb, obj)
            if new_word.exists():
                # noinspection PyProtectedMember
                new_word._fields['num'] += Number(num_add)
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
            elif old_word.txt != new_word.txt or old_word.num != new_word.num:
                new_word.save()
            else:
                # There was an identical sentence already.  Fetch it so new_word.exists().
                # This is the only path through create_word() where no new sentence is created.
                # new_word._from_sbj_vrb_obj_num_txt()
                self.populate_word_from_sbj_vrb_obj_num_txt(new_word, sbj, vrb, obj, Number(num), txt)
                assert new_word.idn == old_word.idn, "Race condition {old} to {new}".format(
                    old=old_word.idn.qstring(),
                    new=new_word.idn.qstring()
                )
        else:
            new_word.save(override_idn=override_idn)
        return new_word

    @classmethod
    def now(cls):
        return Number(time.time())

# TODO:  class LexMemory here (faster unit tests).  Move LexMySQL to lex_mysql.py?


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
    def __init__(self, **kwargs):
        # self.lex = self
        super(LexInMemory, self).__init__(**kwargs)
        # TODO:  new_lex_memory = LexMemory(old_lex_memory)?
        # self._choate()
        # if not self.exists():

        self.words = []
        # NOTE:  Assume zero-starting idns

        self._lex = self.word_class(self.IDN_LEX)

        self._install_all_seminal_words()
        # assert self.exists()
        # assert self.is_lex()
        self._lex = self.words[int(self.IDN_LEX)]
        self._noun = self.words[int(self.IDN_NOUN)]
        self._verb = self.words[int(self.IDN_VERB)]
        self._define = self.words[int(self.IDN_DEFINE)]

    # def exists(self):
    #     if hasattr(self, 'words'):
    #         return super(LexMemory, self).exists()
    #     else:
    #         return False

    def insert_word(self, word):
        assert not word.idn.is_nan()
        word.whn = self.now()
        self.words.append(word)
        # noinspection PyProtectedMember
        word._now_it_exists()

    def disconnect(self):
        pass

    def uninstall_to_scratch(self):
        del self.words

    def populate_word_from_idn(self, word, idn):
        try:
            word_source = self.words[int(idn)]
        except IndexError:
            return False
        else:
            word.populate_from_word(word_source)
            return True

    def populate_word_from_definition(self, word, define_txt):
        for word_source in self.words:
            if (
                word_source.vrb.idn == self.IDN_DEFINE and
                word_source.txt == Text(define_txt)
            ):
                word.populate_from_word(word_source)
                return True
        return False

    def populate_word_from_sbj_vrb_obj(self, word, sbj, vrb, obj):
        for word_source in reversed(self.words):
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
        idn_ascending=True,
        jbo_ascending=True,
        jbo_vrb=(),
        obj_group=False,
        jbo_strictly=False,
        debug=False
    ):
        # TODO:  Implement obj_group here, and test it in unit tests.
        found_words = []
        for word_source in self.words if idn_ascending else reversed(self.words):
            hit = True
            if idn is not None and word_source.idn != idn_from_word_or_number(idn):
                # TODO:  Why does word_match(word_source.idn, idn) fail in one test?
                hit = False
            if sbj is not None and not word_match(word_source.sbj, sbj):
                hit = False
            if vrb is not None and not word_match(word_source.vrb, vrb):
                hit = False
            if obj is not None and not word_match(word_source.obj, obj):
                hit = False
            if hit:
                found_words.append(self[word_source])   # copy constructor

        if jbo_vrb:
            restricted_found_words = []
            for found_word in found_words:
                jbo = []
                for other_word in self.words:
                    if word_match(other_word.obj, found_word.idn) and word_match(other_word.vrb, jbo_vrb):
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


# noinspection SqlDialectInspection,SqlNoDataSourceInspection
class LexMySQL(LexSentence):
    """
    Store a Lex in a MySQL table.
    """
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
            self._connection = mysql.connector.connect(**kwargs_sql)

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
                do_connect()
            except AttributeError as attribute_error:
                if str(attribute_error) == "Unsupported argument 'use_pure'":
                    del kwargs_sql['use_pure']
                    do_connect()
                else:
                    print("Unknown Attribute Error:", str(attribute_error))
                    raise

        try:
            do_connect_with_and_without_use_pure()
        except mysql.connector.Error as exception:
            raise self.ConnectError(exception.__class__.__name__ + " - " + str(exception))
            # EXAMPLE:  (mysqld is down)
            #     InterfaceError - 2003: Can't connect to MySQL server on 'localhost:33073'
            #     (10061 No connection could be made because the target machine actively refused it)
            # EXAMPLE:  (maybe wrong password)
            #     ProgrammingError



        try:
            # self._connection.set_charset_collation(b'binary', b'binary')
            if HORRIBLE_MYSQL_CONNECTOR_WORKAROUND:
                self._connection.set_charset_collation(str('latin1'))
            else:
                self._connection.set_charset_collation(str('utf8'))



            # self.lex = self
            # self.last_inserted_whn = None
            self._lex = self.word_class(self.IDN_LEX)
            try:
                # noinspection PyProtectedMember
                self._lex._choate()   # Get the word out of this Lex that represents the Lex itself.
            except self.SelectError as exception:   # was mysql.connector.ProgrammingError as exception:
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

            # assert self.exists(), self.__dict__
            # # XXX:  Why does this sometimes fail (3 of 254 tests) and then stop failing?
            # # And even weirder, when the assert tries to display self.__dict__ is when it stops failing.

            # self.super_query('SET character_set_results = binary')

            # self.super_query('SET NAMES utf8mb4 COLLATE utf8mb4_general_ci')
            # THANKS:  http://stackoverflow.com/a/27390024/673991

            # assert self.is_lex()
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
        if hasattr(self, '_connection') and self._connection is not None:
            if self._connection.is_connected():
                # NOTE:  Prevent `TypeError: 'NoneType'` deep in MySQL Connector code.
                self._connection.close()
            self._connection = None

    def __del__(self):
        self.disconnect()

    # def noun(self, name=None):
    #     if name is None:
    #         return self._noun
    #     else:
    #         return self._lex.define(self._noun, name)
    #
    # def verb(self, name=None):
    #     if name is None:
    #         return self._verb
    #     else:
    #         return self._lex.define(self._verb, name)

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
                txt_type=self._txt_type,   # Using this was a hard error:  <type> expected found '{'
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

            cursor.execute(query)
            # TODO:  other keys?  sbj-vrb?   obj-vrb?
        self._install_all_seminal_words()

    def _install_one_seminal_word(self, _idn, _obj, _txt):
        try:
            super(LexMySQL, self)._install_one_seminal_word(_idn, _obj, _txt)
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
        except self.QueryError:
            '''Not a problem if MySQL user doesn't have the DELETE privilege'''
        self.super_query('DROP TABLE IF EXISTS', self.table)
        # self._now_it_doesnt_exist()   # So install will insert the lex sentence.
        # After this, we can only install_from_scratch() or disconnect()

    # noinspection SpellCheckingInspection
    def insert_word(self, word):
        assert not word.idn.is_nan()
        whn = self.now()
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
        rows = self.super_select('SELECT * FROM', self.table, 'WHERE idn =', idn)
        return self._populate_from_one_row(word, rows)

    def populate_word_from_definition(self, word, define_txt):
        rows = self.super_select(
            'SELECT * FROM', self.table, 'AS w '
            'WHERE vrb =', self.IDN_DEFINE,
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
                pass
            else:
                assert False, "Cannot populate from unexpected extra rows."
            return True

    # TODO:  Study JOIN with LIMIT 1 in 2 SELECTS, http://stackoverflow.com/a/28853456/673991
    # Maybe also http://stackoverflow.com/questions/11885394/mysql-join-with-limit-1/11885521#11885521

    def find_words(
        self,
        idn=None,
        sbj=None,
        vrb=None,
        obj=None,
        idn_ascending=True,
        jbo_ascending=True,
        jbo_vrb=(),
        obj_group=False,
        jbo_strictly=False,
        debug=False
    ):
        # TODO:  Lex.find()  It should return inchoate words.  Best of both find_words and find_idns.
        """
        Select words by subject, verb, and/or object.

        Return a list of choate words.

        idn,sbj,vrb,obj all restrict the list of returned words.
        jbo_vrb is not restrictive it's elaborative (note 1).
        'jbo' being 'obj' backwards, it represents a reverse reference.
        If jbo_vrb is a container of verbs, each returned word has a jbo attribute
        that is a list of choate words whose object is the word.
        In other words, it gloms onto each word the words that point to it (using approved verbs).
        jbo_vrb cannot be a generator's iterator, because super_select()
        will probably need two passes on it anyway.

        The order of words is chronological.
        idn_ascending=False for reverse-chronological.
        The order of jbo words is always chronological.

        obj_group=True to collapse by obj.
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
        assert isinstance(idn, (Number, Word, type(None)))
        assert isinstance(sbj, (Number, Word, type(None)))
        assert isinstance(vrb, (Number, Word, type(None))) or is_iterable(vrb)
        assert isinstance(obj, (Number, Word, type(None)))
        assert isinstance(jbo_vrb, (list, tuple, set)), "jbo_vrb is a " + type_name(jbo_vrb)
        assert hasattr(jbo_vrb, '__iter__')
        idn_order = 'ASC' if idn_ascending else 'DESC'
        jbo_order = 'ASC' if jbo_ascending else 'DESC'
        query_args = [
            'SELECT '
            'w.obj AS obj, '   # NOTE:  Avoid 
            'w.idn AS idn, '
            'w.sbj AS sbj, '
            'w.vrb AS vrb, '
            'w.num AS num, '
            'w.txt AS txt, '
            'w.whn AS whn',
            None
        ] if obj_group else [
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
        query_args += self._and_clauses(idn, sbj, vrb, obj)

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

    @staticmethod
    def _and_clauses(idn, sbj, vrb, obj):
        assert isinstance(idn, (Number, Word, type(None)))
        assert isinstance(sbj, (Number, Word, type(None)))
        # assert isinstance(vrb, (Number, Word, type(None))) or is_iterable(vrb)
        assert isinstance(vrb, (Number, Word, type(None), collections_abc.Iterable))
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

    class SuperIdentifier(six.text_type):
        """Identifier in an SQL super-query that could go in `back-ticks`."""

    class TableName(SuperIdentifier):
        """Name of a MySQL table in a super-query"""

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
                raise self.SuperSelectStringString(
                    "Consecutive super_select() arguments should not be strings.  " +
                    "Pass string fields through qiki.Text().  " +
                    "Pass identifiers through SuperIdentifier().  " +
                    "Or concatenate actual plaintext strings with +, or intersperse a None.\n"
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
                Intersperse None instead.
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
        return query, parameters

    def server_version(self):
        return Text.decode_if_you_must(self.super_select_one('SELECT VERSION()')[0])

    def super_select_one(self, *query_args, **kwargs):
        query, parameters = self._super_parse(*query_args, **kwargs)
        with self._cursor() as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchone()

    class QueryError(Exception):
        """super_query() had a MySQL exception.  Report the query string along with the error message."""

    def super_query(self, *query_args, **kwargs):
        query, parameters = self._super_parse(*query_args, **kwargs)
        with self._cursor() as cursor:
            try:
                cursor.execute(query, parameters)
            except mysql.connector.ProgrammingError as exception:
                # EXAMPLE:
                #     ProgrammingError: 1142 (42000): DELETE command denied to user 'qiki_unit_tester'@'localhost'
                #     for table 'word_3f054d67009e44cebu4dd5c1ff605faf'
                raise self.QueryError(str(exception) + " on query: " + query)

    class SelectError(Exception):
        """super_select() had a MySQL exception.  Report the query."""

    def super_select(self, *query_args, **kwargs):
        """
        SQL statement-fragment strings interleaved with data, that generates rows

        EXAMPLE:


        :param query_args:  e.g.
        :param kwargs:
        :return:
        """
        debug = kwargs.get('debug', False)
        query, parameters = self._super_parse(*query_args, **kwargs)
        if debug:
            print("Parameters", ", ".join([repr(parameter) for parameter in parameters]))
        with self._cursor() as cursor:
            try:
                cursor.execute(query, parameters)
            except mysql.connector.ProgrammingError as exception:
                # EXAMPLE:
                #     ProgrammingError: 1055 (42000): Expression #1 of SELECT list is not in GROUP BY clause
                #     and contains non-aggregated column 'qiki_unit_tested.w.idn' which is not functionally dependent
                #     on columns in GROUP BY clause; this is incompatible with sql_mode=only_full_group_by
                raise self.SelectError(str(exception) + " on query: " + query)

            for row in cursor:
                field_dictionary = dict()
                if debug:
                    print(end='\t')
                for field, name in zip(row, cursor.column_names):
                    if field is None:
                        value = None
                    elif name.endswith('txt'):   # including jbo_txt
                        value = self.text_from_mysql(field)
                    else:
                        value = self.number_from_mysql(field)
                    field_dictionary[name] = value
                    if debug:
                        print(name, repr(value), end='; ')
                yield field_dictionary
                if debug:
                    print()

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
            elif isinstance(sub_arg, Word):
                yield sub_arg.idn.raw
            else:
                raise TypeError("contains a " + type_name(sub_arg))

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


def idn_from_word_or_number(x):
    """
    Helper for functions that take either idn or word.

    Or for a LexSentence, return its idn for itself!

    CAUTION:  This will of course NOT be the idn that OTHER lexes use
              to refer to this lex.

    :param x:  - an idn or a word
    :return:   - an idn
    """
    # TODO:  Support idn_from_word_or_number(42) !?
    if isinstance(x, Word):
        assert isinstance(x.idn, Number)
        return x.idn
    elif isinstance(x, Number):
        return x
    elif isinstance(x, LexSentence):
        assert isinstance(x.IDN_LEX, Number)
        return x.IDN_LEX
    else:
        raise TypeError(
            "idn_from_word_or_number({}) is not supported, "
            "only Word or Number.".format(
                type_name(x),
            )
        )


def word_match(word_1, word_or_words_2):
    """
    Is a word equal to another word (or any of a nested collection of words)?

    Actually they can be idns too.
    """
    # assert not is_iterable(word_1)
    if is_iterable(word_or_words_2):
        for word_2 in word_or_words_2:
            if word_match(word_1, word_2):
                return True
        return False
    else:
        return idn_from_word_or_number(word_1) == idn_from_word_or_number(word_or_words_2)


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
    try:
        iter(x)
    except TypeError as e:
        assert e.__class__ is TypeError   # A subclass of TypeError raised by comparison operators?  No thanks.
        return False
    else:
        return True


assert is_iterable(['a', 'list', 'is', 'iterable'])
assert not is_iterable('a string is not')


class Text(six.text_type):
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
        return isinstance(x, (type(u''), type(b''), bytearray))


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

    def get_verbs(self, debug=False):
        return self.get_verbs_new(debug)

    def get_verb_dicts(self, debug=False):
        """
        Generate dictionaries about qoolbar verbs:
            idn - qstring of the verb's idn
            name - txt of the verb, e.g. 'like'
            icon_url - txt from the most recent iconify sentence (or None if there weren't any)

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

    def get_verbs_new(self, debug=False):
        qool_verbs = self.lex.find_words(
            vrb=self.lex[u'define'],
            # obj=self.lex[u'verb'],   # Ignore whether object is lex[verb] or lex[qool]
                                       # Because qiki playground did [lex](define][qool] = 'like'
                                       # but now we always do        [lex](define][verb] = 'like'
                                       # so we only care if some OTHER word declares it qool.  And nonzero.
            jbo_vrb=(self.lex[u'iconify'], self.lex[u'qool']),
            jbo_strictly=True,
            debug=debug
        )
        verbs = []
        qool = self.lex[u'qool']
        iconify = self.lex[u'iconify']
        for qool_verb in qool_verbs:
            has_qool = False
            newest_iconify_url = None
            qool_verb.qool_num = None
            for aux in qool_verb.jbo:
                if aux.vrb == qool:
                    has_qool = True
                    qool_verb.qool_num = aux.num   # Remember num from newest qool sentence.
                elif aux.vrb == iconify:
                    newest_iconify_url = aux.txt
            if has_qool:   # and newest_iconify_url is not None:
                # NOTE:  We used to insist that qool verbs have an icon.
                # NOTE:  We don't usually catch ourselves using the royal we.
                qool_verb.icon_url = newest_iconify_url
                verbs.append(qool_verb)
                # yield is not used here because find_word(jbo_vrb) does not handle
                # a generator's iterator well.  Can that be done in one pass anyway?
                # Probably not because of super_select() -- the MySQL version of which
                # needs to pass a list of its values and know its length anyway.
        return verbs

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

    # def nums(self, obj):   # TODO:  Obsolete?
    #     jbo = self.lex.find_words(idn=obj, jbo_vrb=self.get_verbs())[0].jbo
    #     return_dict = dict()
    #     for word in jbo:
    #         icon_entry = return_dict.setdefault(word.vrb, dict())
    #         icon_entry[word.sbj] = dict(num=word.num)
    #     return return_dict

# DONE:  Combine connection and table?  We could subclass like so:  Lex(MySQLConnection)
# DONE:  ...No, make them properties of Lex.  And make all Words refer to a Lex
# DONE:  ...So combine all three.  Maybe Lex should not subclass Word?
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
