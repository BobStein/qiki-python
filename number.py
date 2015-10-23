"""
Qiki Numbers

Both integers and floating point seamlessly represented
Features:
 - arbitrary precision
 - arbitrary range
 - monotonicity (memcmp() order)
"""

import binascii
import math
import struct

import six


# noinspection PyUnresolvedReferences
class Number(object):

    __slots__ = ('__raw', )   # less memory
    # __slots__ = ('__raw', '_zone')   # faster

    def __init__(self, content=None, qigits=None):
        if isinstance(content, six.integer_types):
            self._from_int(content)
        elif isinstance(content, float):
            self._from_float(content, qigits)
        elif isinstance(content, type(self)):  # Number(SonOfNumber())
            self.raw = content.raw
        elif isinstance(self, type(content)):  # SonOfNumber(Number())
            self.raw = content.raw
        elif isinstance(content, six.string_types):
            self._from_string(content)
        elif content is None:
            self.raw = self.RAW_NAN
        else:
            typename = type(content).__name__
            if typename == 'instance':
                typename = content.__class__.__name__
            raise TypeError("{outer}({inner}) is not supported".format(
                outer=type(self).__name__,
                inner=typename,
            ))
        assert(isinstance(self.__raw, six.binary_type))

    RAW_INF     = b'\xFF\x81'
    RAW_ZERO    = b'\x80'
    RAW_INF_NEG = b'\x00\x7F'
    RAW_NAN     = b''


    # Zones
    # -----
    # qiki Numbers fall into zones.
    # The internal Number.Zone class serves as an enumeration.
    # Its members of Number.Zone have values that are *between* zones.
    # Raw, internal binary strings are represented by these values.
    # Each value is less than or equal to all raw values in the zone they represent,
    # and greater than all valid values in the zones below.
    # (So actually, some zone values are valid raw values, others are among the inter-zone values.)
    # The valid raw string for 1 is b'x82\x01' but Number.Zone.POSITIVE is b'x82'.
    # Anything between b'x82' and b'x82\x01' will be interpreted as 1 by any Number Consumer (NumberCon).
    # But any Number Producer (NumberPro) that generates a 1 should generate the raw string b'x82\x01'.

    class Zone(object):
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
        NAN                 = b''   # NAN means Not-a-number, Ass-is-out-of-range, or Nullificationalized.


    # float precision
    # ---------------
    # A "qigit" is a qiki Number byte, or base-256 digit.
    # Number(float) defaults to 8 qigits, for lossless representation of a Python float.
    # IEEE 754 double precision has a 53-bit significand (52 bits stored + 1 implied).
    # SEE:  http://en.wikipedia.org/wiki/Double-precision_floating-point_format
    # Why are 8 qigits needed to store 53 bits, not 7?
    # That's because the most significant qigit may not store a full 8 bits, it may store as few as 1.
    # So 8 qigits can store 57-64 bits, and that may be needed to store 53.
    # For example 1.2 == 0q82_0133333333333330 stores 1+8+8+8+8+8+8+4 = 53 bits in 8 qigits
    # These 8 bytes are the
    QIGITS_PRECISION_DEFAULT = 8

    @property
    def raw(self):
        return self.__raw

    @raw.setter
    def raw(self, value):
        assert(isinstance(value, six.binary_type))
        # noinspection PyAttributeOutsideInit
        self.__raw = value
        self._zone_refresh()

    def __getstate__(self):
        return self.raw

    def __setstate__(self, d):
        self.raw = d

    def __repr__(self):
        return "Number('{}')".format(self.qstring())

    def __str__(self):
        return self.qstring()

    __eq__ = lambda self, other:  Number(self).raw == Number(other).raw
    __ne__ = lambda self, other:  Number(self).raw != Number(other).raw
    __lt__ = lambda self, other:  Number(self).raw <  Number(other).raw
    __le__ = lambda self, other:  Number(self).raw <= Number(other).raw
    __gt__ = lambda self, other:  Number(self).raw >  Number(other).raw
    __ge__ = lambda self, other:  Number(self).raw >= Number(other).raw

    def __hash__(self):
        return hash(self.raw)

    def __sub__(self, other):
        n1 = Number(self)
        n2 = Number(other)
        if n1.is_whole() and n2.is_whole():
            return Number(int(n1) - int(n2))
        else:
            return Number(float(n1) - float(n2))

    def __neg__(self):
        n = Number(self)
        if n.is_whole():
            return Number(-int(n))
        else:
            return Number(-float(n))

    def __rsub__(self, other):
        return -self.__sub__(other)

    def __add__(self, other):
        n1 = Number(self)
        n2 = Number(other)
        if n1.is_whole() and n2.is_whole():
            return Number(int(n1) + int(n2))
        else:
            return Number(float(n1) + float(n2))
    __radd__ = __add__

    def is_whole(self):
        if self.zone in self.ZONE_WHOLE_MAYBE:
            (qan, qanlength) = self.qantissa()
            qexp = self.qexponent() - qanlength
            if qexp >= 0:
                return True
            else:
                if qan % self._exp256(-qexp) == 0:
                    return True
                else:
                    return False
        elif self.zone in self.ZONE_WHOLE_YES:
            return True
        elif self.zone in self.ZONE_WHOLE_NO:
            return False
        else:
            raise   # TODO: raise WholeIndeterminate()?

    def is_nan(self):
        return self == self.NAN

    @classmethod
    def from_raw(cls, value):
        """Construct a Number from its raw, internal binary string of qigits

        Right:  assert Number(1) == Number(0q82_01')
        Wrong:                      Number(b'\x82\x01')
        Right:  assert Number(1) == Number.from_raw(b'\x82\x01')
        Right:  assert Number(1) == Number.from_raw(bytearray(b'\x82\x01'))
        """
        if not isinstance(value, six.binary_type):
            raise ValueError("'{}' is not a binary string.  "
                             "Number.from_raw(needs e.g. b'\\x82\\x01')".format(repr(value)))
        return_value = cls()
        return_value.raw = value
        return return_value

    @classmethod
    def from_bytearray(cls, value):
        return cls.from_raw(six.binary_type(value))

    from_mysql = from_bytearray

    def _from_string(self, s):
        """Construct a Number from a printable, hexadecimal rendering of its raw, internal binary string of qigits

        Example:  assert Number(1) == Number('0q82_01')
        """
        assert(isinstance(s, six.string_types))
        if s[:2] == '0q':
            sdigits = s[2:].replace('_', '')
            if len(sdigits) % 2 != 0:
                sdigits += '0'
            try:
                sdecoded = self.hex_decode(sdigits)
            except TypeError:
                raise ValueError("A qiki Number string must use hexadecimal digits (or underscore), not '{}'".format(s))
            self.raw = six.binary_type(sdecoded)
        else:
            raise ValueError("A qiki Number string must start with '0q' instead of '{}'".format(s))

    def _from_float(self, x, qigits = None):
        """Construct a Number from a Python IEEE 754 double-precision floating point number

        Example:  assert Number(1) == Number(1.0)
        Example:  assert '0q82_01' == Number(1.0).qstring()
        Example:  assert '0q82_03243F6A8885A3' = Number(math.pi).qstring()
        """
        if qigits is None or qigits <= 0:
            qigits = self.QIGITS_PRECISION_DEFAULT

        if math.isnan(x):        self.raw =           self.RAW_NAN
        elif x >= float('+inf'): self.raw =           self.RAW_INF
        elif x >=  1.0:          self.raw =           self._raw_from_float(x, lambda e: 0x81+e, qigits)   # qex <-- e256
        elif x >   0.0:          self.raw = b'\x81' + self._raw_from_float(x, lambda e: 0xFF+e, qigits)
        elif x ==  0.0:          self.raw =           self.RAW_ZERO
        elif x >  -1.0:          self.raw = b'\x7E' + self._raw_from_float(x, lambda e: 0x00-e, qigits)
        elif x > float('-inf'):  self.raw =           self._raw_from_float(x, lambda e: 0x7E-e, qigits)
        else:                    self.raw =           self.RAW_INF_NEG

    def _from_int(self, i):
        if   i >  0:   self.raw = self._raw_from_int(i, lambda e: 0x81+e)
        elif i == 0:   self.raw = self.RAW_ZERO
        else:          self.raw = self._raw_from_int(i, lambda e: 0x7E-e)

    @classmethod
    def _raw_from_float(cls, x, qex_encoder, qigits):
        """Convert nonzero float to internal raw format

        qex_encoder() converts a base-256 exponent to internal qex format
        """
        (significand_base_2, exponent_base_2) = math.frexp(x)
        assert x == significand_base_2 * 2.0**exponent_base_2
        assert 0.5 <= abs(significand_base_2) < 1.0

        (exponent_base_256, zero_to_seven) = divmod(exponent_base_2+7, 8)
        significand_base_256 = significand_base_2 * (2 ** (zero_to_seven-7))
        assert x == significand_base_256 * 256.0**exponent_base_256
        assert 0.00390625 <= abs(significand_base_256) < 1.0

        qan_integer = int(significand_base_256 * cls._exp256(qigits) + 0.5)
        qan00 = cls._pack_integer(qan_integer, qigits)
        qan = cls._right_strip00(qan00)

        qex_integer = qex_encoder(exponent_base_256)
        qex = six.int2byte(qex_integer)

        return qex + qan

    @classmethod
    def _raw_from_int(cls, i, qex_encoder):
        """Convert nonzero integer to internal raw format.

        qex_encoder() converts a base-256 exponent to internal qex format
        """
        qan00 = cls._pack_integer(i)
        qan = cls._right_strip00(qan00)

        exponent_base_256 = len(qan00)
        qex_integer = qex_encoder(exponent_base_256)
        qex = six.int2byte(qex_integer)

        return qex + qan

    @classmethod
    def _pack_integer(cls, the_integer, nbytes=None):
        """Pack an integer into a binary string, which is like a base-256, big-endian string.

        :param the_integer:  an arbitrarily large integer
        :param nbytes:  number of bytes (base-256 digits) to output (omit for minimum)
        :return:  an unsigned two's complement string, MSB first

        Caution, there may not be a "sign bit" in the output unless nbytes is large enough.
            assert     b'\xFF' == Number._pack_integer(255)
            assert b'\x00\xFF' == Number._pack_integer(255,2)
            assert     b'\x01' == Number._pack_integer(-255)
            assert b'\xFF\x01' == Number._pack_integer(-255,2)
        Caution, nbytes lower than minimum may not be enforced, see unit tests
        """
        # GENERIC: This function might be useful elsewhere.

        if nbytes is None:
            nbytes = len(cls._hex_even(abs(the_integer)))//2   # nbytes default = 1 + floor(log(abs(the_integer), 256))

        if nbytes <= 8 and 0 <= the_integer < 4294967296:
            return struct.pack('>Q', the_integer)[8-nbytes:]  # timeit says this is 4x as fast as the Mike Boers way
        elif nbytes <= 8 and -2147483648 <= the_integer < 2147483648:
            return struct.pack('>q', the_integer)[8-nbytes:]
        else:
            return cls._pack_big_integer_via_hex(the_integer, nbytes)

    @classmethod
    def _pack_big_integer_via_hex(cls, num, nbytes):
        """Pack an integer into a binary string.

        Akin to base-256 encode
        """
        # THANKS:  http://stackoverflow.com/a/777774/673991
        if num >= 0:
            num_twos_complement = num
        else:
            num_twos_complement = num + cls._exp256(nbytes)   # two's complement of big negative integers
        return cls._left_pad00(
            cls.hex_decode(
                cls._hex_even(
                    num_twos_complement
                )
            ),
            nbytes
        )

    @staticmethod
    def _hex_even(the_integer):
        """Encode a hexadecimal string from a big integer.

        like hex() but even number of digits, no '0x' prefix, no 'L' suffix
        """
        # THANKS:  Mike Boers code http://stackoverflow.com/a/777774/673991
        # GENERIC:  This function might be useful elsewhere.
        hex_string = hex(the_integer)[2:].rstrip('L')
        if len(hex_string) % 2:
            hex_string = '0' + hex_string
        return hex_string
    assert 'ff' == _hex_even.__func__(255)
    assert '0100' == _hex_even.__func__(256)
    # THANKS:  http://stackoverflow.com/a/12718272/673991

    @staticmethod
    def _left_pad00(the_string, nbytes):
        """Make a string nbytes long by padding '\x00's on the left."""
        # THANKS:  Jeff Mercado http://stackoverflow.com/a/5773669/673991
        assert(isinstance(the_string, six.binary_type))
        return the_string.rjust(nbytes, b'\x00')
    assert b'\x00\x00abcd' == _left_pad00.__func__(b'abcd', 6)

    @staticmethod
    def _right_strip00(the_string):
        """Remove '\x00' NULs from the right end of a string."""
        assert(isinstance(the_string, six.binary_type))
        return the_string.rstrip(b'\x00')
    assert b'abcd' == _right_strip00.__func__(b'abcd\x00\x00')

    @staticmethod
    def _exp256(e):
        """Compute 256**e for nonnegative integer e."""
        assert isinstance(e, six.integer_types)
        assert e >= 0
        return 1 << (e<<3)   # which is the same as 2**(e*8) or (2**8)**e or 256**e
    assert 256 == _exp256.__func__(1)
    assert 65536 == _exp256.__func__(2)

    def qstring(self, underscore=1):
        """Output Number in '0qHHHHHH' string form.

        assert '0q85_1234ABCD' == Number(0x1234ABCD).qstring()
        Q-string is a human-readable form of the raw representation of a qiki number
        Similar to 0x12AB for hexadecimal
        Except q for x, underscores optional, and of course the value interpretation differs.
        """
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
                offset = 1   # TODO:  ludicrous numbers have bigger offsets (for googolplex it's 64)
            h = self.hex_encode(root_raw)
            if length <= offset:
                return_value = '0q' + h
            else:
                return_value = '0q' + h[:2*offset] + '_' + h[2*offset:]
            for suffix in parsed_suffixes:
                return_value += '__'
                return_value += suffix.qstring(underscore)
        return return_value

    def hex(self):
        return self.hex_encode(self.raw)

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

    @staticmethod
    def hex_decode(s):
        """Decode a hexadecimal string into an 8-bit binary (base-256) string."""
        # GENERIC:  This function might be useful elsewhere.
        assert(isinstance(s, six.string_types))
        return binascii.unhexlify(s)
    assert b'\xBE\xEF' == hex_decode.__func__('BEEF')

    @staticmethod
    def hex_encode(s):
        """Encode an 8-bit binary (base-256) string into a hexadecimal string."""
        # GENERIC:  This function might be useful elsewhere.
        assert(isinstance(s, six.binary_type))
        return binascii.hexlify(s).upper().decode()
    assert 'BEEF' == hex_encode.__func__(b'\xBE\xEF')

    def qantissa(self):
        """Extract the base-256 significand in its raw form.

        Returns a tuple:  (integer value of significand, number of qigits)
        The number of qigits is the amount stored in the qantissa,
        and is unrelated to the location of the decimal point.
        """
        try:
            qan_offset = self.__qan_offset_dict[self.zone]
        except KeyError:
            raise ValueError("qantissa() not defined for %s" % repr(self))
        number_qantissa = self._unpack_big_integer(self.raw[qan_offset:])
        return tuple((number_qantissa, len(self.raw) - qan_offset))

    __qan_offset_dict ={
        Zone.POSITIVE:       1,
        Zone.FRACTIONAL:     2,
        Zone.FRACTIONAL_NEG: 2,
        Zone.NEGATIVE:       1,
    }   # TODO:  ludicrous numbers should have a qantissa() too (offset 2^N)

    @classmethod
    def _unpack_big_integer(cls, binary_string):
        """Convert a byte string into an integer.

        Akin to a base-256 decode, big-endian.
        """
        if len(binary_string) <= 8:
            return cls._unpack_big_integer_by_struct(binary_string)
        else:
            return cls._unpack_big_integer_by_brute(binary_string)

    @classmethod
    def _unpack_big_integer_by_struct(cls, binary_string):   # 1.1 to 4 times as fast as _unpack_big_integer_by_brute()
        return struct.unpack('>Q', cls._left_pad00(binary_string, 8))[0]

    @classmethod
    def _unpack_big_integer_by_brute(cls, binary_string):
        return_value = 0
        for i in range(len(binary_string)):
            return_value <<= 8
            return_value |= six.indexbytes(binary_string, i)
        return return_value

    def qexponent(self):
        try:
            encoder = self.__qexponent_encode_dict[self.zone]
        except KeyError:
            raise ValueError("qexponent() not defined for %s" % repr(self))
        try:
            qex = encoder(self)
        except IndexError:
            qex = 0   # XXX:  e.g. 0q81.  Though that qex is more like negative infinity.
        return qex

    __qexponent_encode_dict = {   # qex-decoder, converting to a base-256-exponent from the internal qex format
        Zone.POSITIVE:       lambda self:         six.indexbytes(self.raw, 0) - 0x81,   # e256 <-- qex
        Zone.FRACTIONAL:     lambda self:         six.indexbytes(self.raw, 1) - 0xFF,
        Zone.FRACTIONAL_NEG: lambda self:  0x00 - six.indexbytes(self.raw, 1),
        Zone.NEGATIVE:       lambda self:  0x7E - six.indexbytes(self.raw, 0),
    }   # TODO: ludicrous numbers

    def __long__(self):
       return long(self.__int__())

    def __int__(self):
        int_by_dictionary = self.__int__by_zone_dictionary()
        assert int_by_dictionary == self.__int__by_zone_ifs(), (
            "Mismatched int encoding for %s:  tree method=%s, scan method=%s" % (
                repr(self), int_by_dictionary, self.__int__by_zone_ifs()
            )
        )
        return int_by_dictionary

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
        if self.Zone.LUDICROUS_LARGE <= self.raw:
            return self._int_cant_be_positive_infinity
        elif self.Zone.POSITIVE <= self.raw:
            return self._to_int_positive()
        elif self.Zone.FRACTIONAL_NEG <= self.raw:
            return 0
        elif self.Zone.NEGATIVE <= self.raw:
            return self._to_int_negative()
        elif self.Zone.NAN < self.raw:
            return self._int_cant_be_negative_infinity()
        else:
            return self._int_cant_be_nan()

    @staticmethod
    def _int_cant_be_positive_infinity():
        raise OverflowError("Positive Infinity cannot be represented by integers")

    @staticmethod
    def _int_cant_be_negative_infinity():
        raise OverflowError("Negative Infinity cannot be represented by integers")

    @staticmethod
    def _int_cant_be_nan():
        raise ValueError("Not-A-Number cannot be represented by integers")

    def _to_int_positive(self):
        (qan, qanlength) = self.qantissa()
        qexp = self.qexponent() - qanlength
        return self._shift_left(qan, qexp*8)

    def _to_int_negative(self):
        (qan,qanlength) = self.qantissa()
        qexp = self.qexponent() - qanlength
        qan_negative = qan - self._exp256(qanlength)
        the_int = self._shift_left(qan_negative, qexp*8)
        if qexp < 0:
            extraneous_mask = self._exp256(-qexp) - 1
            extraneous = qan_negative & extraneous_mask   # XXX:  a more graceful way to floor to 0 instead of to -inf
            if extraneous != 0:
                the_int += 1
        return the_int

    @staticmethod
    def _shift_left(n, nbits):
        """Shift positive left, or negative right."""
        # GENERIC:  This function might be useful elsewhere.
        if nbits < 0:
            return n >> -nbits
        else:
            return n << nbits

    assert 64 == _shift_left.__func__(32, 1)
    assert 16 == _shift_left.__func__(32, -1)

    @property
    def zone(self):
        try:
            return self._zone
        except AttributeError:   # (benign, _zone missing from __slots__)
            return self._zone_from_scratch()

    def _zone_refresh(self):
        try:
            self._zone = self._zone_from_scratch()
        except AttributeError:   # (benign, _zone missing from __slots__)
            pass

    def _zone_from_scratch(self):
        zone_by_tree = self._find_zone_by_if_else_tree()
        assert zone_by_tree == self._find_zone_by_for_loop_scan(), \
            "Mismatched zone determination for %s:  tree=%s, scan=%s" % (
                repr(self),
                self.name_of_zone[zone_by_tree],
                self.name_of_zone[self._find_zone_by_for_loop_scan()]
            )
        return zone_by_tree

    def _find_zone_by_for_loop_scan(self):   # likely slower than tree, but helps enforce self.Zone values
        for z in self._sorted_zones:
            if z <= self.raw:
                return z
        raise ValueError("Number._find_zone_by_for_loop_scan() fell through?!  '%s' < Zone.NAN!" % repr(self))

    def _find_zone_by_if_else_tree(self):  # likely faster than a scan, for most values
        if self.raw > self.RAW_ZERO:
            if self.raw >= self.Zone.POSITIVE:
                if self.raw >= self.Zone.LUDICROUS_LARGE:
                    if self.raw >= self.Zone.TRANSFINITE:
                        return                  self.Zone.TRANSFINITE
                    else:
                        return                  self.Zone.LUDICROUS_LARGE
                else:
                    return                      self.Zone.POSITIVE
            else:
                if self.raw >= self.Zone.FRACTIONAL:
                    return                      self.Zone.FRACTIONAL
                elif self.raw >= self.Zone.LUDICROUS_SMALL:
                    return                      self.Zone.LUDICROUS_SMALL
                else:
                    return                      self.Zone.INFINITESIMAL
        elif self.raw == self.RAW_ZERO:
            return                              self.Zone.ZERO
        else:
            if self.raw > self.Zone.FRACTIONAL_NEG:
                if self.raw >= self.Zone.LUDICROUS_SMALL_NEG:
                    if self.raw >= self.Zone.INFINITESIMAL_NEG:
                        return                  self.Zone.INFINITESIMAL_NEG
                    else:
                        return                  self.Zone.LUDICROUS_SMALL_NEG
                else:
                    return                      self.Zone.FRACTIONAL_NEG
            else:
                if self.raw >= self.Zone.NEGATIVE:
                    return                      self.Zone.NEGATIVE
                elif self.raw >= self.Zone.LUDICROUS_LARGE_NEG:
                    return                      self.Zone.LUDICROUS_LARGE_NEG
                elif self.raw >= self.Zone.TRANSFINITE_NEG:
                    return                      self.Zone.TRANSFINITE_NEG
                else:
                    return                      self.Zone.NAN

    @staticmethod
    def _floats_really_same(f1,f2):
        """Compare floating point numbers, a little differently.

        Similar to == except:
         1. They are the same if both are NAN.
         2. They are NOT the same if one is +0.0 and the other -0.0.

        This is useful for precise unit testing.
        """
        # GENERIC:  This function might be useful elsewhere.
        assert type(f1) is float
        assert type(f2) is float
        if math.isnan(f1) and math.isnan(f2):
            return True
        if math.copysign(1,f1) != math.copysign(1,f2):
            # THANKS:  http://stackoverflow.com/a/25338224/673991
            return False
        return f1 == f2

    assert True == _floats_really_same.__func__(float('nan'), float('nan'))
    assert False == _floats_really_same.__func__(+0.0, -0.0)

    def __float__(self):
        float_by_dictionary = self.__float__by_zone_dictionary()
        assert self._floats_really_same(float_by_dictionary, self.__float__by_zone_ifs()), (
            "Mismatched float encoding for %s:  tree method=%s, scan method=%s" % (
                repr(self), float_by_dictionary, self.__float__by_zone_ifs()
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
        if _zone in self.ZONE_REASONABLY_NONZERO:
            return self._to_float()
        elif _zone in self.ZONE_ESSENTIALLY_NONNEGATIVE_ZERO:
            return 0.0
        elif _zone in self.ZONE_ESSENTIALLY_NEGATIVE_ZERO:
            return -0.0
        elif _zone in (self.Zone.TRANSFINITE, self.Zone.LUDICROUS_LARGE):
            return float('+inf')
        elif _zone in (self.Zone.TRANSFINITE_NEG, self.Zone.LUDICROUS_LARGE_NEG):
            return float('-inf')
        else:
            return float('nan')

    def _to_float(self):
        qexp = self.qexponent()
        (qan, qanlength) = self.qantissa()
        if self.raw < self.RAW_ZERO:
            qan -= self._exp256(qanlength)
            if qanlength > 0 and qan >= - self._exp256(qanlength-1):
                (qan, qanlength) = (-1,1)
        else:
            if qanlength < 0:
                return 0.0
            if qanlength == 0 or qan <=  self._exp256(qanlength-1):
                (qan, qanlength) = (1,1)
        exponent_base_2 = 8 * (qexp-qanlength)
        return math.ldexp(float(qan), exponent_base_2)

    @classmethod
    def _sets_exclusive(cls, *sets):
        # GENERIC:  This function might be useful elsewhere.
        for i in range(len(sets)):
            for j in range(i):
                if set(sets[i]).intersection(sets[j]):
                    return False
        return True

    @classmethod
    def _union_of_distinct_sets(cls, *sets):
        # GENERIC:  This function might be useful elsewhere.
        assert cls._sets_exclusive(*sets), "Sets not mutually exclusive:  %s" % repr(sets)
        return_value = set()
        for each_set in sets:
            return_value |= each_set
        return return_value

    def inc(self):
        self.raw = self._inc_via_integer()
        return self

    def _inc_via_integer(self):
        return Number(int(self) + 1).raw

    class Suffix(object):
        """A Number can have suffixes.

        Format of a nonempty suffix:
            PPPPPP_TTLL00
        where:
            PPPPPP - 0 to 250 byte payload
            _  - underscore is a conventional qstring delimiter between payload and the rest
            TT - type code of the suffix
            LL - length, number of bytes in the type and payload, 0x00 to 0xFA
            00 - NUL byte

        The empty suffix is two NUL bytes (or LL length is zero, and there is no type and no payload):
            0000

        The NUL byte is what indicates there is a suffix.
        This is why an unsuffixed number has all its right-end 00-bytes stripped.

        Example:
            assert '778899_110400' == Number.Suffix(type_=0x11, payload=b'\x77\x88\x99').qstring()
        """

        MAX_PAYLOAD_LENGTH = 250

        def __init__(self, type_=None, payload=b''):
            assert isinstance(type_, (int, type(None)))
            assert isinstance(payload, (six.binary_type, self.Number))
            self.type_ = type_
            if isinstance(payload, self.Number):
                self.payload = payload.raw
            else:
                self.payload = payload
            if self.type_ is None:
                assert self.payload == b''
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
                    raise ValueError

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
            whole_suffix_in_hex = self.hex_encode(self.raw)
            if underscore > 0 and self.payload:
                payload_hex = whole_suffix_in_hex[:-6]
                type_length_00_hex = whole_suffix_in_hex[-6:]
                return payload_hex + '_' + type_length_00_hex
            else:
                return whole_suffix_in_hex

        def payload_number(self):
            return self.Number.from_raw(self.payload)

        @classmethod
        def internal_setup(cls, number_class):
            cls.Number = number_class
            # cls.hex_encode = number_class.hex_encode

    Suffix.hex_encode = hex_encode

    def is_suffixed(self):
        return self.raw[-1:] == b'\x00'

    def add_suffix(self, new_type=None, payload=b''):
        if self.is_nan():
            raise ValueError
        suffix = self.Suffix(new_type, payload)
        self.raw += suffix.raw
        return self

    def get_suffix(self, sought_type):
        suffixes = self.parse_suffixes()
        for suffix in suffixes[1:]:
            if suffix.type_ == sought_type:
                return suffix
        raise IndexError


    def get_suffix_payload(self, sought_type):
        return self.get_suffix(sought_type).payload

    def get_suffix_number(self, sought_type):
        return self.from_raw(self.get_suffix_payload(sought_type))

    def parse_suffixes(self):
        return_array = []
        n = Number(self)   # Is this really necessary? self.raw is immutable is it not?
        while True:
            last_byte = n.raw[-1:]
            if last_byte == b'\x00':
                try:
                    length_of_payload_plus_type = six.indexbytes(n.raw, -2)
                except IndexError:
                    raise ValueError
                if length_of_payload_plus_type >= len(n.raw)-2:   # Suffix may neither be larger than raw, nor consume all of it.
                    raise ValueError
                if length_of_payload_plus_type == 0x00:
                    return_array.append(Number.Suffix())
                else:
                    try:
                        type_ = six.indexbytes(n.raw, -3)
                    except IndexError:
                        raise ValueError
                    payload = n.raw[-length_of_payload_plus_type-2:-3]
                    return_array.append(Number.Suffix(type_, payload))
                n = Number.from_raw(n.raw[0:-length_of_payload_plus_type-2])
            else:
                break
        return_array.append(n)
        return tuple(reversed(return_array))

    @classmethod
    def internal_setup(cls):
        """Initialize some class properties after the class is defined."""

        cls.name_of_zone = {   # Translate zone code to zone name, e.g. name_of_zone[b'\x80'] == 'ZERO'
            getattr(cls.Zone, attr):attr for attr in dir(cls.Zone) if not callable(attr) and not attr.startswith("__")
        }
        assert cls.name_of_zone[cls.Zone.ZERO] == 'ZERO'

        cls._sorted_zones = sorted(cls.name_of_zone.keys(), reverse=True)   # zone codes, desc order == defined order


        # Constants
        # ---------
        cls.NAN = cls(None)
        cls.POSITIVE_INFINITY = cls.from_raw(cls.RAW_INF)
        cls.NEGATIVE_INFINITY = cls.from_raw(cls.RAW_INF_NEG)


        # Sets of Zones   TODO:  draw a Venn Diagram or table or something
        # -------------
        cls.ZONE_REASONABLE = {
            cls.Zone.POSITIVE,
            cls.Zone.FRACTIONAL,
            cls.Zone.ZERO,
            cls.Zone.FRACTIONAL_NEG,
            cls.Zone.NEGATIVE,
        }
        cls.ZONE_LUDICROUS = {
            cls.Zone.LUDICROUS_LARGE,
            cls.Zone.LUDICROUS_SMALL,
            cls.Zone.LUDICROUS_SMALL_NEG,
            cls.Zone.LUDICROUS_LARGE_NEG,
        }
        cls.ZONE_NONFINITE = {
            cls.Zone.TRANSFINITE,
            cls.Zone.INFINITESIMAL,
            cls.Zone.INFINITESIMAL_NEG,
            cls.Zone.TRANSFINITE_NEG,
        }
        cls.ZONE_FINITE = cls._union_of_distinct_sets(
            cls.ZONE_LUDICROUS,
            cls.ZONE_REASONABLE,
        )
        cls.ZONE_UNREASONABLE = cls._union_of_distinct_sets(
            cls.ZONE_LUDICROUS,
            cls.ZONE_NONFINITE,
        )

        cls.ZONE_POSITIVE = {
            cls.Zone.TRANSFINITE,
            cls.Zone.LUDICROUS_LARGE,
            cls.Zone.POSITIVE,
            cls.Zone.FRACTIONAL,
            cls.Zone.LUDICROUS_SMALL,
            cls.Zone.INFINITESIMAL,
        }
        cls.ZONE_NEGATIVE = {
            cls.Zone.INFINITESIMAL_NEG,
            cls.Zone.LUDICROUS_SMALL_NEG,
            cls.Zone.FRACTIONAL_NEG,
            cls.Zone.NEGATIVE,
            cls.Zone.LUDICROUS_LARGE_NEG,
            cls.Zone.TRANSFINITE_NEG,
        }
        cls.ZONE_NONZERO = cls._union_of_distinct_sets(
            cls.ZONE_POSITIVE,
            cls.ZONE_NEGATIVE,
        )
        cls.ZONE_ZERO = {
            cls.Zone.ZERO
        }

        cls.ZONE_ESSENTIALLY_POSITIVE_ZERO = {
            cls.Zone.LUDICROUS_SMALL,
            cls.Zone.INFINITESIMAL,
        }
        cls.ZONE_ESSENTIALLY_NEGATIVE_ZERO = {
            cls.Zone.INFINITESIMAL_NEG,
            cls.Zone.LUDICROUS_SMALL_NEG,
        }
        cls.ZONE_ESSENTIALLY_NONNEGATIVE_ZERO = cls._union_of_distinct_sets(
            cls.ZONE_ESSENTIALLY_POSITIVE_ZERO,
            cls.ZONE_ZERO,
        )
        cls.ZONE_ESSENTIALLY_ZERO = cls._union_of_distinct_sets(
            cls.ZONE_ESSENTIALLY_NONNEGATIVE_ZERO,
            cls.ZONE_ESSENTIALLY_NEGATIVE_ZERO,
        )
        cls.ZONE_REASONABLY_POSITIVE = {
            cls.Zone.POSITIVE,
            cls.Zone.FRACTIONAL,
        }
        cls.ZONE_REASONABLY_NEGATIVE = {
            cls.Zone.FRACTIONAL_NEG,
            cls.Zone.NEGATIVE,
        }
        cls.ZONE_REASONABLY_NONZERO = cls._union_of_distinct_sets(
            cls.ZONE_REASONABLY_POSITIVE,
            cls.ZONE_REASONABLY_NEGATIVE,
        )
        cls.ZONE_UNREASONABLY_BIG = {
            cls.Zone.TRANSFINITE,
            cls.Zone.LUDICROUS_LARGE,
            cls.Zone.LUDICROUS_LARGE_NEG,
            cls.Zone.TRANSFINITE_NEG,
        }

        cls.ZONE_WHOLE_NO = {
            cls.Zone.FRACTIONAL,
            cls.Zone.LUDICROUS_SMALL,
            cls.Zone.INFINITESIMAL,
            cls.Zone.INFINITESIMAL_NEG,
            cls.Zone.LUDICROUS_SMALL_NEG,
            cls.Zone.FRACTIONAL_NEG,
        }
        cls.ZONE_WHOLE_YES = {
            cls.Zone.ZERO,
        }
        cls.ZONE_WHOLE_MAYBE = {
            cls.Zone.POSITIVE,
            cls.Zone.NEGATIVE,
        }
        cls.ZONE_WHOLE_INDETERMINATE = {
            cls.Zone.TRANSFINITE,
            cls.Zone.LUDICROUS_LARGE,
            cls.Zone.LUDICROUS_LARGE_NEG,
            cls.Zone.TRANSFINITE_NEG,
        }

        cls.ZONE_NAN = {
            cls.Zone.NAN
        }
        cls._ZONE_ALL_BY_REASONABLENESS = cls._union_of_distinct_sets(
            cls.ZONE_REASONABLE,
            cls.ZONE_UNREASONABLE,
            cls.ZONE_NAN,
        )
        cls._ZONE_ALL_BY_FINITENESS = cls._union_of_distinct_sets(
            cls.ZONE_FINITE,
            cls.ZONE_NONFINITE,
            cls.ZONE_NAN,
        )
        cls._ZONE_ALL_BY_ZERONESS = cls._union_of_distinct_sets(
            cls.ZONE_NONZERO,
            cls.ZONE_ZERO,
            cls.ZONE_NAN,
        )
        cls._ZONE_ALL_BY_BIGNESS = cls._union_of_distinct_sets(
            cls.ZONE_ESSENTIALLY_ZERO,
            cls.ZONE_REASONABLY_NONZERO,
            cls.ZONE_UNREASONABLY_BIG,
            cls.ZONE_NAN,
        )
        cls._ZONE_ALL_BY_WHOLENESS = cls._union_of_distinct_sets(
            cls.ZONE_WHOLE_NO,
            cls.ZONE_WHOLE_YES,
            cls.ZONE_WHOLE_MAYBE,
            cls.ZONE_WHOLE_INDETERMINATE,
            cls.ZONE_NAN,
        )

        cls.ZONE_ALL = {zone for zone in cls._sorted_zones}


Number.internal_setup()
Number.Suffix.internal_setup(Number)
assert '778899_110400' == Number.Suffix(type_=0x11, payload=b'\x77\x88\x99').qstring()



# TODO:  Ludicrous Numbers
# TODO:  Transfinite Numbers
# TODO:  Floating Point should be an add-on.  Standard is int?  Or nothing but raw, qex, qan, zones, and add-on int!?
# TODO:  Suffixes, e.g. 0q81FF_02___8264_71_0500 for precisely 0.01 (0x71 = 'q' for the rational quotient)...
# TODO:  ...would be 8 bytes, same as float64, ...
# TODO:  ...versus 0q81FF_028F5C28F5C28F60 for ~0.0100000000000000002, 10 bytes, as close as float gets to 0.01

# TODO:  decimal.Decimal
# TODO:  complex
# TODO:  Numpy types
# SEE:  http://docs.scipy.org/doc/numpy/user/basics.types.html
# TODO:  other Numpy compatibilities?

# TODO:  Number.inc() native - taking advantage of raw encodings
# TODO:  __neg__ native - taking advantage of two's complement encoding
# TODO:  __add__, __mul__, etc. native
# TODO:  other Number(string)s, e.g. assert 1 == Number('1')

# TODO:  hooks to add features modularly, e.g. suffixes
# TODO:  change % to .format()
# TODO:  change raw from str/bytes to bytearray?
# SEE:  http://ze.phyr.us/bytearray/
# TODO:  raise subclass of built-in exceptions
# TODO:  combine qantissa() and qexponent() into _unpack() that extracts all three pieces
# TODO:  _pack() opposite of _unpack() -- and use it in _from_float(), _from_int()
# TODO:  str(Number('0q80')) should be '0'.  str(Number.NAN should be '0q'
# TODO:  Number.natural() should be int() if whole, float if non-whole -- and .__str__() should call .natural()

# FIXME:  Why is pi 0q82_03243F6A8885A3 but pi-5 = 0q7D_FE243F6A8885A4 ?  (BTW pi in hex is 3.243F6A8885A308D3...)
#   Is that an IEEE float problem or a qiki.Number problem?
#   Similarly e = 0q82_02B7E151628AED but e-5 = 0q7D_FDB7E151628AEE
#   This may not be worth solving, or it may indicate a negative number bug.
#   1.9375 = 0q82_01F0, but 1.9375-5 = 0q7D_FCF00000000001, and -3.062500000000005 = 0q7D_FCF0

# TODO:  Terminology for an unsuffixed Number?  For a suffixed Number?
# Number class is unsuffixed, and derived class is suffixed?
# Name it "Numeraloid?  Identifier?  SuperNumber?  UberNumber?  Umber?