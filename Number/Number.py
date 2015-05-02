"""
Qiki Numbers
Both integers and floating point seamlessly
And more
"""

import sys
import six
from enum import Enum
import math
import struct


class Number(object):

    __slots__ = ('__raw', )   # less memory
    # __slots__ = ('__raw', '_zone')   # faster

    RAW_INF     = '\xFF\x81'
    RAW_ONE     = '\x82\x01'
    RAW_ZERO    = '\x80'
    RAW_ONE_NEG = '\x7D\xFF'
    RAW_INF_NEG = '\x00\x7F'
    RAW_NAN     = ''

    # qiki Numbers fall into zones.
    # Zone enumeration names have values that are *between* zones.
    # Raw, internal binary strings are represented.
    # They are less than or equal to all raw values in the zone they represent,
    # and greater than all valid values in the zones below.
    # (So some zone values are valid raw values, others are among the invalid inter-zone values.)
    # The valid raw string for 1 is '\x82\x01' but Number.Zone.ONE is '\x82'.
    # Anything between '\x82' and '\x82\x01' will be interpreted as 1 by any Number Consumer (NumberCon).
    # But any Number Producer (NumberPro) that generates a 1 should generate the raw string '\x82\x01'.
    class Zone(Enum):
        TRANSFINITE         = '\xFF\x80'
        LUDICROUS_LARGE     = '\xFF'
        POSITIVE            = '\x82\x01\x00'
        ONE                 = '\x82'
        FRACTIONAL          = '\x81'
        LUDICROUS_SMALL     = '\x80\x80'
        INFINITESIMAL       = '\x80\x00'
        ZERO                = '\x80'
        INFINITESIMAL_NEG   = '\x7F\x80'
        LUDICROUS_SMALL_NEG = '\x7F\x00'
        FRACTIONAL_NEG      = '\x7E\x00'
        ONE_NEG             = '\x7D\xFF'
        NEGATIVE            = '\x01'
        LUDICROUS_LARGE_NEG = '\x00\x80'
        TRANSFINITE_NEG     = '\x00'
        NAN                 = ''   # NAN stands for Not-a-number, Ass-is-out-of-range, or Null.

        # the following is an enum34 provision:  http://stackoverflow.com/a/25982264/673991
        __order__ = '''
            TRANSFINITE
            LUDICROUS_LARGE
            POSITIVE
            ONE
            FRACTIONAL
            LUDICROUS_SMALL
            INFINITESIMAL
            ZERO
            INFINITESIMAL_NEG
            LUDICROUS_SMALL_NEG
            FRACTIONAL_NEG
            ONE_NEG
            NEGATIVE
            LUDICROUS_LARGE_NEG
            TRANSFINITE_NEG
            NAN
        '''

    @property
    def raw(self):
        return self.__raw

    @raw.setter
    def raw(self, value):
        assert(isinstance(value, six.string_types))
        self.__raw = value
        self._zone_refresh()

    def __getstate__(self):
        return self.raw

    def __setstate__(self, d):
        self.raw = d

    def __init__(self, content, qigits = None):
        if content is None:
            self.raw = ''
        elif isinstance(content, six.string_types):
            self._from_string(content)
        elif isinstance(content, (int, long)):
            self._from_int(content)
        elif isinstance(content, float):
            self._from_float(content, qigits)
        elif isinstance(content, type(self)):  # ala C++ copy-constructor
            self.raw = content.raw
        else:
            typename = type(content).__name__
            if typename == 'instance':
                typename = content.__class__.__name__
            raise TypeError('Number(%s) not yet supported' % typename)

    def __repr__(self):
        return "Number('%s')" % self.qstring()

    def __str__(self):
        return self.qstring()

    __eq__ = lambda self, other:  Number(self).raw == Number(other).raw
    __ne__ = lambda self, other:  Number(self).raw != Number(other).raw
    __lt__ = lambda self, other:  Number(self).raw <  Number(other).raw
    __le__ = lambda self, other:  Number(self).raw <= Number(other).raw
    __gt__ = lambda self, other:  Number(self).raw >  Number(other).raw
    __ge__ = lambda self, other:  Number(self).raw >= Number(other).raw

    @classmethod
    def from_raw(cls, value):
        """
        Construct a Number from its raw, internal binary string
        Wrong:  assert Number(1) == Number('\x82\x01')
        Right:  assert Number(1) == Number.from_raw('\x82\x01')
        """
        retval = Number(None)
        retval.raw = value
        return retval

    def _from_string(self, s):
        assert(isinstance(s, six.string_types))
        if s.startswith('0q'):
            s = str(s)   # avoids u'0q80' giving TypeError: translate() takes exactly one argument (2 given)
            sdigits = s[2:].translate(None, '_')
            if len(sdigits) % 2 != 0:
                # raise ValueError("A qiki Number string must have an even number of digits, not '%s'" % s)
                sdigits += '0'
            try:
                sdecoded = sdigits.decode('hex')
            except TypeError:
                raise ValueError("A qiki Number string must use hexadecimal digits (or underscore), not '%s'" % s)
            self.raw = sdecoded
        else:
            # TODO:  assert Number('1') == Number(1)
            raise ValueError("A qiki Number string must start with '0q' instead of '%s'" % s)

    _qigits_precision = None

    @classmethod
    def qigits_precision(cls, qigits):
        if qigits is not None and qigits >= 1 and qigits != cls._qigits_precision:
            cls._qigits_precision = qigits
            cls._qigits_scaler = 256**qigits
        else:
            cls._qigits_precision = Number.QIGITS_PRECISION_DEFAULT
            cls._qigits_scaler = Number.QIGITS_SCALER_DEFAULT

    def _from_float(self, x, qigits = None):
        self.qigits_precision(qigits)

        if math.isnan(x):          self.raw =          self.RAW_NAN
        elif x >= float('+inf'):   self.raw =          self.RAW_INF
        elif x >=  1.0:            self.raw =          self._raw_from_float(x, lambda e: 0x81+e)
        elif x >   0.0:            self.raw = '\x81' + self._raw_from_float(x, lambda e: 0xFF+e)
        elif x ==  0.0:            self.raw =          self.RAW_ZERO
        elif x >  -1.0:            self.raw = '\x7E' + self._raw_from_float(x, lambda e: 0x00-e)
        elif x > float('-inf'):    self.raw =          self._raw_from_float(x, lambda e: 0x7E-e)
        else:                      self.raw =          self.RAW_INF_NEG

    def _from_int(self, i):
        if   i >  0:   self.raw = self._raw_from_int(i, lambda e: 0x81+e)
        elif i == 0:   self.raw = self.RAW_ZERO
        else:          self.raw = self._raw_from_int(i, lambda e: 0x7E-e)

    @classmethod
    def _raw_from_float(cls, x, qex_encoder):
        """ Convert float to raw, for nonzero finite (and reasonable) numbers """
        (significand_base_2, exponent_base_2) = math.frexp(x)
        assert x == significand_base_2 * 2.0**exponent_base_2
        assert 0.5 <= abs(significand_base_2) < 1.0

        (exponent_base_256, zero_to_seven) = divmod(exponent_base_2+7, 8)
        significand_base_256 = significand_base_2 * (2 ** (zero_to_seven-7))
        assert x == significand_base_256 * 256.0**exponent_base_256
        assert 0.00390625 <= abs(significand_base_256) < 1.0

        qan_integer = long(significand_base_256 * cls._qigits_scaler + 0.5)
        qan00 = cls._pack_integer(qan_integer, cls._qigits_precision)
        qan = cls._right_strip00(qan00)

        qex_integer = qex_encoder(exponent_base_256)
        qex = chr(qex_integer)

        return qex + qan

    @classmethod
    def _raw_from_int(cls, i, qex_encoder):
        """ Convert integer to raw, for nonzero (and reasonable) numbers """
        qan00 = cls._pack_integer(i)
        qan = cls._right_strip00(qan00)

        exponent_base_256 = len(qan00)
        qex_number = qex_encoder(exponent_base_256)
        qex = chr(qex_number)

        return qex + qan

    @classmethod
    def _pack_integer(cls, theinteger, nbytes=None):
        """
        Pack an integer into a base-256 string.
        :param theinteger:  an arbitrarily large integer
        :param nbytes:  number of bytes (base-256 digits) to output (omit for minimum)
        :return:  an unsigned two's complement string, MSB first

        Caution, there may not be a "sign bit" in the output unless nbytes is large enough.
            assert     '\xFF' == _pack_integer(255)
            assert '\x00\xFF' == _pack_integer(255,2)
            assert     '\x01' == _pack_integer(-255)
            assert '\xFF\x01' == _pack_integer(-255,2)
        Caution, nbytes lower than minimum may or may not be enforced, see unit tests
        """

        if nbytes is None:
            nbytes = len(cls._hex_even(abs(theinteger)))/2   # nbytes default = 1 + floor(log(abs(theinteger), 256))

        if (nbytes <= 8 and 0 <= theinteger < 4294967296):
            return struct.pack('>Q', theinteger)[8-nbytes:]  # timeit says this is 4x as fast as the Mike Boers way
        elif (nbytes <= 8 and -2147483648 <= theinteger < 2147483648):
            return struct.pack('>q', theinteger)[8-nbytes:]
        else:
            return cls._pack_big_integer_Mike_Boers(theinteger, nbytes)

    @classmethod
    def _pack_big_integer_Mike_Boers(cls, num, nbytes):
        """
        Pack an integer into a binary string
        Akin to base-256 encode
        Derived from code by Mike Boers http://stackoverflow.com/a/777774/673991
        """
        if num >= 0:
            num_twos_complement = num
        else:
            num_twos_complement = num + 256**nbytes   # two's complement of big negative integers
        return cls._left_pad00(
            cls._hex_even(
                num_twos_complement
            ).decode('hex'),
            nbytes
        )

    @staticmethod
    def _hex_even(theinteger):
        """
        Hexadecimal string from a big integer
        like hex() but even number of digits, no '0x' prefix, no 'L' suffix
        Also derived from Mike Boers code http://stackoverflow.com/a/777774/673991
        """
        hex_string = hex(theinteger)[2:].rstrip('L')
        if len(hex_string) % 2:
            hex_string = '0' + hex_string
        return hex_string

    @staticmethod
    def _left_pad00(thestring, nbytes):
        """ Thanks Jeff Mercado http://stackoverflow.com/a/5773669/673991 """
        return thestring.rjust(nbytes, '\x00')

    @staticmethod
    def _right_strip00(qan):
        return qan.rstrip('\x00')

    def qstring(self, underscore=1):
        """
        Outputs Number in '0qHHHHHH' string form
        assert '0q85_1234ABCD' == Number(0x1234ABCD).qstring()

        Q-string is the raw text representation of a qiki number
        Similar to 0x12AB for hexadecimal
        Except q for x, underscores optional, and meaning differs
        """
        if underscore == 0:
            return '0q' + self.hex()
        else:
            length = len(self.raw)
            if length == 0:
                offset = 0
            elif ord(self.raw[0]) in (0x7E, 0x7F, 0x80, 0x81):
                offset = 2
            else:
                offset = 1   # TODO: ludicrous numbers have bigger offsets (for googolplex it's 64)
            h = self.hex()
            if length <= offset:
                return '0q' + h
            else:
                return '0q' + h[:2*offset] + '_' + h[2*offset:]

    def hex(self):
        return self.raw.encode('hex').upper()

    def qantissa(self):
        try:
            qan_offset = {
                self.Zone.POSITIVE:       1,
                self.Zone.FRACTIONAL:     2,
                self.Zone.FRACTIONAL_NEG: 2,
                self.Zone.NEGATIVE:       1,
            }[self.zone]
        except KeyError:
            raise ValueError('qantissa() not defined for %s' % repr(self))   # TODO: ludicrous numbers
        number_qantissa = self._unpack_big_integer(self.raw[qan_offset:])
        return (number_qantissa, len(self.raw) - qan_offset)

    @classmethod
    def _unpack_big_integer(cls, binary_string):
        retval = 0L
        for i in range(len(binary_string)):
            retval <<= 8
            retval |= ord(binary_string[i])
        return retval

    def qexponent(self):
        try:
            return self.__qexponent_dict[self.zone](self)
        except KeyError:
            raise ValueError('qexponent() not defined for %s' % repr(self))

    __qexponent_dict = {
        Zone.POSITIVE:       lambda self:         ord(self.raw[0]) - 0x81,
        Zone.FRACTIONAL:     lambda self:         ord(self.raw[1]) - 0xFF,
        Zone.FRACTIONAL_NEG: lambda self:  0x00 - ord(self.raw[1]),
        Zone.NEGATIVE:       lambda self:  0x7E - ord(self.raw[0]),
    }

    def __long__(self):
       return long(self.__int__())

    def __int__(self):
        if '\xFF' <= self.raw:
            raise OverflowError("Positive Infinity can't be represented by integers")
        elif '\x82\x01' < self.raw:
            (qan, qanlength) = self.qantissa()
            qexp = self.qexponent() - qanlength
            if qexp < 0:
                return qan >> (-qexp*8)
            else:
                return qan << (qexp*8)
        elif '\x82' <= self.raw:
            return 1
        elif '\x7E' < self.raw:
            return 0
        elif '\x7D\xFF' <= self.raw:
            return -1
        elif '\x01' <= self.raw:   # <= '\x7D'
            (qan,qanlength) = self.qantissa()
            offset = (2 ** (qanlength*8))
            qan -= offset
            qexp = self.qexponent() - qanlength
            if qexp < 0:
                extraneous_mask = (1 << (-qexp*8)) - 1   # TODO: more graceful way to floor toward 0 instead of -inf
                extraneous = qan & extraneous_mask
                if extraneous == 0:
                    return qan >> (-qexp*8)
                else:
                    return (qan >> (-qexp*8)) + 1
            else:
                return qan << (qexp*8)
        elif self.RAW_NAN < self.raw:
            raise OverflowError("Negative Infinity can't be represented by integers")
        else:
            raise ValueError("Not-A-Number can't be represented by integers")

    @property
    def zone(self):
        try:
            return self._zone
        except AttributeError:
            return self._zone_from_scratch()

    def _zone_refresh(self):
        try:
            self._zone = self._zone_from_scratch()
        except AttributeError:
            pass

    def _zone_from_scratch(self):
        retval_tree = self._zone_tree()
        assert retval_tree == self._zone_scan(), "Mismatched zone determination for %s:  tree=%s, scan=%s" % (
            repr(self), retval_tree, self._zone_scan()
        )
        return retval_tree

    def _zone_scan(self):
        for z in self.Zone:
            if z.value <= self.raw:
                return z
        raise ValueError("Number._zone_scan() fell through!  How can anything be less than Zone.NAN? '%s'" % repr(self))

    def _zone_tree(self):
        if self.raw > self.RAW_ZERO:
            if self.raw > self.RAW_ONE:
                if self.raw >= self.Zone.LUDICROUS_LARGE.value:
                    if self.raw >= self.Zone.TRANSFINITE.value:
                        return                  self.Zone.TRANSFINITE
                    else:
                        return                  self.Zone.LUDICROUS_LARGE
                else:
                    return                      self.Zone.POSITIVE
            elif self.raw >= self.Zone.ONE.value:
                return                          self.Zone.ONE
            else:
                if self.raw >= self.Zone.FRACTIONAL.value:
                    return                      self.Zone.FRACTIONAL
                elif self.raw >= self.Zone.LUDICROUS_SMALL.value:
                    return                      self.Zone.LUDICROUS_SMALL
                else:
                    return                      self.Zone.INFINITESIMAL
        elif self.raw == self.RAW_ZERO:
            return                              self.Zone.ZERO
        else:
            if self.raw > self.Zone.FRACTIONAL_NEG.value:
                if self.raw >= self.Zone.LUDICROUS_SMALL_NEG.value:
                    if self.raw >= self.Zone.INFINITESIMAL_NEG.value:
                        return                  self.Zone.INFINITESIMAL_NEG
                    else:
                        return                  self.Zone.LUDICROUS_SMALL_NEG
                else:
                    return                      self.Zone.FRACTIONAL_NEG
            elif self.raw >= self.RAW_ONE_NEG:
                return                          self.Zone.ONE_NEG
            else:
                if self.raw >= self.Zone.NEGATIVE.value:
                    return                      self.Zone.NEGATIVE
                elif self.raw >= self.Zone.LUDICROUS_LARGE_NEG.value:
                    return                      self.Zone.LUDICROUS_LARGE_NEG
                elif self.raw >= self.Zone.TRANSFINITE_NEG.value:
                    return                      self.Zone.TRANSFINITE_NEG
                else:
                    return                      self.Zone.NAN

    @staticmethod
    def _floats_really_same(f1,f2):
        """
        Same as == with a few exceptions.
        Equal if both NAN.
        Not equal if one is +0.0 and the other -0.0.
        """
        assert type(f1) is float
        assert type(f2) is float
        if math.isnan(f1) and math.isnan(f2):
            return True
        if  math.copysign(1,f1) != math.copysign(1,f2):
            return False
        return f1 == f2

    def __float__(self):
        float_by_dictionary = self.__float__by_zone_dictionary()
        assert self._floats_really_same(float_by_dictionary, self.__float__by_ifs()), (
            "Mismatched float encoding for %s:  tree method=%s, scan method=%s" % (
                repr(self), float_by_dictionary, self.__float__by_ifs()
            )
        )
        return float_by_dictionary

    def __float__by_zone_dictionary(self):
        return self.__float__dict[self.zone](self)

    __float__dict =  {
        Zone.TRANSFINITE:         lambda self: float('+inf'),
        Zone.LUDICROUS_LARGE:     lambda self: float('+inf'),
        Zone.POSITIVE:            lambda self: self._to_float(),
        Zone.ONE:                 lambda self: 1.0,
        Zone.FRACTIONAL:          lambda self: self._to_float(),
        Zone.LUDICROUS_SMALL:     lambda self: 0.0,
        Zone.INFINITESIMAL:       lambda self: 0.0,
        Zone.ZERO:                lambda self: 0.0,
        Zone.INFINITESIMAL_NEG:   lambda self: -0.0,
        Zone.LUDICROUS_SMALL_NEG: lambda self: -0.0,
        Zone.FRACTIONAL_NEG:      lambda self: self._to_float(),
        Zone.ONE_NEG:             lambda self: -1.0,
        Zone.NEGATIVE:            lambda self: self._to_float(),
        Zone.LUDICROUS_LARGE_NEG: lambda self: float('-inf'),
        Zone.TRANSFINITE_NEG:     lambda self: float('-inf'),
        Zone.NAN:                 lambda self: float('nan')
    }

    def __float__by_ifs(self):
        _zone = self.zone
        if _zone == self.Zone.ONE:
            return 1.0
        elif _zone in self.ZONE_REASONABLY_POSITIVE_ZERO:
            return 0.0
        elif _zone in self.ZONE_REASONABLY_NEGATIVE_ZERO:
            return -0.0
        elif _zone == self.Zone.ONE_NEG:
            return -1.0
        elif _zone in (self.Zone.POSITIVE, self.Zone.FRACTIONAL, self.Zone.FRACTIONAL_NEG, self.Zone.NEGATIVE):
            return self._to_float()
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
            qan -= (2 ** (qanlength*8))
        return float(qan) * math.pow(256, (qexp - qanlength))

    def __obsolete_to_int(self):
        if '\x85\x7F\xFF\xFF\xFF' < self.raw:
            return sys.maxint
        elif self.raw <= '\x7A\x80':
            return -sys.maxint - 1
        else:
            return long(self)



