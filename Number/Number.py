"""
Qiki Numbers
Both integers and floating point seamlessly
And more
"""

import six
import math
import struct
import codecs

class Number(object):

    def __init__(self, content=None, qigits = None):
        if isinstance(content, six.integer_types):
            self._from_int(content)
        elif isinstance(content, float):
            self._from_float(content, qigits)
        elif isinstance(content, type(self)):  # copy-constructor
            self.raw = content.raw
        elif isinstance(content, six.string_types):
            self._from_string(content)
        elif content is None:
            self.raw = self.RAW_NAN
        else:
            typename = type(content).__name__
            if typename == 'instance':
                typename = content.__class__.__name__
            raise TypeError('Number(%s) not yet supported' % typename)

    __slots__ = ('__raw', )   # less memory
    # __slots__ = ('__raw', '_zone')   # faster

    RAW_INF     = b'\xFF\x81'
    RAW_ZERO    = b'\x80'
    RAW_INF_NEG = b'\x00\x7F'
    RAW_NAN     = b''


    # Zones
    # -----
    # qiki Numbers fall into zones.
    # The internal Number.Zone class serves as an enumeration.  Its members have values that are *between* zones.
    # Raw, internal binary strings are represented.
    # They are less than or equal to all raw values in the zone they represent,
    # and greater than all valid values in the zones below.
    # (So actually, some zone values are valid raw values, others are among the invalid inter-zone values.)
    # The valid raw string for 1 is b'x82\x01' but Number.Zone.POSITIVE is b'x82'.
    # Anything between b'x82' and b'x82\x01' will be interpreted as 1 by any Number Consumer (NumberCon).
    # But any Number Producer (NumberPro) that generates a 1 should generate the raw string b'x82\x01'.
    class Zone:
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
        NAN                 = b''   # NAN stands for Not-a-number, Ass-is-out-of-range, or Nullificationalized.

    @property
    def raw(self):
        return self.__raw

    @raw.setter
    def raw(self, value):
        assert(isinstance(value, six.binary_type))
        self.__raw = value
        self._zone_refresh()

    def __getstate__(self):
        return self.raw

    def __setstate__(self, d):
        self.raw = d

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
        Wrong:  assert Number(1) == Number(b'x82\x01')
        Right:  assert Number(1) == Number.from_raw(b'x82\x01')
        """
        if not isinstance(value, six.binary_type):
            raise ValueError("'%s' is not a binary string.  Number.from_raw(needs e.g. b'\\x82\\x01')" % repr(value))
        retval = Number(None)
        retval.raw = value
        return retval

    def _from_string(self, s):
        assert(isinstance(s, six.string_types))
        if s[:2] == '0q':
            sdigits = s[2:].replace('_', '')
            if len(sdigits) % 2 != 0:
                sdigits += '0'
            try:
                sdecoded = self.hex_decode(sdigits)
            except TypeError:
                raise ValueError("A qiki Number string must use hexadecimal digits (or underscore), not '%s'" % s)
            self.raw = six.binary_type(sdecoded)
        else:
            raise ValueError("A qiki Number string must start with '0q' instead of '%s'" % s)

    _qigits_precision = None

    @classmethod
    def _set_qigits_precision(cls, qigits):   # FIXME: these class-variables make this not thread-safe
        """Set how many qigits (base-256 digits) will be used when converting from float"""
        if qigits is not None and qigits >= 1 and qigits != cls._qigits_precision:
            cls._qigits_precision = qigits
            cls._qigits_scaler = cls._exp256(qigits)
        else:
            cls._qigits_precision = Number.QIGITS_PRECISION_DEFAULT
            cls._qigits_scaler = Number.QIGITS_SCALER_DEFAULT

    @classmethod
    def _qigits_precision_default(cls, qigits_default):
        cls._set_qigits_precision(qigits_default)
        cls.QIGITS_PRECISION_DEFAULT = cls._qigits_precision
        cls.QIGITS_SCALER_DEFAULT =  cls._qigits_scaler

    def _from_float(self, x, qigits = None):
        self._set_qigits_precision(qigits)

        if math.isnan(x):          self.raw =           self.RAW_NAN
        elif x >= float('+inf'):   self.raw =           self.RAW_INF
        elif x >=  1.0:            self.raw =           self._raw_from_float(x, lambda e: 0x81+e)   # qex <-- e256
        elif x >   0.0:            self.raw = b'\x81' + self._raw_from_float(x, lambda e: 0xFF+e)
        elif x ==  0.0:            self.raw =           self.RAW_ZERO
        elif x >  -1.0:            self.raw = b'\x7E' + self._raw_from_float(x, lambda e: 0x00-e)
        elif x > float('-inf'):    self.raw =           self._raw_from_float(x, lambda e: 0x7E-e)
        else:                      self.raw =           self.RAW_INF_NEG

    def _from_int(self, i):
        if   i >  0:   self.raw = self._raw_from_int(i, lambda e: 0x81+e)
        elif i == 0:   self.raw = self.RAW_ZERO
        else:          self.raw = self._raw_from_int(i, lambda e: 0x7E-e)

    @classmethod
    def _raw_from_float(cls, x, qex_encoder):
        """
        Convert nonzero float to raw
        qex_encoder() converts a base-256 exponent to internal qex format
        """
        (significand_base_2, exponent_base_2) = math.frexp(x)
        assert x == significand_base_2 * 2.0**exponent_base_2
        assert 0.5 <= abs(significand_base_2) < 1.0

        (exponent_base_256, zero_to_seven) = divmod(exponent_base_2+7, 8)
        significand_base_256 = significand_base_2 * (2 ** (zero_to_seven-7))
        assert x == significand_base_256 * 256.0**exponent_base_256
        assert 0.00390625 <= abs(significand_base_256) < 1.0

        qan_integer = int(significand_base_256 * cls._qigits_scaler + 0.5)
        qan00 = cls._pack_integer(qan_integer, cls._qigits_precision)
        qan = cls._right_strip00(qan00)

        qex_integer = qex_encoder(exponent_base_256)
        qex = six.int2byte(qex_integer)

        return qex + qan

    @classmethod
    def _raw_from_int(cls, i, qex_encoder):
        """
        Convert nonzero integer to raw
        qex_encoder() converts a base-256 exponent to internal qex format
        """
        qan00 = cls._pack_integer(i)
        qan = cls._right_strip00(qan00)

        exponent_base_256 = len(qan00)
        qex_integer = qex_encoder(exponent_base_256)
        qex = six.int2byte(qex_integer)

        return qex + qan

    @classmethod
    def _pack_integer(cls, theinteger, nbytes=None):
        """
        Pack an integer into a binary string, which is like a base-256, big-endian string.
        :param theinteger:  an arbitrarily large integer
        :param nbytes:  number of bytes (base-256 digits) to output (omit for minimum)
        :return:  an unsigned two's complement string, MSB first

        Caution, there may not be a "sign bit" in the output unless nbytes is large enough.
            assert     b'xFF' == _pack_integer(255)
            assert b'x00\xFF' == _pack_integer(255,2)
            assert     b'x01' == _pack_integer(-255)
            assert b'xFF\x01' == _pack_integer(-255,2)
        Caution, nbytes lower than minimum may or may not be enforced, see unit tests
        """

        if nbytes is None:
            nbytes = len(cls._hex_even(abs(theinteger)))//2   # nbytes default = 1 + floor(log(abs(theinteger), 256))

        if nbytes <= 8 and 0 <= theinteger < 4294967296:
            return struct.pack('>Q', theinteger)[8-nbytes:]  # timeit says this is 4x as fast as the Mike Boers way
        elif nbytes <= 8 and -2147483648 <= theinteger < 2147483648:
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
    def _hex_even(theinteger):
        """
        Encode a hexadecimal string from a big integer
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
        return thestring.rjust(nbytes, b'\x00')

    @staticmethod
    def _right_strip00(qan):
        return qan.rstrip(b'\x00')

    @staticmethod
    def _exp256(e):
        """Compute 256**e for nonnegative integer e"""
        assert isinstance(e, six.integer_types)
        assert e >= 0
        return 1 << (e<<3)   # which is the same as 2**(e*8) or (2**8)**e or 256**e

    def qstring(self, underscore=1):
        """
        Outputs Number in '0qHHHHHH' string form
        assert '0q85_1234ABCD' == Number(0x1234ABCD).qstring()

        Q-string is the raw text representation of a qiki number
        Similar to 0x12AB for hexadecimal
        Except q for x, underscores optional, and value interpretation differs
        """
        if underscore == 0:
            return '0q' + self.hex()
        else:
            length = len(self.raw)
            if length == 0:
                offset = 0
            elif six.indexbytes(self.raw, 0) in (0x7E, 0x7F, 0x80, 0x81):
                offset = 2
            else:
                offset = 1   # TODO: ludicrous numbers have bigger offsets (for googolplex it's 64)
            h = self.hex()
            if length <= offset:
                return '0q' + h
            else:
                return '0q' + h[:2*offset] + '_' + h[2*offset:]

    def hex(self):
        return self.hex_encode(self.raw)

    @staticmethod
    def hex_decode(s):
        """
        Decode a hexadecimal string into an 8-bit binary (base-256) string.
        This should really be in module "six":  https://bitbucket.org/gutworth/six
        """
        if six.PY2:
            return s.decode('hex')
        else:
            return bytes.fromhex(s)

    @staticmethod
    def hex_encode(s):
        """
        Encode an 8-bit binary (base-256) string into a hexadecimal string.
        This should really be in module "six":  https://bitbucket.org/gutworth/six
        This sole need for the "codecs" module is unfortunate.
        """
        if six.PY2:
            return s.encode('hex').upper()
        else:
            return codecs.encode(s, 'hex').decode().upper()

    def qantissa(self):
        """
        Extract the base-256 significand in its raw form
        Returns a tuple: (integer value, number of qigits)
        """
        try:
            qan_offset = self.__qan_offset_dict[self.zone]
        except KeyError:
            raise ValueError('qantissa() not defined for %s' % repr(self))
        number_qantissa = self._unpack_big_integer(self.raw[qan_offset:])
        return (number_qantissa, len(self.raw) - qan_offset)

    __qan_offset_dict ={
        Zone.POSITIVE:       1,
        Zone.FRACTIONAL:     2,
        Zone.FRACTIONAL_NEG: 2,
        Zone.NEGATIVE:       1,
    }   # TODO: ludicrous numbers

    @classmethod
    def _unpack_big_integer(cls, binary_string):
        """
        Convert a binary byte string into an integer
        Akin to a base-256 decode, big-endian
        """
        if len(binary_string) <= 8:
            return cls._unpack_big_integer_by_struct((binary_string))
        else:
            return cls._unpack_big_integer_by_brute(binary_string)

    @classmethod
    def _unpack_big_integer_by_struct(cls, binary_string):   # 1.1 to 4 times as fast as _unpack_big_integer_by_brute()
        return struct.unpack('>Q', cls._left_pad00(binary_string, 8))[0]

    @classmethod
    def _unpack_big_integer_by_brute(cls, binary_string):
        retval = 0
        for i in range(len(binary_string)):
            retval <<= 8
            retval |= six.indexbytes(binary_string, i)
        return retval

    def qexponent(self):
        try:
            return self.__qexponent_dict[self.zone](self)
        except KeyError:
            raise ValueError('qexponent() not defined for %s' % repr(self))

    __qexponent_dict = {   # qex-decoder, converting to a base-256-exponent from the internal qex format
        Zone.POSITIVE:       lambda self:         six.indexbytes(self.raw, 0) - 0x81,   # e <-- qex
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

    def _int_cant_be_positive_infinity(self):
        raise OverflowError("Positive Infinity can't be represented by integers")

    def _int_cant_be_negative_infinity(self):
        raise OverflowError("Negative Infinity can't be represented by integers")

    def _int_cant_be_nan(self):
        raise ValueError("Not-A-Number can't be represented by integers")

    def _to_int_positive(self):
        (qan, qanlength) = self.qantissa()
        qexp = self.qexponent() - qanlength
        if qexp < 0:
            return qan >> (-qexp*8)
        else:
            return qan << (qexp*8)

    def _to_int_negative(self):
            (qan,qanlength) = self.qantissa()
            offset = self._exp256(qanlength)
            qan -= offset
            qexp = self.qexponent() - qanlength
            if qexp < 0:
                extraneous_mask = self._exp256(-qexp) - 1
                extraneous = qan & extraneous_mask   # XXX: a more graceful way to floor to 0 instead of to -inf
                if extraneous == 0:
                    return qan >> (-qexp*8)
                else:
                    return (qan >> (-qexp*8)) + 1
            else:
                return qan << (qexp*8)

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

    def _find_zone_by_for_loop_scan(self):   # likely slower than tree, but helps enforce self.Zone's values
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
        """
        Are these floats really the same value?
        Similar to == except:
         1. same if both NAN.
         2. not same if one is +0.0 and the other -0.0.
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
            if qanlength != 0 and qan >= - self._exp256(qanlength-1):
                (qan, qanlength) = (-1,1)
        else:
            if qanlength == 0 or qan <=  self._exp256(qanlength-1):
                (qan, qanlength) = (1,1)
        exponent_base_2 = 8 * (qexp-qanlength)
        return math.ldexp(float(qan), exponent_base_2)

    @classmethod
    def _sets_exclusive(cls, *sets):
        for i in range(len(sets)):
            for j in range(i):
                if set(sets[i]).intersection(sets[j]):
                    return False
        return True

    @classmethod
    def _zone_union(cls, *zonesets):
        assert cls._sets_exclusive(*zonesets), "Sets not mutually exclusive: %s" % repr(zonesets)
        retval = set()
        for zoneset in zonesets:
            retval |= zoneset
        return retval


    @classmethod
    def _setup(cls):
        """class variables and settings made after the class is defined"""

        # float precision
        # ---------------
        # Number(float) defaults to 8 qigits, for lossless representation of a Python float.
        # A "qigit" is a base-256 digit.
        # IEEE 754 double precision has a 53-bit significand (52 bits stored + 1 implied).
        # source:  http://en.wikipedia.org/wiki/Double-precision_floating-point_format
        # So 8 qigits are needed to store 57-64 bits.
        # 57 if the MSQigit were b'x01', 64 if b'xFF'.
        # 7 qigits would only store 49-56.

        cls._qigits_precision_default(8)


        cls.name_of_zone = {   # dictionary translating zone codes to zone names
            getattr(cls.Zone, attr):attr for attr in dir(cls.Zone) if not callable(attr) and not attr.startswith("__")
        }

        cls._sorted_zones = sorted(cls.name_of_zone.keys(), reverse=True)   # zone code list in desc order, as defined


        # Constants
        # ---------
        cls.NAN = cls(None)


        # Sets of Zones   TODO: draw a Venn Diagram or table or something
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
        cls.ZONE_FINITE = cls._zone_union(
            cls.ZONE_LUDICROUS,
            cls.ZONE_REASONABLE,
        )
        cls.ZONE_UNREASONABLE = cls._zone_union(
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
        cls.ZONE_NONZERO = cls._zone_union(
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
        cls.ZONE_ESSENTIALLY_NONNEGATIVE_ZERO = cls._zone_union(
            cls.ZONE_ESSENTIALLY_POSITIVE_ZERO,
            cls.ZONE_ZERO,
        )
        cls.ZONE_ESSENTIALLY_ZERO = cls._zone_union(
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
        cls.ZONE_REASONABLY_NONZERO = cls._zone_union(
            cls.ZONE_REASONABLY_POSITIVE,
            cls.ZONE_REASONABLY_NEGATIVE,
        )
        cls.ZONE_UNREASONABLY_BIG = {
            cls.Zone.TRANSFINITE,
            cls.Zone.LUDICROUS_LARGE,
            cls.Zone.LUDICROUS_LARGE_NEG,
            cls.Zone.TRANSFINITE_NEG,
        }

        cls.ZONE_NAN = {
            cls.Zone.NAN
        }
        cls._ZONE_ALL_BY_REASONABLENESS = cls._zone_union(
            cls.ZONE_REASONABLE,
            cls.ZONE_UNREASONABLE,
            cls.ZONE_NAN,
        )
        cls._ZONE_ALL_BY_FINITENESS = cls._zone_union(
            cls.ZONE_FINITE,
            cls.ZONE_NONFINITE,
            cls.ZONE_NAN,
        )
        cls._ZONE_ALL_BY_ZERONESS = cls._zone_union(
            cls.ZONE_NONZERO,
            cls.ZONE_ZERO,
            cls.ZONE_NAN,
        )
        cls._ZONE_ALL_BY_BIGNESS = cls._zone_union(
            cls.ZONE_ESSENTIALLY_ZERO,
            cls.ZONE_REASONABLY_NONZERO,
            cls.ZONE_UNREASONABLY_BIG,
            cls.ZONE_NAN,
        )

        cls.ZONE_ALL = {zone for zone in cls._sorted_zones}


Number._setup()



# TODO: Floating Point should be an add-on.  Standard is int?  Or nothing but raw, qex, qan, zones, and add-on int?!
# TODO: Suffixes, e.g. 0q81FF_02___8264_71_0500 for precisely 0.01 (0x71 = 'q' for the rational quotient)...
# ... would be 8 bytes, same as float64, ...
# ... versus 0q81FF_028F5C28F5C28F60 for ~0.0100000000000000002, 10 bytes, as close as float gets to 0.01
# TODO: Ludicrous Numbers
# TODO: Transfinite Numbers
# TODO: Number.increment()   (phase 1: use float or int, phase 2: native computation)
# TODO: __neg__ (take advantage of two's complement encoding)
# TODO: __add__, __mul__, etc.  (phase 1: mooch float or int, phase 2: native computations)
# TODO:  other Number(string)s, e.g. assert 1 == Number('1')
# TODO: is_whole_number() -- would help discriminate whether phase-1 math should use int or float, (less than 2**52)
# TODO: hooks to add features modularly
# TODO: change % to .format()
# TODO: decimal.Decimal
# TODO: Numpy types -- http://docs.scipy.org/doc/numpy/user/basics.types.html
# TODO: other Numpy compatibilities?


