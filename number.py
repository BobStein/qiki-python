"""
Qiki Numbers

Integers, floating point, complex, and more, are seamlessly represented.
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


class SlotsOptimized(object):
    FOR_MEMORY = False
    FOR_SPEED = True
assert not (SlotsOptimized.FOR_MEMORY and SlotsOptimized.FOR_SPEED)


# TODO:  Docstring every class
# TODO:  Docstring every function
# TODO:  Custom Exceptions should end in Error, e.g. WholeIndeterminate --> WholeIndeterminateError


class Zone(object):
    """
    Each qiki Number is in one of 14 distinct zones.

    This internal Number.Zone class serves as an enumeration of those zones.
    Raw, internal binary strings represent the value of each zone.
    The members of Number.Zone have values that are either:
        minimum value for the zone
        between the zone and the one below it
    Each value is less than or equal to all raw values of numbers in the zone it represents.
    and greater than all *valid* raw values in the numbers in the zones below.
    (So actually, some zone values are valid raw values for numbers in that zone,
    others are among the inter-zone values.  More on this below.)
    For example, the valid raw string for 1 is b'x82\x01' which is the minimum valid value for
    the positive zone.  But Number.Zone.POSITIVE is less than that, b'x82'.
    Anything between b'x82' and b'x82\x01' will be interpreted as 1 by any Number Consumer (NumberCon).
    But any Number Producer (NumberPro) that generates a 1 should generate the raw string b'x82\x01'.


    Between versus Minimum
    ----------------------
    A minor, hair-splitting point.
    Most values of Zone are the minimum of their zone.
    Zone.FRACTIONAL_NEG is one exceptional *between* value, b'\x7E\x00'
    That is never a legal raw value for a number because it ends in a 00 that is not part of a suffix.
    The valid minimum value for this zone cannot be represented in finite storage,
    because the real minimum of that zone would be an impossible hypothetical
    b'\x7E\x00\x00\x00 ... infinite number of \x00s ... followed by something other than \x00'
    Representing a surreal -0.99999999999...infinitely many 9s, but greater than -1.
    So instead we use the illegal, inter-zone b'\x7E\x00' which is *between* legal raw values.
    And all legal raw values in Zone FRACTIONAL_NEG are above it.
    And all legal raw values in Zone NEGATIVE are below it.

    So are there or are not there inter-zone Numbers?
    In other words, are the zones comprehensive?
    Even illegal and invalid values should normalize to valid values.
    """
    # TODO:  Test that invalid and illegal values normalize to valid values.
    # TODO:  Formally define all invalid and illegal raw-strings.

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


class Number(numbers.Complex):
    if SlotsOptimized.FOR_MEMORY:
        __slots__ = ('__raw', )
    elif SlotsOptimized.FOR_SPEED:
        __slots__ = ('__raw', '_zone')

    def __init__(self, content=None, qigits=None, normalize=False):
        """
        Number constructor.

        content - int, float, '0q'-string, 'numeric'-string, complex, another Number, or None
        qigits - number of bytes for the qantissa, see _raw_from_float()
        normalize=True - collapse equal values e.g. 0q82 to 0q82_01, see _normalize_all()
        """
        if isinstance(content, six.integer_types):
            self._from_int(content)
        elif isinstance(content, float):
            self._from_float(content, qigits)
        elif isinstance(content, Number):  # SomeSubclassOfNumber(AnotherSubclassOfNumber())
            self.raw = content.raw
        elif isinstance(content, six.string_types):
            self._from_string(content)
        elif isinstance(content, complex):
            self._from_complex(content)
        elif content is None:
            self.raw = self.RAW_NAN
        else:
            raise self.ConstructorTypeError("{outer}({inner}) is not supported".format(
                outer=type_name(self),
                inner=type_name(content),
            ))

        assert(isinstance(self.__raw, six.binary_type))
        if normalize:
            self._normalize_all()

    class ConstructorTypeError(TypeError):
        """e.g. Number(object) or Number([])"""

    class ConstructorValueError(ValueError):
        """e.g. Number('alpha string') or Number.from_raw(0) or Number.from_qstring('0x80')"""

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
    # Computations normalize to a standard and unique representation (0q82_01).
    # Storage (e.g. a database) may opt for brevity (0q82).
    # So all 8-bit binary strings have exactly one interpretation as the raw part of a Number.
    # And some are redundant, e.g. assert Number('0q82') == Number('0q82_01')
    # The qex and qan may be followed by suffixes.
    # Two underscores conventionally precede each suffix.
    # See the Number.Suffix class for underscore conventions within a suffix.

    # TODO:  Make class Raw?  Then both Number and Suffix contain it?!?
    RAW_INFINITY          = b'\xFF\x81'
    RAW_INFINITESIMAL     = b'\x80\x7F'
    RAW_ZERO              = b'\x80'
    RAW_INFINITESIMAL_NEG = b'\x7F\x81'
    RAW_INFINITY_NEG      = b'\x00\x7F'
    RAW_NAN               = b''

    @property
    def raw(self):
        """
        Internal byte-string representation of the Number.

        assert '\x82\x01' == Number(1).raw

        Implemented as a property so that Number._zone (if there's a slot for it) can be computed in tandem.
        """
        return self.__raw

    @raw.setter
    def raw(self, value):
        """Set the raw byte-string.  Rare."""
        # TODO:  Enforce rarity?  Make this setter raise an exception, and create a _set_raw() method.
        assert(isinstance(value, six.binary_type))
        # noinspection PyAttributeOutsideInit
        self.__raw = value
        self._zone_refresh()

    def __getstate__(self):
        """For the 'pickle' package, object serialization."""
        return self.raw

    def __setstate__(self, d):
        self.raw = d

    def __repr__(self):
        return "Number('{}')".format(self.qstring())

    def __str__(self):
        return self.qstring()


    # Comparison
    # ----------
    def __eq__(self, other):
        try:
            self_ready = self._op_ready(self)
            other_ready = self._op_ready(other)
        except self.Incomparable:
            return False
        else:
            return self_ready == other_ready

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):  self._both_real(other); return self._op_ready(self) <  self._op_ready(other)
    def __le__(self, other):  self._both_real(other); return self._op_ready(self) <= self._op_ready(other)
    def __gt__(self, other):  self._both_real(other); return self._op_ready(self) >  self._op_ready(other)
    def __ge__(self, other):  self._both_real(other); return self._op_ready(self) >= self._op_ready(other)
    # SEE:  Greg Ward sez "avoid __cmp__()", http://gerg.ca/blog/post/2012/python-comparison/

    @classmethod
    def _op_ready(cls, x):
        """Get some kind of value ready for comparison operators."""
        try:
            normalized_number = cls(x, normalize=True)
        except cls.ConstructorTypeError:
            # DEBATE:  Not pythonic to raise an exception here (or in _both_real())
            # 0 < object should always be True, 0 > object always False.
            # With this exception we cannot sort a list of Numbers and other objects
            # (Order would be arbitrary, but it should not raise an exception.)
            # SEE:  about arbitrary ordering, http://stackoverflow.com/a/6252953/673991
            # SEE:  about arbitrary ordering, http://docs.python.org/reference/expressions.html#not-in
            # "...objects of different types ... are ordered consistently but arbitrarily."

            # DEBATE:  As long as a qiki Number is an exotic type, this exception may avoid
            # unintended comparisons, e.g. with other exotic types.  This is more important
            # than being able to "sort" a mixed bag of Numbers and other types.

            # DEBATE:  Return NotImplemented?  http://jcalderone.livejournal.com/32837.html
            # SEE:  http://stackoverflow.com/a/879005/673991

            raise cls.Incomparable("A Number cannot be compared with a " + type(x).__name__)
            # NOTE:  This exception message never makes it out of code in this source file.
            # The only time it is raised, it is also caught, e.g. Number(0) == object
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
    # Option one:  different __raw values, complicated interpretation of them in __eq__() et al.
    #     If going this way, equality might compare Number.raw_normalized().
    #     TODO:  What to do about suffixes, e.g. should this be true?  0q82__FF0100 == 0q82_01__FF0100
    #     TODO:  Obviously different suffixes should matter:  0q80__FF0100 != 0q80__110100
    #     This approach may be the way it needs to go in the future.
    #     For example if lossless rational numbers were supported, you might want 2/10 == 1/5
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
    #     Each raw plateau has a canonical raw value, and a multitude of illegal raw values.
    #     All values at a raw plateau should be "equal".
    #     This approach would vindicate making raw a @property
    # Option three:  give up on Number('0q82') == Number('0q82_01')
    # Option four: exceptions when any raw strings fall within the "illegal" part of a plateau.
    # By the way, zero has no plateau, only 0q80 with no suffix is zero.  (except empty suffix?)
    # TODO:  What about numbers embedded in suffixes, should 0q80__82_7F0200 == 0q80__8201_7F0300 ?
    # TODO:  Number.compacted() that fights against normalize
    # Compacted forms are desirable in suffix numbers
    # TODO:  Should normalization strip empty suffixes?  (__0000)

    class Incomparable(TypeError):
        """e.g. Number(1+2j) < Number(1+3j)"""

    def _both_real(self, other):
        """Make sure both operands are real (not complex) before comparison."""
        if self.is_complex():
            raise self.Incomparable("Complex values are unordered.")
            # TODO:  Should this exception be "Unordered" instead?  Test other.is_complex() too??
        try:
            other_as_a_number = type(self)(other)
        except self.ConstructorTypeError:
            raise self.Incomparable("Number cannot be compared with a " + type(other).__name__)
        else:
            if other_as_a_number.is_complex():
                raise self.Incomparable("Cannot compare complex values.")


    # Math
    # ----
    def __hash__(self):
        return hash(self.raw)

    def __pos__( self): return self._unary_op(operator.__pos__)
    def __neg__( self): return self._unary_op(operator.__neg__)
    def __abs__( self): return self._unary_op(operator.__abs__)

    def __add__( self, other): return self._binary_op(operator.__add__, self, other)
    def __radd__(self, other): return self._binary_op(operator.__add__, other, self)
    def __sub__( self, other): return self._binary_op(operator.__sub__, self, other)
    def __rsub__(self, other): return self._binary_op(operator.__sub__, other, self)
    def __mul__( self, other): return self._binary_op(operator.__mul__, self, other)
    def __rmul__(self, other): return self._binary_op(operator.__mul__, other, self)
    def __truediv__( self, other): return self._binary_op(operator.__truediv__, self, other)
    def __rtruediv__(self, other): return self._binary_op(operator.__truediv__, other, self)
    def __div__( self, other): return self._binary_op(operator.__div__, self, other)
    def __rdiv__(self, other): return self._binary_op(operator.__div__, other, self)
    def __pow__( self, other): return self._binary_op(operator.__pow__, self, other)
    def __rpow__(self, other): return self._binary_op(operator.__pow__, other, self)

    def _unary_op(self, op):
        n = Number(self)
        if n.is_complex():
            return Number(op(complex(n)))
        elif n.is_whole():
            return Number(op(int(n)))
        else:
            return Number(op(float(n)))

    @staticmethod
    def _binary_op(op, input_left, input_right):
        n1 = Number(input_left)
        n2 = Number(input_right)
        if n1.is_complex() or n2.is_complex():
            return Number(op(complex(n1), complex(n2)))
        elif n1.is_whole() and n2.is_whole():
            return Number(op(int(n1), int(n2)))
        else:
            return Number(op(float(n1), float(n2)))

    def _normalize_all(self):
        """
        Eliminate redundancies in the internal __raw string.

        This and other normalization routines operate in-place, modifying self.
        There are no return values.
        """
        self._normalize_plateau()
        self._normalize_imaginary()

    def _normalize_imaginary(self):
        """
        Eliminate imaginary suffix if it is zero.

        So e.g. 1+0j == 1

        We do not check self.imag == self.ZERO because that may try to subtract a missing suffix.
        """
        # TODO:  Multiple imaginary suffixes should check them all, or only remove the zero ones?
        try:
            imaginary_part = self.get_suffix_number(Suffix.TYPE_IMAGINARY)
        except Suffix.NoSuchType:
            """No imaginary suffix already; nothing to normalize away."""
        else:
            if imaginary_part == self.ZERO:
                self.raw = self.minus_suffix(Suffix.TYPE_IMAGINARY).raw

    def _normalize_plateau(self):
        """
        Eliminate redundancies in the internal representation of edge values +/-256**+/-n.

        E.g.  0q82 becomes 0q82_01 for +1.
        E.g.  0q7E01 becomes 0q7E00_FF for -1/256.
        """
        if self.zone in ZoneSet.MAYBE_PLATEAU:
            pieces = self.parse_suffixes()
            raw_qexponent = pieces[0].qex_raw()
            raw_qantissa = pieces[0].qan_raw()
            is_plateau = False
            if len(raw_qantissa) == 0:
                is_plateau = True
                if self.is_positive():
                    self.raw = raw_qexponent + b'\x01'
                else:
                    new_qex_lsb = six.indexbytes(raw_qexponent,-1)
                    new_qex = raw_qexponent[0:-1] + six.int2byte(new_qex_lsb-1)
                    self.raw = new_qex + b'\xFF'
            else:
                if self.is_positive():
                    if raw_qantissa[0:1] == b'\x00':
                        is_plateau = True
                        self.raw = raw_qexponent + b'\x01'
                else:
                    if raw_qantissa[0:1] == b'\xFF':
                        is_plateau = True
                        self.raw = raw_qexponent + b'\xFF'
            if is_plateau:
                for piece in pieces[1:]:
                    self.raw = self.plus_suffix(piece).raw
                    # TODO:  Test this branch (on a number with suffixes)

    def normalized(self):
        return type(self)(self, normalize=True)

    def is_negative(self):
        return_value = ((six.indexbytes(self.raw, 0) & 0x80) == 0)
        assert return_value == (self.zone in ZoneSet.NEGATIVE)
        assert return_value == (self.raw < self.RAW_ZERO)
        return return_value

    def is_positive(self):
        return_value = (not self.is_negative() and not self.is_zero())
        assert return_value == (self.zone in ZoneSet.POSITIVE)
        assert return_value == (self.raw > self.RAW_ZERO)
        return return_value

    def is_zero(self):
        return_value = (self.raw == self.RAW_ZERO)
        assert return_value == (self.zone in ZoneSet.ZERO)
        return return_value

    def is_whole(self):
        if self.zone in ZoneSet.WHOLE_MAYBE:
            (qan, qanlength) = self.qantissa()
            qexp = self.qexponent() - qanlength
            if qexp >= 0:
                return True
            else:
                if qan % exp256(-qexp) == 0:
                    return True
                else:
                    return False
        elif self.zone in ZoneSet.WHOLE_YES:
            return True
        elif self.zone in ZoneSet.WHOLE_NO:
            return False
        else:   #              ZONE_WHOLE_INDETERMINATE
            raise self.WholeIndeterminate("Cannot process " + repr(self))   # e.g. ludicrously large numbers

    is_integer = is_whole

    class WholeIndeterminate(OverflowError):
        """When the whole part of a number does not make sense, e.g. Number.POSITIVE_INFINITY.is_whole()"""

    def is_nan(self):
        return self.raw == self.RAW_NAN

    def is_real(self):
        return not self.is_complex()

    def is_complex(self):
        return self.imag != self.ZERO

    def inc(self):
        self.raw = self._inc_raw_via_integer()
        return self

    def _inc_raw_via_integer(self):
        return Number(int(self) + 1).raw

    @property
    def real(self):
        return self.root()

    def root(self):
        # TODO:  Less vacuous name.  Unsuffixed()?
        return self.parse_suffixes()[0]

    @property
    def imag(self):
        try:
            return self.get_suffix_number(Suffix.TYPE_IMAGINARY)
        except Suffix.NoSuchType:
            return self.ZERO

    def conjugate(self):
        return_value = self.real
        imag = self.imag
        if imag != self.ZERO:
            return_value = return_value.plus_suffix(Suffix.TYPE_IMAGINARY, (-imag).raw)
        return return_value

    # "from" conversions:  Number <-- other type
    # ------------------------------------------
    @classmethod
    def from_raw(cls, value):
        """Construct a Number from its raw, internal binary string of qigits.
        value - an 8-bit binary string (e.g. another Number's raw)

        Right:  assert Number(1) == Number(0q82_01')
        Wrong:                      Number(b'\x82\x01')
        Right:  assert Number(1) == Number.from_raw(b'\x82\x01')
        Right:  assert Number(1) == Number.from_raw(bytearray(b'\x82\x01'))
        """
        if not isinstance(value, six.binary_type):
            raise cls.ConstructorValueError(
                "'{}' is not a binary string.  Number.from_raw(needs e.g. b'\\x82\\x01')".format(repr(value))
            )
        return_value = cls()
        return_value.raw = value
        return return_value

    @classmethod
    def from_bytearray(cls, value):
        return cls.from_raw(six.binary_type(value))

    from_mysql = from_bytearray

    def _from_string(self, s):
        """
        Construct a Number from its string rendering.

        Example:  assert Number(1) == Number('0q82_01')
        Example:  assert Number(1) == Number('1')
        """
        assert(isinstance(s, six.string_types))
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
                            "A qiki Number string must be a valid int, float, or q-string, "
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
        Public factory to generate a Number from its qstring.

        Example:  assert Number(1) == Number.from_qstring('0q82_01')
        """
        if s.startswith('0q'):
            return_value = cls()
            return_value._from_qstring(s)
            return return_value
        else:
            raise cls.ConstructorValueError(
                "A q-string must begin with '0q'.  This does not: " + repr(s)
            )

    def _from_qstring(self, s):
        """Private method to fill in raw from a qstring."""
        digits = s[2:].replace('_', '')
        if len(digits) % 2 != 0:
            digits += '0'
        try:
            byte_string = string_from_hex(digits)
        except TypeError:
            raise self.ConstructorValueError(
                "A q-string must use hexadecimal digits (or underscore), not {}".format(repr(s))
            )
        self.raw = six.binary_type(byte_string)

    def _from_int(self, i):
        if   i >  0:   self.raw = self._raw_from_int(i, lambda e: 0x81+e)
        elif i == 0:   self.raw = self.RAW_ZERO
        else:          self.raw = self._raw_from_int(i, lambda e: 0x7E-e)

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
            # NOTE:  0x00 and 0xFF are for unreasonable numbers (ludicrous or transfinite).
            return six.int2byte(qex_integer)
        else:
            raise cls.LudicrousNotImplemented(
                "Ludicrous Numbers are not yet implemented:  " + str(qex_integer)
            )

    # float precision
    # ---------------
    # A "qigit" is a qiki Number byte, or base-256 digit.
    # Number(float) defaults to 8 qigits, for lossless representation of a Python float.
    # IEEE 754 double precision has a 53-bit significand (52 bits stored + 1 implied).
    # SEE:  http://en.wikipedia.org/wiki/Double-precision_floating-point_format
    # Why are 8 qigits needed to store 53 bits, not 7?
    # That is because the most significant qigit may not store a full 8 bits, it may store as few as 1.
    # So 8 qigits can store 57-64 bits, the minimum needed to store 53.
    # Example, 1.2 == 0q82_0133333333333330 stores 1+8+8+8+8+8+8+4 = 53 bits in 8 qigits.
    QIGITS_PRECISION_DEFAULT = 8

    SMALLEST_UNREASONABLE_FLOAT = 2.0 ** 1000   # == 256.0**125 == 1.0715086071862673e+301

    def _from_float(self, x, qigits=None):
        """Construct a Number from a Python IEEE 754 double-precision floating point number

        The big zone-based if-statement reveals this conversion in its lambdas:
            qex <-- base 256 exponent

        Contrast __qexponent_encode_dict().
        Example:  assert '0q82_01' == Number(1.0).qstring()
        Example:  assert '0q82_03243F6A8885A3' == Number(math.pi).qstring()
        """
        if qigits is None or qigits <= 0:
            qigits = self.QIGITS_PRECISION_DEFAULT

        smurf = self.SMALLEST_UNREASONABLE_FLOAT

        if math.isnan(x):  self.raw =           self.RAW_NAN
        elif x >= smurf:   self.raw =           self._raw_unreasonable_float(x)
        elif x >=  1.0:    self.raw =           self._raw_from_float(x, lambda e: 0x81+e, qigits)
        elif x >   0.0:    self.raw = b'\x81' + self._raw_from_float(x, lambda e: 0xFF+e, qigits)
        elif x ==  0.0:    self.raw =           self.RAW_ZERO
        elif x >  -1.0:    self.raw = b'\x7E' + self._raw_from_float(x, lambda e: 0x00-e, qigits)
        elif x > -smurf:   self.raw =           self._raw_from_float(x, lambda e: 0x7E-e, qigits)
        else:              self.raw =           self._raw_unreasonable_float(x)

    @classmethod
    def _raw_unreasonable_float(cls, x):
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
        self._from_float(c.real)
        self.raw = self.plus_suffix(Suffix.TYPE_IMAGINARY, type(self)(c.imag).raw).raw
        # THANKS:  Call constructor if subclassed, http://stackoverflow.com/a/14209708/673991

    # "to" conversions:  Number --> other type
    # ----------------------------------------
    def qstring(self, underscore=1):
        """Output Number as a q-string:  assert '0q82_01' == Number(1).qstring()

        assert '0q85_12345678' == Number(0x12345678).qstring()
        Q-string is a human-readable form of the raw representation of a qiki number
        Similar to 0x12AB for hexadecimal
        Except q for x, underscores optional, and of course the value interpretation differs.
        """
        # DONE:  double-underscore 1-deep suffixes.  E.g. 0x82_01__8202_7F0300
        # TODO:  triple-underscore 2-deep suffixes?  E.g. 0x82_01___8202__8203_7F0300_7F0800
        # TODO:    quad-underscore 3-deep suffixes?  E.g. 0x82_01____8202___8203__8204_7F0300_7F0800_7F0D00
        # TODO:  Alternative repr() for suffixed numbers, where calling-parens coincide with nesting depth.
        if underscore == 0:
            return_value = '0q' + self.hex()
        else:
            parsed_suffixes = list(self.parse_suffixes())
            root_raw = parsed_suffixes.pop(0).raw
            length = len(root_raw)
            if length == 0:
                offset = 0
            elif six.indexbytes(self.raw, 0) in (0x7E, 0x7F, 0x80, 0x81):
                offset = 2
            else:
                offset = 1   # TODO:  ludicrous numbers have bigger offsets (for googolplex it is 64)
            h = hex_from_string(root_raw)
            if length <= offset:
                return_value = '0q' + h
            else:
                return_value = '0q' + h[:2*offset] + '_' + h[2*offset:]
            for suffix in parsed_suffixes:
                return_value += '__'
                return_value += suffix.qstring(underscore)
        return return_value

    def __int__(self):
        int_by_dictionary = self.__int__by_zone_dictionary()
        assert int_by_dictionary == self.__int__by_zone_ifs(), (
            "Mismatched int encoding for %s:  dict-method=%s, if-method=%s" % (
                repr(self), int_by_dictionary, self.__int__by_zone_ifs()
            )
        )
        return int_by_dictionary

    if six.PY2:
        def __long__(self):
           # noinspection PyCompatibility
           return long(self.__int__())

    def __complex__(self):
        return complex(float(self.real), float(self.imag))

    def __int__by_zone_dictionary(self):
        return self.__int__zone_dict[self.zone](self)

    __int__zone_dict =  {
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

    def __int__by_zone_ifs(self):
        if   Zone.TRANSFINITE          <= self.raw:  return self._int_cant_be_positive_infinity()
        elif Zone.POSITIVE             <= self.raw:  return self._to_int_positive()
        elif Zone.FRACTIONAL_NEG       <= self.raw:  return 0
        elif Zone.LUDICROUS_LARGE_NEG  <= self.raw:  return self._to_int_negative()
        elif Zone.NAN                  <  self.raw:  return self._int_cant_be_negative_infinity()
        else:                                             return self._int_cant_be_nan()

    @staticmethod
    def _int_cant_be_positive_infinity():
        raise OverflowError("Positive Infinity cannot be represented by integers.")

    @staticmethod
    def _int_cant_be_negative_infinity():
        raise OverflowError("Negative Infinity cannot be represented by integers.")

    @staticmethod
    def _int_cant_be_nan():
        raise ValueError("Not-A-Number cannot be represented by integers.")

    def _to_int_positive(self):
        n = self.normalized()
        (qan, qanlength) = n.qantissa()
        qexp = n.qexponent() - qanlength
        return shift_leftward(qan, qexp*8)

    def _to_int_negative(self):
        (qan,qanlength) = self.qantissa()
        qexp = self.qexponent() - qanlength
        qan_negative = qan - exp256(qanlength)
        the_int = shift_leftward(qan_negative, qexp*8)
        if qexp < 0:
            extraneous_mask = exp256(-qexp) - 1
            extraneous = qan_negative & extraneous_mask
            if extraneous != 0:
                the_int += 1   # XXX:  a more graceful way to floor to 0 instead of to -inf
        return the_int

    def __float__(self):
        if self.is_complex():
            raise TypeError("{} has an imaginary part, use complex(n) instead of float(n)".format(self.qstring()))
        x = self.real
        float_by_dictionary = x.__float__by_zone_dictionary()
        assert floats_really_same(float_by_dictionary, x.__float__by_zone_ifs()), (
            "Mismatched float encoding for %s:  dict-method=%s, if-method=%s" % (
                repr(x), float_by_dictionary, x.__float__by_zone_ifs()
            )
        )
        return float_by_dictionary

    def __float__by_zone_dictionary(self):
        return self.__float__zone_dict[self.zone](self)

    __float__zone_dict =  {
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

    def __float__by_zone_ifs(self):
        _zone = self.zone
        if _zone in ZoneSet.REASONABLY_NONZERO:
            return self._to_float()
        elif _zone in ZoneSet.ESSENTIALLY_NONNEGATIVE_ZERO:
            return 0.0
        elif _zone in ZoneSet.ESSENTIALLY_NEGATIVE_ZERO:
            return -0.0
        elif _zone in (Zone.TRANSFINITE, Zone.LUDICROUS_LARGE):
            return float('+inf')
        elif _zone in (Zone.TRANSFINITE_NEG, Zone.LUDICROUS_LARGE_NEG):
            return float('-inf')
        else:
            return float('nan')

    def _to_float(self):
        try:
            qexp = self.qexponent()
        except ValueError:
            return 0.0
        (qan, qanlength) = self.qantissa()
        if self.raw < self.RAW_ZERO:
            qan -= exp256(qanlength)
            if qanlength > 0 and qan >= - exp256(qanlength-1):
                (qan, qanlength) = (-1,1)
        else:
            if qanlength == 0 or qan <=  exp256(qanlength-1):
                (qan, qanlength) = (1,1)
        exponent_base_2 = 8 * (qexp-qanlength)
        return math.ldexp(float(qan), exponent_base_2)

    def qantissa(self):
        """Extract the base-256 significand in its raw form.

        Returns a tuple:  (integer value of significand, number of qigits)
        The number of qigits is the amount stored in the qantissa,
        and is unrelated to the location of the radix point.
        """
        raw_qantissa = self.qan_raw()
        number_qantissa = unpack_big_integer(raw_qantissa)
        return tuple((number_qantissa, len(raw_qantissa)))

    def qan_raw(self):
        # TODO:  unit test
        return self.raw[self.qan_offset():]

    def qex_raw(self):
        # TODO:  unit test
        return self.raw[:self.qan_offset()]

    def qan_offset(self):
        # TODO:  unit test
        try:
            qan_offset = self.__qan_offset_dict[self.zone]
        except KeyError:
            raise self.QanValueError("qantissa() not defined for %s" % repr(self))
        return qan_offset

    class QanValueError(ValueError):
        """Qan for an unsupported zone raises this.  Trivial cases too, e.g. Number.ZERO.qantissa()"""

    __qan_offset_dict ={
        Zone.POSITIVE:       1,
        Zone.FRACTIONAL:     2,
        Zone.FRACTIONAL_NEG: 2,
        Zone.NEGATIVE:       1,
    }   # TODO:  ludicrous numbers should have a qantissa() too (offset 2^N)

    def qexponent(self):
        try:
            encoder = self.__qexponent_encode_dict[self.zone]
        except KeyError:
            raise self.QexValueError("qexponent() not defined for {}".format(repr(self)))
        try:
            qex = encoder(self)
        except IndexError:
            # TODO:  Unit test this branch.
            raise self.QexValueError("qexponent() broken for {}".format(repr(self)))
        return qex

    class QexValueError(ValueError):
        """There is no qex for some zones, e.g. Number.ZERO.qexponent()"""

    # The following dictionary reveals this conversion in its lambdas:
    #     base 256 exponent <-- qex
    #
    # Contrast _from_float().
    __qexponent_encode_dict = {   # qex-decoder, converting to a base-256-exponent from the internal qex format
        Zone.POSITIVE:       lambda self:         six.indexbytes(self.raw, 0) - 0x81,
        Zone.FRACTIONAL:     lambda self:         six.indexbytes(self.raw, 1) - 0xFF,
        Zone.FRACTIONAL_NEG: lambda self:  0x00 - six.indexbytes(self.raw, 1),
        Zone.NEGATIVE:       lambda self:  0x7E - six.indexbytes(self.raw, 0),
    }   # TODO: ludicrous numbers

    def hex(self):
        """Like q-string but denser.

        assert '822A' == Number('0q82_42').hex()
        """
        return hex_from_string(self.raw)

    def x_apostrophe_hex(self):
        return "x'" + self.hex() + "'"

    def zero_x_hex(self):
        return "0x" + self.hex()

    def ditto_backslash_hex(self):
        hex_digits = self.hex()
        escaped_hex_pairs = [r'\x' + hex_digits[i:i+2] for i in range(0, len(hex_digits), 2)]
        # THANKS:  http://stackoverflow.com/a/9475354/673991
        return '"' + ''.join(escaped_hex_pairs) + '"'

    mysql = x_apostrophe_hex

    # Zone Determination
    # ------------------
    @property
    def zone(self):
        try:
            return self._zone
        except AttributeError:   # (benign, this happens if _zone is missing from __slots__)
            return self._zone_from_scratch()

    def _zone_refresh(self):
        try:
            # noinspection PyDunderSlots,PyUnresolvedReferences
            self._zone = self._zone_from_scratch()
        except AttributeError:
            """Benign, this happens if _zone is missing from __slots__"""

    def _zone_from_scratch(self):
        zone_by_tree = self._find_zone_by_if_else_tree()
        assert zone_by_tree == self._find_zone_by_for_loop_scan(), \
            "Mismatched zone determination for %s:  if-tree=%s, loop-scan=%s" % (
                repr(self),
                self.name_of_zone[zone_by_tree],
                self.name_of_zone[self._find_zone_by_for_loop_scan()]
            )
        return zone_by_tree

    def _find_zone_by_for_loop_scan(self):   # slower than if-tree, but enforces Number.Zone value rules
        for z in self._sorted_zone_codes:
            if z <= self.raw:
                return z
        raise ValueError("Number._find_zone_by_for_loop_scan() fell through?!  '%s' < Zone.NAN!" % repr(self))

    def _find_zone_by_if_else_tree(self):   # likely faster than the loop-scan, for most values
        if self.raw > self.RAW_ZERO:
            if self.raw >= Zone.POSITIVE:
                if self.raw >= Zone.LUDICROUS_LARGE:
                    if self.raw >= Zone.TRANSFINITE:
                        return                  Zone.TRANSFINITE
                    else:
                        return                  Zone.LUDICROUS_LARGE
                else:
                    return                      Zone.POSITIVE
            else:
                if self.raw >= Zone.FRACTIONAL:
                    return                      Zone.FRACTIONAL
                elif self.raw >= Zone.LUDICROUS_SMALL:
                    return                      Zone.LUDICROUS_SMALL
                else:
                    return                      Zone.INFINITESIMAL
        elif self.raw == self.RAW_ZERO:
            return                              Zone.ZERO
        else:
            if self.raw > Zone.FRACTIONAL_NEG:
                if self.raw >= Zone.LUDICROUS_SMALL_NEG:
                    if self.raw >= Zone.INFINITESIMAL_NEG:
                        return                  Zone.INFINITESIMAL_NEG
                    else:
                        return                  Zone.LUDICROUS_SMALL_NEG
                else:
                    return                      Zone.FRACTIONAL_NEG
            else:
                if self.raw >= Zone.NEGATIVE:
                    return                      Zone.NEGATIVE
                elif self.raw >= Zone.LUDICROUS_LARGE_NEG:
                    return                      Zone.LUDICROUS_LARGE_NEG
                elif self.raw >= Zone.TRANSFINITE_NEG:
                    return                      Zone.TRANSFINITE_NEG
                else:
                    return                      Zone.NAN

    def is_suffixed(self):
        return self.raw[-1:] == b'\x00'
        # XXX:  This could be much less sneaky if raw were not the primary internal representation.
        # TODO:  is_suffixed(type)?

    def plus_suffix(self, suffix_or_type=None, payload=None):
        """
        Add a suffix to this Number.  Does not mutate self, but returns a new suffixed number.

        Forms:
            m = n.plus_suffix(Number.Suffix.TYPE_TEST, b'byte string')
            m = n.plus_suffix(Number.Suffix.TYPE_TEST, Number(x))
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
            raise Suffix.RawError
        if isinstance(suffix_or_type, Suffix):
            the_suffix = suffix_or_type
            return self.from_raw(self.raw + the_suffix.raw)
        else:
            the_type = suffix_or_type
            suffix = Suffix(the_type, payload)
            return self.plus_suffix(suffix)

    def minus_suffix(self, old_type=None):
        """Make a version of a number without any suffixes of the given type.  This does NOT mutate self."""
        # TODO:  A way to remove just ONE suffix of the given type?
        pieces = self.parse_suffixes()
        new_number = pieces[0]
        any_deleted = False
        for piece in pieces[1:]:
            if piece.type_ == old_type:
                any_deleted = True
            else:
                new_number = new_number.plus_suffix(piece.type_, piece.payload)
        if not any_deleted:
            raise Suffix.NoSuchType
        return new_number

    def get_suffix(self, sought_type):
        suffixes = self.parse_suffixes()
        for suffix in suffixes[1:]:
            if suffix.type_ == sought_type:
                return suffix
        raise Suffix.NoSuchType

    def get_suffix_payload(self, sought_type):
        # TODO:  Default value instead of NoSuchType?
        return self.get_suffix(sought_type).payload

    def get_suffix_number(self, sought_type):
        # TODO:  Default value instead of NoSuchType?
        return self.get_suffix(sought_type).payload_number()

    def parse_suffixes(self):
        """Parse a Number into its root and suffixes.

        Return a tuple of at least one element (the root of the Number)
        followed by zero or more suffixes.

        assert \
            (Number(1), Number.Suffix(2), Number.Suffix(3, b'\x4567')) == \
             Number(1)   .plus_suffix(2)   .plus_suffix(3, b'\x4567').parse_suffixes()
        """
        return_array = []
        n = Number(self)   # Is this really necessary? self.raw is immutable is it not?
        while True:
            last_byte = n.raw[-1:]
            if last_byte == b'\x00':
                try:
                    length_of_payload_plus_type = six.indexbytes(n.raw, -2)
                except IndexError:
                    raise Suffix.RawError("Invalid suffix, or unstripped 00s.")
                if length_of_payload_plus_type >= len(n.raw)-2:
                    # Suffix may neither be larger than raw, nor consume all of it.
                    raise Suffix.RawError("Invalid suffix, or unstripped 00s.")
                if length_of_payload_plus_type == 0x00:
                    return_array.append(Suffix())
                else:
                    try:
                        type_ = six.indexbytes(n.raw, -3)
                    except IndexError:
                        raise ValueError("Invalid suffix, or unstripped 00s.")
                    payload = n.raw[-length_of_payload_plus_type-2:-3]
                    return_array.append(Suffix(type_, payload))
                n = self.from_raw(n.raw[0:-length_of_payload_plus_type-2])
            else:
                break
        return_array.append(n)
        return tuple(reversed(return_array))


    name_of_zone = (lambda zone_class=Zone: {   # Translate zone code to zone name.
        getattr(zone_class, attr): attr
            for attr in dir(zone_class)
            if not callable(attr)
            and not attr.startswith("_")
            and attr.isupper()   # Allow ZONE to have member_functions()
    })()
    # THANKS:  Iterate class members, http://stackoverflow.com/a/11637457/673991
    # THANKS:  Comprehension on class member, http://stackoverflow.com/a/28130950/673991
    assert name_of_zone[Zone.ZERO] == 'ZERO'
    # TODO:  Test that name_of_zone['member_function'] raises IndexError.  Also may test:
    #     "__class__",
    #     "__delattr__",
    #     "__dict__",
    #     "__doc__",
    #     "__format__",
    #     "__getattribute__",
    #     "__hash__",
    #     "__init__",
    #     "__module__",
    #     "__new__",
    #     "__reduce__",
    #     "__reduce_ex__",
    #     "__repr__",
    #     "__setattr__",
    #     "__sizeof__",
    #     "__str__",
    #     "__subclasshook__",
    #     "__weakref__"

    _sorted_zone_codes = sorted(name_of_zone.keys(), reverse=True)
    ZONE_ALL = {zone for zone in _sorted_zone_codes}

    # Constants (see internal_setup())
    # ---------
    NAN = None   # NAN stands for Not-a-number, Ass-is-out-of-range, or Nullificationalized.
    ZERO = None
    POSITIVE_INFINITY = None        # Aleph-null aka aleph-naught
    POSITIVE_INFINITESIMAL = None   # Epsilon-nought aka epsilon-zero
    NEGATIVE_INFINITESIMAL = None
    NEGATIVE_INFINITY = None

    @classmethod
    def internal_setup(cls):
        """Initialize Number constants after the class is defined."""
        cls.NAN = cls(None)
        cls.ZERO = cls(0)
        cls.POSITIVE_INFINITY      = cls.from_raw(cls.RAW_INFINITY)
        cls.POSITIVE_INFINITESIMAL = cls.from_raw(cls.RAW_INFINITESIMAL)
        cls.NEGATIVE_INFINITESIMAL = cls.from_raw(cls.RAW_INFINITESIMAL_NEG)
        cls.NEGATIVE_INFINITY      = cls.from_raw(cls.RAW_INFINITY_NEG)


class Suffix(object):
    """
    A Number can have suffixes.  Suffixed numbers include, complex, alternate ID spaces, etc.

    Format of a nonempty suffix (uppercase letters represent hexadecimal digits):
        PP _ TT LL 00
    where:
        PP - 0-byte to 250-byte payload
         _ - underscore is a conventional qstring delimiter between payload and type-length-NUL
        TT - type code of the suffix, 0x00 to 0xFF or absent
        LL - length, number of bytes, including the type and payload, 0x00 to 0xFA
             but not including the length itself nor the NUL (see empty suffix)
        00 - NUL byte

    The "empty suffix" is two NUL bytes:
        0000

        That ia like saying LL is 00 means there are no type or payload parts.
        (It is not the same as type 00, which is otherwise available.)

    The NUL byte is what indicates there is a suffix.
    This is why an unsuffixed number has all its right-end 00-bytes stripped.

    A number can have multiple suffixes.
    If the payload of a suffix is itself a number, suffixes could be nested.

    Instance properties:
        payload - byte string
        type_ - integer 0x00 to 0xFF type code of suffix, or None for the empty suffix
        length_of_payload_plus_type - integer value of length byte, 0 to MAX_PAYLOAD_LENGTH
        raw - the encoded byte string suffix, including payload, type, length, and NUL

    Example:
        assert '778899_110400' == Number.Suffix(type_=0x11, payload=b'\x77\x88\x99').qstring()
    """
    # TODO:  Should Suffix be a sister class of Number instead of a contained class?
    # Because Suffix knows about Number (Suffix.number_class == Number) and vice versa.

    MAX_PAYLOAD_LENGTH = 250

    # TODO:  Formally define valid payload contents for each type
    # TODO:  Number.Suffix.Type class?
    TYPE_LISTING   = 0x1D   # 'ID' in 1337
    TYPE_IMAGINARY = 0x69   # 'i' in ASCII (three 0x69 suffixes for i,l,k quaternions, etc.)
    TYPE_TEST      = 0x7E   # for unit testing, payload can be anything
    # TODO:  stack-exchange question:  are quaternions a superset of complex numbers?  Does i===i?

    def __init__(self, type_=None, payload=None):
        assert isinstance(type_, (int, type(None)))
        self.type_ = type_
        if payload is None:
            self.payload = b''
        elif isinstance(payload, self.number_class):
            self.payload = payload.raw
        elif isinstance(payload, six.binary_type):
            self.payload = payload
        else:
            # TODO:  Support Number.Suffix(suffix)?  As a copy constructor, ala Number(number)
            raise self.PayloadError("Suffix payload cannot be a {}".format(type_name(payload)))
        if self.type_ is None:
            assert self.payload == b''
            # TODO:  Unit test this case?  Suffix(type None, payload not empty)
            self.length_of_payload_plus_type = 0
            self.raw = b'\x00\x00'
        else:
            self.length_of_payload_plus_type = len(self.payload) + 1
            if 0x00 <= self.length_of_payload_plus_type <= self.MAX_PAYLOAD_LENGTH+1:
                self.raw = self.payload + six.binary_type(bytearray((
                    self.type_,
                    self.length_of_payload_plus_type,
                    0x00
                )))
            else:
                raise self.PayloadError("Suffix payload is {} bytes too long.".format(
                    str(len(self.payload) - self.MAX_PAYLOAD_LENGTH))
                )

    def __eq__(self, other):
        return self.type_ == other.type_ and self.payload == other.payload

    def __repr__(self):
        if self.type_ is None:
            return "Number.Suffix()"
        else:
            return "Number.Suffix({type_}, b'{payload}')".format(
                type_=self.type_,
                payload="".join(["\\x{:02x}".format(byte_) for byte_ in self.payload]),
            )

    def __hash__(self):
        return hash(self.raw)

    def qstring(self, underscore=1):
        whole_suffix_in_hex = hex_from_string(self.raw)
        if underscore > 0 and self.payload:
            payload_hex = whole_suffix_in_hex[:-6]
            type_length_00_hex = whole_suffix_in_hex[-6:]
            return payload_hex + '_' + type_length_00_hex
        else:
            return whole_suffix_in_hex

    def payload_number(self):
        return self.number_class.from_raw(self.payload)

    @classmethod
    def internal_setup(cls, number_class):
        """Initialize some Suffix class properties after the class is defined."""
        cls.number_class = number_class
        # So Suffix can refer to Number:  qiki.Number.Suffix.Number === qiki.Number

    class NoSuchType(Exception):
        """Seek a type that is not there, e.g. Number(1).plus_suffix(0x22).get_suffix(0x33)"""

    class PayloadError(TypeError):
        """Suffix(payload=unexpected_type)"""

    class RawError(ValueError):
        """Unclean distinction between suffix and root, e.g. the crazy length 99 in 0q82_01__9900"""


Number.internal_setup()
Suffix.internal_setup(Number)


def _sets_exclusive(*the_sets):
    for i in range(len(the_sets)):
        for j in range(i):
            if set(the_sets[i]).intersection(the_sets[j]):
                return False
    return True
sets_exclusive = _sets_exclusive
assert True == sets_exclusive({1,2,3}, {4,5,6})
assert False == sets_exclusive({1,2,3}, {3,4,5})


def union_of_distinct_sets(*sets):
    assert sets_exclusive(*sets), "Sets not mutually exclusive:  %s" % repr(sets)
    return_value = set()
    for each_set in sets:
        return_value |= each_set
    return return_value
assert {1,2,3,4,5,6} == union_of_distinct_sets({1,2,3}, {4,5,6})


class ZoneSet(object):
    # Sets of Zones   TODO:  Venn Diagram or table or something.
    # -------------   TODO:  is_x() routine for each zone set X, e.g. is_reasonable()
    # TODO:  class ZONE_SET?  And put union_of_distinct_sets() in it too, instead of at the frikking top of this file.


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

    # TODO:  Maybe REASONABLY_ZERO  should include      infinitesimals and ludicrously small and zero
    #          and ESSENTIALLY_ZERO should include just infinitesimals                       and zero
    # Except then REASONABLY_ZERO overlaps UNREASONABLE (the ludicrously small).
    # Confusing?  Because then epsilon is both reasonable and unreasonable?
    # If not sufficiently confusing, we could also define
    # a REASONABLY_INFINITE set as ludicrously large plus transfinite.

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
        Zone.POSITIVE,
        Zone.NEGATIVE,
    }
    WHOLE_INDETERMINATE = {
        Zone.TRANSFINITE,
        Zone.LUDICROUS_LARGE,
        Zone.LUDICROUS_LARGE_NEG,
        Zone.TRANSFINITE_NEG,
    }

    MAYBE_PLATEAU = REASONABLY_NONZERO

    NAN = {
        Zone.NAN
    }
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

# Hex
# ---
def hex_from_integer(the_integer):
    """Encode a hexadecimal string from a big integer.

    Like hex() but output an even number of digits, no '0x' prefix, no 'L' suffix.
    """
    # THANKS:  Mike Boers code http://stackoverflow.com/a/777774/673991
    hex_string = hex(the_integer)[2:].rstrip('L')
    if len(hex_string) % 2:
        hex_string = '0' + hex_string
    return hex_string
assert 'ff' == hex_from_integer(255)
assert '0100' == hex_from_integer(256)


def string_from_hex(s):
    """Decode a hexadecimal string into an 8-bit binary (base-256) string.

    Raises a TypeError on invalid hex digits."""
    assert(isinstance(s, six.string_types))
    try:
        return binascii.unhexlify(s)
    except binascii.Error as e:   # This happens on '8X' in Python 3.  It is already a TypeError in Python 2.
        raise TypeError("aka binascii.Error: " + str(e))

assert b'\xBE\xEF' == string_from_hex('BEEF')


def hex_from_string(s):
    """Encode an 8-bit binary (base-256) string into a hexadecimal string."""
    assert(isinstance(s, six.binary_type))
    return binascii.hexlify(s).upper().decode()
assert 'BEEF' == hex_from_string(b'\xBE\xEF')


# Math
# ----
def exp256(e):
    """Compute 256**e for nonnegative integer e."""
    assert isinstance(e, six.integer_types)
    assert e >= 0
    return 1 << (e<<3)   # which is the same as 2**(e*8) or (2**8)**e or 256**e
assert 256 == exp256(1)
assert 65536 == exp256(2)


def log256(i):
    """Compute the log base 256 of an integer.  Return the floor integer."""
    assert i > 0
    return_value = (i.bit_length()-1) >> 3
    assert return_value == math.floor(math.log(i, 256)) or i > 2**47, "{0} {1} {2}".format(
        i,
        return_value,
        math.floor(math.log(i, 256))
    )
    assert return_value == len(hex_from_integer(i))//2 - 1
    return return_value
assert 1 == log256(256)
assert 2 == log256(65536)


def shift_leftward(n, nbits):
    """Shift positive left, or negative right."""
    if nbits < 0:
        return n >> -nbits
    else:
        return n << nbits
assert 64 == shift_leftward(32, 1)
assert 16 == shift_leftward(32, -1)


def floats_really_same(f1,f2):
    """Compare floating point numbers, a little differently.

    Similar to == except:
     1. They ARE the same if both are NAN.
     2. They are NOT the same if one is +0.0 and the other -0.0.

    This is useful for precise unit testing.
    """
    assert type(f1) is float
    assert type(f2) is float
    if math.isnan(f1) and math.isnan(f2):
        return True
    if math.copysign(1,f1) != math.copysign(1,f2):
        # THANKS:  http://stackoverflow.com/a/25338224/673991
        return False
    return f1 == f2
assert True == floats_really_same(float('nan'), float('nan'))
assert False == floats_really_same(+0.0, -0.0)


# Padding and Unpadding Strings
# -----------------------------
def left_pad00(the_string, nbytes):
    """Make a string nbytes long by padding '\x00's on the left."""
    # THANKS:  Jeff Mercado http://stackoverflow.com/a/5773669/673991
    assert(isinstance(the_string, six.binary_type))
    return the_string.rjust(nbytes, b'\x00')
assert b'\x00\x00string' == left_pad00(b'string', 8)


def right_strip00(the_string):
    """Remove '\x00' NULs from the right end of a string."""
    assert(isinstance(the_string, six.binary_type))
    return the_string.rstrip(b'\x00')
assert b'string' == right_strip00(b'string\x00\x00')


# Packing and Unpacking Integers
# ------------------------------
def pack_integer(the_integer, nbytes=None):
    """Pack an integer into a binary string, which is like a base-256, big-endian string.

    :param the_integer:  an arbitrarily large integer
    :param nbytes:  number of bytes (base-256 digits) to output (omit for minimum)
    :return:  an unsigned two's complement string, MSB first

    Caution, there may not be a "sign bit" in the output unless nbytes is large enough.
        assert     b'\xFF' == pack_integer(255)
        assert b'\x00\xFF' == pack_integer(255,2)
        assert     b'\x01' == pack_integer(-255)
        assert b'\xFF\x01' == pack_integer(-255,2)
    Caution, nbytes lower than minimum may not be enforced, see unit tests.
    """
    # GENERIC: This function might be useful elsewhere.

    if nbytes is None:
        nbytes =  log256(abs(the_integer)) + 1

    if nbytes <= 8 and 0 <= the_integer < 4294967296:
        return struct.pack('>Q', the_integer)[8-nbytes:]  # timeit says this is 4x as fast as the Mike Boers way
    elif nbytes <= 8 and -2147483648 <= the_integer < 2147483648:
        return struct.pack('>q', the_integer)[8-nbytes:]
    else:
        return pack_big_integer_via_hex(the_integer, nbytes)
assert b'\x00\xAA' == pack_integer(170,2)
assert b'\xFF\x56' == pack_integer(-170,2)


def pack_big_integer_via_hex(num, nbytes):
    """Pack an integer into a binary string.

    Akin to base-256 encode.
    """
    # THANKS:  http://stackoverflow.com/a/777774/673991
    if num >= 0:
        num_twos_complement = num
    else:
        num_twos_complement = num + exp256(nbytes)   # two's complement of big negative integers
    return left_pad00(
        string_from_hex(
            hex_from_integer(
                num_twos_complement
            )
        ),
        nbytes
    )
assert b'\x00\xAA' == pack_big_integer_via_hex(170,2)
assert b'\xFF\x56' == pack_big_integer_via_hex(-170,2)


def unpack_big_integer_by_struct(binary_string):
    """Fast version of unpack_big_integer(), limited to 64 bits."""
    return struct.unpack('>Q', left_pad00(binary_string, 8))[0]


def unpack_big_integer_by_brute(binary_string):
    """Universal version of unpack_big_integer()."""
    return_value = 0
    for i in range(len(binary_string)):
        return_value <<= 8
        return_value |= six.indexbytes(binary_string, i)
    return return_value


def unpack_big_integer(binary_string):
    """Convert a byte string into an integer.

    Akin to a base-256 decode, big-endian.
    """
    if len(binary_string) <= 8:
        return unpack_big_integer_by_struct(binary_string)
        # NOTE:  1.1 to 4 times as fast as _unpack_big_integer_by_brute()
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
        return x.__class__.__name__
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
# TODO:  complex
# TODO:  Numpy types
# SEE:  http://docs.scipy.org/doc/numpy/user/basics.types.html
# TODO:  other Numpy compatibilities?
# TODO:  fractions.Fraction -- rational numbers

# TODO:  Number.inc() native - taking advantage of raw encodings
# TODO:  __neg__ native - taking advantage of two's complement encoding of (non suffixed) qex + qan
#        (and fixing it for unreasonable numbers)
# TODO:  Possibly generate an exception for __neg__ of suffixed number?  For any math on suffixed numbers??
# TODO:  __add__, __mul__, etc. native
# TODO:  other Number(string)s, e.g. assert 1 == Number('1')

# TODO:  hooks to add features modularly, e.g. suffixes
# TODO:  change % to .format()
# TODO:  change raw from str/bytes to bytearray?
# SEE:  http://ze.phyr.us/bytearray/
# TODO:  raise subclass of built-in exceptions
# TODO:  combine qantissa() and qexponent() into _unpack() that extracts all three pieces (qex, qan, qan_length)
# TODO:  _pack() opposite of _unpack() -- and use it in _from_float(), _from_int()
# TODO:  str(Number('0q80')) should be '0'.  str(Number.NAN) should be '0q'
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

# TODO:  Better object internal representation:  store separate qex, qan, suffixes (and synthesize raw on demand)
# perhaps raw == qex + qan + ''.join([suffix.raw for suffix in suffixes])

# TODO:  Number.to_JSON()
# THANKS:  http://stackoverflow.com/q/3768895/673991

# TODO:  mpmath support, http://mpmath.org/
# >>> mpmath.frexp(mpmath.power(mpmath.mpf(2), 65536))
# (mpf('0.5'), 65537)

# TODO:  is_valid() detects (at different severity levels?)  Or validate() raising a family tree of exceptions:
# 0q82_00FF - as 1 but inside the plateau
# 0q82 as - compact but nonstandard
# 0q8183_01 - sensible as 2**-1000 but really should be ludicrous small encoding (longer qex)
# 0q__7E0100 - suffixed NAN
# 0q80__00 - 00-terminated means it should be suffixed but clearly it is not

# TODO:  Lengthed-export.
# The raw attribute is an unlengthed representation of the number.
# That is to say there is no way to know the length of a string of raw bytes from their content.
# Content carries no reliable indication of its length.  Length must be encoded extrinsically somehow.
# So this unlengthed word.raw attribute may be used as the content for a VARBINARY
# field of a MySQL table, where MySQL manages the length of that field.
# For applications where a stream of bytes must encode its own length, a different
# approach must be used.
# One approach might be that if the first byte is 80-FF, what follows is a
# positive integer with no zero stripping. In effect, the first byte is
# the length (including itself) plus 80 hex.  Values could be:
# 8201 8202 8203 ... 82FF 830100 830101 830102 ... FE01(124 00s) ... FEFF(124 FFs)
#    1    2    3      255    256    257    258     2**992            2**1000-1
# In these cases the lengthed-export has the same bytes as the unlengthed export
# except for multiples of 256, e.g. it's 830100 not 8301 (for 0q83_01 == 256).
# (Because of the no-trailing-00 rule for raw.  That rule would not apply to lengthed exported integers.)
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
# So the sequence 7F 80 81 8202 8203 8204 ...
#     represents  -1  0  1    2    3    4 ...

# Negative one might be handy as a brief value.
# Though 017D could encode it, as could 027DFF But maybe plain 7F would be great.
# Then 00-7E would encode "other" (nonnegative, not-minus-one numbers)
# Or 00-7D could be lengthed prefixes that are straightforward, and
# 7E could be a special extender value,
# similar to the FF00FFFF... extended (2^n byte) lex in ludicrous numbers.
# There would be 2^n 7E bytes followed by 2^n (the same n) bytes encoding (MSB first) the real length.
# So e.g. a 256 byte raw value would be lengthed as 7E7E0100...(and then 256 bytes same as raw)
# A 65536-byte raw would have a lengthed-prefix of 7E7E7E7E00010000
# But the number of 7E bytes don't have to be a power of 2, they way they do with the qex
#     (Wait, why do the qex extenders have to be 2^n bytes?)

# So in a way, length bytes 00-7D would be shorthand for 7E00 to 7E7D.
# And                      8202 to FD...(124 FFs) representing integers 2 to 2**992-1
# would be shorthand for 028202 to 7DFD...(124 FFs),
# itself shorthand for 7E028202 to 7E7DFD...(124 FFs)
# theoretically as 7E7E00028202 to 7E7E007DFD...(124 FFs), etc.

# FORMAL DEFINITION:
# The way to look at the lengthed-export version of a Number is that it always conceptually consists of:
#     7E-part, length-part, raw-part, 00-part
# 7E-part is Np bytes of literal 7E.
#     the 7E-part may be omitted if length-part (N) is 0 to 7D.
# length-part (call it N) is Np bytes representing a (big-endian) length N (so N < 256**Np)
#     both 7E-part and length-part may be omitted for an unsuffixed integer 0 to 2**992-1
# raw-part is N bytes, identical to the bytes of Number.raw
# 00-part consists of 00 bytes.
#     It only exists if 7E-part and length-part are omitted.
#     It serves to make the total length (of the entire lengthed-export)
#         equal to the first raw byte minus 81.
#         Except for Number(0) where the raw-part is 80.
#             Then the 00-part is not -1 bytes, it's just empty.
#     So the 00-part is only nonempty (1 or more bytes) for unsuffixed integer multiples of 256.
#     And it's 2 or more bytes for unsuffixed integer multiples of 256**2, etc.
# 7F is an alias for 027DFF representing 0q7D_FF aka -1.
# 81 is an alias for 8201 representing 0q82_01 aka 1.
#     These two weirdo exceptions are the only cases without a raw-part.
#     For every other Number, there is a raw-part in its lengthed-export and it's identical to Number.raw.

# Number.NAN would be seamlessly length-exported as 00.  (Length-part=00, other parts omitted.)
#     The other weirdo case where Number.raw is empty.  So the raw-part is in there, it's just empty.

# Cases with a nonempty 7E-part, i.e. Np > 0:
#     Say the raw-part is 128 bytes (e.g. lots of suffixes, e.g. googolplex approximations)
#         then N is 128 and Np is 1
#         7E 80 (128-byte raw-part)

# The following indented part is bogus.  I think.  Leaving it around until sure:
#     Notice there is no shorthand for the sliver of integers at the top of the reasonable numbers:
#     0qFE_01 == 2**992 to 0qFE_FF...(124 more FFs) == 2**1000-1
#     The lengthed exports of those would be:
#     7E02FE01 to 7E7E007EFEFF...(124 more FFs)
# Wrong, FE01(plus 124 00s) makes sense for 2**992

# This lengthed export is not monotonic.

# This scheme leaves an initial FF free for future something-or-other.

# What to call it?
#     lengthed export
#     dna
#     freeze-dried
#     p-string
#         "packed"
#         "packet"
#         but it is not a string
#         but p has some symmetry with q
#         but it should not)
#     b or d string would also be symmetrical with q, but it should rather be symmetrical with raw
#     ink
#     What real-world analogy for packaging a word for transport down a stream?
#     stream byte array
#     morse code
#     packet
#     Think of a tardigrade, dessicated.  And reconstituted back to life.
#         but this is not condensing, in fact it is expanding.
#         really is more like a packetized number

# The lengthed-export version of a Number might be useful for embedding multiple numbers in a suffix.
# An example of multiple numbers in a suffix might be a "user-defined" type for a suffix
#     where one number identifies the user, and the other has user-defined meaning.
# This seems complicated and intricate (complicantricate?) but so are consecutive or nested suffixes.
# Particularly in the case of user-defined suffix types, we want the syntax to be simple
# so it's easy to use, and economical with bytes, so the 250 or so 1-byte suffix types are greedily sought
# and we can be extremely parsimonious with them.