Number.NAN = Number(None)

Number.ZONE_REASONABLE = {
    Number.Zone.POSITIVE,
    Number.Zone.ONE,
    Number.Zone.FRACTIONAL,
    Number.Zone.ZERO,
    Number.Zone.FRACTIONAL_NEG,
    Number.Zone.ONE_NEG,
    Number.Zone.NEGATIVE,
}
Number.ZONE_LUDICROUS = {
    Number.Zone.LUDICROUS_LARGE,
    Number.Zone.LUDICROUS_SMALL,
    Number.Zone.LUDICROUS_SMALL_NEG,
    Number.Zone.LUDICROUS_LARGE_NEG,
}
Number.ZONE_NONFINITE = {
    Number.Zone.TRANSFINITE,
    Number.Zone.INFINITESIMAL,
    Number.Zone.INFINITESIMAL_NEG,
    Number.Zone.TRANSFINITE_NEG,
}
Number.ZONE_FINITE = Number.ZONE_LUDICROUS | Number.ZONE_REASONABLE
Number.ZONE_ALL_BY_FINITY = Number.ZONE_FINITE | Number.ZONE_NONFINITE

Number.ZONE_POSITIVE = {
    Number.Zone.TRANSFINITE,
    Number.Zone.LUDICROUS_LARGE,
    Number.Zone.POSITIVE,
    Number.Zone.ONE,
    Number.Zone.FRACTIONAL,
    Number.Zone.LUDICROUS_SMALL,
    Number.Zone.INFINITESIMAL,
}
Number.ZONE_REASONABLY_ZERO = {
    Number.Zone.INFINITESIMAL,
    Number.Zone.LUDICROUS_SMALL,
    Number.Zone.ZERO,
    Number.Zone.INFINITESIMAL_NEG,
    Number.Zone.LUDICROUS_SMALL_NEG,
}
Number.ZONE_REASONABLY_POSITIVE_ZERO = {
    Number.Zone.INFINITESIMAL,
    Number.Zone.LUDICROUS_SMALL,
    Number.Zone.ZERO,
}
Number.ZONE_REASONABLY_NEGATIVE_ZERO = {
    Number.Zone.INFINITESIMAL_NEG,
    Number.Zone.LUDICROUS_SMALL_NEG,
}
Number.ZONE_NEGATIVE = {
    Number.Zone.INFINITESIMAL_NEG,
    Number.Zone.LUDICROUS_SMALL_NEG,
    Number.Zone.FRACTIONAL_NEG,
    Number.Zone.ONE_NEG,
    Number.Zone.NEGATIVE,
    Number.Zone.LUDICROUS_LARGE_NEG,
    Number.Zone.TRANSFINITE_NEG,
}
Number.ZONE_ZERO = {Number.Zone.ZERO}
Number.ZONE_ALL_BY_POSITIVITY = Number.ZONE_POSITIVE | Number.ZONE_NEGATIVE | Number.ZONE_ZERO

Number.ZONE_ALL = {zone for zone in Number.Zone if zone != Number.Zone.NAN}



# Number(float) defaults to 8 qigits, for lossless representation of a Python float.
# A "qigit" is a base-256 digit.
# IEEE 754 double precision has a 53-bit significand (52 bits stored + 1 implied).
# source:  http://en.wikipedia.org/wiki/Double-precision_floating-point_format
# So 8 qigits are needed to store 57-64 bits.
# 57 if the MSQigit were '\x01', 64 if '\xFF'.
# 7 qigits would only store 49-56.
Number.qigits_precision(8)
Number.QIGITS_PRECISION_DEFAULT = 8
Number.QIGITS_SCALER_DEFAULT = 256**Number.QIGITS_PRECISION_DEFAULT


if __name__ == '__main__':
    import unittest
    unittest.main()   # TODO: why 0 tests?