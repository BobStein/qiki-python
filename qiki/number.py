"""
A qiki Number is an integer, floating point, complex, and more, seamlessly represented.

Features:
 - arbitrary precision
 - arbitrary range
 - monotonicity (memcmp() order)
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import binascii
import math
import numbers
import operator
import struct

import six


# TODO:  Move big comment sections to docstrings.


class Zone(object):
    """
    A Zone represents a contiguous range of qiki Number values.

    Each valid qiki Number is in exactly one zone.
    (A few invalid values are between zones.)
    There are 14 zones.  This class enumerates the zones.

    Also, it encapsulates some utilities, e.g. Zone.name_from_code[Zone.NAN] == 'NAN'

    Zone Code
    ---------
    Each member of the Zone class has a value that is the zone code.
    A zone code is a raw binary string,
    of the same type as the raw internal binary string of a qiki Number.
    A zone code is either:
        minimum value for the zone
        between the values of its zone and the one below it
    Each code is less than or equal to all raw values of numbers in the zone it represents
    and greater than all values in the zones below.
    (So some zone codes are valid raw values for numbers in that zone,
    others are among the invalid inter-zone values.  More on this below.)
    For example, the raw binary string for 1 is b'x82\x01' which is the minimum valid value for
    the positive zone.  But Zone.POSITIVE is less than that, it is b'x82'.
    Anything between b'x82' and b'x82\x01' will be interpreted as 1 by a Number Consumer (NumberCon).
    But any Number Producer (NumberPro) that generates a 1 should generate the raw string b'x82\x01'.

    Between versus Minimum
    ----------------------
    A minor, hair-splitting point, but it explains why some zone codes are between zones.
    Most zone codes are the raw byte string same as the minimum Number in their zone.
    Zone.FRACTIONAL_NEG is one exception.  Its code is b'\x7E\x00'.
    That binary string is not valid for a number's binary string.
    That is never a valid raw value for a number because it ends in a 00,
    and ending in a 00 is used to indicate a suffix.
    The actual minimum value for this zone cannot be represented in finite storage,
    because that would be a hypothetical infinite byte string.  Conceptually the minimum would be
    b'\x7E\x00\x00\x00 ... infinite number of \x00s ... followed by something other than \x00'
    Representing a surreal -0.99999999999...infinitely many 9s, but still greater than -1.
    So instead we use the invalid, inter-zone b'\x7E\x00' which is *between* valid raw values.
    And all valid raw values in Zone FRACTIONAL_NEG are above it.
    And all valid raw values in Zone NEGATIVE are below it.

    The "between" zone codes are:
        INFINITESIMAL
        LUDICROUS_SMALL_NEG
        FRACTIONAL_NEG
        TRANSFINITE_NEG

    So are there or are not there inter-zone Numbers?  No.
    In other words, are the zones comprehensive? Yes.
    Invalid values should normalize to valid values.

    Zone class properties
    ---------------------
        Zone.name_from_code - dictionary translating each zone code to its name
            {Zone.TRANSFINITE: 'TRANSFINITE', ...}
        Zone.descending_codes - list of zone codes in descending order:
            [Zone.TRANSFINITE, ...]
    """
    # TODO:  Make these caching functions?  Zone.name_from_code() and Zone.descending_codes().

    # TODO:  Move the part of this docstring on invalid values and plateau values somewhere else?
    # To Number class FFS?  To the Raw class!  No, it means different things in Number and Suffix.
    # Or we could make classes Raw and RawForNumber and RawForSuffix?  Bah!  Forget that.
    # This talk belongs in class Number docstring.
    # TODO:  Rename invalid values to plateau values?
    # TODO:  Or rename Plateau Codes or Code Plateaus, or Raw Plateau?
    # since every qstring at a plateau represents the same VALUE.
    # TODO:  Test that invalid values normalize to valid values.
    # Or should illegal values just crash?  I mean come on, 0q80_00 is just insane.
    # TODO:  Formally define all invalid raw-strings.
    # TODO:  Remove redundancies in this docstring.

    TRANSFINITE         = b'\xFF\x80'
    LUDICROUS_LARGE     = b'\xFF'
    POSITIVE            = b'\x82'
    FRACTIONAL          = b'\x81'
    LUDICROUS_SMALL     = b'\x80\x80'
    INFINITESIMAL       = b'\x80\x00'
    ZERO                = b'\x80'
    INFINITESIMAL_NEG   = b'\x7F\x80'
    LUDICROUS_SMALL_NEG = b'\x7F\x00'
    FRACTIONAL_NEG      = b'\x7E\x00'
    NEGATIVE            = b'\x01'
    LUDICROUS_LARGE_NEG = b'\x00\x80'
    TRANSFINITE_NEG     = b'\x00'
    NAN                 = b''

    name_from_code = None   # {b'\xFF\x80': 'TRANSFINITE', b'\xFF': 'LUDICROUS_LARGE', ... }
    descending_codes = None   # [b'\xFF\x80', b'\xFF', b'\x82', b'\x81', b'\x80\x80', ..., b'' ]

    @classmethod
    def internal_setup(cls):
        """Initialize Zone properties after the Zone class is otherwise defined."""
        cls.name_from_code = { getattr(cls, attr): attr for attr in dir(cls) if attr.isupper() }
        cls.descending_codes = sorted(Zone.name_from_code.keys(), reverse=True)


Zone.internal_setup()
assert Zone.name_from_code[Zone.ZERO] == 'ZERO'
assert Zone.descending_codes[0] == Zone.TRANSFINITE
assert Zone.descending_codes[13] == Zone.NAN


class Number(numbers.Complex):
    """
    Integers, floating point numbers, complex numbers, and more.

    A qiki Number is internally represented by a binary string of 8-bit bytes, called its raw value.
        Example:  b'\x82\x01' is the raw value for the number 1.
    A qstring is a text representation of a qiki Number.
        Example:  '0q82_01' is the qstring for the number 1.
    A qstring contains the hexadecimal digits of the raw value.
        Examples:
            +2 == Number('0q82_02')
            +1 == Number('0q82_01')
            +0 == Number('0q80')
            -1 == Number('0q7D_FF')
            -2 == Number('0q7D_FE')
          -2.5 == Number('0q7D_FD80')

    More examples:
                       pi - 0q82_03243F6A8885A3
                            (a 53-bit IEEE double precision version of pi)
                       pi - 0q82_03243F6A8885A308D313198A2E03707344A409382229
                            9F31D0082EFA98EC4E6C89452821E638D01377BE54
                            (a 338-bit version of pi, about 100 decimal digits)
                   googol - 0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7C
                            AAB24308A82E8F10 (exactly 10^100)
        negative infinity - 0q00_7F   (negative omega, the first transfinite negative ordinal)
            infinitesimal - 0q807F   (epsilon)
                        i - 0q80__8201_690300   (the imaginary number)

    0q-what?  Let's review.

    Every Python integer has a hexadecimal representation (42 == 0x2A).
    Similarly, every qiki Number has a qstring representation.  This shows its guts.
    A qiki Number stores a string of bytes, called its raw value.
    The qstring has those bytes in hexadecimal.
    Underscores are decoration for human readers, to break up the hex into parts.
    The parts are called qex, qan, and suffixes.  More on those later.
    Underscores do not affect the raw value.

        assert Number(1) == Number('0q82_01')
        assert '0q82_01' == Number(1).qstring()

    The qiki Number one is internally represented as two bytes b'\x82\x01'.
    82 is the qex, kind of like an exponent.
    01 is the qan, like a mantissa.
    """

    # __slots__ = ('_raw',        )   # slightly less memory    \ pick
    __slots__ = ('_raw', '_zone')   # slightly faster         / one

    def __init__(self, *args, **kwargs):   # content=None, qigits=None, normalize=False):
        """
        Number constructor.

        content - the type can be:
            int               10**100
            float             3.14
            qstring          '0q82_01'
            numeric string   '1'
            complex number   1j2
            another Number   Number(42)
            None             None
        qigits - number of bytes to put in the qan
                 see _raw_from_float()
                 see QIGITS_PRECISION_DEFAULT
        normalize=True - collapse equal values e.g. 0q82 becomes 0q82_01
                         see _normalize_all()

        See _from_float() for more about floating point values.
        """

        args_list = list(args)
        try:
            content = args_list.pop(0)
        except IndexError:
            content = kwargs.pop(str('content'), None)
        qigits = kwargs.pop(str('qigits'), None)
        normalize = bool(kwargs.pop(str('normalize'), False))

        assert isinstance(qigits, (int, type(None)))
        assert isinstance(normalize, bool)

        # TODO:  Is-instance or duck-typing or factory-method?
        #        is-instance calls isinstance(content) many times in the constructor,
        #                    each type gets converted differently
        #        duck-typing would somehow try to convert the content in different ways
        #                    and use exceptions to fall back on other ways, leading to the correct way
        #        factory-method would not allow a constructor, or allow it for only one type, probably
        #                       a qstring.  Callers would resort to factory methods for converting other
        #                       types into a Number.
        # SEE:  Duck-typing constructor arguments, https://stackoverflow.com/q/602046/673991
        # NOTE:  Is-instance pros:
        #        Brief use:  Number(42)
        #        Readable type alternatives
        #        Explicit hierarchy, more straightforward debugging
        # NOTE:  Duck-typing pros:
        #        Brief use:  Number(42)
        #        Flexibility, may inadvertently support unfamiliar number types
        # NOTE:  factory-method pros:
        #        Clear use:  Number.from_int(42)
        #        Clear implementation code
        if isinstance(content, six.integer_types):
            self._from_int(content)
        elif isinstance(content, float):
            self._from_float(content, qigits)
        elif isinstance(content, Number):
            self._from_another_number(content)
        elif isinstance(content, six.string_types):
            self._from_string(content)
        elif isinstance(content, complex):
            self._from_complex(content)
        elif content is None:
            if len(args_list) > 0:
                raise self.ConstructorSuffixError("Don't suffix Number.NAN")
            self.raw = self.RAW_NAN
        else:
            raise self.ConstructorTypeError("{outer}({inner}) is not supported".format(
                outer=type_name(self),
                inner=type_name(content),
            ))

        for suffix in flatten(args_list):
            # TODO:  Isn't calling flatten() silly overkill?  Why not just insist
            #        args_list be a single-level list of Suffix() instances?
            #        So you have a list of Suffix() instances, s, you call Number(_, *s).
            # THANKS:  Flattening list, http://stackoverflow.com/a/952952/673991
            if isinstance(suffix, Suffix):
                self.raw = self.plus_suffix(suffix).raw
            else:
                raise self.ConstructorSuffixError("Expecting suffixes, not a '{}'".format(type_name(suffix)))

        assert isinstance(self._raw, six.binary_type)
        if normalize:
            self._normalize_all()

    def _from_another_number(self, another_number_instance):
        """
        Copy Constructor

        So sensible things happen:

            assert Number(1) == Number(Number(1))

        It could convert between subclasses:

            x = SomeSubclassOfNumber(DifferentSubclassOfNumber())
        """
        self.raw = another_number_instance.raw

    class ConstructorTypeError(TypeError):
        """e.g. Number(object) or Number(content=[])"""

    class ConstructorValueError(ValueError):
        """e.g. Number('alpha string') or Number.from_raw(0) or Number.from_qstring('0x80')"""

    class ConstructorSuffixError(TypeError):
        """e.g. Number(1, object), Number(None, 1)"""

    # Raw internal format
    # -------------------
    # The raw string is the internal representation of a qiki Number.
    # It is a string of 8-bit binary bytes.
    # E.g. b"\x82\x01" in Python version 2 or 3.
    # Any storage mechanism for the raw format (such as a database)
    # should expect any of the 256 values for any of the bytes.
    # So for example they could not be stored in a C-language string with NUL terminators.
    # The length must be stored extrinsic to the raw string
    # though it can be limited, such as to 255 bytes max.
    # It is represented textually by a "qstring" which is hexadecimal digits,
    # preceded by '0q', and containing optional '_' underscores.
    # The raw string consists of a qex and a qan.
    # Conventionally one underscore separates the qex and qan.
    # These are analogous to a floating point exponent and a significand or mantissa.
    # The qex and qan are encoded so that the raw mapping is monotonic.
    # That is, iff x1.raw < x2.raw then x1 < x2.
    # With a few caveats raw strings are also bijective
    # (aka one-to-one and onto, aka unique).
    # That is, if x1.raw == x2.raw then x1 == x2.
    # Caveat #1, some raw strings represent the same number,
    # for example 0q82 and 0q82_01 are both exactly one.
    # Computation results normalize to a standard and unique representation (0q82_01).
    # Storage (e.g. a database) may opt for brevity (0q82).
    # So all 8-bit binary strings have at most one interpretation as the raw part of a Number.
    # And some are redundant, e.g. assert Number('0q82') == Number('0q82_01')
    # And some are invalid, e.g. 0q00
    # The qex and qan may be followed by suffixes.
    # Two underscores conventionally precede each suffix.
    # See the Number.Suffix class for underscore conventions within a suffix.
    # All suffixes end in a 00 zero-tag.  The qex+qan pair never ends in a 00.

    # TODO:  Make class Raw?  Then both Number and Suffix contain instances of Raw??  Yay!
    # Except even merely subclassing bytes, the size goes up from py23(24,20) bytes to 40.
    # With composition the size goes up even more
    #  __slots__=() helps in subclassing int, but not apparently in subclassing bytes.
    # Except in Python 3 it does help!  Apparently it removes all overhead of subclassing!
    # So I was wrong above, subclassing changes sizeof from py23(24,20) to py23(40,20).
    # If we did make a Raw class, we could Number(Raw(b'\x82\x01')) instead of Number.from_raw(b'\x82\x01')
    # And Number(bytearray(b'\x82\x01')) could be made to work but should it?  Abolish from_raw_bytearray()?
    # Probably not, because from_mysql == from_raw_bytearray.
    # In any case Number(bytes(b'\x82\x01')) should raise an exception.
    # In Python 3 rather easily, but Python 2 because it fails int(content) etc.
    # Number.from_qstring() is the only remaining public class method that makes sense.
    # One good reason to put off implementing a Raw class:  resolve Suffix formatting,
    # in case there's a more generic, open, powerful way to encode them, e.g. type field being a Number.
    RAW_INFINITY          = bytes(b'\xFF\x81')
    RAW_INFINITESIMAL     = bytes(b'\x80\x7F')
    RAW_ZERO              = bytes(b'\x80')
    RAW_INFINITESIMAL_NEG = bytes(b'\x7F\x81')
    RAW_INFINITY_NEG      = bytes(b'\x00\x7F')
    RAW_NAN               = bytes(b'')

    # TODO:  Remove bytes() calls when PyCharm stops its boneheaded warnings on b'literal' not being bytes.

    # TODO:  New warning quandary with PyCharm 2018.2
    #        RAW_ZERO = b'\x80'        -- ok 2.7, ok 3.5, PyCharm warning: Expected type 'bytes', got 'str' instead)
    #        RAW_ZERO = six.b('\x80')  -- no 2.7, ok 3.5
    #        RAW_ZERO = six.b(b'\x80') -- ok 2.7, no 3.5
    #        RAW_ZERO = bytes(b'\x80') -- ok 2.7, ok 3.5, and runs. Yippee.  (PyCharm 2018.3)

    @property
    def raw(self):
        """
        Get the internal byte-string representation of the Number.

            assert '\x82\x01' == Number(1).raw

        Implemented as a property so that self._zone (if there's a slot to store it)
        can be computed in sync with the raw value.
        """
        return self._raw

    @raw.setter
    def raw(self, value):
        """ Set the raw byte-string.  Rare. """
        # TODO:  Enforce rarity?  Make this setter raise an exception, and create a _set_raw() method.
        # Would making Number immutable avoid common ref bugs, e.g. def f(n=Number(0)):  n += 1 ...
        assert isinstance(value, six.binary_type)
        # noinspection PyAttributeOutsideInit
        self._raw = value
        self._zone_setter()

    def __getstate__(self):
        """For the 'pickle' package, object serialization."""
        # TODO:  Test with dill.
        return self.raw

    def __setstate__(self, raw_incoming):
        """For the 'pickle' package, object serialization."""
        self.raw = raw_incoming

    # TODO:  def __format__() that behaves like EITHER an int or float depending on specifier
    #        e.g. {:d} for int, {:f} for float

    def __repr__(self):
        """Handle repr(Number(x))"""
        # TODO:  Alternative repr() for suffixed numbers, e.g.
        #        assert "Number('0q80__7E0100')"       == repr(Number(0, Suffix(Suffix.Type.TEST)))
        #        assert "Number('0q80', Suffix(TEST))" == repr2(Number(0, Suffix(Suffix.Type.TEST)))
        return "Number('{}')".format(self.qstring())

    def __str__(self):
        """Handle str(Number(x))"""
        try:
            return self.qstring()
        except Suffix.RawError:
            return "?" + self.hex() + "?"

    def to_json(self):
        # return self.qstring()

        if self.is_suffixed():
            # TODO:  Complex?
            return self.qstring()
        elif not self.is_reasonable():
            # THANKS:  JSON is a dummy about NaN, inf,
            #          https://stackoverflow.com/q/1423081/673991#comment52764219_1424034
            # THANKS:  None to nul, https://docs.python.org/library/json.html#py-to-json-table
            return None
        elif self.is_whole():
            return int(self)
        else:
            # TODO:  Ludicrous numbers should become int.
            # NOTE:  Infinitesimal numbers should not become zero passively, right?
            #        Maybe instead make a Number.approximate() function that turns them to zero.
            #        Although 0.0 == float(Number.POSITIVE.INFINITESIMAL) does it already.
            return float(self)


    # Comparison
    # ----------
    def __eq__(self, other):
        """Handle Number(x) == something"""
        # TODO:  Make more efficient.
        #        Maybe normalize on construction or computation.
        #        Maybe from_qstring() with a non-normalized contents will just suffer from
        #        "appearing" not equal.
        try:
            self_ready = self._op_ready(self)
            other_ready = self._op_ready(other)
        except self.CompareError:
            # FIXME:  This never happens now that _op_ready() returns NotImplemented itself.
            return NotImplemented
            # THANKS:  Fall back to e.g. other.__eq__(self), http://jcalderone.livejournal.com/32837.html
        else:
            return self_ready == other_ready

    def __ne__(self, other):
        """Handle Number(x) != something"""
        eq_result = self.__eq__(other)
        if eq_result is NotImplemented:
            return NotImplemented
        return not eq_result

    def __lt__(self, other):  self._comparable(other); return self._op_ready(self) <  self._op_ready(other)
    def __le__(self, other):  self._comparable(other); return self._op_ready(self) <= self._op_ready(other)
    def __gt__(self, other):  self._comparable(other); return self._op_ready(self) >  self._op_ready(other)
    def __ge__(self, other):  self._comparable(other); return self._op_ready(self) >= self._op_ready(other)
    # SEE:  Avoiding __cmp__(), http://gerg.ca/blog/post/2012/python-comparison/

    @classmethod
    def _op_ready(cls, x):
        """Get x ready for comparison operators."""
        try:
            normalized_number = cls(x, normalize=True)
        except cls.ConstructorTypeError:
            # DEBATE:  Not pythonic to raise an exception here (or in _comparable())
            # 0 < object will always be True, 0 > object always False.
            # With this exception we cannot sort a mixed type list of Numbers and other objects
            # (Order would be arbitrary, but it should not raise an exception.)
            # SEE:  about arbitrary ordering, http://stackoverflow.com/a/6252953/673991
            # SEE:  about arbitrary ordering, http://docs.python.org/reference/expressions.html#not-in
            # "...objects of different types ... are ordered consistently but arbitrarily."

            # DEBATE:  As long as a qiki Number is an exotic type, this exception may avoid
            # unintended comparisons, e.g. with other exotic types.  This is more important
            # than being able to "sort" a mixed bag of Numbers and other types.

            # DEBATE:  Return NotImplemented?  http://jcalderone.livejournal.com/32837.html
            # SEE:  Comparison in list.sort(), http://stackoverflow.com/a/879005/673991

            # EXAMPLE:  Number(1) == object is one way to get here.

            return NotImplemented

            # raise cls.CompareError("A Number cannot be compared with a " + type(x).__name__)
            # # NOTE:  This exception message never makes it out of code in this source file.
            # # The only time it is raised, it is also caught, e.g. Number(0) == object
            # # Whoa, not true, it can be intercepted by trying Number(0) < object
        else:
            return normalized_number.raw

    # Comparisons and Redundant Values
    # --------------------------------
    # TODO:  Turn the blather below into documentation
    # The conundrum comparing Numbers is to comply with Postel's Law
    #     "Be conservative in what you emit, and liberal in what you accept."
    # That is, certain raw byte sequences should be interpreted with redundancy on input,
    # but they should be generated with uniqueness.  E.g. 4 minus 3 should always output 0q82_01 never 0q82
    # They must behave immune to redundancies, e.g. 0q82 == 0q82_01.
    # They may be stored with compactness, e.g. '\x82' for 1.0 in a database.
    #
    # The options...
    # (By the way, I went with Option one.)
    # Option one:  different _raw values, complicated interpretation of them in __eq__() et al.
    #     If going this way, equality might compare Number.raw_normalized().
    #     DONE:  0q82__FF0100 == 0q82_01__FF0100
    #     Obviously different suffix contents matter:  0q80__FF0100 != 0q80__110100
    #     This approach may be the way it needs to go in the future.
    #     For example if loss-less rational numbers were supported, you might want 2/10 == 1/5
    #     So if rational numbers were implemented by approximation in the root number,
    #     and the denominator in a suffix, this could lead to storage ambiguities that
    #     should appear unambiguous to __eq__() etc.
    # Option two:  convert in raw.setter into normalized raw value.
    #     This one feels safer in the long run.
    #     __eq__() stays simple and direct.
    #     Does this only affect single-byte raw strings??  e.g. 0q82 --> 0q82_01
    #                                                      e.g. 0q7E --> 0q7D_FF
    #     No!                                e.g.  0q81FF_00anything --> 0q81FF_01
    #                                          e.g.  0q82_00anything --> 0q82_01
    #     Oh wow, a regular expression might be devised to take care of normalization.
    #     A very binary-intensive and bytearray-using regular expression.
    #     Let us call these "raw plateaus".
    #     Each raw plateau has a canonical raw value, and a multitude of invalid raw values.
    #     All values at a raw plateau should be "equal".
    #     This approach would vindicate making raw a @property
    # Option three:  give up on Number('0q82') == Number('0q82_01')
    # Option four: exceptions when any raw strings fall within the "invalid" part of a plateau.
    # By the way, zero has no plateau, only 0q80 with no suffix is zero.  (except empty suffix?)
    # TODO:  What about numbers embedded in suffixes, should these be equal?
    #            0q80__82_7F0200
    #            0q80__8201_7F0300
    #        Same root, same suffix type, different suffix payloads: 82 and 8201
    #                                                                which are both Number(1)
    #                                                                if these payloads are in fact Numbers.
    # TODO:  Number.compacted() an alternative to Number.normalized()
    #        Compacted forms may be desirable Numbers in payload suffixes
    # TODO:  Should normalization strip empty suffixes?  (__0000)

    class CompareError(TypeError):
        """e.g. Number(1+2j) < Number(1+3j)"""

    def _comparable(self, other):
        """ Make sure operands can be compared.  Otherwise ConstructorTypeError. """
        if self.is_complex():
            raise self.CompareError("Complex values are unordered.")
            # TODO:  Should this exception be "Unordered" instead?
        try:
            other_as_a_number = type(self)(other)
        except self.ConstructorTypeError:

            raise self.CompareError("Number cannot be compared with a " + type(other).__name__)
        else:
            if other_as_a_number.is_complex():
                raise self.CompareError("Cannot compare complex values.")

    # Math
    # ----
    def __hash__(self):
        return hash(self.raw)

    def __pos__(self): return self._unary_op(operator.__pos__)
    def __neg__(self): return self._unary_op(operator.__neg__)
    def __abs__(self): return self._unary_op(operator.__abs__)

    def __add__(self, other): return self._binary_op(operator.__add__, self, other)
    def __radd__(self, other): return self._binary_op(operator.__add__, other, self)
    def __sub__(self, other): return self._binary_op(operator.__sub__, self, other)
    def __rsub__(self, other): return self._binary_op(operator.__sub__, other, self)
    def __mul__(self, other): return self._binary_op(operator.__mul__, self, other)
    def __rmul__(self, other): return self._binary_op(operator.__mul__, other, self)
    def __truediv__( self, other): return self._binary_op(operator.__truediv__, self, other)
    def __rtruediv__(self, other): return self._binary_op(operator.__truediv__, other, self)
    def __floordiv__( self, other): return self._binary_op(operator.__floordiv__, self, other)
    def __rfloordiv__(self, other): return self._binary_op(operator.__floordiv__, other, self)
    def __pow__(self, other): return self._binary_op(operator.__pow__, self, other)
    def __rpow__(self, other): return self._binary_op(operator.__pow__, other, self)

    def __div__(self, other):
        """
        Implement the single-slash division operator for Python 2.

        This will never be hybrid division. (Hybrid division is true-
        division with floats, but floor-division with integers. That's
        the way Python 2 handles the single-slash operator.)

        Even though we use future division in this source file, a client
        might not.  So a Python 2 client using Number(x) / Number(y)
        will just have to live with true-division, whether or not they do:
        from __future__ import division.

        Otherwise, there would be no sensible way to force a true-
        division for that client.  To get true-division with native types,
        you make sure one of the operands is a float.  For example, 2/3 is
        zero but 2.0/3 is 0.666...  But Number(2.0)/Number(3) is
        indistinguishable from Number(2)/Number(3).  So in this sense,
        Number behaves slightly more like float than int.  Or you could
        say Number imposes a little Python 3 onto Python 2 users.
        """
        return operator.__truediv__(self, other)

        # return self._binary_op(operator.__truediv__, self, other)
        # NOTE:  Pointless to call _binary_op(), because truediv always uses float

        # TODO:  Does using true-division here cause weird effects at float/int boundary?
        #        Expose them in unit tests.
        #        Apparently operator.__truediv__() always converts to float.
        # TODO:  Re-review division, here and unit tests, yet again.

        # TODO:  Should large (N >= 2**54) Numbers divide as int?
        #        That is, use floordiv (aka int) instead of truediv (aka float).
        #        Floor-division may be better than true-division:
        #            (N+1)*(N+1)/(N+1) - N should be 1 not 0.0

    def __rdiv__(self, other):
        """Handle something / Number(x) when something is int/float/etc."""
        return self._binary_op(operator.__truediv__, other, self)

    def _unary_op(self, op):
        """One-input operator - fob off on int or float or complex math."""
        n = type(self)(self)
        if n.is_complex():
            # NO LONGER NEEDED? noinspection PyTypeChecker
            return type(self)(op(complex(n)))
            # FIXME:  Unexpected type(s): (Number) Possible types: (float) (str)
            # SEE:  https://youtrack.jetbrains.com/issue/PY-27766

        # try:
        #     int_is_better_than_float = n.is_whole()
        # except self.WholeError:
        #     int_is_better_than_float = False
        #
        # if int_is_better_than_float:

        elif n.is_whole():
            return type(self)(op(int(n)))
        else:
            return type(self)(op(float(n)))

    @classmethod
    def _binary_op(cls, op, input_left, input_right):
        """Two-input operator - fob off on int or float or complex math."""
        n1 = cls(input_left)
        n2 = cls(input_right)
        if n1.is_complex() or n2.is_complex():
            # NO LONGER NEEDED?  noinspection PyTypeChecker
            return cls(op(complex(n1), complex(n2)))
            # FIXME:  Unexpected type(s): (Number) Possible types: (float) (str)
            # SEE:  https://youtrack.jetbrains.com/issue/PY-27766

        # try:
        #     int_better_than_float = n1.is_whole() and n2.is_whole()
        # except cls.WholeError:
        #     int_better_than_float = False
        #
        # if int_better_than_float:

        elif n1.is_whole() and n2.is_whole():
            return cls(op(int(n1), int(n2)))
        else:
            return cls(op(float(n1), float(n2)))

    def _normalize_all(self):
        """
        Eliminate redundancies in the internal _raw string.

        This operates in-place, modifying self.  So there are no return values.
        """
        self._normalize_plateau()
        self._normalize_imaginary()

    def _normalize_imaginary(self):
        """
        Eliminate imaginary suffix if it is zero.  Change in-place, does not return anything.

        So e.g. 1+0j == 1

        Don't check self.imag == self.ZERO because that may try to subtract a suffix that isn't there.

        Check all imaginary suffixes. If any nonzero, leave them all alone.
        This might one day help support quaternions that have three imaginary suffixes.
        """
        imaginaries = [suffix.number for suffix in self.suffixes if suffix.type_ == Suffix.Type.IMAGINARY]
        all_imaginaries_zero = all(imaginary == self.ZERO for imaginary in imaginaries)
        if imaginaries and all_imaginaries_zero:
            self.raw = self.minus_suffix(Suffix.Type.IMAGINARY).raw

    def _normalize_plateau(self):
        """
        Eliminate redundancies in the internal representation of edge values +/-256**+/-n.

        E.g.  0q82 becomes 0q82_01 for +1.
        E.g.  0q7E01 becomes 0q7E00_FF for -1/256.
        """
        if self.zone in ZoneSet.REASONABLY_NONZERO:
            unsuffixed = self.unsuffixed
            suffixes = self.suffixes
            raw_qex = unsuffixed.qex_raw()
            raw_qan = unsuffixed.qan_raw()
            is_plateau = False
            if len(raw_qan) == 0:
                is_plateau = True
                if self.is_positive():
                    self.raw = raw_qex + bytes(b'\x01')
                else:
                    new_qex_lsb = six.indexbytes(raw_qex,-1)
                    new_qex = raw_qex[0:-1] + six.int2byte(new_qex_lsb-1)
                    self.raw = new_qex + bytes(b'\xFF')
            else:
                if self.is_positive():
                    if raw_qan[0:1] == bytes(b'\x00'):
                        is_plateau = True
                        self.raw = raw_qex + bytes(b'\x01')
                else:
                    if raw_qan[0:1] == bytes(b'\xFF'):
                        is_plateau = True
                        self.raw = raw_qex + bytes(b'\xFF')
            if is_plateau and suffixes:
                # NOTE:  A Number with suffixes whose unsuffixed part needed plateau-normalizing
                for suffix in suffixes:
                    self.raw = self.plus_suffix(suffix).raw

    def normalized(self):
        """
        Return a normalized version of this number.

        assert '0q82'    == Number('0q82').qstring()
        assert '0q82_01' == Number('0q82').normalized().qstring()
        """
        return type(self)(self, normalize=True)

    @staticmethod
    def is_number(x):
        """
        Is this fundamentally numeric?

        Not to be confused with what the Number() constructor could take.
        Because Number('0q82_01') and Number("42") are valid but
        Number.is_number('0q82_01') and Number.is_number("42") are false.
        """
        return isinstance(x, numbers.Number)

    def is_negative(self):
        """Is this Number negative?"""
        return_value = ((six.indexbytes(self.raw, 0) & 0x80) == 0)
        assert return_value == (self.zone in ZoneSet.NEGATIVE)
        assert return_value == (self.raw < self.RAW_ZERO)
        return return_value

    def is_positive(self):
        """Is this Number positive?"""
        return_value = (not self.is_negative() and not self.is_zero())
        assert return_value == (self.zone in ZoneSet.POSITIVE)
        assert return_value == (self.raw > self.RAW_ZERO)
        return return_value

    def is_zero(self):
        """Is this Number zero?"""
        return_value = (self.raw == self.RAW_ZERO)
        assert return_value == (self.zone in ZoneSet.ZERO)
        return return_value

    def is_reasonable(self):
        return self.zone in ZoneSet.REASONABLE

    def is_whole(self):
        """Can this number be represented by an integer?"""
        if self.zone in ZoneSet.WHOLE_MAYBE:
            (qan_int, qan_len) = self.qan_int_len()
            qex = self.base_256_exponent() - qan_len
            if qex >= 0:
                return True
            else:
                if qan_int % exp256(-qex) == 0:
                    return True
                else:
                    return False
        elif self.zone in ZoneSet.WHOLE_YES:
            return True
        elif self.zone in ZoneSet.WHOLE_NO:
            return False
        else:           # ZoneSet.WHOLE_INDETERMINATE
            return False
            # NOTE:  Lets just not make a big deal out of it
            #        and say transfinite numbers are NOT whole.
            #        So n.is_whole() is more like asking
            #        whether int(n) can represent the number.

    is_integer = is_whole

    def is_nan(self):
        """Is this NAN?"""
        return self.raw == self.RAW_NAN

    def is_real(self):
        """Is the imaginary part zero?"""
        return not self.is_complex()

    def is_complex(self):
        """Is the imaginary part nonzero?"""
        return self.imag != self.ZERO

    def inc(self):
        """Add one."""
        self.raw = self._inc_raw_via_integer()
        return self

    def _inc_raw_via_integer(self):
        """Add one by fobbing off on int."""
        return type(self)(int(self) + 1).raw

    @property
    def real(self):
        """
        Real part, of this seamlessly complex number.

        Stripped of any imaginary suffix.  And any other suffix too.
        """
        return self.unsuffixed

    @property
    def imag(self):
        """Imaginary part, of this seamlessly complex number."""
        try:
            return type(self)(self.suffix(Suffix.Type.IMAGINARY).number)
        except Suffix.NoSuchType:
            return type(self)(self.ZERO)

    def conjugate(self):
        """Complex conjugate.  a + bj --> a - bj"""
        imag = self.imag
        if imag == self.ZERO:
            return self.real
        else:
            return self.real.plus_suffix(Suffix.Type.IMAGINARY, (-imag))

    # "from" conversions:  Number <-- other type
    # ------------------------------------------
    @classmethod
    def from_raw(cls, value):
        """Construct a Number from its raw, internal binary string of qigits.
        value - an 8-bit binary string (e.g. another Number's raw)

        Right:  assert Number(1) == Number(0q82_01')
        Wrong:                      Number(b'\x82\x01')
        Right:  assert Number(1) == Number.from_raw(b'\x82\x01')
        """
        if not isinstance(value, six.binary_type):
            raise cls.ConstructorValueError(
                "'{}' is not a binary string.  Number.from_raw(needs e.g. b'\\x82\\x01')".format(repr(value))
            )
        return_value = cls()
        return_value.raw = value
        return return_value

    @classmethod
    def from_raw_bytearray(cls, value):
        """
        Construct a Number from a bytearray().

        assert Number(1) == Number.from_raw_bytearray(bytearray(b'\x82\x01'))
        """
        return cls.from_raw(six.binary_type(value))

    from_mysql = from_raw_bytearray

    def _from_string(self, s):
        """
        Construct a Number from a string rendering.

        assert Number(1) == Number('0q82_01')
        assert Number(1) == Number('1')
        """
        assert isinstance(s, six.string_types)
        if s.startswith('0q'):
            self._from_qstring(s)
        else:
            try:
                int_value = int(s)   # e.g.  '42' '099'
            except ValueError:
                try:
                    int_value = int(s, 0)   # e.g.  '0x1F' '0o377' '0b11011'
                except ValueError:
                    try:
                        float_value = float(s)   # e.g.  '1.5' '-1e-100'
                    except ValueError:
                        raise self.ConstructorValueError(
                            "A qiki Number string must be a valid int, float, or qstring, "
                            "but not {}".format(repr(s))
                        )
                    else:
                        self._from_float(float_value)
                else:
                    self._from_int(int_value)
            else:
                self._from_int(int_value)

    @classmethod
    def from_qstring(cls, s):
        """
        Construct a Number from its qstring.

        assert Number(1) == Number.from_qstring('0q82_01')
        """
        if s.startswith('0q'):
            return_value = cls()
            return_value._from_qstring(s)
            return return_value
        else:
            raise cls.ConstructorValueError(
                "A qstring must begin with '0q'.  This does not: " + repr(s)
            )

    def _from_qstring(self, s):
        """Fill in raw from a qstring.  Nonsensical q"""
        s_without_0q = s[2:]
        digits = s_without_0q.replace('_', '')
        if len(digits) % 2 != 0:
            digits += '0'
        try:
            byte_string = bytes_from_hex(digits)
        except bytes_from_hex.Error:
            raise self.ConstructorValueError(
                "A qstring consists of hexadecimal digits or underscores, not {}".format(repr(s))
            )
        self.raw = six.binary_type(byte_string)

    def _from_int(self, i):
        """Fill in raw from an int."""
        if   i >  0:   self.raw = self._raw_from_int(i, lambda e: 0x81 + e)
        elif i == 0:   self.raw = self.RAW_ZERO
        else:          self.raw = self._raw_from_int(i, lambda e: 0x7E - e)

    @classmethod
    def _raw_from_int(cls, i, qex_encoder):
        """Convert nonzero integer to internal raw format.

        qex_encoder() converts a base-256 exponent to internal qex format
        """
        qan00 = pack_integer(i)
        qan = right_strip00(qan00)

        exponent_base_256 = len(qan00)
        qex_integer = qex_encoder(exponent_base_256)
        qex = cls._qex_int_byte(qex_integer)

        return qex + qan

    @classmethod
    def _qex_int_byte(cls, qex_integer):
        """Store encoded qex in a single byte, in the raw."""
        if 0x01 <= qex_integer <= 0xFE:
            return six.int2byte(qex_integer)
        else:
            # NOTE:  0x00 and 0xFF are for unreasonable numbers (ludicrous or transfinite).
            raise cls.LudicrousNotImplemented(
                "Ludicrous Numbers are not yet implemented:  {:02x}".format(qex_integer)
            )

    QIGITS_PRECISION_DEFAULT = 8

    SMALLEST_UNREASONABLE_FLOAT = 2.0 ** 1000   # == 256.0**125 ~~ 1.0715086071862673e+301

    def _from_float(self, x, qigits=None):
        """
        Construct a Number from a Python IEEE-754 double-precision floating point number

        float('nan'), float('+inf'), float('-inf') each correspond to distinct Number values.

        float(-0.0) is trickier, mostly because -0.0 == 0.0:
        Number(-0.0) == 0q80 == Number(0.0) == 0.0 == -0.0
        But float(Number.NEGATIVE_INFINITESIMAL)) is -0.0

        The raw part of a number starts with a qex which encodes the base 256 exponent.
        The big zone-based if-statement in this function encodes the qex differently for each zone.
        That qex encoding is what the lambda functions do.
        Contrast the lambdas in the dictionary _qex_decoder().
        Those do the inverse, decoding the qex into the base 256 exponent.

        Example:  assert '0q82_01' == Number(1.0).qstring()
        Example:  assert '0q82_03243F6A8885A3' == Number(math.pi).qstring()

        float precision
        ---------------
        A "qigit" is a qiki Number byte, or base-256 digit.
        Number(float) defaults to 8 qigits, for lossless representation of a Python float.
        IEEE 754 double precision has a 53-bit significand (52 bits stored + 1 implied).
        SEE:  http://en.wikipedia.org/wiki/Double-precision_floating-point_format
        Why are 8 qigits needed to store 53 bits, not 7?
        That is because the most significant qigit may not store a full 8 bits, it may store as few as 1.
        So 8 qigits can store 57-64 bits, the minimum needed to store 53.
        Example, 1.2 == 0q82_0133333333333330 stores 1+8+8+8+8+8+8+4 = 53 bits in 8 qigits.
        """
        if qigits is None or qigits <= 0:
            qigits = self.QIGITS_PRECISION_DEFAULT

        smurf = self.SMALLEST_UNREASONABLE_FLOAT

        if math.isnan(x):  self.raw =                  self.RAW_NAN
        elif x >= smurf:   self.raw =                  self._raw_unreasonable_float(x)
        elif x >=  1.0:    self.raw =                  self._raw_from_float(x, lambda e: 0x81 + e, qigits)
        elif x >   0.0:    self.raw = bytes(b'\x81') + self._raw_from_float(x, lambda e: 0xFF + e, qigits)
        elif x ==  0.0:    self.raw =                  self.RAW_ZERO
        elif x >  -1.0:    self.raw = bytes(b'\x7E') + self._raw_from_float(x, lambda e: 0x00 - e, qigits)
        elif x > -smurf:   self.raw =                  self._raw_from_float(x, lambda e: 0x7E - e, qigits)
        else:              self.raw =                  self._raw_unreasonable_float(x)

    @classmethod
    def _raw_unreasonable_float(cls, x):
        """Handle a float that is too big to handle."""
        if x == float('+inf'):
            return cls.RAW_INFINITY
        elif x == float('-inf'):
            return cls.RAW_INFINITY_NEG
        else:
            raise cls.LudicrousNotImplemented(
                "Floating point {}, a Ludicrous number, is not yet implemented.".format(x)
            )

    @staticmethod
    def _raw_from_float(x, qex_encoder, qigits):
        """
        Convert nonzero float to internal raw format.

        :param x:            the float to convert
        :param qex_encoder:  function encodes the qex from the base-256 exponent
        :param qigits:       number of base-256 digits for the qan
        :return:             raw string
        """
        (significand_base_2, exponent_base_2) = math.frexp(x)
        assert x == significand_base_2 * 2.0**exponent_base_2
        assert 0.5 <= abs(significand_base_2) < 1.0

        (exponent_base_256, zero_to_seven) = divmod(exponent_base_2+7, 8)
        significand_base_256 = significand_base_2 * (2 ** (zero_to_seven-7))
        assert x == significand_base_256 * 256.0**exponent_base_256
        assert 0.00390625 <= abs(significand_base_256) < 1.0

        rounder = +0.5 if x >= 0 else -0.5
        qan_integer = int(significand_base_256 * exp256(qigits) + rounder)
        qan00 = pack_integer(qan_integer, qigits)
        qan = right_strip00(qan00)

        qex_integer = qex_encoder(exponent_base_256)
        qex = six.int2byte(qex_integer)

        return qex + qan

    class LudicrousNotImplemented(NotImplementedError):
        """
        Until Ludicrous Numbers are implemented, they should raise this.

        e.g. Number(2**1000)
        e.g. Number(-2.0 ** -1000.0)
        """

    def _from_complex(self, c):
        """Fill in raw from a complex number."""
        self._from_float(c.real)
        self.raw = self.plus_suffix(Suffix.Type.IMAGINARY, type(self)(c.imag)).raw
        # THANKS:  Call constructor if subclassed, http://stackoverflow.com/a/14209708/673991

    # "to" conversions:  Number --> other type
    # ----------------------------------------
    def qstring(self, underscore=1):
        """
        Output Number as a qstring.  0q82_2A for Number(42)

        assert '0q82_01' == Number(1).qstring()
        assert '0q82_2A' == Number(42).qstring()
        assert '0q85_12345678' == Number(0x12345678).qstring()

        Qstring is a human-readable form of the raw representation of a qiki number
        Similar to 0x12AB for hexadecimal
        Except q for x, underscores optional, and of course the value interpretation differs.
        """
        error_tag = ""
        if underscore == 0:
            return_value = '0q' + self.hex()
        else:
            try:
                unsuffixed = self.unsuffixed
            except Suffix.RawError:
                unsuffixed = self
                error_tag = "!?"
            length = len(unsuffixed.raw)
            if length == 0:
                offset = 0
            elif six.indexbytes(self.raw, 0) in (0x7E, 0x7F, 0x80, 0x81):
                offset = 2
            else:
                offset = 1
                # TODO:  ludicrous numbers have bigger offsets (for googolplex it is 64)
            h = hex_from_bytes(unsuffixed.raw)
            if length <= offset:
                return_value = '0q' + h
            else:
                return_value = '0q' + h[ : 2*offset] + '_' + h[2*offset : ]
            for suffix in self.suffixes:
                return_value += '__'
                return_value += suffix.qstring(underscore)
        return return_value + error_tag

    def __int__(self):
        """Convert to an integer."""
        return self._int_zone_dict[self.zone](self)

    _int_zone_dict =  {
        Zone.TRANSFINITE:         lambda self: self._int_cant_be_positive_infinity(),
        Zone.LUDICROUS_LARGE:     lambda self: self._to_int_positive(),
        Zone.POSITIVE:            lambda self: self._to_int_positive(),
        Zone.FRACTIONAL:          lambda self: 0,
        Zone.LUDICROUS_SMALL:     lambda self: 0,
        Zone.INFINITESIMAL:       lambda self: 0,
        Zone.ZERO:                lambda self: 0,
        Zone.INFINITESIMAL_NEG:   lambda self: 0,
        Zone.LUDICROUS_SMALL_NEG: lambda self: 0,
        Zone.FRACTIONAL_NEG:      lambda self: 0,
        Zone.NEGATIVE:            lambda self: self._to_int_negative(),
        Zone.LUDICROUS_LARGE_NEG: lambda self: self._to_int_negative(),
        Zone.TRANSFINITE_NEG:     lambda self: self._int_cant_be_negative_infinity(),
        Zone.NAN:                 lambda self: self._int_cant_be_nan(),
    }

    @classmethod
    def _int_cant_be_positive_infinity(cls):
        """Handle integer positive infinity."""
        raise cls.IntOverflowError("Positive Infinity cannot be represented by integers.")

    @classmethod
    def _int_cant_be_negative_infinity(cls):
        """Handle integer negative infinity."""
        raise cls.IntOverflowError("Negative Infinity cannot be represented by integers.")

    class IntOverflowError(OverflowError):
        """Python int has no sane way to represent infinity.  Example int(Number.POSITIVE_INFINITY)"""

    @staticmethod
    def _int_cant_be_nan():
        """Handle integer NAN."""
        raise ValueError("Not-A-Number cannot be represented by integers.")

    def _to_int_positive(self):
        """
        To a positive integer.

        Only the unsuffixed part is converted, otherwise suffix bytes
        might get interpreted as part of the qan value.
        """
        n = self.normalized()
        (qan_int, qan_len) = n.qan_int_len()
        qex = n.base_256_exponent() - qan_len
        return shift_leftward(qan_int, qex*8)

    def _to_int_negative(self):
        """To a negative integer."""
        (qan_int, qan_len) = self.qan_int_len()
        qex = self.base_256_exponent() - qan_len
        qan_negative = qan_int - exp256(qan_len)
        the_int = shift_leftward(qan_negative, qex*8)
        if qex < 0:
            extraneous_mask = exp256(-qex) - 1
            extraneous = qan_negative & extraneous_mask
            if extraneous != 0:
                the_int += 1   # XXX:  Find a more graceful way to floor to 0 instead of to -inf
        return the_int

    if six.PY2:
        def __long__(self):
            """To a long int."""
            # noinspection PyCompatibility,PyUnresolvedReferences
            return long(self.__int__())

    def __complex__(self):
        """To a complex number."""
        return complex(float(self.real), float(self.imag))

    def __float__(self):
        """To a floating point number."""
        if self.is_complex():
            raise TypeError("{} has an imaginary part, use float(n.real) or complex(n) instead of float(n)".format(
                self.qstring()
            ))
        return self._float_zone_dict[self.zone](self)

    _float_zone_dict =  {
        Zone.TRANSFINITE:         lambda self: float('+inf'),
        Zone.LUDICROUS_LARGE:     lambda self: float('+inf'),
        Zone.POSITIVE:            lambda self: self._to_float(),
        Zone.FRACTIONAL:          lambda self: self._to_float(),
        Zone.LUDICROUS_SMALL:     lambda self: 0.0,
        Zone.INFINITESIMAL:       lambda self: 0.0,
        Zone.ZERO:                lambda self: 0.0,
        Zone.INFINITESIMAL_NEG:   lambda self: -0.0,
        Zone.LUDICROUS_SMALL_NEG: lambda self: -0.0,
        Zone.FRACTIONAL_NEG:      lambda self: self._to_float(),
        Zone.NEGATIVE:            lambda self: self._to_float(),
        Zone.LUDICROUS_LARGE_NEG: lambda self: float('-inf'),
        Zone.TRANSFINITE_NEG:     lambda self: float('-inf'),
        Zone.NAN:                 lambda self: float('nan')
    }

    def _to_float(self):
        """To a reasonable, nonzero floating point number."""
        try:
            qex = self.base_256_exponent()
        except ValueError:
            return 0.0
        (qan_int, qan_len) = self.qan_int_len(max_qigits=self.QIGITS_PRECISION_DEFAULT + 2)
        # NOTE:  The +2 gives slightly less inaccurate rounding on e.g. 0q82_01000000000000280001
        if self.raw < self.RAW_ZERO:
            qan_int -= exp256(qan_len)
            if qan_len > 0 and qan_int >= - exp256(qan_len-1):
                (qan_int, qan_len) = (-1, 1)
        else:
            if qan_len == 0 or qan_int <=  exp256(qan_len-1):
                (qan_int, qan_len) = (1, 1)
        exponent_base_2 = 8 * (qex - qan_len)
        return math.ldexp(float(qan_int), exponent_base_2)

    def qan_int_len(self, max_qigits=None):
        """Extract the base-256 significand in integer form.  And its length.

        That is, return a tuple of the integer form of the qan, and the number of qigits it contains.

        max_qigits limits how many qigits.  (None means no limit.)

        The number of qigits may be up to the number of bytes in the raw qan.
        It is unrelated to the location of the radix point,
        which may be between any qigits, and may be outside the qan integer.
        """
        raw_qan = self.qan_raw(max_qigits=max_qigits)
        qan_int = unpack_big_integer(raw_qan)
        return tuple((qan_int, len(raw_qan)))

    def qan_raw(self, max_qigits=None):
        """The qan in raw, base-256 bytes."""
        # TODO:  unit test
        unsuffixed_raw = self.unsuffixed.raw
        offset = self.qan_offset()
        if max_qigits is None:
            return unsuffixed_raw[offset : ]
        else:
            return unsuffixed_raw[offset : offset + max_qigits]


    def qex_raw(self):
        """The qex in raw bytes"""
        # TODO:  Any way in the world a suffix can impinge upon the qex the way it can upon the qan?  On the zone?!
        # TODO:  unit test
        return self.raw[ : self.qan_offset()]

    def qan_offset(self):
        """The offset into self.raw of the qan."""
        # TODO:  unit test
        try:
            qan_offset = self.__qan_offset_dict[self.zone]
        except KeyError:
            raise self.QanValueError("qan not defined for {qstring}".format(qstring=self.qstring()))
        return qan_offset

    class QanValueError(ValueError):
        """Qan for an unsupported zone raises this.  Trivial cases too, e.g. Number.ZERO.qan_int_len()"""

    __qan_offset_dict = {
        Zone.POSITIVE:       1,
        Zone.FRACTIONAL:     2,
        Zone.FRACTIONAL_NEG: 2,
        Zone.NEGATIVE:       1,
    }   # TODO:  ludicrous numbers will have a qan too (offset 4,8,16,...)

    def base_256_exponent(self):
        """
        The base-256 exponent, when you interpret the qan in the range [0...1)

        (The range of values for the qan is actually [0.00390625...1).
        The qan never represents a number smaller than 1/256.0.
        Just like the mantissa of an IEEE floating point number never represents
        a number smaller than 0.5.)

        So this function returns
            2 for a number in the range [    256...65536)
            1 for                       [      1...256)
            0 for                       [  1/256...1)
           -1 for                       [1/65536...1/256)

        Raise QexValueError for 0 or unreasonable numbers.
        """
        try:
            decoder = self._qex_decoder[self.zone]
        except KeyError:
            raise self.QexValueError("qex not defined for {}".format(repr(self)))

        try:
            return decoder(self)
        except IndexError:
            # TODO:  Unit test this branch.
            #        It may not be possible without breaking the .zone() method,
            #        because Zone.POSITIVE must have at least one byte,
            #        and Zone.FRACTIONAL must have at least two.
            raise self.QexValueError("qex broken for {}".format(repr(self)))

    class QexValueError(ValueError):
        """There is no qex for some zones, e.g. Number.ZERO.base_256_exponent()"""

    # _qex_decoder contains zone-specific converter functions.
    # Each lambda function in the following dictionary performs this conversion:
    #
    #     base 256 exponent <-- qex
    #
    # Contrast _from_float() which has lambdas that convert the other way.
    _qex_decoder = {
        Zone.POSITIVE:       lambda self:         six.indexbytes(self.raw, 0) - 0x81,
        Zone.FRACTIONAL:     lambda self:         six.indexbytes(self.raw, 1) - 0xFF,
        Zone.FRACTIONAL_NEG: lambda self:  0x00 - six.indexbytes(self.raw, 1),
        Zone.NEGATIVE:       lambda self:  0x7E - six.indexbytes(self.raw, 0),
    }   # TODO:  ludicrous numbers will encode the exponents differently.

    def hex(self):
        """Like the printable qstring() but simpler (no 0q prefix, no underscores).

        assert '822A' == Number('0q82_2A').hex()
        """
        return hex_from_bytes(self.raw)

    def x_apostrophe_hex(self):
        """
        Encode raw value into a string that MySQL understands:  x'8201'

        assert "x'8201'" == Number(1).x_apostrophe_hex()
        """
        return "x'" + self.hex() + "'"

    def zero_x_hex(self):
        """
        Hexadecimal literal for the entire raw string as a big integer.

        (But NOT the integer the number represents.)

        Based on C,C++,Java,JavaScript,etc. syntax.
        """
        return "0x" + self.hex()

    def ditto_backslash_hex(self):
        """
        Encode raw value into a string that C or Python understands:  "\x82\x01"

        assert r'"\x82\x01"' == Number(1).ditto_backslash_hex()
        """
        hex_digits = self.hex()
        escaped_hex_pairs = [r'\x' + hex_digits[i:i+2] for i in range(0, len(hex_digits), 2)]
        # THANKS:  Split string into pairs, http://stackoverflow.com/a/9475354/673991
        return '"' + ''.join(escaped_hex_pairs) + '"'

    mysql_string = x_apostrophe_hex
    c_string = ditto_backslash_hex

    # Zone Determination
    # ------------------
    @property
    def zone(self):
        """Get the Zone code for this Number.  Works whether _zone is among the __slots__ or not."""
        try:
            return self._zone
        except AttributeError:
            '''Benign, this happens if _zone is missing from __slots__'''
            return self._zone_from_raw(self.raw)

    def _zone_setter(self):
        """Set the _zone property for this Number, if allowed by __slots__."""
        try:
            self._zone = self._zone_from_raw(self.raw)
        except AttributeError:
            '''Benign, this happens if _zone is missing from __slots__'''

    @staticmethod
    def _zone_from_raw(raw):
        """
        Compute the Zone code for a Number, based on its raw value.

        Uses a vaguely binary tree of comparisons of raw byte strings.
        At most 4 comparisons.  Common numbers have 2 or 3 comparisons.
        """
        if raw > Zone.ZERO:
            if raw >= Zone.POSITIVE:
                if raw >= Zone.LUDICROUS_LARGE:
                    if raw >= Zone.TRANSFINITE:
                        return                  Zone.TRANSFINITE
                    else:
                        return                  Zone.LUDICROUS_LARGE
                else:
                    return                      Zone.POSITIVE
            else:
                if raw >= Zone.FRACTIONAL:
                    return                      Zone.FRACTIONAL
                elif raw >= Zone.LUDICROUS_SMALL:
                    return                      Zone.LUDICROUS_SMALL
                else:
                    return                      Zone.INFINITESIMAL
        elif raw == Zone.ZERO:
            return                              Zone.ZERO
        else:
            if raw > Zone.FRACTIONAL_NEG:
                if raw >= Zone.LUDICROUS_SMALL_NEG:
                    if raw >= Zone.INFINITESIMAL_NEG:
                        return                  Zone.INFINITESIMAL_NEG
                    else:
                        return                  Zone.LUDICROUS_SMALL_NEG
                else:
                    return                      Zone.FRACTIONAL_NEG
            else:
                if raw >= Zone.NEGATIVE:
                    return                      Zone.NEGATIVE
                elif raw >= Zone.LUDICROUS_LARGE_NEG:
                    return                      Zone.LUDICROUS_LARGE_NEG
                elif raw >= Zone.TRANSFINITE_NEG:
                    return                      Zone.TRANSFINITE_NEG
                else:
                    return                      Zone.NAN

    # TODO:  Alternative suffix syntax
    #                     n.suffixes() === n.parse_suffixes()[1:]
    #                           n.root === n.parse_suffixes()[0]
    #        n.add(Suffix(...))        === n = n.plus_suffix(...)
    #        n.suffixes += Suffix(...) === n = n.plus_suffix(...)
    #        n          += Suffix(...) === n = n.plus_suffix(...)
    #        n.remove(Suffix(...))     === n = n.minus_suffix(...)
    #        n.suffixes -= Suffix(...) === n = n.minus_suffix(...)
    #        n          -= Suffix(...) === n = n.minus_suffix(...)
    #        Number(n, *[suffix for suffix in n.suffixes() if suffix.type != t])
    #                                  === n.minus_suffix(t)
    #        s = n.suffixes(); s.remove(t); m = Number(n.root, s)
    #                                  === m = n.minus_suffix(t)
    #                    n - Suffix(t) === n.minus_suffix(t)

    def is_suffixed(self):
        """Does this Number have any suffixes?"""
        try:
            return six.indexbytes(self.raw, -1) == Suffix.TERMINATOR
            # NOTE:  This would be less sneaky if the internal representation kept suffixes in a list.
        except IndexError:
            '''Well it has no bytes at all.  So no.'''
            return False
        # TODO:  is_suffixed(self, type)?

    def plus_suffix(self, suffix_or_type=None, payload=None):
        """
        Add a suffix to this Number.  Does not mutate self, but returns a new suffixed number.

        Forms:
            m = n.plus_suffix(Number.Suffix.Type.TEST, b'byte string')
            m = n.plus_suffix(Number.Suffix.Type.TEST, Number(x))
            m = n.plus_suffix(Number.Suffix(...))
            m = n.plus_suffix()
        """
        assert (
            isinstance(suffix_or_type, int) and isinstance(payload, six.binary_type) or
            isinstance(suffix_or_type, int) and payload is None or
            isinstance(suffix_or_type, int) and isinstance(payload, Number) or
            isinstance(suffix_or_type, Suffix) and payload is None or
            suffix_or_type is None and payload is None
        ), "Bad call to plus_suffix({suffix_or_type}, {payload})".format(
            suffix_or_type=repr(suffix_or_type),
            payload=repr(payload),
        )
        if self.is_nan():
            # TODO:  Is this really so horrible?  A suffixed NAN?  e.g. 0q__7F0100
            raise Suffix.RawError("Number.NAN may not be suffixed.")
        if isinstance(suffix_or_type, Suffix):
            the_suffix = suffix_or_type
            return self.from_raw(self.raw + the_suffix.raw)
        else:
            the_type = suffix_or_type
            suffix = Suffix(the_type, payload)
            return self.plus_suffix(suffix)

    def minus_suffix(self, old_type=None):
        """
        Make a version of a number without any suffixes of the given type.
        This does not mutate self.  Returns a new Number instance.
        """
        # TODO:  A way to remove just ONE suffix of the given type?
        #        minus_suffix(t) for one, minus_suffixes(t) for all?
        #        minus_suffix(t, global=True) for all?
        #        minus_suffix(t, count=1) for one?
        new_number = self.unsuffixed
        any_deleted = False
        for suffix in self.suffixes:
            if suffix.type_ == old_type:
                any_deleted = True
            else:
                new_number = new_number.plus_suffix(suffix.type_, suffix.payload)
        if not any_deleted:
            raise Suffix.NoSuchType("Number {} had no suffix type {:02x}".format(self.qstring(), old_type))
        return new_number

    def suffix(self, sought_type):
        """Get suffix by type.  Only sees the first (left-most) suffix of a type."""
        for suffix in self.suffixes:
            if suffix.type_ == sought_type:
                return suffix
        raise Suffix.NoSuchType("Number {qstring} has no suffix type {sought_type:02x}".format(
            qstring=self.qstring(),
            sought_type=sought_type
        ))

    # noinspection SpellCheckingInspection
    @property
    def unsuffixed(self):
        """Get the Number minus all suffixes."""

        # TODO:  Less vacuous names.
        #            for Suffix (the thing)
        #            for Number.unsuffixed() (a number without any things)
        #        Objectives:
        #            Harder to misunderstand, or conflate.
        #            Easier to search for.
        #        root alternatives:
        #            unsuffixed
        #            core
        #            apex
        #            base
        #            crux
        #            pith   <===
        #            gist
        #            stem   <=== (if Suffix changes to leaf)
        #            trunk  (also if Suffix changes to leaf)
        #            pit
        #            tigo (esperanto word for stem)
        #                ((except there's a tigoenergy.com, solar and stuff))
        #            kofro (esperanto word for trunk, but as in chest, not tree trunk)
        #            radiko (esperanto for root)
        #            radish
        #               hmm, like radix which is latin for root,
        #               but that conventionally means something different, aka base
        #        Maybe "suffix" is vacuous and misunderstandable too.  Need a new name for that.
        #        suffix alternatives:
        #            pod
        #            pac
        #            fix
        #            extension
        #            attachment
        #            augmentation
        #            aug
        #            adjoin (not to be confused with adjective, which could be a word thing)
        #            annex
        #            accession
        #            accretion
        #            ps
        #            addendum
        #            amendment
        #            supplemental
        #            additive
        #            extra
        #            add-on
        #            spice
        #            endowment
        #            boon
        #            complement
        #            extra
        #            perk
        #            perq   <===
        #            bonus
        #            fringe
        #            lagniappe
        #            secret passage
        #            leaf    <===   (leading to "leafless" number) (ala tree leaf, table leaf)
        #            branch
        #            arm
        #            folio (esperanto for leaf, Latin is folium)
        #            bai (Lao for leaf)
        #            blat (Luxembourgish for leaf)
        #        root/leaf (aka root/suffix) alternatives:
        #            rot/blad (swedish and norwegian for root/leaf) (blad also means blade)
        #            rod/blad (danish)
        #            rot/lauf (icelandic) (lauf also means run)
        #            wurzel/blatt (german) (stamm means stem)
        #            wortel/blad (dutch)
        #            juur/leht (estonian)
        #            sakne/lapu (latvian)
        #            saknis/lapelis (lithuanian)
        #            hak/bai (lao)
        #            blat/vortsl (yiddish)
        #            radish/lettuce
        #            rad/fol (shortened versions of Latin and Esperanto for root/leaf)
        #            leups/wrdha (leaf/root in proto-Indo-European, the shorter versions anyway)
        #            raiz/hoja (spanish)
        #            koren/list (russian, macedonian)
        #            Gen/yezi (chinese)
        #            mzizi/jani (swahili)
        #            rut/aku (telugu)
        #            erroa/hostoa (basque) nope, those don't have any confusing associations
        #            riza/fyllo (greek)
        #        Then what's the better word for the PAYLOAD of the suffix??
        #            the thing other than the "type" and the length, and the packing 00-byte
        # Criteria for naming:
        #     (10) unique in technology (e.g. `root` and `tag` are too common)
        #     (2) pronouncable by English speaker
        #     (2) no need to spell it out
        #     (2) memorable
        #     (1) brief
        #     (1) bland or abstract
        #     (1) English word, so PyCharm won't flag it
        #     (1) initial-letter distinct: word-parts i,s,v,o,n,t,w
        #     (0.5) informal (not stuffy)
        #     (0.5) obvious plural
        #     (0.5) distinct from word-parts, because it's so different
        #     (0.1) funny

        index_unsuffixed_end = len(self.raw)
        for index_unsuffixed_end in self._suffix_indexes_backwards():
            '''Find the FIRST suffix index, i.e. the LAST one backwards.'''
        return self.from_raw(self.raw[ : index_unsuffixed_end])

    @property
    def suffixes(self):
        """A list of Suffix objects, the Number's suffixes in order from left-to-right."""

        def suffixes_backwards():
            """Generate the Suffix objects from this Number, right-to-left."""
            last_suffix_index = len(self.raw)
            for suffix_index in self._suffix_indexes_backwards():
                index_type = last_suffix_index - 3
                if index_type >= suffix_index:
                    type_ = six.indexbytes(self.raw, index_type)
                    payload = self.raw[suffix_index : index_type]
                    yield Suffix(type_, payload)
                else:
                    yield Suffix()
                last_suffix_index = suffix_index

        return list(reversed(list(suffixes_backwards())))

    def _suffix_indexes_backwards(self):
        """
        Find the starting indexes of all the suffixes.  Last first, that is right-to-left.

        Returns an iterator of values each in range(len(self.raw)).
        Suffix indexes are yielded in REVERSE ORDER
        because we have to parse the terminators and lengths from the right end.
        """
        index_end = len(self.raw)
        if index_end > 0:
            # NOTE:  This if-test removes the unsuffixed NAN possibility, which is legit of course.
            #        From now on index_terminator should never underflow,
            #        because we don't allow NAN to be suffixed.
            while True:
                index_terminator = index_end - 1
                if index_terminator < 0:
                    raise Suffix.RawError("Invalid suffix, cannot suffix NAN.")
                maybe_terminator = six.indexbytes(self.raw, index_terminator)
                if maybe_terminator != Suffix.TERMINATOR:
                    return
                index_length = index_end - 2
                if index_length < 0:
                    raise Suffix.RawError("Invalid suffix, length underflow.")
                    # NOTE:  The first byte of raw is a terminator, so there's no room for a length byte.
                length = six.indexbytes(self.raw, index_length)
                index_end = index_length - length
                if index_end < 0:
                    raise Suffix.RawError("Invalid suffix, payload overflow.")
                    # NOTE:  The length indicates a payload that extends beyond the start of the raw byte string.
                yield index_end

    # Constants named for convenience
    # ---------
    NAN = None   # NAN stands for Not-a-number, Ass-is-out-of-range, Nullificationalized.
    ZERO = None   # No ambiguity here, none, zip zed zilch.
    POSITIVE_INFINITY = None        # Omega.  No wait Aleph-zero and (or/xor) or Omega.
    POSITIVE_INFINITESIMAL = None   # Epsilon-zero
    NEGATIVE_INFINITESIMAL = None
    NEGATIVE_INFINITY = None

    @classmethod
    def internal_setup(cls):
        """Initialize Number constants after the Number class is defined."""
        cls.NAN                    = cls.from_raw(cls.RAW_NAN)    # Number(None)
        cls.ZERO                   = cls.from_raw(cls.RAW_ZERO)   # Number(0)
        cls.POSITIVE_INFINITY      = cls.from_raw(cls.RAW_INFINITY)
        cls.POSITIVE_INFINITESIMAL = cls.from_raw(cls.RAW_INFINITESIMAL)
        cls.NEGATIVE_INFINITESIMAL = cls.from_raw(cls.RAW_INFINITESIMAL_NEG)
        cls.NEGATIVE_INFINITY      = cls.from_raw(cls.RAW_INFINITY_NEG)


def flatten(things, destination_list=None):
    """
    Flatten a nested container into a list.

    THANKS:  List nested irregularly, http://stackoverflow.com/q/2158395/673991
    THANKS:  List nested exactly 2 levels, http://stackoverflow.com/a/40252152/673991
    """
    # TODO:  Unit test.  Or get rid of it?  Or use it in word.LexMySQL._super_parse()?
    # TODO:  Make a version with no recursion and full yield pass-through.
    if destination_list is None:
        destination_list = []
    for thing in things:
        # TODO:  Use is_iterable(), now in word.py.
        try:
            0 in thing
        except TypeError:
            destination_list.append(thing)
        else:
            flatten(thing, destination_list)
    return destination_list
assert [1,2,3,4,'five',6,7,8] == list(flatten([1,(2,[3,(4,{'five'}),6],7),8]))


# noinspection PyProtectedMember
Number.internal_setup()
assert Number.NAN.raw == Number.RAW_NAN


# Set Logic (for testing ZoneSet instances)
# ---------
def sets_exclusive(*sets):
    """Are these sets mutually exclusive?  Is every member unique?"""
    for each_index in range(len(sets)):
        for each_preceding_index in range(each_index):
            members_in_both = sets[each_index].intersection(sets[each_preceding_index])
            if len(members_in_both) > 0:
                return False
    return True
assert  True is sets_exclusive({1,2,3}, {4,5,6}, {7, 8, 9})
assert False is sets_exclusive({1,2,3}, {4,5,6}, {6, 7, 8})


def union_of_distinct_sets(*sets):
    """Return the union of these sets.  There must be no overlapping members."""
    assert sets_exclusive(*sets), "Sets not mutually exclusive:  %s" % repr(sets)
    return set.union(*sets)
assert {1,2,3,4,5,6} == union_of_distinct_sets({1,2,3}, {4,5,6})


class ZoneSet(object):
    """Sets of Zones, for categorizing Numbers."""
    # TODO:  Venn Diagram or table or something.
    # TODO:  is_x() routine for each zone set X
    #        e.g. is_reasonable() based on ZoneSet.REASONABLE

    ALL = {
        Zone.TRANSFINITE,
        Zone.LUDICROUS_LARGE,
        Zone.POSITIVE,
        Zone.FRACTIONAL,
        Zone.LUDICROUS_SMALL,
        Zone.INFINITESIMAL,
        Zone.ZERO,
        Zone.INFINITESIMAL_NEG,
        Zone.LUDICROUS_SMALL_NEG,
        Zone.FRACTIONAL_NEG,
        Zone.NEGATIVE,
        Zone.LUDICROUS_LARGE_NEG,
        Zone.TRANSFINITE_NEG,
        Zone.NAN,
    }

    # The basic way to group the zones:  REASONABLE, LUDICROUS, NONFINITE
    REASONABLE = {
        Zone.POSITIVE,
        Zone.FRACTIONAL,
        Zone.ZERO,
        Zone.FRACTIONAL_NEG,
        Zone.NEGATIVE,
    }
    LUDICROUS = {
        Zone.LUDICROUS_LARGE,
        Zone.LUDICROUS_SMALL,
        Zone.LUDICROUS_SMALL_NEG,
        Zone.LUDICROUS_LARGE_NEG,
    }
    NONFINITE = {
        Zone.TRANSFINITE,
        Zone.INFINITESIMAL,
        Zone.INFINITESIMAL_NEG,
        Zone.TRANSFINITE_NEG,
    }

    # Other ways to group the zones
    FINITE = union_of_distinct_sets(
        LUDICROUS,
        REASONABLE,
    )
    UNREASONABLE = union_of_distinct_sets(
        LUDICROUS,
        NONFINITE,
    )
    POSITIVE = {
        Zone.TRANSFINITE,
        Zone.LUDICROUS_LARGE,
        Zone.POSITIVE,
        Zone.FRACTIONAL,
        Zone.LUDICROUS_SMALL,
        Zone.INFINITESIMAL,
    }
    NEGATIVE = {
        Zone.INFINITESIMAL_NEG,
        Zone.LUDICROUS_SMALL_NEG,
        Zone.FRACTIONAL_NEG,
        Zone.NEGATIVE,
        Zone.LUDICROUS_LARGE_NEG,
        Zone.TRANSFINITE_NEG,
    }
    NONZERO = union_of_distinct_sets(
        POSITIVE,
        NEGATIVE,
    )
    ZERO = {
        Zone.ZERO
    }

    # Some interesting Venn overlaps
    ESSENTIALLY_POSITIVE_ZERO = {
        Zone.LUDICROUS_SMALL,
        Zone.INFINITESIMAL,
    }
    ESSENTIALLY_NEGATIVE_ZERO = {
        Zone.INFINITESIMAL_NEG,
        Zone.LUDICROUS_SMALL_NEG,
    }
    ESSENTIALLY_NONNEGATIVE_ZERO = union_of_distinct_sets(
        ESSENTIALLY_POSITIVE_ZERO,
        ZERO,
    )
    ESSENTIALLY_ZERO = union_of_distinct_sets(
        ESSENTIALLY_NONNEGATIVE_ZERO,
        ESSENTIALLY_NEGATIVE_ZERO,
    )
    REASONABLY_POSITIVE = {
        Zone.POSITIVE,
        Zone.FRACTIONAL,
    }
    REASONABLY_NEGATIVE = {
        Zone.FRACTIONAL_NEG,
        Zone.NEGATIVE,
    }
    REASONABLY_NONZERO = union_of_distinct_sets(
        REASONABLY_POSITIVE,
        REASONABLY_NEGATIVE,
    )
    UNREASONABLY_BIG = {
        Zone.TRANSFINITE,
        Zone.LUDICROUS_LARGE,
        Zone.LUDICROUS_LARGE_NEG,
        Zone.TRANSFINITE_NEG,
    }

    # TODO:  Maybe REASONABLY_ZERO  could include      infinitesimals and ludicrously small and zero
    #          and ESSENTIALLY_ZERO could include just infinitesimals                       and zero
    # Except then REASONABLY_ZERO overlaps UNREASONABLE (the ludicrously small).
    # Confusing because then epsilon is both reasonable and unreasonable?
    # And it's not interesting to say that ludicrously small numbers are not reasonably zero.
    #     They kind of totally are.
    # That's why the term ESSENTIALLY was introduced, because it's distinct from REASONABLY.
    #     So that's that, no REASONABLY_ZERO because it'd be confusing or useless.
    # But then there's a REASONABLY_NONZERO and no REASONABLY_ZERO.  Is that confusing?

    # If not sufficiently confusing, we could also define
    #     a REASONABLY_INFINITE set as ludicrously large plus transfinite.
    #     Nah that's UNREASONABLY_BIG
    #     There's nothing "reasonable" about infinity.
    # How about ESSENTIALLY_INFINITE as just +/- transfinite. (excluding ludicrously large)
    #     The same as a TRANSFINITE set would be.
    #     (But not NONFINITE, as that includes infinitesimals.)

    WHOLE_NO = {
        Zone.FRACTIONAL,
        Zone.LUDICROUS_SMALL,
        Zone.INFINITESIMAL,
        Zone.INFINITESIMAL_NEG,
        Zone.LUDICROUS_SMALL_NEG,
        Zone.FRACTIONAL_NEG,
    }
    WHOLE_YES = {
        Zone.ZERO,
    }
    WHOLE_MAYBE = {
        Zone.LUDICROUS_LARGE,
        Zone.POSITIVE,
        Zone.NEGATIVE,
        Zone.LUDICROUS_LARGE_NEG,
    }
    WHOLE_INDETERMINATE = {
        Zone.TRANSFINITE,
        Zone.TRANSFINITE_NEG,
    }

    NAN = {
        Zone.NAN
    }

    # Sets of Zone Sets
    # -----------------
    # Different ways to slice the pie.
    # Each of these sets are MECE, mutually exclusive and collectively exhaustive.
    # Each is identical to ZoneSet.ALL.
    # For documentation and testing.

    _ALL_BY_SOME_KIND_OF_BASIC_WAY = union_of_distinct_sets(
        REASONABLE,
        LUDICROUS,
        NONFINITE,
        NAN,
    )

    _ALL_BY_REASONABLENESS = union_of_distinct_sets(
        REASONABLE,
        UNREASONABLE,
        NAN,
    )
    _ALL_BY_FINITENESS = union_of_distinct_sets(
        FINITE,
        NONFINITE,
        NAN,
    )
    _ALL_BY_ZERONESS = union_of_distinct_sets(
        NONZERO,
        ZERO,
        NAN,
    )
    _ALL_BY_BIGNESS = union_of_distinct_sets(
        ESSENTIALLY_ZERO,
        REASONABLY_NONZERO,
        UNREASONABLY_BIG,
        NAN,
    )
    _ALL_BY_WHOLENESS = union_of_distinct_sets(
        WHOLE_NO,
        WHOLE_YES,
        WHOLE_MAYBE,
        WHOLE_INDETERMINATE,
        NAN,
    )


def byte(integer):
    """
    Convert integer to a one-character byte-string

    Similar to chr(), except in Python 3 produce bytes() not str()
    Same as pack_integer(integer, num_bytes=1)
    """
    return six.binary_type(bytearray((integer,)))
assert b'A' == byte(65)


class Suffix(object):
    # SEE:  Alternative names for Suffix at Number.unsuffixed()
    """
    A Number can have suffixes.  E.g. complex numbers.  E.g. alternate ID spaces.

    Format of a nonempty suffix (uppercase letters represent hexadecimal digits):
        PP...PP _ TT LL 00
    where:
        PP...PP - 1-byte to 250-byte payload (Never 0-byte -- suffixing NAN is not allowed)
         _ - underscore is a conventional qstring delimiter between payload and type-length-zero
        TT - type code of the suffix, 0x00 to 0xFF or absent
        LL - length, number of bytes, including the type and payload, 0x00 to 0xFA
             but not including the length itself nor the zero-tag (see empty suffix)
        00 - the zero-tag, this indicates presence of the suffix.

    The "empty suffix" is two 00 bytes:
        0000

        That is like saying LL is 00, meaning the type is missing and the payload is empty.
        (It is not the same as type 00, which is otherwise available.)

    The zero-tag is what indicates there is a suffix.
    This is why an unsuffixed number has all its right-end 00-bytes stripped.

    A number can have multiple suffixes.
    If the payload of a suffix is itself a number, suffixes could be nested.

    Instance properties:
        payload - byte string
        type_ - integer 0x00 to 0xFF type code of suffix, or None for the empty suffix
        length_of_payload_plus_type - integer value of length byte, 0 to MAX_PAYLOAD_LENGTH
        raw - the encoded byte string suffix, including payload, type, length, and zero-tag

    Example:
        assert '778899_110400' == Number.Suffix(type_=0x11, payload=b'\x77\x88\x99').qstring()
    """
    # TODO:  Another name for type TT.  Alternatives:
    # CC class (haha no)
    # (Make them both apply by subclassing Suffix, and each subclass assigns its own whatever-its-called?)
    # (Make it a Number?  Every suffix could be a Number plus a Number/Text/empty payload?)
    #     (Too bad 0q00 is so fundamentally malformed -- that could be the type of the "pad" suffix.)

    MAX_PAYLOAD_LENGTH = 250

    NUM_OVERHEAD = 3
    # This is a class constant so if we ever want to change it we know where to work.
    # In particular, the suffix type may be too limiting at 1 byte.
    # On the other hand we can have the best of both worlds (or the best of EITHER world, more accurately)
    # If we keep this 3 forever, and just have an expanded suffix type (a ONE-BYTE type) that
    # includes a Number subtype in a special part of the payload.
    # And some kind of length to separate it from the rest of the payload.
    # Or maybe the payload is just a series of containers, using the lengthed-export version of Numbers.

    TERMINATOR = 0x00
    # TODO:  Use this everywhere, not literal 00
    #        Not that it could ever change.  More to be able to find where it's used.

    class Type(object):
        """The 3rd byte from the right of a Suffix.  (Except the empty suffix 0000 has no type.)"""
        # TODO:  Move to suffix_type.py?  Because it knows about qiki.Word.Listing, and much more.
        #        Its scope is only going to grow.  Seems wrong buried here somehow.
        # TODO:  Formally define valid payload contents for each type (Number(s), utf8 string, etc.)
        #        or range of types, at least one of which is extensible or something.
        # TODO:  OMG Suffix.Type should be a Lex.
        LISTING   = 0x1D   # 'ID' in 1337, payload
        IMAGINARY = 0x69   # 'i' in ASCII, payload is qiki.Number for imaginary part
        TEST      = 0x7E   # for unit testing, payload can be anything

    # TODO:  math.stackexchange question:  are quaternions a superset of complex numbers?  Does i===i?
    #        Oh well I think the obvious thing to do is to duck the problem.
    #        If a number has 3 imaginary suffixes it's a quaternion. If 7 octonion.
    #        But what to do about split-complex numbers, or dual numbers?  Or biquaternions?
    # SEE:  quaternions from complex, http://math.stackexchange.com/q/1426433/60679
    # SEE:  "k ... same role as ... imaginary", http://math.stackexchange.com/a/1159825/60679
    # SEE:  "...any one of the imaginary components", http://math.stackexchange.com/a/1167326/60679
    # SEE:  https://math.stackexchange.com/q/1916870/60679
    #       what is the relation between quaternions and imaginary numbers?
    #       In particular, Jean Marie's comment "there is no canonical embedding of C in H"
    # TODO:  Support other hyper-complex numbers.
    #        Bicomplex numbers are pairs of complex numbers, e.g. (1+2j,3+4j)
    #        Tessarines are 4-tuple mutants resembling quaternions but where ij == k, jj == +1, etc.
    #        Supposedly they are isomorphic to bicomplex numbers.

    def __init__(self, type_=None, payload=None):
        """Suffix constructor.  Given its one-byte type and multi-byte payload.  Both optional."""
        assert isinstance(type_, (int, type(None)))
        self.type_ = type_
        # TODO:  Another name for type -- tired of that underscore
        if payload is None:
            self.payload = b''
        elif isinstance(payload, Number):
            self.payload = payload.raw
        elif isinstance(payload, six.binary_type):
            self.payload = payload
        else:
            # TODO:  Support Number.Suffix(suffix)?  As a copy constructor, ala Number(number)
            raise self.PayloadError("Suffix payload cannot be a {}".format(type_name(payload)))

        if self.type_ is None:
            assert self.payload == b''
            # TODO:  Raise custom exception on Suffix(type_=None, payload='not empty')
            # TODO:  Unit test this case
            self.length_of_payload_plus_type = 0
            self.raw = (   # The empty suffix:  b'\x00\x00'
                # no payload
                # no type
                byte(self.length_of_payload_plus_type) +
                byte(self.TERMINATOR)
            )
        else:
            self.length_of_payload_plus_type = len(self.payload) + 1
            if self.length_of_payload_plus_type <= self.MAX_PAYLOAD_LENGTH + 1:
                self.raw = (
                    self.payload +
                    byte(self.type_) +                           # \   Here are the
                    byte(self.length_of_payload_plus_type) +     #  >  NUM_OVERHEAD
                    byte(self.TERMINATOR)                        # /   bytes
                )
            else:
                raise self.PayloadError("Suffix payload is {:d} bytes too long.".format(
                    len(self.payload) - self.MAX_PAYLOAD_LENGTH)
                )

    def __eq__(self, other):
        """Are suffixes equal?"""
        try:
            other_type = other.type_
            other_payload = other.payload
        except AttributeError:
            return False
        return self.type_ == other_type and self.payload == other_payload

    def __ne__(self, other):
        """Are suffixes unequal?"""
        eq_result = self.__eq__(other)
        if eq_result is NotImplemented:
            return NotImplemented
        return not eq_result

    def __repr__(self):
        """Source representation of a suffix."""
        if self.type_ is None:
            return "Suffix()"
        else:
            return "Suffix({type_}, b'{payload}')".format(
                type_=repr(self.type_),
                # payload="".join(["\\x{:02x}".format(byte_) for byte_ in self.payload]),
                payload=hex_from_bytes(self.payload),
            )

    def __hash__(self):
        """So Suffixes could be keys of a dict."""
        return hash(self.raw)

    def qstring(self, underscore=1):
        """
        The qstring of a suffix only underscore-separates the payload (if any) from the overhead.

        Even if the payload is itself a Number, its parts will not be underscore-separated.
        """
        whole_suffix_in_hex = hex_from_bytes(self.raw)
        if underscore > 0 and self.payload:
            payload_hex = whole_suffix_in_hex[ : -self.NUM_OVERHEAD*2]
            type_length_00_hex = whole_suffix_in_hex[-self.NUM_OVERHEAD*2 : ]
            return payload_hex + '_' + type_length_00_hex
        else:
            return whole_suffix_in_hex

    @property
    def number(self):
        """Interpret the payload as the raw bytes of an embedded Number."""
        return Number.from_raw(self.payload)

    class NoSuchType(ValueError):
        """Seek a type that is not there, e.g. Number(1).plus_suffix(0x22).suffix(0x33)"""

    class PayloadError(ValueError):
        """Suffix(payload=unexpected_type)"""

    class RawError(ValueError):
        """Unclean distinction between suffix and root, e.g. the crazy length 99 in 0q82_01__9900"""


# Hexadecimal
# -----------
def hex_from_integer(the_integer):
    """
    Encode a hexadecimal string from an arbitrarily big integer.

    Like hex() but output has:  an even number of digits, no '0x' prefix, no 'L' suffix.
    """
    # THANKS:  Mike Boers code, http://stackoverflow.com/a/777774/673991
    hex_string = hex(the_integer)[2:].rstrip('L')
    if len(hex_string) % 2:
        hex_string = '0' + hex_string
    return hex_string
assert 'ff' == hex_from_integer(255)
assert '0100' == hex_from_integer(256)


def bytes_from_hex(hexadecimal_digits):
    # noinspection SpellCheckingInspection
    """
        Decode a hexadecimal string into an 8-bit binary (base-256) string.

        Raises bytes_from_hex.Error if hexadecimal_digits is not an even number of digits.
        The bytes_from_hex.Error exception is a ValueError.  Why a ValueError?
            Pro:  bytearray.fromhex('nonsense') raises a ValueError
            Pro:  int('0xNonsense', 0) raises a ValueError
            Con:  binascii.unhexlify('nonsense') raises a TypeError in Python 2
            Con:  binascii.unhexlify('nonsense') raises a binascii.Error in Python 3

        NOTE:  binascii.unhexlify() is slightly faster than bytearray.fromhex()

        2.7>>>timeit.timeit('bytes(bytearray.fromhex("123456789ABCDEF0"))', number=1000000)
        0.3824402171467758
        2.7>>>timeit.timeit('binascii.unhexlify("123456789ABCDEF0")', number=1000000, setup='import binascii')
        0.30095773581510343

        3.5>>>timeit.timeit('bytes.fromhex("123456789ABCDEF0")', number=1000000)
        0.16179575853203687
        3.5>>>timeit.timeit('binascii.unhexlify("123456789ABCDEF0")', number=1000000, setup='import binascii')
        0.12774858387598442

        Possibly because fromhex is more permissive:  bytearray.fromhex('12 AB')
        """
    assert isinstance(hexadecimal_digits, six.string_types)
    try:
        return_value = binascii.unhexlify(hexadecimal_digits)
    except (
        TypeError,        # binascii.unhexlify('nonsense') in Python 2.
        binascii.Error,   # binascii.unhexlify('nonsense') in Python 3.
    ):
        raise bytes_from_hex.Error("Not an even number of hexadecimal digits: " + repr(hexadecimal_digits))
    assert return_value == six.binary_type(bytearray.fromhex(hexadecimal_digits))
    return return_value
assert b'\xBE\xEF' == bytes_from_hex('BEEF')


class BytesFromHexError(ValueError):
    """bytes_from_hex() invalid input"""
bytes_from_hex.Error = BytesFromHexError


def hex_from_bytes(string_of_8_bit_bytes):
    """Encode an 8-bit binary (base-256) string into a hexadecimal string."""
    assert isinstance(string_of_8_bit_bytes, six.binary_type)
    return binascii.hexlify(string_of_8_bit_bytes).decode().upper()
assert 'BEEF' == hex_from_bytes(b'\xBE\xEF')


# Math
# ----
def exp256(e):
    """Compute 256**e for nonnegative integer e."""
    assert isinstance(e, six.integer_types)
    assert e >= 0
    return 1 << (e << 3)   # == 2**(e*8) == (2**8)**e == 256**e
assert 256 == exp256(1)
assert 65536 == exp256(2)


def log256(i):
    """Compute the log base 256 of an integer.  Return the floor integer of that."""
    assert isinstance(i, six.integer_types)
    assert i > 0
    return_value = (i.bit_length()-1) >> 3
    assert return_value == len(hex_from_integer(i))//2 - 1
    assert return_value == math.floor(math.log(float(i), 256)) or i >= 2**48-1, "Math.log disagrees, {} {} {}".format(
        i,
        return_value,
        math.floor(math.log(i, 256))
    )
    return return_value
assert 1 == log256(256)
assert 2 == log256(65536)


def shift_leftward(n, nbits):
    """Shift positive left, or negative right.  Same as n * 2**nbits"""
    if nbits < 0:
        return n >> -nbits
    else:
        return n << nbits
assert 64 == shift_leftward(32, 1)
assert 16 == shift_leftward(32, -1)


def floats_really_same(f1,f2):
    """
    Compare floating point numbers.

    Similar to the == equality operator except:
     1. They ARE the same if both are NAN.
     2. They are NOT the same if one is +0.0 and the other -0.0.

    This is useful for unit testing.
    """
    assert type(f1) is float
    assert type(f2) is float
    if math.isnan(f1) and math.isnan(f2):
        return True
    if math.copysign(1,f1) != math.copysign(1,f2):
        # THANKS:  Comparing with -0.0, http://stackoverflow.com/a/25338224/673991
        return False
    return f1 == f2
assert True is floats_really_same(float('nan'), float('nan'))
assert False is floats_really_same(+0.0, -0.0)


# Padding and Unpadding Bytes
# ---------------------------
def left_pad00(the_string, num_bytes):
    """Make a byte-string num_bytes long by padding '\x00' bytes on the left."""
    assert isinstance(the_string, six.binary_type)
    return the_string.rjust(num_bytes, bytes(b'\x00'))
assert b'\x00\x00string' == left_pad00(b'string', 8)


def right_strip00(the_string):
    """Remove '\x00' bytes from the right end of a byte-string."""
    assert isinstance(the_string, six.binary_type)
    return the_string.rstrip(bytes(b'\x00'))
assert b'string' == right_strip00(b'string\x00\x00')


# Packing and Unpacking Bytes
# ---------------------------
def pack_integer(the_integer, num_bytes=None):
    """
    Pack an integer into a byte-string, which becomes a kind of base-256, big-endian number.

    :param the_integer:  an arbitrarily large integer
    :param num_bytes:  number of bytes (base-256 digits aka qigits) to output (omit for minimum)
    :return:  an unsigned two's complement string, MSB first

    Caution, there may not be a "sign bit" in the output unless num_bytes is large enough.
        assert     b'\xFF' == pack_integer(255)
        assert b'\x00\xFF' == pack_integer(255,2)
        assert     b'\x01' == pack_integer(-255)
        assert b'\xFF\x01' == pack_integer(-255,2)
    Caution, num_bytes lower than the minimum may not be enforced, see unit tests.
    """

    if num_bytes is None:
        num_bytes =  log256(abs(the_integer)) + 1

    if num_bytes <= 8 and 0 <= the_integer < 4294967296:
        return struct.pack('>Q', the_integer)[8-num_bytes:]  # timeit:  4x as fast as the Mike Boers way
    elif num_bytes <= 8 and -2147483648 <= the_integer < 2147483648:
        return struct.pack('>q', the_integer)[8-num_bytes:]
    else:
        return pack_big_integer_via_hex(the_integer, num_bytes)
        # NOTE:  Pretty sure this could never ever raise bytes_from_hex.Error
assert b'\x00\xAA' == pack_integer(170,2)
assert b'\xFF\x56' == pack_integer(-170,2)
assert byte(42) == pack_integer(42, num_bytes=1)


def pack_big_integer_via_hex(num, num_bytes):
    """
    Pack an arbitrarily large integer into a binary string, via hexadecimal encoding.

    Akin to base-256 encode.
    """
    # THANKS:  http://stackoverflow.com/a/777774/673991
    if num >= 0:
        num_twos_complement = num
    else:
        num_twos_complement = num + exp256(num_bytes)   # two's complement of big negative integers
    return left_pad00(
        bytes_from_hex(
            hex_from_integer(
                num_twos_complement
            )
        ),
        num_bytes
    )
assert b'\x00\xAA' == pack_big_integer_via_hex(170,2)
assert b'\xFF\x56' == pack_big_integer_via_hex(-170,2)


def unpack_big_integer_by_struct(binary_string):
    """Fast version of unpack_big_integer(), limited to 64 bits."""
    return struct.unpack('>Q', left_pad00(binary_string, 8))[0]
    # TODO:  unpack bigger integers, 64 bits at a time.
    # SEE:  128-bit unpack, https://stackoverflow.com/a/11895244/673991
assert 170 == unpack_big_integer_by_struct(b'\x00\xAA')


def unpack_big_integer_by_brute(binary_string):
    """Universal version of unpack_big_integer()."""
    return_value = 0
    for i in range(len(binary_string)):
        return_value <<= 8
        return_value |= six.indexbytes(binary_string, i)
    return return_value
assert 170 == unpack_big_integer_by_brute(b'\x00\xAA')


def unpack_big_integer(binary_string):
    """
    Convert a byte string into an integer.

    Akin to a base-256 decode, big-endian.
    """
    if len(binary_string) <= 8:
        return unpack_big_integer_by_struct(binary_string)
        # NOTE:  1.1 to 4 times as fast as unpack_big_integer_by_brute()
    else:
        return unpack_big_integer_by_brute(binary_string)
assert 170 == unpack_big_integer(b'\x00\xAA')


# Inspection
# ----------
def type_name(x):
    """
    Describe (very briefly) what type of object this is.

    THANKS:  http://stackoverflow.com/a/5008854/673991
    """
    the_type_name = type(x).__name__
    if the_type_name == 'instance':
        the_type_name = x.__class__.__name__
    return the_type_name
assert 'int' == type_name(3)
assert 'list' == type_name([])
assert 'Number' == type_name(Number.ZERO)
assert 'function' == type_name(type_name)


# TODO:  Ludicrous Numbers
# TODO:  Transfinite Numbers
# TODO:  Floating Point could be an add-on?  Standard is int?
#     Or nothing but raw, qex, qan, zones, and add-on int!?
# TODO:  Rational Suffix, e.g. 0q81FF_02___8264_71_0500 for precisely 0.01
#     (0x71 = 'q' for the rational quotient)
#     would be 8 bytes, same as float64
#     versus 0q81FF_028F5C28F5C28F60 for ~0.0100000000000000002, 10 bytes, as close as float gets to 0.01

# TODO:  decimal.Decimal
# TODO:  Numpy types
# SEE:  http://docs.scipy.org/doc/numpy/user/basics.types.html
# TODO:  other Numpy compatibilities?
# TODO:  fractions.Fraction -- rational numbers

# TODO:  Number.inc() native - taking advantage of raw encodings
# TODO:  __neg__ native - taking advantage of two's complement encoding of (non suffixed) qex + qan
#        (and fixing it for unreasonable numbers)
# TODO:  Possibly generate an exception for __neg__ of suffixed number?
# For any math on suffixed numbers??
# TODO:  __add__, __mul__, etc. native
# TODO:  other Number(string)s, e.g. assert 1 == Number('1')

# TODO:  hooks to add features in some modular way, e.g. suffixes
# TODO:  change % to .format()
# TODO:  change raw from str/bytes to bytearray?
# SEE:  http://ze.phyr.us/bytearray/
# TODO:  raise subclass of built-in exceptions
# (qex, qan, qan_length)
# TODO:  _pack() opposite of _unpack() -- and use it in _from_float(), _from_int()
# TODO:  str(Number('0q80')) should be '0'.  str(Number.NAN) should (continue to) be '0q'
# TODO:  Number.natural() should be int() if whole, float if non-whole.
# Maybe .__str__() should call .natural()

# FIXED:  pi = 0q82_03243F6A8885A3 and pi-5 = 0q7D_FE243F6A8885A3  (BTW pi in hex is 3.243F6A8885A308D3...)
#   Also, e  = 0q82_02B7E151628AED and e-5  = 0q7D_FDB7E151628AED  (BTW e  in hex is 2.B7E151628AED2A6A...)

# TODO:  Term for an unsuffixed Number?
# TODO:  Term for a suffixed Number?
# DONE:  Term for the unsuffixed part of a suffixed number:  "root"
# NOPE:  Name it "Numeraloid?  Identifier?  SuperNumber?  UberNumber?  Umber?
# NOPE:  Number class could be unsuffixed, and derived class could be suffixed?

# DONE:  (littlest deal) subclass numbers.Number.
# DONE:  (little deal) subclass numbers.Complex.
# First made unit tests for each of the operations named in the following TypeError:
#     "Cannot instantiate abstract class Number with abstract methods ..."
# DONE:  __abs__, __complex__, conjugate, __div__, imag,  __mul__, __pos__, __pow____, __rdiv__, real,
# __rmul__, __rpow, __rtruediv__, __truediv__

# TODO:  (big deal) subclass numbers.Integral.  (Includes numbers.Rational and numbers.Real.)
# TypeError: Cannot instantiate abstract class Number with abstract methods __and__, __floordiv__,
# __invert__, __lshift__, __mod__, __or__, __rand__, __rfloordiv__, __rlshift__, __rmod__, __ror__,
# __rrshift__, __rshift__, __rxor__, __trunc__, __xor__

# TODO:  Better object internal representation:  store separate qex, qan, suffixes
# (and synthesize raw on demand)
# perhaps raw == qex + qan + ''.join([suffix.raw for suffix in suffixes])

# TODO:  Number.to_JSON()
# THANKS:  http://stackoverflow.com/q/3768895/673991

# TODO:  mpmath support, http://mpmath.org/
# >>> mpmath.frexp(mpmath.power(mpmath.mpf(2), 65536))
# (mpf('0.5'), 65537)

# TODO:  is_valid() detects (at different severity levels?)
# Or validate() raising a family tree of exceptions:
# 0q82_00FF - as 1 but inside the plateau
# 0q82 as - compact but nonstandard
# 0q8183_01 - sensible as 2**-1000 but really should be ludicrous small encoding (longer qex)
# 0q__7E0100 - suffixed NAN
# 0q80__00 - 00-terminated means it should be suffixed but clearly it is not

# TODO:  Other infinities:
#     Omega
#     Omega + N
#     Aleph-zero
#     Aleph-one
#     Complex Infinity
#     Inaccessible Cardinal
#     Ramsey

# TODO:  Other NaNs, e.g. 0q0000_01, 0q0000_02, ...?  Suffixed NaN e.g. 0q__8201_770300?
# There's Quiet NaN and Signaling NaN.
# SEE:  qNaN and sNan, https://en.wikipedia.org/wiki/NaN
# There's reflexive and non-reflexive NaN -- within the Quiet NaNs.
# NaN ala IEEE 754 is non-reflexive, where NaN != NaN
# NaN could be reflexive if NaN == NaN
# Number.NAN resembles Python float('nan')
#     It is non-reflexive.
#     It is a Quiet NaN except for division by zero which is a Signaling NaN.

# TODO:  Lengthed-export.  Package up a Number value in a byte sequence that knows its own length.
##### LENGTHED EXPORT
##### ===============

# Background:
# The raw attribute is an unlengthed representation of the number.
# That is to say there is no way to know the length of a string of raw bytes from their content.
# Content carries no reliable indication of its length.  Length must be encoded extrinsically somehow.
# So this unlengthed word.raw attribute may be used as the content for a VARBINARY
# field of a MySQL table, where MySQL manages the length of that field.
# For applications where a stream of bytes must encode its own length, a different
# approach must be used.
# Similar to pickling but more byte-efficient for a Number (and only supports Numbers).

# One approach might be that if the first byte is 80-FE, what follows is the rest of a
# positive integer with no zero stripping. In effect, the first byte is
# the length (not including itself) plus 81 hex.  Values could be:
# 8201 8202 8203 ... 82FF 830100 830101 830102 ... FE01(124 00s) ... FEFF(124 FFs)
#    1    2    3      255    256    257    258     2**992            2**1000-1
# In these cases the lengthed-export has the same bytes as the unlengthed export
# except for the zero-stripping, i.e. multiples of 256, e.g. it's 830100 not 8301 (for 0q83_01 == 256).
# (The no-trailing-00 rule for raw would not apply to lengthed exported integers.)
# (So conversion when importing must strip those 00s.)
# (And so suffixed integers cannot be encoded this way, and must have the length prefix(es).)

# Any number other than nonnegative integers would be lengthed-exported as:  N + raw
# Where N (00 to 7D) is the length of the raw part.  So:
# -1   is 027DFF
# -2   is 027DFE
# -2.5 is 037DFD80
# +2.5 is 03820280

# The lengthed export might be used for exporting a word,
# taking the form of 6 numbers and a (somehow lengthed) utf-8 string.

# Special case 7F represents -1, aka 0q7D_FF aka 0q7E
# Special case 80 represents 0, aka 0q80
# Special case 81 represents 1, aka 0q82_01.
# So the sequence is 7F 80 81 8202 8203 8204 ...
#       representing -1  0  1    2    3    4 ...

# Negative one might be handy as a brief value.
# Though 017E could encode it, as could 027DFF But maybe plain 7F would be great.
# Then 00-7E would encode "other" (nonnegative, not-minus-one numbers)
# Or 00-7D could be lengthed prefixes that are straightforward, and
# 7E could be a special extender value,
# similar to the FF00FFFF... extended (2^n byte) lex in ludicrous numbers.
# There would be 2^n 7E bytes followed by 2^n (the same n) bytes encoding (MSB first) the real length.
# So e.g. a 256 byte raw value would be lengthed as 7E7E0100...(and then 256 bytes same as raw)
# A 65536-byte raw would have a lengthed-prefix of 7E7E7E7E00010000
# But the number of 7E bytes don't have to be a power of 2, they way they do with the qex
#     (Wait, why do the qex extenders have to be 2^n bytes?)
#     (Maybe they don't!)

# So in a way, length bytes 00-7D would be shorthand for 7E00 to 7E7D.
# And                      8202 to FD...(124 FFs) representing integers 2 to 2**992-1
# would be shorthand for 028202 to 7DFD...(124 FFs),
# itself shorthand for 7E028202 to 7E7DFD...(124 FFs)
# theoretically as 7E7E00028202 to 7E7E007DFD...(124 FFs), etc.

# FORMAL DEFINITION:
# The way to look at the lengthed-export version of a Number is that it always conceptually consists of:
#     7E-part, length-part, raw-part, 00-part
#
# 1. 7E-part is Np bytes of literal 7E.
# 2. length-part (call its value N) is stored in Np bytes representing a big-endian length N
# 3. raw-part is N bytes, identical to the bytes of Number.raw
# 4. 00-part consists of 00 bytes.  It only appears for unsuffixed integer multiples of 256.
#
# Example:
#     7E027DD6 for 0q7D_D6 aka -42
#
# Exceptions:
#     The 7E-part may be omitted if length-part (N) is 0 to 7D.
#         So the above example is misleading in that 027DD6 would be the "real" export of -42.
#     Clearly N < 256**Np
#     both 7E-part and length-part may be omitted for an unsuffixed integer 1 to 2**992-1
#     It only exists if 7E-part and length-part are omitted.
#     It serves to make the total length (of the raw-part after its first byte)
#         equal to the first raw byte minus 81.
#         Except for Number(0) where the raw-part is 80.
#             Then the 00-part is not -1 bytes, it's just empty.
#         And except for Number(-1) where the raw-part is 7F.
#             Then the 00-part is not -2 bytes, it's just empty.
#     So the 00-part is only nonempty (1 or more bytes) for unsuffixed integer multiples of 256.
#     And it's 2 or more bytes for unsuffixed integer multiples of 256**2, etc.
#     For large exponents of 256, it might be shorter to use the length-part than the 00-part
#         256**0 == 0q82_01 could be exported as 8201 or 028201 or 0182 or 81
#         256**1 == 0q83_01 could be exported as 830100 or 028301
#         256**2 == 0q84_01 could be exported as 84010000 or 028401
#         256**3 == 0q85_01 could be exported as 8501000000 or 028501
#     Clearly the 00-part is a penalty for 256**(2 or more)
#
# 7F is a fabricated alias for 027DFF representing 0q7D_FF aka -1.
# 80 is a fabricated alias for 0180   representing 0q80    aka  0.
# 81 is a fabricated alias for 8201   representing 0q82_01 aka +1.
#     These three weirdo exceptions are the only cases when the raw-part doesn't come from Number.raw.
#     For every other Number, there is a raw-part in its lengthed-export and it's identical to Number.raw.
#     In particular, the raw length N is 0, not first-raw-byte minus 81.
# 00 is a natural alias for Number.NAN  (Length-part=00, other parts omitted or empty.)
#     In this case Number.raw is empty.  So the raw-part is not so much omitted as empty anyway.

# Cases with a nonempty 7E-part, i.e. Np > 0:
#     Say the raw-part is 128 bytes (e.g. lots of suffixes, e.g. googolplex approximations)
#         then N is 128 and Np is 1
#     Its lengthed-export would look like this:
#         7E 80 (128-byte raw-part)

# The following indented part is bogus.  I think.  Leaving it around until sure:
#     Notice there is no shorthand for the sliver of integers at the top of the reasonable numbers:
#     0qFE_01 == 2**992 to 0qFE_FF...(124 more FFs) == 2**1000-1
#     The lengthed exports of those would be:
#     7E02FE01 to 7E7E007EFEFF...(124 more FFs)
# Wrong, FE01(plus 124 00s) makes sense for 2**992
# But is there a problem for 2**992+1?  Does that fit?

# This lengthed export is not monotonic.

# This scheme leaves an initial FF free for a future something-or-other.
# Possibly for qiki.word.Text, a utf-8 string, or some other octet-stream.
# Nt bytes of FF, Nt bytes storing a length N (the first byte of which is NOT FF), then the N-byte
# octet-stream.
# Perhaps more initial values should be "reserved".  We could reserve F0-FF for example,
# then 0qFO_01 (2**880 ~~ 8e264) and larger would require a lengthed-part:  02F001

##### REDOING THE CODING - A NEW IMPROVED LENGTHED EXPORT (or is this just a rewording?)
##### ---------------------------------------------------
#
# Interpreting the (left-lengthed) export, i.e. converting it to raw.  Start with first byte of raw, call it Byte0.
# ---------------------------------------
# Byte0
# -----
# FF - Count consecutive starting FF bytes, that's how many bytes follow that encoding the (big-endian) length.
#      That many bytes after both of those is raw.  e.g. FFFF0100(and then a 256-byte raw)
# C0-FE - open for expansion (63 values)
# 82-BF - positive integers +2 to +2**496-1.  Length (not including Byte0) is Byte0-81.  Entire export identical to raw.
# 81 - +1
# 80 -  0
# 7F - -1
# 7E - open for expansion
# 40-7D - negative integers -2 to -2**496+1.  Length (not including Byte0) is 7E-Byte0.  Entire export identical to raw.
# 00-3F - length (not including Byte0) is Byte0.  Verbatim raw follows.
#
# Converting raw to export
# ------------------------
# Unsuffixed positive integer, +2 to +2**496-1 that is NOT a multiple of 256 - export identical to raw
# Unsuffixed negative integer, -2 to -2**496+1 that is NOT a multiple of 256 - export identical to raw
# Unsuffixed +1 - 81
# Unsuffixed 0 - 80
# Unsuffixed -1 - 7F
# Otherwise, if the raw length is 0-63 bytes - encode as length (one byte) + raw
# All other cases - Compute Np = log(base 256)(raw length) rounded up, or 0 if length is 0.
#                   Export is:  Np FF bytes + length (big endian) + raw
#
# BTW 2**496 ~~ 2e149
#
# Hey, with so many values open for expansion, perhaps some compression is possible.
# For example if 15% of the byte stream consisted of some 3-byte value, e.g. 0q83_8888,
# then even though raw and export were the same, encoding the value as one-byte C0
# would save 10% of space.  Or if 80% of the byte stream consisted of some 13-byte
# export, e.g. 0q83_8888__8888_7E0200 exported as 0C83888888887E0200, then arranging to
# encode it in one byte.
#
# Perhaps there's some advantage to using 7E bytes for the big-length preamble instead of FF?
# Though FF is aesthetically more pleasing, this would free up the 64 expansion values C0-FF to all
# have the same upper 2 bits (11) so the lower 6 bits can be any pattern.  Perhaps this makes some kind
# of compression algorithm a little smoother (fewer special cases).
#
# But then said compression algorithm would use ALL the extra values.  Maybe the verbatim conversions
# should shrink, e.g. how bad would 82-9F and 7D-60 be?  Integers 2**248 don't include googol (~1.7e72).
# But that frees up another 64 expansion values!
#
# We could use more expansion values for text.  We NEED expansion values to identify the compression values!
# BTW some compression values could be 1-byte, others 2-byte, etc., ala UTF-8.
# So the ranges 82-AF and 7D-50 would include googol:  2**368 ~~ 6e110, and would free up 32 values (40-4F, B0-BF).
#
# Heck there's wiggle room with the lengths too.  Maybe leaving some room there (to possibly be taken up
# by lengths anyway in the future) is wise.  Some codes could be dynamic (more lengths for a while, more compression
# for a while).  But if compression is important, lots more could be done by compressing the whole
# stream in some kind of lossless method, e.g. zlib.

# What to call it?
#     lengthed export
#     dna
#     freeze-dried
#     p-string
#         "packed"
#         "packet"
#         but it is not a "string" in the sense that the qstring is a printable string
#         but p has some symmetry with q
#         but the p-string is really too different from the qstring
#     b or d string would also be symmetrical with q, but it should rather be symmetrical with raw
#     ink
#     What real-world analogy for packaging a word for transport down a stream?
#     stream byte array
#     morse code
#     packet
#         good that it's similar to pickle but it's not pickle
#         or maybe not, pickling has more to do with making a byte stream,
#         and anyway it doesn't seem that pickled data knows its length
#     packetized
#     Think of a tardigrade, desiccated.  And reconstituted back to life.
#         but this is not condensing, in fact it is expanding.
#         really it is more like a packetized number
#     pickled?  That term is taken, but something analogous...
#     fermented?   <--- I think I like this one best.  Make wine not pickle juice.
#     calcified
#     emulsified
#     cauterized
#     mummified
#     individually wrapped
#     shrink wrapped
#     candy coat
#     dragee (jordan almond)
#     sun dried
#     shell (except that verb normally means to remove, so does un-shell mean to ADD a shell??)
#     serialized
#     marshalled
#     flattened
#     gherkin (or some other pickle, though dill is taken, SEE http://dare.wisc.edu/survey-results/1965-1970/foods/h56)

# Or maybe this is really similar to pickling.

# The lengthed-export version of a Number might be useful for embedding multiple numbers in a suffix.
# An example of multiple numbers in a suffix might be a "user-defined" type for a suffix
#     where one number identifies the user, and the other has user-defined meaning.
#     Or 3 numbers:  user number, type number, content
#        Oh wait, it can be just type number and content
#        Because the type number can be an idn for a word that itself represents
#            user number and the user's custom-defined type
#            that is, a word
#                [user](define, 'foobar')[system]
#        and another word
#                [user](define, type-number)[foobar]
# This seems complicated and intricate (complicantricate?) but so are consecutive or nested suffixes.
#     (the other alternative for a user-defined type)
# Particularly in the case of user-defined suffix types, we want the syntax to be simple
# so it's easy to use, and economical with bytes, so the 1-byte suffix types are not so greedily sought
# and we can be extremely parsimonious with them, sloughing off many proposals for them to user-defined
# types.
# OMG is this leading to the notion of encoding a WORD inside a NUMBER?!?
#     If it did, the "root" of a Number would correspond to Word.num
#     and Suffix.type would correspond to Word.vrb
#     and Suffix.payload                  Word.obj
#     and Suffix.user/definer             Word.sbj
#
# Freaky thought:  What if a word and a number were the same thing!?!
#
# I keep trying to unify everything else.
# A regular "number" could be a word with a value and no sbj,vrb,obj?

# NOTE:  The lengthed export is only lengthed from the "left". It cannot be interpreted from the "right".
# That is, if the byte stream is coming in reverse order for some reason,
# the length cannot be reliably determined.
# So if the payload of a suffix has any lengthed-export numbers
# then any other parts must also be lengthed somehow.
# e.g. it's not possible for a payload to contain string + lengthed-exported-number
# unless the string were lengthed (NUL-terminated or preceded by length bytes).

# Whoa!  If we had right-lengthed export in the suffix then most suffixes
# could contain two numbers (besides the zero-tag), type and payload. No need for a length-part!
# I could store these suffix number raw bytes effing backwards!
# All of this crap leads to the idea that Number should store separately:
#     ludicrous-preamble (e.g. FF00FFFF...)
#     qex (itself could store an exponent, but .raw could be the bytes)
#     qan
#     suffixes
#        suffix
#            type - a number (idn of a sentence defining the suffix type)
#            payload - a number that's type-specific (which may be itself suffixed)
#            raw - reversed(payload.lengthed_export) + reversed(type.lengthed_export) + 00

# One super crazy way to have a right-lengthed export of a Number is to store the
# left-lengthed export bytes in reverse order.  I didn't even want to write this idea here
# it's so wild.  Why wild?  Well if one of the Numbers inside a Suffix (type, payload)
# were itself suffixed, then those bytes would be in double-reverse order, i.e. normal.
# It would be very hard to interpret a Suffixed Number looking at the qstring.
# But how would it compare in terms of byte-efficiency, to the existing Suffix scheme?
# An actual functional drawback would be the loss of sort order.  One lex's idn referring to
#     another lex's idn would have it stored in reverse order (the root identifies the other lex)
#     But then several idns from that lex would not sort by raw.
#
# If we did have two directions of lengthed-exports, it would be wild if they could be named
# b-something for the left-lengthed and d-something for right-lengthed.
# Then the strings could be e.g. 0b123456 and 0d563412 (or 563412d0!)
# "boxed" both starts with a b and ends with a d.
# Oh wait, b and d are both valid hex digits, that seems wrong somehow.  Good thing p and q are not.
# s and z are mirrors in almost all fonts and styles.
# k and y are kinda rotated versions.  u/n and m/w are kinda rotated pairs too.
# In a way the existing Suffix scheme is already a right-lengthed export, with payload-type-length-00

# There might be use for a #### bidirectional-lengthed-export.
# That is, a sequence of numbers stored in bytes that could be interpreted in either direction.
# An application could be a file that accumulates chronologically,
# A LexBinaryFlatFile or something that just writes its sentences
# (each of which consists of 6 numbers and a UTF-8 string)
# to the end of a binary file.
# Then another process might want to scan that file -- and here's the crucial part --
# either earliest-first or latest-first.
# Though latest-first might not be so useful if one couldn't interpret earlier words.
# So, a THIRD way to scan is from any byte position, thereby iteratively zooming in on
# some SPECIFIC word by index.

##### (end of lengthed-export talk)

# TODO:  Move a lot of these TODOs to github issues.  And give them qiki interactivity there!

# TODO:  Are Numbers immutable after __init__() is done or not?
#        If they are, then several of the type(self)(self) calls and their ilk may be unnecessary.
#        They kind of have to be immutable, because strings and integers are ffs.
#        But that means no Number().addSuffix() <-- already fixed, replaced with plus_suffix()
#        which sounds SLIGHTLY less like something that could mutate in place.
