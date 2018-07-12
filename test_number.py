# coding=utf-8
"""
Testing qiki number.py
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
# noinspection PyUnresolvedReferences
import operator
import pickle
import sys
import unittest

from number import *


# Slow tests:
TEST_INC_ON_THOUSAND_POWERS_OF_TWO = False   # E.g. 0q86_01.inc() == 0q86_010000000001 (2-12 seconds)
LUDICROUS_NUMBER_SUPPORT = False   # True => to and from int and float.
                                   # False => invalid values, or raise LudicrousNotImplemented


class NumberAlternate(Number):
    """
    This derived class will be tested here, in the place of Number.

    It implements some alternate methods, and makes sure they behave the same as the standard methods.
    """

    @property
    def zone(self):
        """Try both methods for computing zone.  Make sure they agree."""
        zone_original = super(NumberAlternate, self).zone
        zone_alternate = self.zone_alternate_by_loop()
        assert zone_alternate == zone_original, \
            "Mismatched zone determination for {qstring}:  if-method {if_answer}, loop-method {loop_answer}".format(
                qstring=self.qstring(),
                if_answer=Zone.name_from_code[zone_original],
                loop_answer=Zone.name_from_code[zone_alternate],
            )
        return zone_original

    def zone_alternate_by_loop(self):   # slower than if-else-tree, but enforces Zone value rules
        """Get the Zone for a Number, by scanning Zone values."""
        for z in Zone.descending_codes:
            if z <= self.raw:
                return z
        raise RuntimeError("zone_alternate_by_loop() fell through?!  '{}' < Zone.NAN!".format(repr(self)))



    def __int__(self):
        """Try both methods for converting to int.  Make sure they agree."""
        int_original = super(NumberAlternate, self).__int__()
        int_alternate = self._int_alternate_by_ifs()
        assert int_alternate == int_original, (
            "Mismatched int conversion for {qstring}:  dict-method {dict_answer}, if-method {if_answer}".format(
                qstring=self.qstring(),
                dict_answer=int_original,
                if_answer=int_alternate,
            )
        )
        return int_original

    def _int_alternate_by_ifs(self):
        """Convert to an integer, using exhaustive if-clauses."""
        if   Zone.TRANSFINITE          <= self.raw:  return self._int_cant_be_positive_infinity()
        elif Zone.POSITIVE             <= self.raw:  return self._to_int_positive()
        elif Zone.FRACTIONAL_NEG       <= self.raw:  return 0
        elif Zone.LUDICROUS_LARGE_NEG  <= self.raw:  return self._to_int_negative()
        elif Zone.NAN                  <  self.raw:  return self._int_cant_be_negative_infinity()
        else:                                        return self._int_cant_be_nan()



    def __float__(self):
        """Try both methods for converting to float.  Make sure they agree."""
        float_original = super(NumberAlternate, self).__float__()
        float_alternate = self._float_alternate_by_ifs()
        assert floats_really_same(float_alternate, float_original), (
            "Mismatched float conversion for {qstring}:  dict-method {dict_answer}, if-method {if_answer}".format(
                qstring=self.qstring(),
                dict_answer=float_original,
                if_answer=float_alternate,
            )
        )
        return float_original

    def _float_alternate_by_ifs(self):
        """To a floating point number, using exhaustive if-clauses."""
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



    def is_suffixed(self):
        """Try all methods for determining whether the number has any suffixes.  Make sure they agree."""
        is_suffixed_original = super(NumberAlternate, self).is_suffixed()
        is_suffixed_alternate_1 = self._is_suffixed_alternate_1()
        is_suffixed_alternate_2 = self._is_suffixed_alternate_2()
        assert is_suffixed_alternate_1 == is_suffixed_alternate_2 == is_suffixed_original, (
            "Mismatched is_suffixed for {qstring}:  "
            "terminator-method {terminator_answer}, "
            "parsing-method {parsing_answer}, "
            "suffixes-method {suffixes_answer}".format(
                qstring=self.qstring(),
                terminator_answer=is_suffixed_original,
                parsing_answer=is_suffixed_alternate_1,
                suffixes_answer=is_suffixed_alternate_2,
            )
        )
        return is_suffixed_original

    def _is_suffixed_alternate_1(self):
        try:
            next(self._suffix_indexes_backwards())
        except StopIteration:
            return False
        else:
            return True

    def _is_suffixed_alternate_2(self):
        return len(self.suffixes) != 0


NumberOriginal = Number
Number = NumberAlternate


class NumberTests(unittest.TestCase):

    def assertFloatSame(self, x1, x2):
        self.assertTrue(floats_really_same(x1, x2), "{x1} is not the same as {x2}".format(
            x1=x1,
            x2=x2,
        ))

    def assertFloatNotSame(self, x1, x2):
        self.assertFalse(floats_really_same(x1, x2), "{x1} is the same as {x2}".format(
            x1=x1,
            x2=x2,
        ))

    def assertEqualSets(self, s1, s2):
        if s1 != s2:
            self.fail(
                "Left extras:\n"
                "\t{left_extras}"
                "\nRight extras:\n"
                "\t{right_extras}\n".format(
                    left_extras='\n\t'.join((Zone.name_from_code[z] for z in (s1-s2))),
                    right_extras='\n\t'.join((Zone.name_from_code[z] for z in (s2-s1))),
                )
            )

    def assertPositive(self, n):
        self.assertTrue(n.is_positive())
        self.assertFalse(n.is_zero())
        self.assertFalse(n.is_negative())

    def assertZero(self, n):
        self.assertFalse(n.is_positive())
        self.assertTrue(n.is_zero())
        self.assertFalse(n.is_negative())

    def assertNegative(self, n):
        self.assertFalse(n.is_positive())
        self.assertFalse(n.is_zero())
        self.assertTrue(n.is_negative())

    def assertRaisesRegex(self, error, expression, *args, **kwargs):
        """
        A lot of shenanigans just to avoid a warning in Python 3, or an error in Python 2.

        The warning in Python 3 when using assertRaisesRegexp:
            DeprecationWarning: Please use assertRaisesRegex instead.
        The error in Python 2 when using assertRaisesRegex:
            AttributeError: 'NumberSuffixTests' object has no attribute 'assertRaisesRegex'

        :param error: - class derived from Error
        :param expression: - regular expression to match the error message
        :return: - for use in a with statement
        """
        if hasattr(super(NumberTests, self), 'assertRaisesRegex'):
            # noinspection PyUnresolvedReferences,PyCompatibility
            return super(NumberTests, self).assertRaisesRegex(error, expression, *args, **kwargs)
        elif hasattr(super(NumberTests, self), 'assertRaisesRegexp'):
            # noinspection PyUnresolvedReferences
            return super(NumberTests, self).assertRaisesRegexp(error, expression, *args, **kwargs)
        else:
            raise AttributeError("Cannot find the assert function for matching the message")


# noinspection SpellCheckingInspection
class NumberBasicTests(NumberTests):

    def test_raw(self):
        n = Number('0q82_01')
        self.assertEqual(b'\x82\x01', n.raw)

    def test_raw_from_unicode(self):
        n = Number(u'0q82_01')
        self.assertEqual(b'\x82\x01', n.raw)

    def test_raw_from_byte_string(self):
        self.assertEqual(Number(1), Number(u'0q82_01'))
        if six.PY2:
            self.assertEqual(       u'0q82_01',         b'0q82_01')
            self.assertEqual(Number(u'0q82_01'), Number(b'0q82_01'))
        else:
            self.assertNotEqual(    u'0q82_01',         b'0q82_01')
            with self.assertRaises(TypeError):
                Number(b'0q82_01')

    def test_unsupported_type(self):
        class SomeType(object):
            pass
        some_type = SomeType()

        with self.assertRaises(TypeError):
            Number(some_type)
        with self.assertRaises(Number.ConstructorTypeError):
            Number(some_type)
        try:
            Number(some_type)
        except Number.ConstructorTypeError as e:
            self.assertIn('SomeType', str(e))


    def test_hex(self):
        n = Number('0q82')
        self.assertEqual('82', n.hex())

    def test_str(self):
        """
        Test that str(Number) outputs a string, and it can reconstitute the value.

        Don't test what str() outputs -- it's some human-readable string version of the Number.
        This test only makes sure that plowing that string back into Number() leads to the same value.

        NOTE:  Throughout these unit tests, str(n) is avoided in favor of n.qstring().
        That way e.g. str(Number(1)) is free to be '0q82_01' or '1'.
        """
        n = Number('0q83_03E8')
        self.assertEqual('str', type(str(n)).__name__)
        self.assertEqual(n, Number(str(n)))

    def test_unicode(self):
        n = Number('0q83_03E8')
        if six.PY2:
            # noinspection PyCompatibility,PyUnresolvedReferences
            self.assertEqual('0q83_03E8', unicode(n))
            # noinspection PyCompatibility,PyUnresolvedReferences
            self.assertEqual('unicode', type(unicode(n)).__name__)
        else:
            with self.assertRaises(NameError):
                # noinspection PyCompatibility,PyUnresolvedReferences
                unicode(n)

    def test_unicode_output(self):
        n = Number('0q83_03E8')
        self.assertEqual(u"0q83_03E8", six.text_type(n))
        self.assertIsInstance(six.text_type(n), six.text_type)

    def test_unicode_input(self):
        n = Number(u'0q83_03E8')
        self.assertEqual("0q83_03E8", n.qstring())
        self.assertEqual(u"0q83_03E8", six.text_type(n))

    def test_isinstance(self):
        n = Number(1)
        self.assertIsInstance(n, Number)
        assert isinstance(n, Number)

    def test_qstring(self):
        n = Number('0q82')
        self.assertEqual('0q82', n.qstring())
        self.assertEqual('0q8201C0', Number('0q8201C0').qstring(underscore=0))

    def test_qstring_underscore_in_zero(self):
        self.assertEqual('0q8201C0', Number('0q82_01C0').qstring(underscore=0))

    def test_qstring_underscore_in_one(self):
        self.assertEqual('0q82_01C0', Number('0q82_01C0').qstring(underscore=1))

    def test_qstring_underscore_in_default(self):
        self.assertEqual('0q82_01C0', Number('0q82_01C0').qstring())

    def test_qstring_underscore_out(self):
        self.assertEqual('0q807F', Number('0q807F').qstring())
        self.assertEqual('0q7F81', Number('0q7F81').qstring())
        self.assertEqual('0q7E00_80', Number('0q7E0080').qstring())
        self.assertEqual('0q81FF_80', Number('0q81FF80').qstring())
        self.assertEqual('0q82_01C0', Number('0q8201C0').qstring())
        self.assertEqual('0q82_02', Number('0q8202').qstring())
        self.assertEqual('0q82', Number('0q82').qstring())
        self.assertEqual('0q80', Number('0q80').qstring())
        self.assertEqual('0q', Number('0q').qstring())

    def test_invalid_qstring(self):
        """Invalid Number contents still have a value."""
        self.assertFloatSame(+0.0, float(Number('0q81')))
        self.assertFloatSame(-0.0, float(Number('0q7EFF')))

    def test_from_qstring(self):
        n = Number.from_qstring('0q82_01')
        self.assertEqual('0q82_01', n.qstring())
        with self.assertRaises(Number.ConstructorValueError):
            Number.from_qstring('qqqqq')

    def test_from_raw_bytearray(self):
        self.assertEqual(Number('0q82_2A'), Number.from_raw_bytearray(bytearray(b'\x82\x2A')))

    def test_to_x_apostrophe_hex(self):
        self.assertEqual("x'822A80'", Number('0q82_2A80').x_apostrophe_hex())
        self.assertEqual("x'822A'", Number('0q82_2A').x_apostrophe_hex())
        self.assertEqual("x'80'", Number('0q80').x_apostrophe_hex())
        self.assertEqual("x''", Number('0q').x_apostrophe_hex())

    def test_to_zero_x_hex(self):
        self.assertEqual("0x822A80", Number('0q82_2A80').zero_x_hex())
        self.assertEqual("0x822A", Number('0q82_2A').zero_x_hex())
        self.assertEqual("0x80", Number('0q80').zero_x_hex())
        self.assertEqual("0x", Number('0q').zero_x_hex())

    def test_to_ditto_backslash_hex(self):
        self.assertEqual(r'"\x82\x2A\x80"', Number('0q82_2A80').ditto_backslash_hex())
        self.assertEqual(r'"\x82\x2A"', Number('0q82_2A').ditto_backslash_hex())
        self.assertEqual(r'"\x80"', Number('0q80').ditto_backslash_hex())
        self.assertEqual(r'""', Number('0q').ditto_backslash_hex())

    def test_from_mysql(self):
        self.assertEqual(Number('0q82_2A'), Number.from_mysql(bytearray(b'\x82\x2A')))

    def test_to_mysql(self):
        self.assertEqual("x'822A'", Number('0q82_2A').mysql_string())

    def test_to_c(self):
        self.assertEqual(r'"\x82\x2A"', Number('0q82_2A').c_string())

    # TODO:  test from_mysql and to_mysql using SELECT and @-variables
    #         -- maybe in test_word.py because it already has a db connection.

    # Blob literal syntaxes:
    # ----------------------
    # mysql: x'822A' or 0x822A
    # mssql: 0x822A
    # sqlite or DB2: x'822A'
    # postgre: E'\x82\x2A'
    # c or java or javascript: "\x82\x2A"

    def test_repr(self):
        n =               Number('0q83_03E8')
        self.assertEqual("Number('0q83_03E8')", repr(n))
        self.assertEqual(        '0q83_03E8', eval(repr(n)).qstring())
        self.assertEqual(n, eval(repr(n)))

    def test_zero(self):
        self.assertEqual('0q80', Number.ZERO.qstring())
        self.assertEqual(0, int(Number.ZERO))
        self.assertEqual(0.0, float(Number.ZERO))

    def test_nan(self):
        self.assertEqual('0q', Number.NAN.qstring())
        self.assertEqual(b'', Number.NAN.raw)
        self.assertEqual('', Number.NAN.hex())
        self.assertEqual('nan', str(float(Number.NAN)))
        self.assertFloatSame(float('nan'), float(Number.NAN))

    def test_nan_default(self):
        self.assertEqual('0q', Number().qstring())

    def test_nan_equality(self):
        # TODO:  Is this right?  Number.NAN comparisons behave like any other number, not like float('nan')?
        # SEE:  float('nan') comparisons all False, https://stackoverflow.com/q/1565164/673991
        # TODO:  Any comparisons with NAN should raise Number.CompareError("...is_nan() instead...").
        nan = Number.NAN
        self.assertEqual(nan, Number.NAN)
        self.assertEqual(nan, Number(None))
        self.assertEqual(nan, Number('0q'))
        self.assertEqual(nan, Number(float('nan')))
        self.assertEqual(nan, float('nan'))

    def test_nan_inequality(self):
        nan = Number.NAN
        self.assertNotEqual(nan, Number(0))
        self.assertNotEqual(nan, 0)
        self.assertNotEqual(nan, float('inf'))

    def test_nan_result(self):
        """SEE:  https://en.wikipedia.org/wiki/NaN#Operations_generating_NaN"""
        self.assertEqual(Number.NAN, Number.NAN + Number.NAN)
        self.assertEqual(Number.NAN, Number.NAN + Number(0))
        self.assertEqual(Number.NAN, Number(0) + Number.NAN)
        self.assertEqual(Number.NAN, Number(0) - Number.NAN)
        self.assertEqual(Number.NAN, Number(0) * Number.NAN)
        self.assertEqual(Number.NAN, Number(0) / Number.NAN)
        self.assertEqual(Number.NAN, Number.NAN + Number(1.5))
        self.assertEqual(Number.NAN, Number.NAN + Number(2**1000-2))
        self.assertEqual(Number.NAN, Number.NAN + Number(2**1000-1))
        if LUDICROUS_NUMBER_SUPPORT:
            self.assertEqual(Number.NAN, Number.NAN + Number(2**1000))
            self.assertEqual(Number.NAN, Number.NAN + Number(2**1000+1))

        self.assertEqual(Number.NAN, Number.POSITIVE_INFINITY - Number.POSITIVE_INFINITY)
        self.assertEqual(Number.NAN, Number.POSITIVE_INFINITY + Number.NEGATIVE_INFINITY)
        self.assertEqual(Number.NAN, Number.NEGATIVE_INFINITY + Number.POSITIVE_INFINITY)
        self.assertEqual(Number.NAN, Number.NEGATIVE_INFINITY - Number.NEGATIVE_INFINITY)

        self.assertEqual(Number.NAN, Number(0) * Number.POSITIVE_INFINITY)
        self.assertEqual(Number.NAN, Number(0) * Number.NEGATIVE_INFINITY)
        self.assertEqual(Number.NAN, Number.POSITIVE_INFINITY * Number(0))
        self.assertEqual(Number.NAN, Number.NEGATIVE_INFINITY * Number(0))

        self.assertEqual(Number.NAN, Number.POSITIVE_INFINITY / Number.POSITIVE_INFINITY)
        self.assertEqual(Number.NAN, Number.POSITIVE_INFINITY / Number.NEGATIVE_INFINITY)
        self.assertEqual(Number.NAN, Number.NEGATIVE_INFINITY / Number.POSITIVE_INFINITY)
        self.assertEqual(Number.NAN, Number.NEGATIVE_INFINITY / Number.NEGATIVE_INFINITY)

    def test_infinite_result(self):
        self.assertEqual(Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY + Number.POSITIVE_INFINITY)
        self.assertEqual(Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY + Number.NEGATIVE_INFINITY)
        self.assertEqual(Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY - Number.NEGATIVE_INFINITY)
        self.assertEqual(Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY - Number.POSITIVE_INFINITY)

        self.assertEqual(Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY * Number.POSITIVE_INFINITY)
        self.assertEqual(Number.NEGATIVE_INFINITY, Number.POSITIVE_INFINITY * Number.NEGATIVE_INFINITY)
        self.assertEqual(Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY * Number.POSITIVE_INFINITY)
        self.assertEqual(Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY * Number.NEGATIVE_INFINITY)

    def test_zero_result(self):
        self.assertEqual(Number(0), Number(1) / Number.POSITIVE_INFINITY)
        self.assertEqual(Number(0), Number(1.5) / Number.POSITIVE_INFINITY)
        self.assertEqual(Number(0), Number(-1.5) / Number.POSITIVE_INFINITY)
        self.assertEqual(Number(0), Number(-1.5) / Number.NEGATIVE_INFINITY)
        self.assertEqual(Number(0), Number(1.5) / Number.NEGATIVE_INFINITY)
        self.assertEqual(Number(0), Number(1) / Number.NEGATIVE_INFINITY)

    def test_one_result(self):
        """
        A different school of thought is that the following computations should result in NAN.

        Here's why e.g. 0**0 is not so cut and dry:
        The limit of x**0 as x approaches 0 from the positive is 1
        The limit of x**0 as x approaches 0 from the negative is -1
        The limit of 0**x as x approaches 0 from the positive is 0
        The limit of 0**x as x approaches 0 from the negative is division by zero, infinity maybe
        """
        self.assertEqual(Number(1), Number(0) ** Number(0))
        self.assertEqual(Number(1), Number(1) ** Number.POSITIVE_INFINITY)
        self.assertEqual(Number(1), Number.POSITIVE_INFINITY ** Number(0))

    def test_ludicrous_boundary(self):
        big_reasonable = Number(2**999-1)
        self.assertEqual(Number(2**1000-2), big_reasonable + big_reasonable)

        max_reasonable = Number(2**1000-1)
        if LUDICROUS_NUMBER_SUPPORT:
            self.assertEqual(Number(2**1001-2), max_reasonable + max_reasonable)
        else:
            with self.assertRaises(Number.LudicrousNotImplemented):
                _ = Number(2**1001-2)
            with self.assertRaises(Number.LudicrousNotImplemented):
                _ = max_reasonable + max_reasonable

    def test_zero_division(self):
        with self.assertRaises(ZeroDivisionError):
            _ = Number(0) / Number(0)
        with self.assertRaises(ZeroDivisionError):
            _ = Number(1) / Number(0)
        with self.assertRaises(ZeroDivisionError):
            _ = Number(1.5) / Number(0)
        with self.assertRaises(ZeroDivisionError):
            _ = Number(-0.0) / Number(0)
        with self.assertRaises(ZeroDivisionError):
            _ = Number.POSITIVE_INFINITY / Number(0)
        with self.assertRaises(ZeroDivisionError):
            _ = Number.NEGATIVE_INFINITY / Number(0)

    def test_infinite_constants(self):
        self.assertEqual('0qFF_81', Number.POSITIVE_INFINITY.qstring())
        self.assertEqual('0q00_7F', Number.NEGATIVE_INFINITY.qstring())

        self.assertEqual(float('+inf'), Number.POSITIVE_INFINITY)
        self.assertEqual(float('-inf'), Number.NEGATIVE_INFINITY)

    def test_infinitesimal_float(self):
        self.assertNotEqual(0, Number.POSITIVE_INFINITESIMAL)
        self.assertNotEqual(0, Number.NEGATIVE_INFINITESIMAL)

        self.assertEqual(0, float(Number.POSITIVE_INFINITESIMAL))
        self.assertEqual(0, float(Number.NEGATIVE_INFINITESIMAL))

        self.assertFloatSame(+0.0, float(Number.POSITIVE_INFINITESIMAL))
        self.assertFloatSame(-0.0, float(Number.NEGATIVE_INFINITESIMAL))

    def test_qantissa_max_qigits(self):
        qstring =     '0q82_112233445566778899AABBCCDDEEFF'
        self.assertEqual((0x112233445566778899AABBCCDDEEFF, 15), Number(qstring).qan_int_len())
        self.assertEqual((0x112233445566778899AABBCCDD    , 13), Number(qstring).qan_int_len(max_qigits=13))
        self.assertEqual((0x112233445566778899AABBCCDDEE  , 14), Number(qstring).qan_int_len(max_qigits=14))
        self.assertEqual((0x112233445566778899AABBCCDDEEFF, 15), Number(qstring).qan_int_len(max_qigits=15))
        self.assertEqual((0x112233445566778899AABBCCDDEEFF, 15), Number(qstring).qan_int_len(max_qigits=16))

    def test_qantissa_positive(self):
        self.assertEqual((0x03E8,2), Number('0q83_03E8').qan_int_len())
        self.assertEqual((0x03E8,2), Number('0q83_03E8').qan_int_len())
        self.assertEqual((0x0101,2), Number('0q83_0101').qan_int_len())
        self.assertEqual((  0x01,1), Number('0q83_01').qan_int_len())
        self.assertEqual((  0x00,0), Number('0q83').qan_int_len())
        self.assertEqual((  0xFF,1), Number('0q82_FF').qan_int_len())
        self.assertEqual((  0xFA,1), Number('0q7D_FA').qan_int_len())

    def test_qantissa_negative(self):
        self.assertEqual((0xFE,1), Number('0q7D_FE').qan_int_len())
        self.assertEqual((0x01,1), Number('0q7D_01').qan_int_len())
        self.assertEqual((0xFEFFFFFA,4), Number('0q7A_FEFFFFFA').qan_int_len())
        self.assertEqual((0x00000001,4), Number('0q7A_00000001').qan_int_len())

    def test_qantissa_fractional(self):
        self.assertEqual(  (0x80,1), Number('0q81FF_80').qan_int_len())
        self.assertEqual(  (0x40,1), Number('0q81FF_40').qan_int_len())
        self.assertEqual((0x4220,2), Number('0q81FF_4220').qan_int_len())

    def test_qantissa_fractional_neg(self):
        self.assertEqual(  (0x01,1), Number('0q7E00_01').qan_int_len())
        self.assertEqual(  (0x80,1), Number('0q7E00_80').qan_int_len())
        self.assertEqual(  (0xC0,1), Number('0q7E00_C0').qan_int_len())
        self.assertEqual(  (0xFF,1), Number('0q7E00_FF').qan_int_len())
        self.assertEqual(  (0xFF,1), Number('0q7E01_FF').qan_int_len())
        self.assertEqual((0xFF80,2), Number('0q7E01_FF80').qan_int_len())

    def test_qantissa_unsupported(self):
        number_has_no_qantissa = Number(0)
        with self.assertRaises(Number.QanValueError):
            number_has_no_qantissa.qan_int_len()

    def test_qexponent_unsupported(self):
        number_has_no_qexponent = Number(0)
        with self.assertRaises(Number.QexValueError):
            number_has_no_qexponent.qex_int()

    def test_qexponent_positive(self):
        self.assertEqual(1, Number('0q82_01').qex_int())
        self.assertEqual(1, Number('0q82_01000001').qex_int())
        self.assertEqual(1, Number('0q82_02').qex_int())
        self.assertEqual(1, Number('0q82_FF').qex_int())
        self.assertEqual(2, Number('0q83_01').qex_int())
        self.assertEqual(3, Number('0q84_01').qex_int())
        self.assertEqual(4, Number('0q85_01').qex_int())
        self.assertEqual(5, Number('0q86_01').qex_int())
        self.assertEqual(6, Number('0q87_01').qex_int())
        self.assertEqual(124, Number('0qFD_01').qex_int())
        self.assertEqual(125, Number('0qFE_01').qex_int())

    def test_qexponent_negative(self):
        self.assertEqual(6, Number('0q78').qex_int())
        self.assertEqual(5, Number('0q79').qex_int())
        self.assertEqual(4, Number('0q7A').qex_int())
        self.assertEqual(3, Number('0q7B').qex_int())
        self.assertEqual(2, Number('0q7C').qex_int())
        self.assertEqual(1, Number('0q7D').qex_int())

        self.assertEqual(125, Number('0q01').qex_int())
        self.assertEqual(124, Number('0q02').qex_int())

    def test_qexponent_fractional(self):
        self.assertEqual(   0, Number('0q81FF_80').qex_int())
        self.assertEqual(   0, Number('0q81FF_01').qex_int())
        self.assertEqual(  -1, Number('0q81FE_01').qex_int())
        self.assertEqual(  -2, Number('0q81FD_01').qex_int())
        self.assertEqual(-123, Number('0q8184_01').qex_int())
        self.assertEqual(-124, Number('0q8183_01').qex_int())

    def test_qexponent_fractional_neg(self):
        self.assertEqual(   0, Number('0q7E00_01').qex_int())   # -.996
        self.assertEqual(   0, Number('0q7E00_80').qex_int())   # -.5
        self.assertEqual(   0, Number('0q7E00_FF').qex_int())   # -.004
        self.assertEqual(  -1, Number('0q7E01_FF').qex_int())
        self.assertEqual(  -2, Number('0q7E02_FF').qex_int())
        self.assertEqual(-123, Number('0q7E7B_FF').qex_int())
        self.assertEqual(-124, Number('0q7E7C_FF').qex_int())

    def test_alias_one(self):
        """
        Redundant, invalid values near 1 should be interpreted as 1.

        NOTE:  Every integral power of 256 (including negative exponents or significands)
        has a plateau of redundant, invalid values like this.
        """
        self.assertEqual(1.0, float(Number('0q82_01')))
        self.assertEqual(1.0, float(Number('0q82_00FFFFFF')))
        self.assertEqual(1.0, float(Number('0q82_00C0')))
        self.assertEqual(1.0, float(Number('0q82_0080')))
        self.assertEqual(1.0, float(Number('0q82_0040')))
        self.assertEqual(1.0, float(Number('0q82__0000__0000')))
        self.assertEqual(1.0, float(Number('0q82__0000')))
        self.assertEqual(1.0, float(Number('0q82')))

    def test_alias_one_neg(self):
        self.assertEqual(-1.0, float(Number('0q7D_FF')))
        self.assertEqual(-1.0, float(Number('0q7D_FF__0000')))
        self.assertEqual(-1.0, float(Number('0q7D_FF3C7A38A1F250DE7E9071')))
        self.assertEqual(-1.0, float(Number('0q7D_FF40')))
        self.assertEqual(-1.0, float(Number('0q7D_FF80')))
        self.assertEqual(-1.0, float(Number('0q7D_FFC0')))
        self.assertEqual(-1.0, float(Number('0q7D_FFF0')))
        self.assertEqual(-1.0, float(Number('0q7D_FFFF')))
        self.assertEqual(-1.0, float(Number('0q7E')))

    def test_alias_positive(self):
        self.assertEqual(256.0, float(Number('0q83_01')))
        self.assertEqual(256.0, float(Number('0q83_00FFFFFF')))
        self.assertEqual(256.0, float(Number('0q83_00C0')))
        self.assertEqual(256.0, float(Number('0q83_0080')))
        self.assertEqual(256.0, float(Number('0q83_0040')))
        self.assertEqual(256.0, float(Number('0q83__0000__0000')))
        self.assertEqual(256.0, float(Number('0q83__0000')))
        self.assertEqual(256.0, float(Number('0q83')))

        self.assertEqual(65536.0, float(Number('0q84_01')))
        self.assertEqual(65536.0, float(Number('0q84_00FFFFFF')))
        self.assertEqual(65536.0, float(Number('0q84_00C0')))
        self.assertEqual(65536.0, float(Number('0q84_0080')))
        self.assertEqual(65536.0, float(Number('0q84_0040')))
        self.assertEqual(65536.0, float(Number('0q84__0000__0000')))
        self.assertEqual(65536.0, float(Number('0q84__0000')))
        self.assertEqual(65536.0, float(Number('0q84')))

    def test_alias_negative(self):
        self.assertEqual(-256.0, float(Number('0q7C_FF')))
        self.assertEqual(-256.0, float(Number('0q7C_FF__0000')))
        self.assertEqual(-256.0, float(Number('0q7C_FF3C7A38A1F250DE7E9071')))
        self.assertEqual(-256.0, float(Number('0q7C_FF40')))
        self.assertEqual(-256.0, float(Number('0q7C_FF80')))
        self.assertEqual(-256.0, float(Number('0q7C_FFC0')))
        self.assertEqual(-256.0, float(Number('0q7C_FFF0')))
        self.assertEqual(-256.0, float(Number('0q7C_FFFF')))
        self.assertEqual(-256.0, float(Number('0q7D')))

        self.assertEqual(-65536.0, float(Number('0q7B_FF')))
        self.assertEqual(-65536.0, float(Number('0q7B_FF__0000')))
        self.assertEqual(-65536.0, float(Number('0q7B_FF3C7A38A1F250DE7E9071')))
        self.assertEqual(-65536.0, float(Number('0q7B_FF40')))
        self.assertEqual(-65536.0, float(Number('0q7B_FF80')))
        self.assertEqual(-65536.0, float(Number('0q7B_FFC0')))
        self.assertEqual(-65536.0, float(Number('0q7B_FFF0')))
        self.assertEqual(-65536.0, float(Number('0q7B_FFFF')))
        self.assertEqual(-65536.0, float(Number('0q7C')))

    def test_alias_positive_fractional(self):
        self.assertEqual(1.0/256.0, float(Number('0q81FF_01')))
        self.assertEqual(1.0/256.0, float(Number('0q81FF_00FFFFFF')))
        self.assertEqual(1.0/256.0, float(Number('0q81FF_00C0')))
        self.assertEqual(1.0/256.0, float(Number('0q81FF_0080')))
        self.assertEqual(1.0/256.0, float(Number('0q81FF_0040')))
        self.assertEqual(1.0/256.0, float(Number('0q81FF__0000__0000')))
        self.assertEqual(1.0/256.0, float(Number('0q81FF__0000')))
        self.assertEqual(1.0/256.0, float(Number('0q81FF')))

        self.assertEqual(1.0/65536.0, float(Number('0q81FE_01')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_00FFFFFF')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_00C0')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_0080')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_0040')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_00000000')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE__0000')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE')))

    def test_alias_negative_fractional(self):
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FF')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FF__0000')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FF3C7A38A1F250DE7E9071')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FF40')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FF80')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FFC0')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FFF0')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FFFF')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E01_0000')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E01')))

        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FF')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FF__0000')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FF3C7A38A1F250DE7E9071')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FF40')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FF80')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FFC0')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FFF0')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FFFF')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E02')))

    def test_normalize_plateau_compact_256(self):   # 256**1
        self.assertEqual('0q83'   , Number('0q83'                 ).qstring())
        self.assertEqual('0q83'   , Number('0q83', normalize=False).qstring())
        self.assertEqual('0q83_01', Number('0q83', normalize=True).qstring())
        self.assertEqual('0q83_01', Number('0q83').normalized().qstring())

    def test_normalize_plateau_compact_one(self):   # 256**0
        self.assertEqual('0q82'   , Number('0q82'                 ).qstring())
        self.assertEqual('0q82'   , Number('0q82', normalize=False).qstring())
        self.assertEqual('0q82_01', Number('0q82', normalize=True).qstring())
        self.assertEqual('0q82_01', Number('0q82').normalized().qstring())

    def test_normalize_plateau_compact_positive_fractional(self):   # 256**-1
        self.assertEqual('0q81FF'   , Number('0q81FF'                 ).qstring())
        self.assertEqual('0q81FF'   , Number('0q81FF', normalize=False).qstring())
        self.assertEqual('0q81FF_01', Number('0q81FF', normalize=True).qstring())
        self.assertEqual('0q81FF_01', Number('0q81FF').normalized().qstring())

    def test_normalize_plateau_compact_negative_fractional(self):   # -256**-1
        self.assertEqual('0q7E01'   , Number('0q7E01'                 ).qstring())
        self.assertEqual('0q7E01'   , Number('0q7E01', normalize=False).qstring())
        self.assertEqual('0q7E00_FF', Number('0q7E01', normalize=True).qstring())
        self.assertEqual('0q7E00_FF', Number('0q7E01').normalized().qstring())

    def test_normalize_plateau_compact_one_negative(self):   # -256**0
        self.assertEqual('0q7E'   , Number('0q7E'                 ).qstring())
        self.assertEqual('0q7E'   , Number('0q7E', normalize=False).qstring())
        self.assertEqual('0q7D_FF', Number('0q7E', normalize=True).qstring())
        self.assertEqual('0q7D_FF', Number('0q7E').normalized().qstring())

    def test_normalize_plateau_compact_256_negative(self):   # -256**1
        self.assertEqual('0q7D'   , Number('0q7D'                 ).qstring())
        self.assertEqual('0q7D'   , Number('0q7D', normalize=False).qstring())
        self.assertEqual('0q7C_FF', Number('0q7D', normalize=True).qstring())
        self.assertEqual('0q7C_FF', Number('0q7D').normalized().qstring())

    def test_normalize_plateau_gibberish(self):
        self.assertEqual('0q82_00DEADBEEF', Number('0q82_00DEADBEEF'                 ).qstring())
        self.assertEqual('0q82_00DEADBEEF', Number('0q82_00DEADBEEF', normalize=False).qstring())
        self.assertEqual('0q82_01',         Number('0q82_00DEADBEEF', normalize=True).qstring())
        self.assertEqual('0q82_01',         Number('0q82_00DEADBEEF').normalized().qstring())

        self.assertEqual('0q81FF_00DEADBEEF', Number('0q81FF_00DEADBEEF'                 ).qstring())
        self.assertEqual('0q81FF_00DEADBEEF', Number('0q81FF_00DEADBEEF', normalize=False).qstring())
        self.assertEqual('0q81FF_01',         Number('0q81FF_00DEADBEEF', normalize=True).qstring())
        self.assertEqual('0q81FF_01',         Number('0q81FF_00DEADBEEF').normalized().qstring())

        self.assertEqual('0q7E00_FFDEADBEEF', Number('0q7E00_FFDEADBEEF'                 ).qstring())
        self.assertEqual('0q7E00_FFDEADBEEF', Number('0q7E00_FFDEADBEEF', normalize=False).qstring())
        self.assertEqual('0q7E00_FF',         Number('0q7E00_FFDEADBEEF', normalize=True).qstring())
        self.assertEqual('0q7E00_FF',         Number('0q7E00_FFDEADBEEF').normalized().qstring())

        self.assertEqual('0q7D_FFDEADBEEF', Number('0q7D_FFDEADBEEF'                 ).qstring())
        self.assertEqual('0q7D_FFDEADBEEF', Number('0q7D_FFDEADBEEF', normalize=False).qstring())
        self.assertEqual('0q7D_FF',         Number('0q7D_FFDEADBEEF', normalize=True).qstring())
        self.assertEqual('0q7D_FF',         Number('0q7D_FFDEADBEEF').normalized().qstring())

    def test_normalize_plateau_suffixed(self):
        self.assertEqual('0q83_01__7E0100', Number('0q83', Suffix(Suffix.Type.TEST)).normalized().qstring())
        self.assertEqual('0q82_01__7E0100', Number('0q82', Suffix(Suffix.Type.TEST)).normalized().qstring())
        self.assertEqual('0q81FF_01__7E0100', Number('0q81FF_00BEEF', Suffix(Suffix.Type.TEST)).normalized().qstring())
        self.assertEqual('0q7E00_FF__7E0100', Number('0q7E00_FFBEEF', Suffix(Suffix.Type.TEST)).normalized().qstring())
        self.assertEqual('0q7D_FF__7E0100', Number('0q7E', Suffix(Suffix.Type.TEST)).normalized().qstring())
        self.assertEqual('0q7C_FF__7E0100', Number('0q7D', Suffix(Suffix.Type.TEST)).normalized().qstring())

    def test_normalize_imaginary(self):
        n = Number(42, Suffix(Suffix.Type.IMAGINARY, Number(10)))
        self.assertEqual('0q82_2A__820A_690300', n.qstring())
        n._normalize_imaginary()
        self.assertEqual('0q82_2A__820A_690300', n.qstring())

        n = Number(42, Suffix(Suffix.Type.IMAGINARY, Number(0)))
        self.assertEqual('0q82_2A__80_690200', n.qstring())
        n._normalize_imaginary()
        self.assertEqual('0q82_2A', n.qstring())

        n = Number(
            42,
            Suffix(Suffix.Type.IMAGINARY, Number(10)),
            Suffix(Suffix.Type.IMAGINARY, Number(10))
        )
        self.assertEqual('0q82_2A__820A_690300__820A_690300', n.qstring())
        n._normalize_imaginary()
        self.assertEqual('0q82_2A__820A_690300__820A_690300', n.qstring())

        n = Number(
            42,
            Suffix(Suffix.Type.IMAGINARY, Number(10)),
            Suffix(Suffix.Type.IMAGINARY, Number(0))
        )
        self.assertEqual('0q82_2A__820A_690300__80_690200', n.qstring())
        n._normalize_imaginary()
        self.assertEqual('0q82_2A__820A_690300__80_690200', n.qstring())

        n = Number(
            42,
            Suffix(Suffix.Type.IMAGINARY, Number(0)),
            Suffix(Suffix.Type.IMAGINARY, Number(10))
        )
        self.assertEqual('0q82_2A__80_690200__820A_690300', n.qstring())
        n._normalize_imaginary()
        self.assertEqual('0q82_2A__80_690200__820A_690300', n.qstring())

        n = Number(
            42,
            Suffix(Suffix.Type.IMAGINARY, Number(0)),
            Suffix(Suffix.Type.IMAGINARY, Number(0))
        )
        self.assertEqual('0q82_2A__80_690200__80_690200', n.qstring())
        n._normalize_imaginary()
        self.assertEqual('0q82_2A', n.qstring())


    def test_int_plateau(self):
        self.assertEqual(65536, int(Number('0q84_01')))
        self.assertEqual(65536, int(Number('0q84')))
        self.assertEqual(256, int(Number('0q83_01')))
        self.assertEqual(256, int(Number('0q83')))
        self.assertEqual(1, int(Number('0q82_01')))
        self.assertEqual(1, int(Number('0q82')))
        self.assertEqual(-1, int(Number('0q7E')))
        self.assertEqual(-1, int(Number('0q7D_FF')))
        self.assertEqual(-256, int(Number('0q7D')))
        self.assertEqual(-256, int(Number('0q7C_FF')))
        self.assertEqual(-65536, int(Number('0q7C')))
        self.assertEqual(-65536, int(Number('0q7B_FF')))

        

    def test_normalize_less(self):
        self.assertFalse(Number('0q82') < Number('0q82_01'))
        self.assertFalse(Number('0q81FF') < Number('0q81FF_01'))
        self.assertFalse(Number('0q7E00_FF') < Number('0q7E01'))
        self.assertFalse(Number('0q7D_FF') < Number('0q7E'))

    def test_normalize_greater(self):
        self.assertFalse(Number('0q82_01') > Number('0q82'))
        self.assertFalse(Number('0q81FF_01') > Number('0q81FF'))
        self.assertFalse(Number('0q7E01') > Number('0q7E00_FF'))
        self.assertFalse(Number('0q7E') > Number('0q7D_FF'))

    def test_normalize_less_equal(self):
        self.assertTrue(Number('0q82_01') <= Number('0q82'))
        self.assertTrue(Number('0q81FF_01') <= Number('0q81FF'))
        self.assertTrue(Number('0q7E01') <= Number('0q7E00_FF'))
        self.assertTrue(Number('0q7E') <= Number('0q7D_FF'))

    def test_normalize_greater_equal(self):
        self.assertTrue(Number('0q82') >= Number('0q82_01'))
        self.assertTrue(Number('0q81FF') >= Number('0q81FF_01'))
        self.assertTrue(Number('0q7E00_FF') >= Number('0q7E01'))
        self.assertTrue(Number('0q7D_FF') >= Number('0q7E'))

    def test_alias_equality(self):
        """Test number plateaus at +/-256**+/-n for n=0,1,2."""
        self.assertEqual(Number('0q84'), Number('0q84_01'))        #  256**2
        self.assertEqual(Number('0q83'), Number('0q83_01'))        #  256**1
        self.assertEqual(Number('0q82'), Number('0q82_01'))        #  256**0
        self.assertEqual(Number('0q81FF'), Number('0q81FF_01'))    #  256**-1
        self.assertEqual(Number('0q7E02'), Number('0q7E01_FF'))    #  256**-2
        self.assertEqual(Number('0q81FE'), Number('0q81FE_01'))    # -256**-2
        self.assertEqual(Number('0q7E01'), Number('0q7E00_FF'))    # -256**-1
        self.assertEqual(Number('0q7E'), Number('0q7D_FF'))        # -256**0
        self.assertEqual(Number('0q7D'), Number('0q7C_FF'))        # -256**1
        self.assertEqual(Number('0q7C'), Number('0q7B_FF'))        # -256**2

    def test_integers_and_qstrings(self):

        def i__q(i, q):
            """
            Test the Number constructor on an integer and a qstring, converting in both directions.

            Very Short Version:
                assert Number(i) == Number(q)

            Less Short version:
                assert q == Number(i).qstring()
                assert i == int(Number(q))

            Verify each integer and qstring is monotonic -- the values are tested
            in descending order.

            Why a buncha i__q() calls are superior to a list of test case data:
            so the stack trace identifies the line with the failing data.
            """
            assert isinstance(i, six.integer_types)
            assert isinstance(q, six.string_types)
            i_new = int(Number(q))
            q_new =     Number(i).qstring()
            self.assertEqual(i, i_new, "{} != {} <--Number--- '{}'"        .format(i, i_new,       q))
            self.assertEqual(q_new, q,       "{} ---Number--> '{}' != '{}'".format(i,       q_new, q))

            out_of_sequence = []
            if not context.the_first:
                integers_oos =        i      >        context.i_last
                strings_oos  = Number(q).raw > Number(context.q_last).raw
                if integers_oos:
                    out_of_sequence.append(
                        "Integers out of sequence: {i_below:d} should be less than {i_above:d}".format(
                            i_below=i,
                            i_above=context.i_last
                        )
                    )
                if strings_oos:
                    out_of_sequence.append(
                        "qstrings out of sequence: {q_below} should be less than {q_above}".format(
                            q_below=q,
                            q_above=context.q_last
                        )
                    )
                if out_of_sequence:
                    self.fail("\n".join(out_of_sequence))

            context.i_last = i
            context.q_last = q
            context.the_first = False

        # noinspection PyPep8Naming
        class context(object):
            """Variables that are local to test_integers_and_qstrings(), but global to i__q()."""
            the_first = True
            i_last = None
            q_last = None

        if LUDICROUS_NUMBER_SUPPORT:
            i__q(256**65536,  '0qFF00FFFF00010000_01')   # 1 * 256**65536
            i__q(256**65535,  '0qFF00FFFF0000FFFF_01')
            i__q(256**65282,  '0qFF00FFFF0000FF02_01')
            i__q(256**65281,  '0qFF00FFFF0000FF01_01')
            i__q(256**65280,  '0qFF00FFFF0000FF00_01')   #  __/ 8-byte qex, at 256**0xFF00 \ this preserves
            i__q(256**65279,  '0qFF00FEFF_01')           #    \ 4-byte qex, at 256**0xFEFF / monotonicity
            i__q(256**65278,  '0qFF00FEFE_01')
            i__q(256**65277,  '0qFF00FEFD_01')
            i__q(256**128,    '0qFF000080_01')
            i__q(  2**1024,   '0qFF000080_01')
            i__q(  2**1000,   '0qFF00007D_01')   # 1 * 256**125 == 2**1000
        i__q(   2**1000-1,'0qFE_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'
                               'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'
                               'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__q(   int('1071508607186267320948425049060001810561404811705533607443750388370351051124936122493198378815695'
                    '8581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141'
                    '8779541821530464749835819412673987675591655439460770629145711964776865421676604298316526243868372'
                    '05668069375'),
                          '0qFE_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__q(   2**1000-2,'0qFE_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFE')
        i__q(   2**999+1, '0qFE_8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__q(   2**999,   '0qFE_80')
        i__q(   2**999-1, '0qFE_7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__q(   2**998+1, '0qFE_4000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__q(   2**998,   '0qFE_40')
        i__q(   2**998-1, '0qFE_3FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__q(  10**300+1, '0qFE_17E43C8800759BA59C08E14C7CD7AAD86A4A458109F91C21C571DBE84D52D936F44ABE8A3D5B48C100959D9D0B6CC856B3ADC93B67AEA8F8E067D2C8D04BC177F7B4287A6E3FCDA36FA3B3342EAEB442E15D450952F4DD1000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__q(  10**300,   '0qFE_17E43C8800759BA59C08E14C7CD7AAD86A4A458109F91C21C571DBE84D52D936F44ABE8A3D5B48C100959D9D0B6CC856B3ADC93B67AEA8F8E067D2C8D04BC177F7B4287A6E3FCDA36FA3B3342EAEB442E15D450952F4DD10')   # Here googol cubed has 37 stripped 00-qigits, or 296 bits.
        i__q(  10**300-1, '0qFE_17E43C8800759BA59C08E14C7CD7AAD86A4A458109F91C21C571DBE84D52D936F44ABE8A3D5B48C100959D9D0B6CC856B3ADC93B67AEA8F8E067D2C8D04BC177F7B4287A6E3FCDA36FA3B3342EAEB442E15D450952F4DD0FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__q( 256**124,   '0qFE_01')
        i__q(   2**992,   '0qFE_01')
        i__q(41855804968213567224547853478906320725054875457247406540771499545716837934567817284890561672488119458109166910841919797858872862722356017328064756151166307827869405370407152286801072676024887272960758524035337792904616958075776435777990406039363527010043736240963055342423554029893064011082834640896,
                          '0qFE_01')
        i__q( 256**123,   '0qFD_01')
        i__q(   2**984,   '0qFD_01')
        i__q(   2**504,   '0qC1_01')
        i__q(   2**503,   '0qC0_80')
        i__q(   2**500,   '0qC0_10')
        i__q(   2**496,   '0qC0_01')
        i__q(  10**100+1, '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10000000000000000000000001')   # googol + 1  (integers can distinguish these)
        i__q(  10**100,   '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10')                           # googol
        i__q(  10**100-1, '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F0FFFFFFFFFFFFFFFFFFFFFFFFF')   # googol - 1
        i__q(1766847064778384329583297500742918515827483896875618958121606201292619777,'0qA0_01000000000000000000000000000000000000000000000000000000000001')
        i__q(1766847064778384329583297500742918515827483896875618958121606201292619776,'0qA0_01')
        i__q(5192296858534827628530496329220096,'0q90_01')
        i__q(20282409603651670423947251286016,'0q8F_01')
        i__q(10000000000000000000000001,'0q8C_084595161401484A000001')
        i__q(10000000000000000000000000,'0q8C_084595161401484A')
        i__q(18446744073709551618,'0q8A_010000000000000002')
        i__q(18446744073709551617,'0q8A_010000000000000001')
        i__q(18446744073709551616,'0q8A_01')
        i__q(18446744073709551615,'0q89_FFFFFFFFFFFFFFFF')
        i__q(18446744073709551614,'0q89_FFFFFFFFFFFFFFFE')
        i__q(72057594037927936,'0q89_01')
        i__q(281474976710656,'0q88_01')
        i__q(1099511627776,'0q87_01')
        i__q(68719476736, '0q86_10')
        i__q(68719476735, '0q86_0FFFFFFFFF')
        i__q(10000000001, '0q86_02540BE401')
        i__q(10000000000, '0q86_02540BE4')
        i__q( 4294967299, '0q86_0100000003')
        i__q( 4294967298, '0q86_0100000002')
        i__q( 4294967297, '0q86_0100000001')
        i__q( 4294967296, '0q86_01')
        i__q( 4294967295, '0q85_FFFFFFFF')
        i__q( 2147483649, '0q85_80000001')
        i__q( 2147483648, '0q85_80')
        i__q( 2147483647, '0q85_7FFFFFFF')
        i__q(  268435457, '0q85_10000001')
        i__q(  268435456, '0q85_10')
        i__q(  268435455, '0q85_0FFFFFFF')
        i__q(   16777217, '0q85_01000001')
        i__q(   16777216, '0q85_01')
        i__q(   16777215, '0q84_FFFFFF')
        i__q(    1048577, '0q84_100001')
        i__q(    1048576, '0q84_10')
        i__q(    1048575, '0q84_0FFFFF')
        i__q(      65538, '0q84_010002')
        i__q(      65537, '0q84_010001')
        i__q(      65536, '0q84_01')
        i__q(      65535, '0q83_FFFF')
        i__q(       4097, '0q83_1001')
        i__q(       4096, '0q83_10')
        i__q(       4095, '0q83_0FFF')
        i__q(       1729, '0q83_06C1')
        i__q(        257, '0q83_0101')
        i__q(        256, '0q83_01')
        i__q(        255, '0q82_FF')
        i__q(          3, '0q82_03')
        i__q(          2, '0q82_02')
        i__q(          1, '0q82_01')
        i__q(          0, '0q80')
        i__q(         -1, '0q7D_FF')
        i__q(         -2, '0q7D_FE')
        i__q(         -3, '0q7D_FD')
        i__q(         -4, '0q7D_FC')
        i__q(         -8, '0q7D_F8')
        i__q(        -16, '0q7D_F0')
        i__q(        -32, '0q7D_E0')
        i__q(        -42, '0q7D_D6')
        i__q(        -64, '0q7D_C0')
        i__q(       -128, '0q7D_80')
        i__q(       -252, '0q7D_04')
        i__q(       -253, '0q7D_03')
        i__q(       -254, '0q7D_02')
        i__q(       -255, '0q7D_01')
        i__q(       -256, '0q7C_FF')
        i__q(       -257, '0q7C_FEFF')
        i__q(       -258, '0q7C_FEFE')
        i__q(       -259, '0q7C_FEFD')
        i__q(       -260, '0q7C_FEFC')
        i__q(       -511, '0q7C_FE01')
        i__q(       -512, '0q7C_FE')
        i__q(       -513, '0q7C_FDFF')
        i__q(      -1023, '0q7C_FC01')
        i__q(      -1024, '0q7C_FC')
        i__q(      -1025, '0q7C_FBFF')
        i__q(     -65534, '0q7C_0002')
        i__q(     -65535, '0q7C_0001')
        i__q(     -65536, '0q7B_FF')
        i__q(     -65537, '0q7B_FEFFFF')
        i__q(     -65538, '0q7B_FEFFFE')
        i__q(  -16777214, '0q7B_000002')
        i__q(  -16777215, '0q7B_000001')
        i__q(  -16777216, '0q7A_FF')
        i__q(  -16777217, '0q7A_FEFFFFFF')
        i__q(  -16777218, '0q7A_FEFFFFFE')
        i__q(-2147483647, '0q7A_80000001')
        i__q(-2147483648, '0q7A_80')
        i__q(-2147483649, '0q7A_7FFFFFFF')
        i__q(-4294967294, '0q7A_00000002')
        i__q(-4294967295, '0q7A_00000001')
        i__q(-4294967296, '0q79_FF')
        i__q(-4294967297, '0q79_FEFFFFFFFF')
        i__q(-4294967298, '0q79_FEFFFFFFFE')
        i__q(  -2**125,   '0q6E_E0')
        i__q(  -2**250,   '0q5E_FC')
        i__q(  -2**375,   '0q4F_80')
        i__q(  -204586912993508866875824356051724947013540127877691549342705710506008362275292159680204380770369009821930417757972504438076078534117837065833032974336,
                          '0q3F_FF')
        i__q(  -2**496,   '0q3F_FF')
        i__q(  -3273390607896141870013189696827599152216642046043064789483291368096133796404674554883270092325904157150886684127560071009217256545885393053328527589376,
                          '0q3F_F0')
        i__q(  -2**500,   '0q3F_F0')
        i__q(  -2**625,   '0q2F_FE')
        i__q(  -2**750,   '0q20_C0')
        i__q(  -2**875,   '0q10_F8')
        i__q(  -5357543035931336604742125245300009052807024058527668037218751941851755255624680612465991894078479290637973364587765734125935726428461570217992288787349287401967283887412115492710537302531185570938977091076523237491790970633699383779582771973038531457285598238843271083830214915826312193418602834034687,
                          '0q01_8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__q(  -2**999+1, '0q01_8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__q(  -5357543035931336604742125245300009052807024058527668037218751941851755255624680612465991894078479290637973364587765734125935726428461570217992288787349287401967283887412115492710537302531185570938977091076523237491790970633699383779582771973038531457285598238843271083830214915826312193418602834034688,
                          '0q01_80')
        i__q(  -2**999,   '0q01_80')
        i__q(int('-1071508607186267320948425049060001810561404811705533607443750388370351051124936122493198378815695858'
                 '12759467291755314682518714528569231404359845775746985748039345677748242309854210746050623711418779541'
                 '82153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375'
                 ),       '0q01_000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
                          '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
                          '00000000000000000000000000000000000000000000000000000000000000000000001')
        i__q(  -2**1000+1,'0q01_000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
                          '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
                          '00000000000000000000000000000000000000000000000000000000000000000000001')

    def test_int_ludicrous_large(self):
        """
        Test the max reasonable positive integer, 2**1000 - 1.

        And the min ludicrous positive integer, 2**1000.

        Where is the radix point in a ludicrous qan?
            If way left,  then 0qFF000001_01 ==   1 and smallest_ludicrous == 0qFF00007E_01
            If way right, then 0qFF000001_01 == 256 and smallest_ludicrous == 0qFF00007D_01
        (The fictional 0qFF000001_01 and 0qFF000000_01 are nonstandard and would break monotonicity,
        but they are still illustrative.)
            If way left,  then 0x82_01 == 0qFF000001_01 and 0x81 is the "offset" for reasonable qex
            If way right, then 0x82_01 == 0qFF000000_01 and 0x82 is the "offset" for reasonable qex

        Decision:  It's way right.   0qFF000000_01 would be 1.  A qan of 888888 is conceptually 88.8888
        """
        smallest_ludicrous = 2 ** 1000
        biggest_reasonable = 2 ** 1000 - 1
        assert smallest_ludicrous == 10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069376
        assert biggest_reasonable == 10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375
        self.assertEqual(
            '0qFE_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'
            'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'
            'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF',
            Number(biggest_reasonable).qstring()
        )
        if LUDICROUS_NUMBER_SUPPORT:
            self.assertEqual('0qFF00007D_01', Number(smallest_ludicrous).qstring())
        else:
            with self.assertRaises(NotImplementedError):
                Number(smallest_ludicrous)

    def test_int_ludicrous_large_negative(self):
        smallest_ludicrous = -2 ** 1000
        biggest_reasonable = -2 ** 1000 + 1
        assert smallest_ludicrous == -10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069376
        assert biggest_reasonable == -10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375
        self.assertEqual(
            '0q01_000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
            '00000000000000000000000000000000000000000000000000000000000000000000001',
            Number(biggest_reasonable).qstring()
        )
        if not LUDICROUS_NUMBER_SUPPORT:
            with self.assertRaises(NotImplementedError):
                Number(smallest_ludicrous)

    def test_integer_nan(self):
        nan = Number(float('nan'))
        with self.assertRaises(ValueError):
            int(nan)
        with self.assertRaises(ValueError):
            int(float('nan'))

    def test_integer_infinity(self):
        positive_infinity = Number(float('+inf'))
        with self.assertRaises(OverflowError):
            int(positive_infinity)
        with self.assertRaises(OverflowError):
            int(float('+inf'))

    def test_integer_infinity_negative(self):
        negative_infinity = Number(float('-inf'))
        with self.assertRaises(OverflowError):
            int(negative_infinity)
        with self.assertRaises(OverflowError):
            int(float('-inf'))

    def test_integer_infinitesimal(self):
        self.assertEqual(0, int(Number('0q807F')))
        self.assertEqual(0, int(Number('0q80')))
        self.assertEqual(0, int(Number('0q7F81')))
        self.assertEqual('0q80', Number(0).qstring())

    def test_zone_sets(self):
        self.assertEqualSets(ZoneSet.ALL, ZoneSet._ALL_BY_SOME_KIND_OF_BASIC_WAY)
        self.assertEqualSets(ZoneSet.ALL, ZoneSet._ALL_BY_REASONABLENESS)
        self.assertEqualSets(ZoneSet.ALL, ZoneSet._ALL_BY_FINITENESS)
        self.assertEqualSets(ZoneSet.ALL, ZoneSet._ALL_BY_ZERONESS)
        self.assertEqualSets(ZoneSet.ALL, ZoneSet._ALL_BY_BIGNESS)
        self.assertEqualSets(ZoneSet.ALL, ZoneSet._ALL_BY_WHOLENESS)
        self.assertEqualSets(ZoneSet.ALL, set(Zone.descending_codes))
        # TODO:  Test Number._descending_zone_codes too.

    def test_zone(self):
        """Test an example number in each zone."""
        self.assertEqual(Zone.TRANSFINITE,         Number('0qFF_81').zone)
        self.assertEqual(Zone.LUDICROUS_LARGE,     Number('0qFF00FFFF_5F5E00FF').zone)
        self.assertEqual(Zone.POSITIVE,            Number('0q82_2A').zone)
        self.assertEqual(Zone.POSITIVE,            Number('0q82_01').zone)
        self.assertEqual(Zone.POSITIVE,            Number('0q82').zone)
        self.assertEqual(Zone.FRACTIONAL,          Number('0q81FF_80').zone)
        self.assertEqual(Zone.LUDICROUS_SMALL,     Number('0q80FF0000_FA0A1F01').zone)
        self.assertEqual(Zone.INFINITESIMAL,       Number('0q807F').zone)
        self.assertEqual(Zone.ZERO,                Number('0q80').zone)
        self.assertEqual(Zone.INFINITESIMAL_NEG,   Number('0q7F81').zone)
        self.assertEqual(Zone.LUDICROUS_SMALL_NEG, Number('0q7F00FFFF_5F5E00FF').zone)
        self.assertEqual(Zone.FRACTIONAL_NEG,      Number('0q7E00_80').zone)
        self.assertEqual(Zone.NEGATIVE,            Number('0q7E').zone)
        self.assertEqual(Zone.NEGATIVE,            Number('0q7D_FF').zone)
        self.assertEqual(Zone.NEGATIVE,            Number('0q7D_D6').zone)
        self.assertEqual(Zone.LUDICROUS_LARGE_NEG, Number('0q00FF0000_FA0A1F01').zone)
        self.assertEqual(Zone.TRANSFINITE_NEG,     Number('0q00_7F').zone)
        self.assertEqual(Zone.NAN,                 Number('0q').zone)

    def test_float_qigits(self):
        self.assertEqual('0q82_01', Number(1.1, qigits=1).qstring())
        self.assertEqual('0q82_011A', Number(1.1, qigits=2).qstring())
        self.assertEqual('0q82_01199A', Number(1.1, qigits=3).qstring())
        self.assertEqual('0q82_0119999A', Number(1.1, qigits=4).qstring())
        self.assertEqual('0q82_011999999A', Number(1.1, qigits=5).qstring())
        self.assertEqual('0q82_01199999999A', Number(1.1, qigits=6).qstring())
        self.assertEqual('0q82_0119999999999A', Number(1.1, qigits=7).qstring())
        self.assertEqual('0q82_01199999999999A0', Number(1.1, qigits=8).qstring())   # so float has about
        self.assertEqual('0q82_01199999999999A0', Number(1.1, qigits=9).qstring())   # 7 significant qigits
        self.assertEqual('0q82_01199999999999A0', Number(1.1, qigits=15).qstring())

    def test_float_qigits_default(self):
        self.assertEqual('0q82_01199999999999A0', Number(1.1).qstring())
        self.assertEqual('0q82_01199999999999A0', Number(1.1, qigits=None).qstring())
        self.assertEqual('0q82_01199999999999A0', Number(1.1, qigits=-1).qstring())
        self.assertEqual('0q82_01199999999999A0', Number(1.1, qigits=0).qstring())

    def test_float_qigits_default_not_sticky(self):
        self.assertEqual('0q82_01199999999999A0', Number(1.1).qstring())
        self.assertEqual('0q82_0119999A', Number(1.1, qigits=4).qstring())
        self.assertEqual('0q82_01199999999999A0', Number(1.1).qstring())

    def test_float_qigits_fractional(self):
        self.assertEqual('0q81FF_199999999A', Number(0.1, qigits=5).qstring())
        self.assertEqual('0q81FF_19999999999A', Number(0.1, qigits=6).qstring())
        self.assertEqual('0q81FF_1999999999999A', Number(0.1, qigits=7).qstring())
        self.assertEqual('0q81FF_1999999999999A', Number(0.1, qigits=8).qstring())
        self.assertEqual('0q81FF_1999999999999A', Number(0.1, qigits=9).qstring())

        self.assertEqual('0q81FF_3333333333', Number(0.2, qigits=5).qstring())
        self.assertEqual('0q81FF_333333333333', Number(0.2, qigits=6).qstring())
        self.assertEqual('0q81FF_33333333333334', Number(0.2, qigits=7).qstring())
        self.assertEqual('0q81FF_33333333333334', Number(0.2, qigits=8).qstring())
        self.assertEqual('0q81FF_33333333333334', Number(0.2, qigits=9).qstring())
        # Ending in 34 is not a bug.
        # The 7th qigit above gets rounded to 34, not in Number, but when float was originally decoded from 0.2.
        # That's because the IEEE-754 53-bit (double precision) float significand can only fit 7 of those bits there.
        # The 1st qigit uses 6 bits.  Middle 5 qigits use all 8 bits.  So 6+(5*8)+7 = 53.
        # So Number faithfully stored all 53 bits from the float.

    def test_float_qigits_fractional_neg(self):
        self.assertEqual('0q7E00_E666666666', Number(-0.1, qigits=5).qstring())
        self.assertEqual('0q7E00_E66666666666', Number(-0.1, qigits=6).qstring())
        self.assertEqual('0q7E00_E6666666666666', Number(-0.1, qigits=7).qstring())
        self.assertEqual('0q7E00_E6666666666666', Number(-0.1, qigits=8).qstring())
        self.assertEqual('0q7E00_E6666666666666', Number(-0.1, qigits=9).qstring())

        self.assertEqual('0q7E00_CCCCCCCCCD', Number(-0.2, qigits=5).qstring())
        self.assertEqual('0q7E00_CCCCCCCCCCCD', Number(-0.2, qigits=6).qstring())
        self.assertEqual('0q7E00_CCCCCCCCCCCCCC', Number(-0.2, qigits=7).qstring())
        self.assertEqual('0q7E00_CCCCCCCCCCCCCC', Number(-0.2, qigits=8).qstring())
        self.assertEqual('0q7E00_CCCCCCCCCCCCCC', Number(-0.2, qigits=9).qstring())

    def test_float_qigits_neg(self):
        self.assertEqual('0q7D_FEE6666666', Number(-1.1, qigits=5).qstring())
        self.assertEqual('0q7D_FEE666666666', Number(-1.1, qigits=6).qstring())
        self.assertEqual('0q7D_FEE66666666666', Number(-1.1, qigits=7).qstring())
        self.assertEqual('0q7D_FEE6666666666660', Number(-1.1, qigits=8).qstring())   # float's 53-bit significand:
        self.assertEqual('0q7D_FEE6666666666660', Number(-1.1, qigits=9).qstring())   # 2+8+8+8+8+8+8+3 = 53

        self.assertEqual('0q7D_FECCCCCCCD', Number(-1.2, qigits=5).qstring())
        self.assertEqual('0q7D_FECCCCCCCCCD', Number(-1.2, qigits=6).qstring())
        self.assertEqual('0q7D_FECCCCCCCCCCCD', Number(-1.2, qigits=7).qstring())
        self.assertEqual('0q7D_FECCCCCCCCCCCCD0', Number(-1.2, qigits=8).qstring())
        self.assertEqual('0q7D_FECCCCCCCCCCCCD0', Number(-1.2, qigits=9).qstring())

    def test_float_qigits_negative_one_bug(self):
        self.assertEqual('0q7D_FF', Number(-1.0).qstring())
        self.assertEqual('0q7D_FF', Number(-1.0, qigits=9).qstring())
        self.assertEqual('0q7D_FF', Number(-1.0, qigits=8).qstring())
        self.assertEqual('0q7D_FF', Number(-1.0, qigits=7).qstring())   # not 0q7D_FF000000000001
        self.assertEqual('0q7D_FF', Number(-1.0, qigits=6).qstring())
        self.assertEqual('0q7D_FF', Number(-1.0, qigits=5).qstring())
        self.assertEqual('0q7D_FF', Number(-1.0, qigits=4).qstring())
        self.assertEqual('0q7D_FF', Number(-1.0, qigits=3).qstring())
        self.assertEqual('0q7D_FF', Number(-1.0, qigits=2).qstring())
        self.assertEqual('0q7D_FF', Number(-1.0, qigits=1).qstring())

    def test_floats_and_qstrings(self):

        def f__q(x, q, q_input_alternate=None):
            """
            Test the Number constructor on a float and a qstring, converting in both directions.

            Very Short Version:
                assert Number(x) == Number(q)

            Less Short version:
                assert q == Number(x).qstring()
                assert x == float(Number(q))

            Verify each float and qstring is monotonic -- the values must be tested
            in descending order.

            The optional alternate qstring should convert to the same float.
            It may represent a different value, too finely distinct for float to register.
            Or it may represent the same value in one of the Code Plateaus.

            Zones change, and only change, where zone_boundary() is called.
            """
            assert isinstance(x, float), \
                "f__q({},_) should be a float".format(type_name(x))
            assert isinstance(q, six.string_types), \
                "f__q(_,{}) should be a string".format(type_name(q))
            assert isinstance(q_input_alternate, six.string_types) or q_input_alternate is None, \
                "f__q(_,_,{}) should be a qstring".format(type_name(q_input_alternate))

            q_in = q if q_input_alternate is None else q_input_alternate

            # Compare x and Number(q)
            try:
                x_new = float(Number(q_in))
            except Exception as e:
                print("{exception_type} <--Number--- {q_string_input}".format(
                    exception_type=type_name(e),
                    q_string_input=q_in,
                ))
                # NOTE:  print THEN a stack trace
                raise
            match_x = floats_really_same(x_new, x)

            # Compare Number(x) and q
            try:
                q_new = Number(x).qstring()
            except Exception as e:
                print("{x_input:.17e} ---Number--> {exception_type}".format(
                    x_input=x,
                    exception_type=type_name(e),
                ))
                raise
            match_q = q_new == q

            if not match_x or not match_q:
                report = "\n"
                if not match_x:
                    q_shoulda = Number(x, qigits = 7).qstring()
                    report += "Number({}) ~~ ".format(q_shoulda)
                report += \
                    "{x_out_expected:.17e} {equality} {x_out_computed:.17e} " \
                    "<--- " \
                    "Number({q_in}).__float__()".format(
                        x_out_expected=x,
                        equality='==' if match_x else '!!!=',
                        x_out_computed=x_new,
                        q_in=q_in,
                    )
                report += \
                    "\nNumber._from_float({x_in:.17e}) " \
                    "---> " \
                    "{q_out_computed} {equality} {q_out_expected}".format(
                        x_in=x,
                        q_out_computed=q_new,
                        equality='==' if match_q else '!!!=',
                        q_out_expected=q,
                    )
                self.fail(report)

            if not context.the_first:
                x_oos    =        x         >        context.x_in_last
                qin_oos  = Number(q_in).raw > Number(context.q_in_last ).raw
                qout_oos = Number(q   ).raw > Number(context.q_out_last).raw
                if x_oos:
                    self.fail("Float out of sequence: {x_later:.17e} should be less than {x_early:.17e}".format(
                        x_later=x, 
                        x_early=context.x_in_last,
                    ))
                if qin_oos:   
                    self.fail("Qiki Number input out of sequence: {q_later} should be less than {q_early}".format(
                        q_later=q_in, 
                        q_early=context.q_in_last,
                    ))
                if qout_oos:  
                    self.fail("Qiki Number output out of sequence: {q_later} should be less than {q_early}".format(
                        q_later=q, 
                        q_early=context.q_out_last,
                    ))

                this_zone = Number(q_in).zone
                last_zone =  Number(context.q_in_last).zone
                if not context.after_zone_boundary and this_zone != last_zone:
                    self.fail("{zone_early} is in a different zone than {zone_later} -- need zone_boundary()?".format(
                        zone_early=context.q_in_last,
                        zone_later=q_in,
                    ))
                if context.after_zone_boundary and this_zone == last_zone:
                    self.fail("{zone_early} is in the same zone as {zone_later} -- remove zone_boundary()?".format(
                        zone_early=context.q_in_last, 
                        zone_later=q_in,
                    ))

            context.x_in_last = x
            context.q_in_last = q_in
            context.q_out_last = q

            context.the_first = False
            context.after_zone_boundary = False

        # noinspection PyPep8Naming
        class context(object):
            """Variables that are local to test_floats_and_qstrings(), but global to f__q()."""
            the_first = True
            after_zone_boundary = False
            x_in_last = None
            q_in_last = None
            q_out_last = None

        def zone_boundary():
            context.after_zone_boundary = True

        def try_out_f__q_errors():
            """Uncomment each set of statements to test f__q() exceptions and error messages."""

            # f__q(object(), '0q80')

            # f__q(0.0, object())

            # f__q(0.0, '0q80', object())

            # f__q(0.0, 'nonsense')

            # f__q(sys.float_info.max, '0q')

            # f__q(1.0, '0q82____01')   # Both reports:  f == f <--- q and f ---> q !!!= q

            # f__q(0.0, '0q80')
            # f__q(1.0, '0q82_01')

            # f__q(1.0, '0q82_01', '0q82_0001')
            # f__q(1.0, '0q82_01')

            # NOTE:  Can't trigger "Qiki Number output out of sequence..." without a bug in Number.

            # f__q(2.0, '0q82_02')
            # f__q(0.0, '0q80')

            # f__q(0.0, '0q80')
            # zone_boundary()
            # f__q(0.0, '0q80')

        try_out_f__q_errors()

        f__q(float('+inf'),               '0qFF_81')
        zone_boundary()
        if LUDICROUS_NUMBER_SUPPORT:
            # noinspection PyUnresolvedReferences
            m__s(mpmath.power(2,1024),    '0qFF000080_01')   # A smidgen too big for floating point
            f__q(1.7976931348623157e+308, '0qFF00007F_FFFFFFFFFFFFF8')   # Largest IEEE-754 64-bit floating point number -- a little ways into Zone.LUDICROUS_LARGE
            f__q(math.pow(2,1000),        '0qFF00007D_01')   # TODO:  Smallest Ludicrously Large number:  +2 ** +1000.
        else:
            f__q(float('+inf'),           '0qFF_81', '0qFF00FFFF_5F5E00FF_01')   # 2**99999999, a ludicrously large positive number
            f__q(float('+inf'),           '0qFF_81', '0qFF000080_01')   # A smidgen too big for floating point
        zone_boundary()
        f__q(1.0715086071862672e+301,     '0qFE_FFFFFFFFFFFFF8')   # Largest reasonable number that floating point can represent, 2**1000 - 2**947
        f__q(5.3575430359313366e+300,     '0qFE_80')
        f__q(math.pow(2,999),             '0qFE_80')   # Largest reasonable integral power of 2:  +2 ** +999.
        f__q(math.pow(2,992),             '0qFE_01')
        f__q(math.pow(2,880),             '0qF0_01')
        f__q(2.04586912993508844e+149,    '0qBF_FFFFFFFFFFFFF8')
        f__q(       1e100+1.0,            '0qAB_1249AD2594C37D', '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10000000000000000000000001')   # googol+1 (though float can't distinguish)
        f__q(       1e100,                '0qAB_1249AD2594C37D', '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10')   # googol, or as close to it as float can get
        f__q(       1e25,                 '0q8C_0845951614014880')
        f__q(       1e10,                 '0q86_02540BE4')
        f__q(4294967296.0,                '0q86_01')
        f__q(4294967296.0,                '0q86_01', '0q86')   # 0q86 is an alias for +256**4, the official code being 0q86_01
        f__q(  16777216.0,                '0q85_01')
        f__q(     65536.0,                '0q84_01')
        f__q(     32768.0,                '0q83_80')
        f__q(     16384.0,                '0q83_40')
        f__q(      8192.0,                '0q83_20')
        f__q(      4096.0,                '0q83_10')
        f__q(      2048.0,                '0q83_08')
        f__q(      1234.567890123456789,  '0q83_04D291613F43F8')
        f__q(      1234.5678901234,       '0q83_04D291613F43B980')
        f__q(      1234.56789,            '0q83_04D291613D31B9C0')
        f__q(      1111.1111112,          '0q83_04571C71C89A3840')
        f__q(      1111.111111111111313,  '0q83_04571C71C71C72')    # XXX: use numpy.nextafter(1111.111111111111111, 1) or something -- http://stackoverflow.com/a/6163157/673991
        f__q(      1111.111111111111111,  '0q83_04571C71C71C71C0')  # float has just under 17 significant digits
        f__q(      1111.1111111,          '0q83_04571C71C6ECB9')
        f__q(      1024.0,                '0q83_04')
        f__q(      1000.0,                '0q83_03E8')
        f__q(       512.0,                '0q83_02')
        f__q(       258.0,                '0q83_0102')
        f__q(       257.0,                '0q83_0101')
        f__q(       256.0,                '0q83_01')
        f__q(       256.0,                '0q83_01', '0q83')   # alias for +256
        f__q(       256.0,                '0q83_01', '0q82_FFFFFFFFFFFFFC')
        f__q(       255.9999999999999801, '0q82_FFFFFFFFFFFFF8')     # 53 bits in the float mantissa
        f__q(       255.5,                '0q82_FF80')
        f__q(       255.0,                '0q82_FF')
        f__q(       254.0,                '0q82_FE')
        f__q(       216.0,                '0q82_D8')
        f__q(       128.0,                '0q82_80')
        f__q(       100.0,                '0q82_64')
        f__q(math.pi*2,                   '0q82_06487ED5110B46')
        f__q(math.pi,                     '0q82_03243F6A8885A3')   # 50-bit pi mantissa?  Next qigit:  '08'.
        f__q(         3.0,                '0q82_03')
        f__q(math.exp(1),                 '0q82_02B7E151628AED20')   # 53-bit mantissa for e.
        f__q(         2.5,                '0q82_0280')
        f__q(         2.4,                '0q82_0266666666666660')
        f__q(         2.3,                '0q82_024CCCCCCCCCCCC0')
        f__q(         2.2,                '0q82_0233333333333340')
        f__q(         2.1,                '0q82_02199999999999A0')
        f__q(         2.0,                '0q82_02')
        f__q(         1.875,              '0q82_01E0')
        f__q(         1.75,               '0q82_01C0')
        f__q(math.sqrt(3),                '0q82_01BB67AE8584CAA0')
        f__q(         1.6666666666666666, '0q82_01AAAAAAAAAAAAA0')
        f__q((1+math.sqrt(5))/2,          '0q82_019E3779B97F4A80')   # golden ratio
        f__q(         1.6,                '0q82_01999999999999A0')
        f__q(         1.5333333333333333, '0q82_0188888888888880')
        f__q(         1.5,                '0q82_0180')
        f__q(         1.4666666666666666, '0q82_0177777777777770')
        f__q(math.sqrt(2),                '0q82_016A09E667F3BCD0')
        f__q(         1.4,                '0q82_0166666666666660')
        f__q(         1.3333333333333333, '0q82_0155555555555550')
        f__q(         1.3,                '0q82_014CCCCCCCCCCCD0')
        f__q(         1.2666666666666666, '0q82_0144444444444440')
        f__q(         1.25,               '0q82_0140')
        f__q(         1.2,                '0q82_0133333333333330')
        f__q(         1.1333333333333333, '0q82_0122222222222220')
        f__q(         1.125,              '0q82_0120')
        f__q(         1.1,                '0q82_01199999999999A0')
        f__q(         1.0666666666666666, '0q82_0111111111111110')
        f__q(         1.0625,             '0q82_0110')
        f__q(math.pow(2, 1/12.0),         '0q82_010F38F92D979630')   # semitone (twelfth of an octave)
        f__q(         1.03125,            '0q82_0108')
        f__q(         1.015625,           '0q82_0104')
        f__q(         1.01,               '0q82_01028F5C28F5C290')
        f__q(         1.0078125,          '0q82_0102')
        f__q(         1.00390625,         '0q82_0101')
        f__q(         1.001953125,        '0q82_010080')
        f__q(         1.001,              '0q82_01004189374BC6A0')
        f__q(         1.0009765625,       '0q82_010040')
        f__q(         1.00048828125,      '0q82_010020')
        f__q(         1.000244140625,     '0q82_010010')
        f__q(         1.0001,             '0q82_0100068DB8BAC710')
        f__q(         1.00001,            '0q82_010000A7C5AC4720')
        f__q(         1.000001,           '0q82_01000010C6F7A0B0')
        f__q(         1.0000001,          '0q82_01000001AD7F29B0')
        f__q(         1.00000001,         '0q82_010000002AF31DC0')
        f__q(         1.000000001,        '0q82_01000000044B83')
        f__q(         1.0000000001,       '0q82_01000000006DF380')
        f__q(         1.00000000001,      '0q82_01000000000AFEC0')
        f__q(         1.000000000001,     '0q82_0100000000011980')
        f__q(         1.0000000000001,    '0q82_0100000000001C20')
        f__q(         1.00000000000001,   '0q82_01000000000002D0')
        f__q(         1.000000000000001,  '0q82_0100000000000050')
        f__q(         1.00000000000000067,'0q82_0100000000000030')
        f__q(         1.00000000000000067,'0q82_0100000000000030', '0q82_01000000000000280001')
        f__q(         1.00000000000000044,'0q82_0100000000000020', '0q82_0100000000000028')
        f__q(         1.00000000000000044,'0q82_0100000000000020')
        f__q(         1.00000000000000044,'0q82_0100000000000020', '0q82_0100000000000018')
        f__q(         1.00000000000000022,'0q82_0100000000000010', '0q82_0100000000000017FFFF')  # alternated rounding?
        f__q(         1.00000000000000022,'0q82_0100000000000010')
        f__q(         1.00000000000000022,'0q82_0100000000000010', '0q82_01000000000000080001')
        f__q(         1.0                ,'0q82_01',               '0q82_0100000000000008')   # so float granularity [1.0,2.0) is 2**-52 ~~ 22e-17
        f__q(         1.0,                '0q82_01')
        f__q(         1.0,                '0q82_01',  '0q82')   # alias for +1
        zone_boundary()
        f__q(         0.99999237060546875,'0q81FF_FFFF80')
        f__q(         0.9998779296875,    '0q81FF_FFF8')
        f__q(         0.999,              '0q81FF_FFBE76C8B43958')     # 999/1000
        f__q(         0.998046875,        '0q81FF_FF80')
        f__q(         0.998,              '0q81FF_FF7CED916872B0')     # 998/1000
        f__q(         0.9972222222222222, '0q81FF_FF49F49F49F4A0')     # 359/360
        f__q(         0.9944444444444445, '0q81FF_FE93E93E93E940')     # 358/360
        f__q(         0.99,               '0q81FF_FD70A3D70A3D70')     # 99/100
        f__q(         0.98,               '0q81FF_FAE147AE147AE0')     # 98/100
        f__q(         0.96875,            '0q81FF_F8')
        f__q(         0.9375,             '0q81FF_F0')
        f__q(         0.875,              '0q81FF_E0')
        f__q(         0.75,               '0q81FF_C0')
        f__q(math.sqrt(0.5),              '0q81FF_B504F333F9DE68')
        f__q(         0.5,                '0q81FF_80')
        f__q(         0.25,               '0q81FF_40')
        f__q(         0.125,              '0q81FF_20')
        f__q(         0.0625,             '0q81FF_10')
        f__q(         0.03125,            '0q81FF_08')
        f__q(         0.02,               '0q81FF_051EB851EB851EC0')   # 2/200
        f__q(         0.015625,           '0q81FF_04')
        f__q(         0.01171875,         '0q81FF_03')
        f__q(         0.01,               '0q81FF_028F5C28F5C28F60')   # 1/100
        f__q(         0.0078125,          '0q81FF_02')
        f__q(         0.005555555555555556,'0q81FF_016C16C16C16C170')  # 2/360
        f__q(         0.0039520263671875, '0q81FF_0103')               # 259/65536
        f__q(         0.003936767578125,  '0q81FF_0102')               # 258/65536
        f__q(         0.0039215087890625, '0q81FF_0101')               # 257/65536
        f__q(         0.00390625,         '0q81FF_01')                 # 256/65536 aka 1/256
        f__q(         0.00390625,         '0q81FF_01', '0q81FF')       # 1/256 alias
        f__q(         0.0038909912109375, '0q81FE_FF')                 # 255/65536
        f__q(         0.003875732421875,  '0q81FE_FE')                 # 254/65536
        f__q(         0.0038604736328125, '0q81FE_FD')                 # 253/65536
        f__q(         0.002777777777777778,'0q81FE_B60B60B60B60B8')    # 1/360
        f__q(         0.002,              '0q81FE_83126E978D4FE0')     # 2/1000
        f__q(         0.001953125,        '0q81FE_80')
        f__q(         0.001,              '0q81FE_4189374BC6A7F0')     # 1/1000 = 0x0.004189374BC6A7EF9DB22D0E560 4189374BC6A7EF9DB22D0E560 ...
        f__q(         0.0009765625,       '0q81FE_40')
        f__q(         0.00048828125,      '0q81FE_20')
        f__q(         0.000244140625,     '0q81FE_10')
        f__q(         0.0001220703125,    '0q81FE_08')
        f__q(         0.00006103515625,   '0q81FE_04')
        f__q(         0.000030517578125,  '0q81FE_02')
        f__q(math.pow(256, -2),           '0q81FE_01')
        f__q(         0.0000152587890625, '0q81FE_01')                 # 1/65536
        f__q(         0.0000152587890625, '0q81FE_01', '0q81FE')       # 1/65536 alias
        f__q(         0.00000762939453125,'0q81FD_80')
        f__q(math.pow(256, -3),           '0q81FD_01')
        f__q(math.pow(256, -4),           '0q81FC_01')
        f__q(math.pow(256, -10),          '0q81F6_01')
        f__q(math.pow(256, -100),         '0q819C_01')
        f__q(math.pow(256, -100),         '0q819C_01', '0q819C')   # alias for 256**-100
        f__q(math.pow(  2, -991),         '0q8184_02')
        f__q(math.pow(  2, -992),         '0q8184_01')
        f__q(math.pow(256, -124),         '0q8184_01')
        f__q(math.pow(  2, -993),         '0q8183_80')
        f__q(math.pow(  2, -994),         '0q8183_40')
        f__q(math.pow(  2, -998),         '0q8183_04')
        f__q(math.pow(  2, -999),         '0q8183_02')
        f__q(math.pow(  2, -1000) + math.pow(2,-1052),
                                          '0q8183_0100000000000010')   # boldest reasonable float, near positive ludicrously small boundary
        if LUDICROUS_NUMBER_SUPPORT:
            f__q(math.pow(  2, -1000),    'something')   # gentlest positive ludicrously small number
            f__q(math.pow(256, -125),     'something')
        else:
            f__q(math.pow(  2, -1000),    '0q8183_01')   # gentlest positive ludicrously small number
            f__q(math.pow(256, -125),     '0q8183_01')
        zone_boundary()
        f__q(         0.0,                '0q80',  '0q80FF0000_FF4143E0_01')   # +2**-99999999, a ludicrously small positive number
        zone_boundary()
        f__q(         0.0,                '0q80',  '0q807F')   # +infinitesimal
        zone_boundary()
        f__q(         0.0,                '0q80')
        zone_boundary()
        f__q(        -0.0,                '0q80',  '0q7F81')   # -infinitesimal
        zone_boundary()
        f__q(        -0.0,                '0q80',  '0q7F00FFFF_00BEBC1F_80')   # -2**-99999999, a ludicrously small negative number
        zone_boundary()
        if LUDICROUS_NUMBER_SUPPORT:
            f__q(-math.pow(256, -125),    'something')
            f__q(-math.pow(  2, -1000),   'something')   # gentlest negative ludicrously small number
        else:
            f__q(-math.pow(256, -125),    '0q7E7C_FF')
            f__q(-math.pow(  2, -1000),   '0q7E7C_FF')   # gentlest negative ludicrously small number
        f__q(-math.pow(  2, -1000) - math.pow(2,-1052),
                                          '0q7E7C_FEFFFFFFFFFFFFF0')   # boldest reasonable float, near negative ludicrously small boundary
        f__q(-math.pow(  2, -999),        '0q7E7C_FE')
        f__q(-math.pow(  2, -998),        '0q7E7C_FC')
        f__q(-math.pow(  2, -994),        '0q7E7C_C0')
        f__q(-math.pow(  2, -993),        '0q7E7C_80')
        f__q(-math.pow(256, -124),        '0q7E7B_FF')
        f__q(-math.pow(  2, -992),        '0q7E7B_FF')
        f__q(-math.pow(  2, -991),        '0q7E7B_FE')
        f__q(-math.pow(256, -100),        '0q7E63_FF', '0q7E64')   # alias for -256**-100
        f__q(-math.pow(256, -100),        '0q7E63_FF')
        f__q(-math.pow(256, -10),         '0q7E09_FF')
        f__q(-math.pow(256, -4),          '0q7E03_FF')
        f__q(-math.pow(256, -3),          '0q7E02_FF')
        f__q(        -0.00000762939453125,'0q7E02_80')
        f__q(        -0.0000152587890625, '0q7E01_FF', '0q7E02')   # alias for -256**-2
        f__q(-math.pow(256, -2),          '0q7E01_FF')
        f__q(        -0.0000152587890625, '0q7E01_FF')
        f__q(        -0.000030517578125,  '0q7E01_FE')
        f__q(        -0.00006103515625,   '0q7E01_FC')
        f__q(        -0.0001220703125,    '0q7E01_F8')
        f__q(        -0.000244140625,     '0q7E01_F0')
        f__q(        -0.00048828125,      '0q7E01_E0')
        f__q(        -0.0009765625,       '0q7E01_C0')
        f__q(        -0.001953125,        '0q7E01_80')
        f__q(        -0.001953125,        '0q7E01_80')
        f__q(        -0.0038604736328125, '0q7E01_03')             # -253/65536
        f__q(        -0.003875732421875,  '0q7E01_02')             # -254/65536
        f__q(        -0.0038909912109375, '0q7E01_01')             # -255/65536
        f__q(        -0.00390625,         '0q7E00_FF', '0q7E01')   # -256/65536  aka -1/256  aka -256**-1
        f__q(        -0.00390625,         '0q7E00_FF')             # -256/65536
        f__q(        -0.0039215087890625, '0q7E00_FEFF')           # -257/65536
        f__q(        -0.003936767578125,  '0q7E00_FEFE')           # -258/65536
        f__q(        -0.0039520263671875, '0q7E00_FEFD')           # -259/65536
        f__q(        -0.0078125,          '0q7E00_FE')
        f__q(        -0.01171875,         '0q7E00_FD')
        f__q(        -0.015625,           '0q7E00_FC')
        f__q(        -0.03125,            '0q7E00_F8')
        f__q(        -0.0625,             '0q7E00_F0')
        f__q(        -0.125,              '0q7E00_E0')
        f__q(        -0.25,               '0q7E00_C0')
        f__q(        -0.5,                '0q7E00_80')
        f__q(        -0.75,               '0q7E00_40')
        f__q(        -0.875,              '0q7E00_20')
        f__q(        -0.9375,             '0q7E00_10')
        f__q(        -0.96875,            '0q7E00_08')
        f__q(        -0.998046875,        '0q7E00_0080')
        f__q(        -0.9998779296875,    '0q7E00_0008')
        f__q(        -0.99999237060546875,'0q7E00_000080')
        zone_boundary()
        f__q(        -1.0,                '0q7D_FF', '0q7E')   # alias for -1
        f__q(        -1.0,                '0q7D_FF')
        f__q(        -1.000001,           '0q7D_FEFFFFEF39085F50')
        f__q(        -1.00000762939453125,'0q7D_FEFFFF80')
        f__q(        -1.0001220703125,    '0q7D_FEFFF8')
        f__q(        -1.000244140625,     '0q7D_FEFFF0')
        f__q(        -1.00048828125,      '0q7D_FEFFE0')
        f__q(        -1.0009765625,       '0q7D_FEFFC0')
        f__q(        -1.001953125,        '0q7D_FEFF80')
        f__q(        -1.00390625,         '0q7D_FEFF')
        f__q(        -1.0078125,          '0q7D_FEFE')
        f__q(        -1.015625,           '0q7D_FEFC')
        f__q(        -1.03125,            '0q7D_FEF8')
        f__q(        -1.0625,             '0q7D_FEF0')
        f__q(        -1.1,                '0q7D_FEE6666666666660')  # TODO:  Try more rational weirdos
        f__q(        -1.125,              '0q7D_FEE0')
        f__q(        -1.25,               '0q7D_FEC0')
        f__q(        -1.5,                '0q7D_FE80')
        f__q(        -1.75,               '0q7D_FE40')
        f__q(        -1.875,              '0q7D_FE20')
        f__q(        -1.9375,             '0q7D_FE10')
        f__q(        -1.96875,            '0q7D_FE08')
        f__q(        -1.998046875,        '0q7D_FE0080')
        f__q(        -1.9998779296875,    '0q7D_FE0008')
        f__q(        -1.99999237060546875,'0q7D_FE000080')
        f__q(        -2.0,                '0q7D_FE')
        f__q(        -2.00000762939453125,'0q7D_FDFFFF80')
        f__q(        -2.25,               '0q7D_FDC0')
        f__q(        -2.5,                '0q7D_FD80')
        f__q(        -2.75,               '0q7D_FD40')
        f__q(        -3.0,                '0q7D_FD')
        f__q(        -3.06249999999999645,'0q7D_FCF00000000001')
        f__q(        -3.0625,             '0q7D_FCF0')
        f__q(        -3.062500000000005,  '0q7D_FCEFFFFFFFFFFEA0')
        f__q(        -4.0,                '0q7D_FC')
        f__q(        -8.0,                '0q7D_F8')
        f__q(       -16.0,                '0q7D_F0')
        f__q(       -32.0,                '0q7D_E0')
        f__q(       -64.0,                '0q7D_C0')
        f__q(      -128.0,                '0q7D_80')
        f__q(      -255.0,                '0q7D_01')
        f__q(      -255.5,                '0q7D_0080')
        f__q(      -255.98046875,         '0q7D_0005')
        f__q(      -255.984375,           '0q7D_0004')
        f__q(      -255.98828125,         '0q7D_0003')
        f__q(      -255.9921875,          '0q7D_0002')
        f__q(      -255.99609375,         '0q7D_0001')
        f__q(      -255.999984741210938,  '0q7D_000001')
        f__q(      -255.999999940395355,  '0q7D_00000001')
        f__q(      -255.999999999767169,  '0q7D_0000000001')
        f__q(      -255.999999999999091,  '0q7D_000000000001')
        f__q(      -255.999999999999943,  '0q7D_00000000000010')
        f__q(      -255.999999999999972,  '0q7D_00000000000008')
        f__q(      -256.0,                '0q7C_FF', '0q7D')   # alias for -256
        f__q(      -256.0,                '0q7C_FF')
        f__q(      -256.00390625,         '0q7C_FEFFFF')
        f__q(      -256.0078125,          '0q7C_FEFFFE')
        f__q(      -256.01171875,         '0q7C_FEFFFD')
        f__q(      -256.015625,           '0q7C_FEFFFC')
        f__q(      -256.01953125,         '0q7C_FEFFFB')
        f__q(      -257.0,                '0q7C_FEFF')
        f__q(      -512.0,                '0q7C_FE')
        f__q(     -1024.0,                '0q7C_FC')
        f__q(     -2048.0,                '0q7C_F8')
        f__q(     -4096.0,                '0q7C_F0')
        f__q(     -8192.0,                '0q7C_E0')
        f__q(    -16384.0,                '0q7C_C0')
        f__q(    -32768.0,                '0q7C_80')
        f__q(    -65536.0,                '0q7B_FF', '0q7C')   # alias for -256**2
        f__q(    -65536.0,                '0q7B_FF')
        f__q(   -131072.0,                '0q7B_FE')
        f__q(-4294967296.0,               '0q79_FF')
        f__q(-2.04586912993508844e+149,   '0q40_00000000000008')
        f__q(-math.pow(2,992),            '0q01_FF', '0q02')   # alias for -256**124
        f__q(-math.pow(2,992),            '0q01_FF')
        f__q(-math.pow(2,996),            '0q01_F0')
        f__q(-math.pow(2,997),            '0q01_E0')
        f__q(-math.pow(2,998),            '0q01_C0')
        f__q(-math.pow(2,999),            '0q01_80')
        f__q(-1.0715086071862672e+301,    '0q01_00000000000008')   # Boldest (furthest from one) reasonable number that floating point can represent
        zone_boundary()
        # f__q(math.pow(2,1000),            '0q00FFFF83_01')   # TODO:  -2 ** +1000 == Gentlest (closest to one) negative Ludicrously Large integer.
        zone_boundary()
        f__q(float('-inf'),               '0q00_7F', '0q00FF0000_FA0A1F01_01')   # -2**99999999, a ludicrously large negative number
        zone_boundary()
        f__q(float('-inf'),               '0q00_7F')
        zone_boundary()
        f__q(float('nan'),                '0q')

    def test_float_ludicrous_large(self):
        gentlest_ludicrous = 2.0 ** 1000
        boldest_reasonable = 2.0 ** 1000 - 2.0 ** 947
        assert gentlest_ludicrous == 1.0715086071862673e+301
        assert boldest_reasonable == 1.0715086071862672e+301
        self.assertEqual('0qFE_FFFFFFFFFFFFF8', Number(boldest_reasonable).qstring())
        # NOTE:  significant is 53 1-bits.
        if not LUDICROUS_NUMBER_SUPPORT:
            with self.assertRaises(NotImplementedError):
                Number(gentlest_ludicrous)
            with self.assertRaises(NotImplementedError):
                Number(sys.float_info.max)   # boldest ludicrously large float
                # THANKS:  http://stackoverflow.com/a/3477332/673991

    def test_float_ludicrous_large_negative(self):
        gentlest_ludicrous = -2.0 ** 1000
        boldest_reasonable = -2.0 ** 1000 + 2.0 ** 947
        assert gentlest_ludicrous == -1.0715086071862673e+301
        assert boldest_reasonable == -1.0715086071862672e+301
        self.assertEqual('0q01_00000000000008', Number(boldest_reasonable).qstring())
        if not LUDICROUS_NUMBER_SUPPORT:
            with self.assertRaises(NotImplementedError):
                Number(gentlest_ludicrous)
            with self.assertRaises(NotImplementedError):
                Number(-sys.float_info.max)

    def test_float_ludicrous_small(self):
        """
        Test floats near the positive ludicrously small boundary (2**-1000).

        In the naming of all these ludicrous/reasonable boundary test cases
            gentlest_ludicrous means
                closest to 1.0
                at the limit of the ludicrous numbers
                closest to the reasonable numbers
                furthest from 0.0 or infinity
            boldest_reasonable means
                furthest from 1.0
                at the limit of the reasonable numbers
                closest to 0.0 or infinity
                closest to the ludicrous numbers
        """
        gentlest_ludicrous = 2.0 ** -1000
        boldest_reasonable = 2.0 ** -1000 + 2.0 ** -1052
        # NOTE:  Why -1052, not -1053?
        assert gentlest_ludicrous == 9.332636185032189e-302
        assert boldest_reasonable == 9.33263618503219e-302
        self.assertEqual('0q8183_0100000000000010', Number(boldest_reasonable).qstring())
        # NOTE:  Significand is 1 1-bit, 51 0-bits, 1 1-bit.
        if not LUDICROUS_NUMBER_SUPPORT:
            self.assertEqual('0q8183_01', Number(gentlest_ludicrous).qstring())
            # TODO:
            # with self.assertRaises(NotImplementedError):
            #     Number(gentlest_ludicrous)
            self.assertEqual('0q8180_04', Number(sys.float_info.min).qstring())   # boldest ludicrously small float
            # TODO:
            # with self.assertRaises(NotImplementedError):
            #     Number(sys.float_info.min)

    def test_float_ludicrous_small_negative(self):
        gentlest_ludicrous = -2.0 ** -1000
        boldest_reasonable = -2.0 ** -1000 - 2.0 ** -1052
        assert gentlest_ludicrous == -9.332636185032189e-302
        assert boldest_reasonable == -9.33263618503219e-302
        self.assertEqual('0q7E7C_FEFFFFFFFFFFFFF0', Number(boldest_reasonable).qstring())
        # TODO:  Enforce negative ludicrously small boundary -- or implement these ludicrous numbers:
        self.assertEqual('0q7E7C_FF', Number(gentlest_ludicrous).qstring())
        # with self.assertRaises(NotImplementedError):
        #     Number(gentlest_ludicrous)
        self.assertEqual('0q7E7F_FC', Number(-sys.float_info.min).qstring())
        # with self.assertRaises(NotImplementedError):
        #     Number(-sys.float_info.min)

    def test_copy_constructor(self):
        self.assertEqual('0q83_03E8', Number(Number('0q83_03E8')).qstring())
        self.assertEqual('0q7C_FEFF', Number(Number('0q7C_FEFF')).qstring())

    def test_copy_constructor_ancestored(self):
        """Propagate up the type hierarchy."""

        class SonOfNumber(Number):
            pass

        self.assertEqual('0q83_03E8', Number(SonOfNumber('0q83_03E8')).qstring())
        self.assertEqual('0q7C_FEFF', Number(SonOfNumber('0q7C_FEFF')).qstring())

    def test_copy_constructor_inherited(self):
        """Propagate down the type hierarchy."""

        class SonOfNumber(Number):
            pass

        self.assertEqual('0q83_03E8', SonOfNumber(Number('0q83_03E8')).qstring())
        self.assertEqual('0q7C_FEFF', SonOfNumber(Number('0q7C_FEFF')).qstring())

    def test_copy_constructor_related(self):
        """Propagate across the type hierarchy."""

        class SonOfNumber(Number):
            pass

        class DaughterOfNumber(Number):
            pass

        self.assertIsInstance(SonOfNumber(), Number)
        self.assertIsInstance(DaughterOfNumber(), Number)
        self.assertNotIsInstance(SonOfNumber(), DaughterOfNumber)
        self.assertNotIsInstance(DaughterOfNumber(), SonOfNumber)
        self.assertEqual('0q83_03E8', SonOfNumber(DaughterOfNumber('0q83_03E8')).qstring())
        self.assertEqual('0q7C_FEFF', DaughterOfNumber(SonOfNumber('0q7C_FEFF')).qstring())

        # noinspection PyClassHasNoInit
        class GrandSonOfNumber(SonOfNumber):
            pass

        # noinspection PyClassHasNoInit
        class GrandDaughterOfNumber(DaughterOfNumber):
            pass

        self.assertEqual('0q83_03E8', GrandSonOfNumber(GrandDaughterOfNumber('0q83_03E8')).qstring())
        self.assertEqual('0q7C_FEFF', GrandDaughterOfNumber(GrandSonOfNumber('0q7C_FEFF')).qstring())

    def test_copy_constructor_by_value(self):
        """Make sure copy constructor copies by value, not reference."""
        source = Number(1)
        destination = Number(source)
        self.assertEqual('0q82_01', source.qstring())
        self.assertEqual('0q82_01', destination.qstring())

        source.raw = Number(9).raw
        self.assertEqual('0q82_09', source.qstring())
        self.assertEqual('0q82_01', destination.qstring())

    def test_assignment_by_reference(self):
        """Make sure assignment copies by reference, not by value."""
        # TODO:  Make Number an immutable class, so assignment is by value?
        # SEE:  Immuutable objects, http://stackoverflow.com/q/4828080/673991
        source = Number(1)
        destination = source
        source.raw = Number(9).raw
        self.assertEqual('0q82_09', destination.qstring())

    def test_sizeof(self):
        """Illicit snooping into how big these things are."""
        expected_sizes = (
            28,   # Windows 7, 64-bit desktop, Python 2.7.9-12
            32,   # Windows 7, 64-bit desktop, Python 3.5.1-2
            40,   # Windows 7, 64-bit desktop, Python 2.7.12 after hardcoding __slots__ to _raw, _zone
            56,   # Windows 7, 64-bit laptop, Python 2.7.12, 3.5.2
            64,   # macOS 10, 64-bit macbook, Python 2.7.10
            72,   # Windows 7, 64-bit desktop, Python 3.6 after hardcoding __slots__ to _raw, _zone
        )  # depends on Number.__slots__ containing _zone or not
        self.assertIn(sys.getsizeof(Number('0q')), expected_sizes)
        self.assertIn(sys.getsizeof(Number('0q80')), expected_sizes)
        self.assertIn(sys.getsizeof(Number('0q83_03E8')), expected_sizes)
        self.assertIn(sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8')), expected_sizes)
        self.assertIn(sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8'
                                                  'E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8'
                                                  'E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8'
                                                  'E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8'
                                                  'E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8'
                                                  'E8E8E8E8E8E8E8E8E8E8E8')), expected_sizes)

        # Testing getsizeof() on raw was a dumb idea.  Anyway it broke over some distinction between laptop and desktop.
        # self.assertEqual(py2312( 21, 17, 33), sys.getsizeof(Number('0q').raw))
        # self.assertEqual(py2312( 22, 18, 34), sys.getsizeof(Number('0q80').raw))
        # self.assertEqual(py2312( 23, 19, 35), sys.getsizeof(Number('0q82_01').raw))
        # self.assertEqual(py2312( 24, 20, 36), sys.getsizeof(Number('0q83_03E8').raw))
        # self.assertEqual(py2312( 25, 21, 37), sys.getsizeof(Number('0q82_018888').raw))
        # self.assertEqual(py2312( 45, 41, 57), sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8').raw))
        # self.assertEqual(py2312(144,140,156), sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8').raw))
        #
        # self.assertEqual(py2312(21, 17, 33), sys.getsizeof(b''))
        # self.assertEqual(py2312(22, 18, 34), sys.getsizeof(b'\x80'))
        # self.assertEqual(py2312(24, 20, 36), sys.getsizeof(b'\x83\x03\xE8'))
        # self.assertEqual(py2312(45, 41, 57), sys.getsizeof(b'\x83\x03\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8'))

    def test_uneven_hex(self):
        self.assertEqual(
            Number('0q82_028'),
            Number('0q82_0280')
        )
        self.assertEqual('0q80', Number('0q8').qstring())
        self.assertEqual('0q80', Number('0q8_').qstring())
        self.assertEqual('0q80', Number('0q_8').qstring())

    def test_bad_string_hex(self):
        Number('0q')
        Number('0q80')
        Number('0q82_FF')
        with self.assertRaises(Number.ConstructorValueError):
            Number('0q8X')
        with self.assertRaises(Number.ConstructorValueError):
            Number('0q82_FG')

    def test_bad_string_prefix(self):
        Number('0q')
        Number('0q80')
        with self.assertRaises(Number.ConstructorValueError):
            Number('')
        with self.assertRaises(Number.ConstructorValueError):
            Number('00q80')
        with self.assertRaises(Number.ConstructorValueError):
            Number('q80')

    def test_string_int(self):
        self.assertEqual(1, Number("1"))
        self.assertEqual(0, Number("0"))
        self.assertEqual(-1, Number("-1"))
        self.assertEqual( 11111111111111111,     Number("11111111111111111"))
        self.assertEqual( 11111111111111112,  int(float("11111111111111111")))
        self.assertEqual(111111111111111111,    Number("111111111111111111"))
        self.assertEqual(111111111111111104, int(float("111111111111111111")))
        self.assertEqual(11111111111111111111111111111111111111,    Number("11111111111111111111111111111111111111"))
        self.assertEqual(11111111111111110860978869272892669952, int(float("11111111111111111111111111111111111111")))

    def test_string_numeric_Eric_Leschinski(self):
        """
        Testing the example number formats (for Python float()) as described by Eric Leschinski.

        SPECIAL THANKS:  http://stackoverflow.com/a/20929983/673991
        """
        with self.assertRaises(Number.ConstructorValueError):
            Number("")
        self.assertEqual(127, Number("127"))
        self.assertEqual(1, Number(True))
        # with self.assertRaises(Number.ConstructorTypeError):
        #     Number(True)   # Even though float(True) == 1.0?
        with self.assertRaises(Number.ConstructorValueError):
            Number("True")
        self.assertEqual(0, Number(False))
        # with self.assertRaises(Number.ConstructorTypeError):
        #     Number(False)
        self.assertEqual(123.456, Number("123.456"))
        self.assertEqual(-127, Number("      -127    "))
        self.assertEqual(12, Number("\t\n12\r\n"))
        self.assertEqual(Number.NAN, Number("NaN"))
        with self.assertRaises(Number.ConstructorValueError):
            Number("NaNanananaBATMAN")
        self.assertEqual(Number.NEGATIVE_INFINITY, Number("-iNF"))
        self.assertEqual(123.0e4, Number("123.E4"))
        self.assertEqual(0.1, Number(".1"))
        with self.assertRaises(Number.ConstructorValueError):
            Number("1,234")
        self.assertEqual(0, Number(u'\x30'))
        with self.assertRaises(Number.ConstructorValueError):
            Number("NULL")
        self.assertEqual(0x3fade, Number(0x3fade))
        self.assertEqual(Number.POSITIVE_INFINITY, Number("6e7777777777777"))   # TODO:  Ludicrous Number
        self.assertEqual(1.797693e+300, Number("1.797693e+300"))   # TODO:  MAX_FLOAT support (e+308)
        self.assertEqual(Number.POSITIVE_INFINITY, Number("inf"))
        self.assertEqual(Number.POSITIVE_INFINITY, Number("infinity"))
        with self.assertRaises(Number.ConstructorValueError):
            Number("infinityandBEYOND")
        with self.assertRaises(Number.ConstructorValueError):
            Number("12.34.56")
        with self.assertRaises(Number.ConstructorValueError):
            Number(u'四')
        with self.assertRaises(Number.ConstructorValueError):
            Number("#56")
        with self.assertRaises(Number.ConstructorValueError):
            Number("56%")
        self.assertEqual(0e0, Number("0E0"))
        self.assertEqual(1, Number(0**0))
        self.assertEqual(-5e-5, Number("-5e-5"))
        self.assertEqual(+1e1, Number("+1e1"))
        with self.assertRaises(Number.ConstructorValueError):
            Number("+1e1^5")
        with self.assertRaises(Number.ConstructorValueError):
            Number("+1e1.3")
        with self.assertRaises(Number.ConstructorValueError):
            Number("-+1")
        with self.assertRaises(Number.ConstructorValueError):
            Number("(1)")

    def test_string_numeric_space_after_minus(self):
        if six.PY2:
            self.assertEqual(-42, Number("- 42"))
            # NOTE:  Python 2 int() is crazy permissive with space after minus.
        else:
            with self.assertRaises(Number.ConstructorValueError):
                Number("- 42")

        with self.assertRaises(Number.ConstructorValueError):
            Number("- 42.0")
            # NOTE:  float() sensibly rejects space after minus at any version.

    def test_string_numeric_more_errors(self):
        with self.assertRaises(Number.ConstructorValueError):
            Number("2+2")
        with self.assertRaises(Number.ConstructorValueError):
            Number("0-0")
        with self.assertRaises(Number.ConstructorValueError):
            Number("0 0")
        with self.assertRaises(Number.ConstructorValueError):
            Number("--0")
        with self.assertRaises(Number.ConstructorValueError):
            Number("       ")

    def test_string_numeric_more_formats(self):
        self.assertEqual(32, Number("0x20"))
        self.assertEqual(0, Number("-0"))
        self.assertEqual(10, Number("00010"))   # Not octal
        self.assertEqual(8, Number("0o10"))   # Octal
        self.assertEqual(10, Number("    00010"))
        self.assertEqual(10, Number("    00010"))
        self.assertEqual(42, Number(u"\u0020" + "42" + u"\u0020"))
        self.assertEqual(42, Number(u"\u00A0" + "42" + u"\u00A0"))
        self.assertEqual(42, Number(u"\u1680" + "42" + u"\u1680"))
        self.assertEqual(42, Number(u"\u2000" + "42" + u"\u2000"))   # All kinds of exotic space allowed.
        self.assertEqual(42, Number(u"\u2009" + "42" + u"\u2009"))
        self.assertEqual(42, Number(u"\u3000" + "42" + u"\u3000"))
        with self.assertRaises(Number.ConstructorValueError):
            Number(u"\u200B" + "42" + u"\u200B")   # Zero-width spaces not allowed

    def test_from_int(self):
        self.assertEqual('0q80', Number(0).qstring())
        self.assertEqual('0q82_01', Number(1).qstring())
        self.assertEqual('0q82_02', Number(2).qstring())
        self.assertEqual('0q82_03', Number(3).qstring())
        self.assertEqual('0q82_FF', Number(255).qstring())
        self.assertEqual('0q83_01', Number(256).qstring())
        self.assertEqual('0q83_0101', Number(257).qstring())
        self.assertEqual('0q8C_01', Number(256*256*256*256*256*256*256*256*256*256).qstring())
        self.assertEqual('0q8B_FFFFFFFFFFFFFFFFFFFF', Number(256*256*256*256*256*256*256*256*256*256-1).qstring())
        self.assertEqual('0q8C_0100000000000000000001', Number(256*256*256*256*256*256*256*256*256*256+1).qstring())

    def test_from_int_negative(self):
        self.assertEqual('0q80',    Number(-0).qstring())
        self.assertEqual('0q7D_FF', Number(-1).qstring())
        self.assertEqual('0q7D_FE', Number(-2).qstring())
        self.assertEqual('0q7D_FD', Number(-3).qstring())
        self.assertEqual('0q7D_FC', Number(-4).qstring())
        self.assertEqual('0q7D_01', Number(-255).qstring())
        self.assertEqual('0q7C_FF', Number(-256).qstring())
        self.assertEqual('0q7C_FEFF', Number(-257).qstring())

    def test_from_raw_docstring_example(self):
        with self.assertRaises((ValueError, Number.ConstructorTypeError)):
            Number(b'\x82\x01')   # Wrong, don't pass raw string to constructor.
        self.assertEqual(Number(1), Number.from_raw(b'\x82\x01'))   # Right, use from_raw() instead.

    def test_from_raw(self):
        self.assertEqual(b'',             Number.from_raw(b'').raw)
        self.assertEqual(b'\x80',         Number.from_raw(b'\x80').raw)
        self.assertEqual(b'\x83\x03\xE8', Number.from_raw(b'\x83\x03\xE8').raw)

    def test_from_raw_unicode(self):
        with self.assertRaises(Number.ConstructorValueError):
            Number.from_raw(u'\x80')

    def test_number_subclasses_number(self):
        self.assertTrue(issubclass(Number, numbers.Number))

    def test_number_is_a_number(self):
        n = Number(1)
        self.assertIsInstance(n, numbers.Number)

    def test_big_qan_float(self):
        """
        Make sure we can handle a long qan.  float() may lose some accuracy.

        This used to raise an OverflowError in Number._to_float() because the entire
        qan was converted to an integer, and then to a float.  A qan with more than
        about 128 qigits has an integer value greater than 2**1024 which exceeds
        sys.float_info.max.  The solution is to limit how much of the qan
        is converted for the purpose of making a float.

        The complete, humungous integer version of the qan is still used in
        Number._to_int_xxx().  A 254-qigit
        """
        qstring_for_pi = \
            '0q82_03243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89452821E638D01377BE5466CF34' \
            'E90C6CC0AC29B7C97C50DD3F84D5B5B54709179216D5D98979FB1BD1310BA698DFB5AC2FFD72DBD01ADFB7B8E1AFED6A2' \
            '67E96BA7C9045F12C7F9924A19947B3916CF70801F2E2858EFC16636920D871574E69A458FEA3F4933D7E0D95748F728E' \
            'B658718BCD5882154AEE7B54A41DC25A59B59C30D5392AF26013C5D1B023286085F0CA417918B8DB38EF8E79DCB0603A1' \
            '80E6C9E0E8BB01E8A3ED71577C1BD314B2778AF2FDA55605C60E65525F3AA55AB945748986263E8144055CA396A2AAB10' \
            'B6B4CC5C341141E8CEA15486AF7C'   # 254-qigit qan (2032 bits, or about 610 decimal digits)
        pi = Number(qstring_for_pi)
        math_pi = Number(math.pi)

        self.assertEqual(qstring_for_pi, pi.qstring())
        self.assertEqual('0q82_03243F6A8885A3', math_pi.qstring())

        pi_f = float(pi)
        math_pi_f = float(math_pi)

        self.assertNotEqual(pi,   math_pi  )
        self.assertEqual   (pi_f, math_pi_f)

    def test_big_qan_int(self):
        """
        Make sure we can handle a long qan integer with no loss of accuracy.

        The biggest qan for a reasonable integer is the 125-qigit 2**1000-1.
        (A 254-qigit qan integer would in the Ludicrous zone.)
        """
        qstring_for_max_reasonable = \
            '0qFE_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF' \
            'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF' \
            'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'   # 125-qigit qan
        max_reasonable = Number(qstring_for_max_reasonable)

        self.assertEqual(qstring_for_max_reasonable, max_reasonable.qstring())
        self.assertEqual(2**1000-1, int(max_reasonable))

        self.assertEqual('FF', (max_reasonable - Number(0)).qstring()[-2:])
        self.assertEqual('FE', (max_reasonable - Number(1)).qstring()[-2:])   # See the rightmost qigit work.
        self.assertEqual('FD', (max_reasonable - Number(2)).qstring()[-2:])
        self.assertEqual('FC', (max_reasonable - Number(3)).qstring()[-2:])


################## new INDIVIDUAL tests go above here ###########################












class NumberComparisonTests(NumberTests):

    def test_equality_operator(self):
        self.assertTrue (Number(0.0) == Number(0.0))
        self.assertFalse(Number(0.0) == Number(1.0))
        self.assertTrue (Number(1.0) == Number(1.0))
        self.assertFalse(Number(1.0) == Number(0.0))

    def test_inequality_operator(self):
        self.assertFalse(Number(0.0) != Number(0.0))
        self.assertTrue (Number(0.0) != Number(1.0))
        self.assertFalse(Number(1.0) != Number(1.0))
        self.assertTrue (Number(1.0) != Number(0.0))

    def test_rich_comparison_operators(self):
        self.assertFalse(Number(1.0) < Number(0.0))
        self.assertFalse(Number(0.0) < Number(0.0))
        self.assertTrue (Number(0.0) < Number(1.0))

        self.assertFalse(Number(1.0) <= Number(0.0))
        self.assertTrue (Number(0.0) <= Number(0.0))
        self.assertTrue (Number(0.0) <= Number(1.0))

        self.assertTrue (Number(1.0) > Number(0.0))
        self.assertFalse(Number(0.0) > Number(0.0))
        self.assertFalse(Number(0.0) > Number(1.0))

        self.assertTrue (Number(1.0) >= Number(0.0))
        self.assertTrue (Number(0.0) >= Number(0.0))
        self.assertFalse(Number(0.0) >= Number(1.0))

    def test_rich_comparison_number_op_float(self):
        self.assertFalse(Number(1.0) ==        0.0)
        self.assertTrue (Number(0.0) ==        0.0)
        self.assertFalse(Number(0.0) ==        1.0)

        self.assertTrue (Number(1.0) !=        0.0)
        self.assertFalse(Number(0.0) !=        0.0)
        self.assertTrue (Number(0.0) !=        1.0)

        self.assertFalse(Number(1.0) <         0.0)
        self.assertFalse(Number(0.0) <         0.0)
        self.assertTrue (Number(0.0) <         1.0)

        self.assertFalse(Number(1.0) <=        0.0)
        self.assertTrue (Number(0.0) <=        0.0)
        self.assertTrue (Number(0.0) <=        1.0)

        self.assertTrue (Number(1.0) >         0.0)
        self.assertFalse(Number(0.0) >         0.0)
        self.assertFalse(Number(0.0) >         1.0)

        self.assertTrue (Number(1.0) >=        0.0)
        self.assertTrue (Number(0.0) >=        0.0)
        self.assertFalse(Number(0.0) >=        1.0)

    # noinspection PyRedundantParentheses
    def test_rich_comparison_float_op_number(self):
        self.assertFalse(       1.0  == Number(0.0))
        self.assertTrue (       0.0  == Number(0.0))
        self.assertFalse(       0.0  == Number(1.0))

        self.assertTrue (       1.0  != Number(0.0))
        self.assertFalse(       0.0  != Number(0.0))
        self.assertTrue (       0.0  != Number(1.0))

        self.assertFalse(       1.0  <  Number(0.0))
        self.assertFalse(       0.0  <  Number(0.0))
        self.assertTrue (       0.0  <  Number(1.0))

        self.assertFalse(       1.0  <= Number(0.0))
        self.assertTrue (       0.0  <= Number(0.0))
        self.assertTrue (       0.0  <= Number(1.0))

        self.assertTrue (       1.0  >  Number(0.0))
        self.assertFalse(       0.0  >  Number(0.0))
        self.assertFalse(       0.0  >  Number(1.0))

        self.assertTrue (       1.0  >= Number(0.0))
        self.assertTrue (       0.0  >= Number(0.0))
        self.assertFalse(       0.0  >= Number(1.0))

    def test_unittest_equality(self):
        """
        Do qiki.Number and assertEqual() handle googol with finesse?

        See also test_02_big_int_unittest_equality().
        """
        googol        = Number(10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000)
        googol_plus_1 = Number(10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001)
        self.assertEqual   (googol       , googol)
        self.assertNotEqual(googol       , googol_plus_1)
        self.assertNotEqual(googol_plus_1, googol)
        self.assertEqual   (googol_plus_1, googol_plus_1)

    def test_op_equality(self):
        """
        Do qiki.Number and its own equality operator handle googol with finesse?

        See also test_02_big_int_op_equality().
        """
        googol        = Number(10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000)
        googol_plus_1 = Number(10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001)
        self.assertTrue (googol        == googol)
        self.assertFalse(googol        == googol_plus_1)
        self.assertFalse(googol_plus_1 == googol)
        self.assertTrue (googol_plus_1 == googol_plus_1)

    def test_googol_math(self):
        """Googol math okay?"""
        googol = Number(100**10)
        googol_plus_one = googol + 1
        self.assertNotEqual(googol, googol_plus_one)
        self.assertTrue(googol != googol_plus_one)

    # noinspection SpellCheckingInspection
    def test_googol_raw_string(self):
        """Googol is big huh!  How big is it?  How long is the qstring?"""
        googol = Number(10**100)
        googol_plus_one = googol + Number(1)
        googol_minus_one = googol - Number(1)
        self.assertEqual(31, len(googol.raw))             # So 1e100 needs 31 qigits
        self.assertEqual(43, len(googol_plus_one.raw))    # But 1e100+1 needs 43 qigits.
        self.assertEqual(43, len(googol_minus_one.raw))   # Because 1e100 has 12 stripped 00 qigits.
        self.assertEqual('0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10', googol.qstring())
        self.assertEqual('0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10000000000000000000000001', googol_plus_one.qstring())
        self.assertEqual('0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F0FFFFFFFFFFFFFFFFFFFFFFFFF', googol_minus_one.qstring())

    # noinspection SpellCheckingInspection
    def test_googol_cubed_raw_string(self):
        """Googol cubed is really big huh!!  How long is the qstring?"""
        g_cubed = Number(10**300)
        g_cubed_plus_one = g_cubed + Number(1)
        g_cubed_minus_one = g_cubed - Number(1)
        self.assertEqual(89, len(g_cubed.raw))              # So 1e300 needs 89 qigits
        self.assertEqual(126, len(g_cubed_plus_one.raw))    # But 1e300+1 needs 126 qigits.
        self.assertEqual(126, len(g_cubed_minus_one.raw))   # Because 1e300 has 37 stripped 00 qigits.
        self.assertEqual('0qFE_17E43C8800759BA59C08E14C7CD7AAD86A4A458109F91C21C571DBE84D52D936F44ABE8A3D5B48C100959D9D0B6CC856B3ADC93B67AEA8F8E067D2C8D04BC177F7B4287A6E3FCDA36FA3B3342EAEB442E15D450952F4DD10', g_cubed.qstring())
        self.assertEqual('0qFE_17E43C8800759BA59C08E14C7CD7AAD86A4A458109F91C21C571DBE84D52D936F44ABE8A3D5B48C100959D9D0B6CC856B3ADC93B67AEA8F8E067D2C8D04BC177F7B4287A6E3FCDA36FA3B3342EAEB442E15D450952F4DD1000000000000000000000000000000000000000000000000000000000000000000000000001', g_cubed_plus_one.qstring())
        self.assertEqual('0qFE_17E43C8800759BA59C08E14C7CD7AAD86A4A458109F91C21C571DBE84D52D936F44ABE8A3D5B48C100959D9D0B6CC856B3ADC93B67AEA8F8E067D2C8D04BC177F7B4287A6E3FCDA36FA3B3342EAEB442E15D450952F4DD0FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF', g_cubed_minus_one.qstring())

    def test_biggie_raw_string(self):
        """How long is the raw string for "biggie" the biggest reasonable integer?"""
        biggie_minus_one = Number(2**1000 - 1)
        self.assertEqual(126, len(biggie_minus_one.raw))   # So biggie needs 126 qigits

    def test_incomparable(self):
        class SomeType(object):
            pass

        with self.assertRaises(Number.CompareError):   _ =  Number(1) <  SomeType()
        with self.assertRaises(Number.CompareError):   _ =  Number(1) <= SomeType()
        self.assertFalse(                                   Number(1) == SomeType())
        self.assertTrue(                                    Number(1) != SomeType())
        with self.assertRaises(Number.CompareError):   _ =  Number(1) >  SomeType()
        with self.assertRaises(Number.CompareError):   _ =  Number(1) >= SomeType()
        with self.assertRaises(Number.CompareError):   _ = SomeType() <  Number(1)
        with self.assertRaises(Number.CompareError):   _ = SomeType() <= Number(1)
        self.assertFalse(                                  SomeType() == Number(1))
        self.assertTrue(                                   SomeType() != Number(1))
        with self.assertRaises(Number.CompareError):   _ = SomeType() >  Number(1)
        with self.assertRaises(Number.CompareError):   _ = SomeType() >= Number(1)

    def test_in_and_sorted(self):
        """
        The 'in' operator should work, even though comparisons of Number with
        an arbitrary type raises an exception.

        Inspired by this ominous statement in docs.python:

        "...objects of different types always compare unequal, and are ordered consistently but arbitrarily.
        This unusual definition of comparison was used to simplify the definition of operations
        ... like sorting and the in and not in operators."

        So sorted(numbers) should work but sorted(mixed) should raise an exception.

        SEE:  Number._op_ready().
        """

        number_tuple = (Number(33), Number(22), Number(11))
        self.assertIn(Number(22), number_tuple)
        self.assertNotIn(Number(99), number_tuple)

        sorted_tuple = sorted(number_tuple)
        self.assertIn(Number(22), sorted_tuple)
        self.assertNotIn(Number(99), sorted_tuple)
        self.assertEqual([Number(11), Number(22), Number(33)], sorted_tuple)

        class SomeType(object):
            pass
        some_instance = SomeType()
        another_instance = SomeType()
        mixed_tuple = (Number(11), Number(22), Number(33), some_instance)

        self.assertIn(Number(22), mixed_tuple)
        self.assertNotIn(Number(99), mixed_tuple)
        self.assertIn(some_instance, mixed_tuple)
        self.assertNotIn(another_instance, mixed_tuple)

        with self.assertRaises(Number.CompareError):
            sorted(mixed_tuple)


# noinspection SpellCheckingInspection
class NumberIsTests(NumberTests):

    def test_is_whole(self):
        self.assertFalse(Number(-2.5).is_whole())
        self.assertTrue (Number(-2  ).is_whole())
        self.assertTrue (Number(-1  ).is_whole())
        self.assertFalse(Number(-0.5).is_whole())
        self.assertTrue (Number( 0  ).is_whole())
        self.assertFalse(Number( 0.5).is_whole())
        self.assertTrue (Number( 1  ).is_whole())
        self.assertTrue (Number( 2  ).is_whole())
        self.assertFalse(Number( 2.5).is_whole())
        self.assertTrue (Number('0q8A_01').is_whole())
        self.assertTrue (Number('0q8A_01').is_whole())
        self.assertTrue (Number('0q8A_010000000000000001').is_whole())
        self.assertTrue (Number('0q8A_010000000000000001').is_whole())
        self.assertFalse(Number('0q8A_0100000000000000010001').is_whole())
        self.assertFalse(Number('0q8A_01000000000000000180').is_whole())
        self.assertTrue (Number('0q8A_010000000000000002').is_whole())

        self.assertEqual(Number('0q8A_01'), 2**64)
        self.assertEqual(Number('0q8A_01'),                 18446744073709551616)
        self.assertEqual(Number('0q8A_010000000000000001'), 18446744073709551617)

    def test_is_whole_indeterminate(self):
        with self.assertRaises(Number.WholeError):
            Number(float('+inf')).is_whole()
        with self.assertRaises(Number.WholeError):
            Number(float('-inf')).is_whole()
        with self.assertRaises(Number.WholeError):
            Number.POSITIVE_INFINITY.is_whole()
        with self.assertRaises(Number.WholeError):
            Number.NEGATIVE_INFINITY.is_whole()

    def test_comparable_whole_indeterminate(self):
        self.assertTrue(Number.POSITIVE_INFINITY > Number.NEGATIVE_INFINITY)
        self.assertTrue(Number.POSITIVE_INFINITY >= Number.NEGATIVE_INFINITY)
        self.assertTrue(Number.NEGATIVE_INFINITY < Number.POSITIVE_INFINITY)
        self.assertTrue(Number.NEGATIVE_INFINITY <= Number.POSITIVE_INFINITY)

    def test_binary_op_whole_indeterminate(self):
        self.assertEqual(Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY + Number.POSITIVE_INFINITY)
        self.assertEqual(Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY + Number.NEGATIVE_INFINITY)

        self.assertEqual(Number.POSITIVE_INFINITY, Number.POSITIVE_INFINITY * Number.POSITIVE_INFINITY)
        self.assertEqual(Number.NEGATIVE_INFINITY, Number.POSITIVE_INFINITY * Number.NEGATIVE_INFINITY)
        self.assertEqual(Number.NEGATIVE_INFINITY, Number.NEGATIVE_INFINITY * Number.POSITIVE_INFINITY)
        self.assertEqual(Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY * Number.NEGATIVE_INFINITY)

    def test_unary_op_whole_indeterminate(self):
        self.assertEqual(Number.POSITIVE_INFINITY, -Number.NEGATIVE_INFINITY)
        self.assertEqual(Number.NEGATIVE_INFINITY, -Number.POSITIVE_INFINITY)

    def test_is_integer(self):
        """
        Number.is_integer() alias for Number.is_whole()

        NOTE:  Python builtin is_integer() does not check type, it checks value.
        """
        self.assertFalse(Number(-2.5).is_integer())
        self.assertTrue (Number(-1  ).is_integer())
        self.assertTrue (Number( 0  ).is_integer())
        self.assertFalse(Number( 0.5).is_integer())
        self.assertTrue (Number('0q8A_0100000000000000010000').is_integer())
        self.assertFalse(Number('0q8A_0100000000000000010001').is_integer())

        self.assertTrue(4321.0.is_integer())

    def test_is_nan(self):
        self.assertFalse(Number(0).is_nan())
        self.assertFalse(Number(1).is_nan())
        self.assertFalse(Number(float('inf')).is_nan())
        self.assertTrue(Number(float('nan')).is_nan())
        # noinspection PyUnresolvedReferences
        self.assertTrue(Number.NAN.is_nan())

    def test_is_pos_zer_neg(self):
        self.assertPositive(Number(float('+inf')))
        self.assertPositive(Number(math.pow(10,100)))
        self.assertPositive(Number(1))
        self.assertPositive(Number(math.pow(10,-100)))
        self.assertZero(Number(0))
        self.assertNegative(Number(-math.pow(10,-100)))
        self.assertNegative(Number(-1))
        self.assertNegative(Number(-math.pow(10,100)))
        self.assertNegative(Number(float('-inf')))

    def test_is_pos_zer_neg_boundary(self):
        self.assertPositive(Number('0q81FF_01'))
        self.assertPositive(Number('0q81FF_0000'))   # Normalizes to 0q81FF_01
        self.assertPositive(Number('0q810000'))   # TODO:  Normalize to 0q807F?
        self.assertPositive(Number('0q80FF_0000'))   # TODO:  Normalize to 0q807F?
        self.assertPositive(Number('0q80DEADBEEF'))
        self.assertPositive(Number('0q807F'))
        self.assertPositive(Number('0q8001'))
        self.assertPositive(Number('0q80_0000'))
        self.assertZero(Number('0q80'))
        self.assertNegative(Number('0q7FFFFF'))
        self.assertNegative(Number('0q7F81'))
        self.assertNegative(Number('0q7F76543210'))
        self.assertNegative(Number('0q7F01_0000'))   # TODO:  Normalize to 0q7F81?
        self.assertNegative(Number('0q7FFFFF'))   # TODO:  Normalize to 0q7F81?
        self.assertNegative(Number('0q7E01_0000'))   # Normalizes to 7E00_FF
        self.assertNegative(Number('0q7E00_FF'))


    # noinspection PyUnusedLocal
    def someday_assertIses(self, number_able, is_zero = None, all_true = None, all_false = None):
        number = Number(number_able)
        if is_zero is not None:
            self.assertEqual(is_zero, number.is_zero())

    # noinspection PyUnresolvedReferences
    def someday_test_is(self):
        self.assertTrue(Number('0q80').iszero())
        self.assertFalse(Number('0q80').nonzero())
        self.assertIses('0q80', is_zero=True,  all_true=('zero',),     all_false=('infinite', 'negative', 'positive'))
        self.assertIses('0q82', is_zero=False, all_true=('positive',), all_false=('infinite', 'negative', 'zero'))
        self.assertIses('0q7E', is_zero=False, all_true=('negative',), all_false=('infinite', 'zero', 'positive'))
        self.assertAllAre('zero', ('0q80',))
        self.assertAllAreNot('zero', ('0q82','0q7E'))
        self.assertAllAre('positive', ('0q82',))
        self.assertAllAreNot('positive', ('0q80','0q7E'))
        self.assertISnon('0q82', ('nan', 'negative', 'zero', 'infinitesimal', 'POSITIVE', 'REASONABLE', 'ludicrous', 'FINITE', 'infinite' 'transfinite'))
        self.assertAREarent('0q80', ('non', 'neg', 'ZERO', 'pos', 'REAS', 'lud', 'FIN', 'inf', 'lud'))
        self.assertAREarent('0q7E', ('non', 'NEG', 'zero', 'pos', 'REAS', 'lud', 'FIN', 'inf', 'lud'))
        # other possibilities
        # isvalid() nonvalid() isnan() nonnan() isstrictlyvalid() isunderscoredright()
        # wouldfloat() wouldint() wouldlong() wouldDecimal()
        # almostzero() essentiallyzero() issmall() nearzero() approacheszero() (zero or infinitesimal OR MAYBE ludicrous_small)
        # reasonablyzero() (includes ludicrous_small)
        # essentiallyzero() (does NOT include ludicrous_small, only infinitesimal and zero)
        # islarge() (ludicrous_large or infinite)


# noinspection SpellCheckingInspection
class NumberMathTests(NumberTests):

    def unary_op(self, op, output, input_):
        self.assertEqual(output,              op(       input_ ))
        self.assertEqual(output, type(output)(op(       input_ )))
        self.assertEqual(output, type(output)(op(Number(input_))))
        self.assertEqual(Number(output),      op(Number(input_)))

    def binary_op(self, op, output, input_left, input_right):
        """
        Test case for a binary operator.

        Make sure the operation works, as well as its 'r' (right) alternate.
        Equality is tested primarily in the native type of the output
        so as not to rely so much on Number.__eq__().
        For a similar reason, if output is a Number, qstrings are compared.
        """
        self.assertEqual(output,              op(       input_left ,        input_right ))
        self.assertIs(type(output),      type(op(       input_left ,        input_right)))
        self.assertEqual(output, type(output)(op(       input_left ,        input_right )))
        self.assertEqual(output, type(output)(op(Number(input_left), Number(input_right))))
        self.assertEqual(output, type(output)(op(Number(input_left),        input_right )))
        self.assertEqual(output, type(output)(op(       input_left , Number(input_right))))
        self.assertEqual(Number(output),      op(Number(input_left), Number(input_right)))
        if isinstance(output, Number):
            self.assertEqual(output.qstring(), op(Number(input_left), Number(input_right)).qstring())

    def test_int_too_big_to_be_a_float(self):
        """
        Prove that 0q8A_010000000000000001 is too big to be a float, accurately.

        So we can prove Number math isn't simply float math.
        """
        self.assertEqual(     0x10000000000000001, 2**64 + 1)
        self.assertNotEqual(  0x10000000000000001,         int(float(0x10000000000000001)))
        self.assertEqual(     0x10000000000000000,         int(float(0x10000000000000001)))
        self.assertEqual('0q8A_010000000000000001',           Number(0x10000000000000001).qstring())
        self.assertEqual(Number('0q8A_01'), Number(float(Number('0q8A_010000000000000001'))))

    def test_pos(self):
        self.unary_op(operator.__pos__, 42, 42)
        self.unary_op(operator.__pos__, -42, -42)
        self.unary_op(operator.__pos__, 42.0625, 42.0625)
        self.unary_op(operator.__pos__, -42.0625, -42.0625)
        self.unary_op(operator.__pos__, Number('0q8A_010000000000000001'), Number('0q8A_010000000000000001'))
        self.unary_op(operator.__pos__, Number('0q75_FEFFFFFFFFFFFFFFFF'), Number('0q75_FEFFFFFFFFFFFFFFFF'))

    def test_neg(self):
        self.unary_op(operator.__neg__, -42, 42)
        self.unary_op(operator.__neg__, 42, -42)
        self.unary_op(operator.__neg__, -42.0625, 42.0625)
        self.unary_op(operator.__neg__, 42.0625, -42.0625)
        self.unary_op(operator.__neg__, Number('0q75_FEFFFFFFFFFFFFFFFF'), Number('0q8A_010000000000000001'))
        self.unary_op(operator.__neg__, Number('0q8A_010000000000000001'), Number('0q75_FEFFFFFFFFFFFFFFFF'))

    def test_abs(self):
        self.unary_op(operator.__abs__, 42, 42)
        self.unary_op(operator.__abs__, 42, -42)
        self.unary_op(operator.__abs__, 42.0625, 42.0625)
        self.unary_op(operator.__abs__, 42.0625, -42.0625)
        self.unary_op(operator.__abs__, Number('0q8A_010000000000000001'), Number('0q8A_010000000000000001'))
        self.unary_op(operator.__abs__, Number('0q8A_010000000000000001'), Number('0q75_FEFFFFFFFFFFFFFFFF'))

    def test_add(self):
        self.binary_op(operator.__add__, 4, 2, 2)
        self.binary_op(operator.__add__, 4.375, 2.125, 2.25)
        self.binary_op(operator.__add__, Number('0q8A_020000000000000002'),
                                         Number('0q8A_010000000000000001'),
                                         Number('0q8A_010000000000000001'))
        self.binary_op(operator.__add__, Number('0q8A_010000000000000002'),
                                         Number('0q8A_010000000000000001'),
                                         1)
        self.binary_op(operator.__add__, Number('0q8A_010000000000000003'),
                                         2,
                                         Number('0q8A_010000000000000001'))
        self.binary_op(operator.__add__, 88+11j, 80+10j, 8+1j)
        self.binary_op(operator.__add__, 88+11j, 88, 11j)
        self.binary_op(operator.__add__, 88+11j, 11j, 88)

    def test_sub(self):
        self.binary_op(operator.__sub__, 42, 8642, 8600)
        self.binary_op(operator.__sub__, -0.125, 2.125, 2.25)
        self.binary_op(operator.__sub__, Number('0q8A_010000000000000001'),
                                         Number('0q8A_020000000000000002'),
                                         Number('0q8A_010000000000000001'))
        self.binary_op(operator.__sub__, 8+1j, 88+11j, 80+10j)

    def test_mul(self):
        self.binary_op(operator.__mul__, 42, 6, 7)
        self.binary_op(operator.__mul__, 3.75, 2.5, 1.5)
        self.binary_op(operator.__mul__, Number('0q92_0100000000000000020000000000000001'),
                                         Number('0q8A_010000000000000001'),
                                         Number('0q8A_010000000000000001'))
        self.binary_op(operator.__mul__, -5+10j, 1+2j, 3+4j)
        self.binary_op(operator.__mul__, 3+6j, 1+2j, 3)
        self.binary_op(operator.__mul__, 6+8j, 2, 3+4j)

    def test_truediv(self):
        """Single-slash true division outputs floating point."""
        self.binary_op(operator.__truediv__, 7.0, 42.0, 6.0)
        self.binary_op(operator.__truediv__, 1.5, 3.75, 2.5)
        self.binary_op(operator.__truediv__, 1+2j, -5+10j, 3+4j)
        self.assertEqual('0q82_07',              (Number('0q82_2A')   / Number('0q82_06')).qstring())
        self.assertEqual('0q82_0180',            (Number('0q82_03C0') / Number('0q82_0280')).qstring())
        self.assertEqual('0q82_01__8202_690300', (Number('0q7D_FB__820A_690300')
                                                                      / Number('0q82_03__8204_690300')).qstring())

    def test_floordiv(self):
        """Double-slash floor division truncates toward negative infinity, outputing the nearest whole number."""
        self.binary_op(operator.__floordiv__, 7, 47, 6)
        self.binary_op(operator.__floordiv__, 2.0, 6.0, 2.5)
        self.assertEqual('0q82_07', (Number(47)  // Number(6)).qstring())
        self.assertEqual('0q82_02', (Number(6.0) // Number(2.5)).qstring())

    def test_hybrid_python_division(self):
        """
        Pyrhon 2 has hybrid division.  True-division for floats, floor-division for ints.

        In Python 2, int single-slash int behaves like int double-slash int,
        when not importing division from __future__.  But we do that import in this file.
        We can't unimport future division, see http://stackoverflow.com/q/12498866/673991
        So instead we call operator.__div__(), which does NOT honor our future imports.
        """
        self.assertEqual(2.5, 5 / 2)
        self.assertEqual(2, 5 // 2)

        self.assertEqual(2.5, operator.__truediv__(5, 2))
        self.assertEqual(2, operator.__floordiv__(5, 2))

        if six.PY2:
            # noinspection PyUnresolvedReferences
            self.assertEqual(2, operator.__div__(5, 2))
        else:
            with self.assertRaises(AttributeError):
                # noinspection PyUnresolvedReferences
                operator.__div__(5, 2)

    def test_no_hybrid_number_division(self):
        """qiki.Number divides ala Python 3:  single-slash always means true division."""
        self.assertEqual(2, operator.__floordiv__(5, 2))
        self.assertEqual(2.5, operator.__truediv__(5, 2))
        self.assertEqual(2.75, operator.__truediv__(5.5, 2))

        self.assertEqual(Number(2), Number(5) // Number(2))
        self.assertEqual(Number(2.5), Number(5) / Number(2))   # true-div even though 5 and 2 are whole
        self.assertEqual(Number(2.75), Number(5.5) / Number(2))

        self.assertEqual(Number(2.5), Number(5).__div__(Number(2)))   # true-div even though 5 and 2 are whole
        self.assertEqual(Number(2.75), Number(5.5).__div__(Number(2)))

        self.assertEqual('0q82_0280', Number('0q82_05').__div__(Number('0q82_02')))   # true-div though whole
        self.assertEqual('0q82_02C0', Number('0q82_0580').__div__(Number('0q82_02')))

    def test_floordiv_complex(self):
        """
        Floor-division with complex numbers is
            odd in Python 2:
                floor() seems to strip the imaginary part.
            disallowed in Python 3:
                TypeError: can't take floor of complex number.
        """
        if six.PY2:
            self.binary_op(operator.__floordiv__, 1+0j,  -5+10j,     3+4j )
            # noinspection PyUnresolvedReferences
            self.assertEqual(                     1+0j, (-5+10j) // (3+4j))
            self.assertEqual(                     1+2j, (-5+10j) /  (3+4j))
        else:
            with self.assertRaises(TypeError):
                self.binary_op(operator.__floordiv__, 1+0j, -5+10j,   3+4j)
            with self.assertRaises(TypeError):
                # noinspection PyTypeChecker
                self.assertEqual(                     1+0j, -5+10j // 3+4j)
            with self.assertRaises(TypeError):
                # noinspection PyTypeChecker
                _ = -5+10j // 3+4j

    def test_operator_div(self):
        if six.PY2:
            self.assertTrue(hasattr(operator, '__div__'))
            # noinspection PyUnresolvedReferences
            self.binary_op(operator.__div__, 7, 42, 6)
            # noinspection PyUnresolvedReferences
            self.binary_op(operator.__div__, Number('0q8A_01'),   # Loss of precision; true-div uses float
                                             Number('0q92_0100000000000000020000000000000001'),
                                             Number('0q8A_010000000000000001'))
            self.binary_op(operator.__floordiv__,       0x010000000000000001,   # floor-div precise on large int
                                                        0x0100000000000000020000000000000001,
                                                        0x010000000000000001)
        else:
            self.assertFalse(hasattr(operator, '__div__'))

    def test_pow(self):
        self.binary_op(operator.__pow__, 65536, 2, 16)
        self.binary_op(operator.__pow__, 3.375, 1.5, 3.0)
        self.binary_op(operator.__pow__, Number('0qFE_80'), Number(2), Number(999))

    def test_pow_lander_and_parkin(self):
        """
        Test formula from 1966 counterexample paper by Lander & Parkin.

        THANKS:  Numberphile, https://youtu.be/QvvkJT8myeI
        """
        self.assertEqual(27**5 + 84**5 + 110**5 + 133**5, 144**5)
        self.assertEqual(
            Number(27)**Number(5) +
            Number(84)**Number(5) +
            Number(110)**Number(5) +
            Number(133)**Number(5),

            Number(144)**Number(5)
        )

        # A slight digression...
        self.assertEqual(27.0**5.0 + 84.0**5.0 + 110.0**5.0 + 133.0**5.0, 144.0**5.0)
        # NOTE:  No round-off errors in floating point.
        self.assertEqual(144**5, 61917364224)
        self.assertEqual(144**5, 0xE6A900000)
        self.assertEqual(2**36, 0x1000000000)
        # NOTE:  The biggest value in the formula fits in 36 bits.
        self.assertEqual('0q86_0E6A90', Number(144**5).qstring())

    def test_add_assign(self):
        """
        Test the __iadd__ operator.

        So apparently implementing __add__ means you get __iadd__ for free.
        """
        n = 2
        n += Number(2)
        self.assertEqual(Number(4), n)

        n = Number(2)
        n += Number(2)
        self.assertEqual(Number(4), n)

        n = Number(2)
        n += 2
        self.assertEqual(Number(4), n)

    def test_div_assign(self):
        n = 42
        n /= Number(6)
        self.assertEqual(Number(7), n)

        n = Number(42)
        n /= Number(6)
        self.assertEqual(Number(7), n)

        n = Number(42)
        n /= 6
        self.assertEqual(Number(7), n)

    # TODO:  Other assignment operators -= *= //= %= **= |= &= ^= >>= <<=

    def assert_inc_works_on(self, integer):
        n = Number(integer)
        n_plus_one = Number(integer)
        n_plus_one.inc()
        self.assertEqual(   integer+1, int(n_plus_one))
        self.assertNotEqual(integer,   int(n_plus_one))
        self.assertNotEqual(integer+1, int(n))
        self.assertEqual(   integer,   int(n))

    def test_inc(self):
        self.assert_inc_works_on(0)
        self.assert_inc_works_on(1)

    def test_inc_googol(self):
        googol = 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
        self.assert_inc_works_on(googol)

    if TEST_INC_ON_THOUSAND_POWERS_OF_TWO:
        def test_inc_powers_of_2(self):   # Takes take a long time, 2-12 seconds.
            power_of_two = 1
            for binary_exponent in range(0,1000):
                self.assert_inc_works_on(power_of_two-4)
                self.assert_inc_works_on(power_of_two-3)
                self.assert_inc_works_on(power_of_two-2)
                self.assert_inc_works_on(power_of_two-1)
                self.assert_inc_works_on(power_of_two)
                self.assert_inc_works_on(power_of_two+1)
                self.assert_inc_works_on(power_of_two+2)
                self.assert_inc_works_on(power_of_two+3)
                self.assert_inc_works_on(power_of_two+4)
                power_of_two *= 2


# noinspection SpellCheckingInspection
class NumberComplex(NumberTests):

    def test_01a_real(self):
        """Test Number.real."""
        n = Number(1)
        self.assertEqual(1.0, float(n))
        self.assertEqual(1.0, float(n.real))
        self.assertIsInstance(n, Number)
        self.assertIsInstance(n.real, Number)

    def test_01b_real(self):
        """Number.real should never return self, even if it's the same value."""
        n = Number(1)
        nreal = n.real
        self.assertIsNot(nreal, n)

    def test_02a_imag_zero(self):
        """Test Number.imag for a real number."""
        n = Number(1)
        self.assertEqual(1.0, float(n))
        self.assertEqual(0.0, float(n.imag))

    def test_02b_imag(self):
        """Test Number.imag for a complex number."""
        n = Number('0q82_07__8209_690300')
        self.assertEqual('0q82_07', n.real.qstring())
        self.assertEqual('0q82_09', n.imag.qstring())
        self.assertEqual(7.0, float(n.real))
        self.assertEqual(9.0, float(n.imag))
        self.assertEqual('0q82_07__8209_690300', n.qstring())   # make sure n unchanged by all that
        self.assertIsInstance(n, Number)
        self.assertIsInstance(n.imag, Number)

    def test_03a_complex_conversion(self):
        """Test complex --> Number --> complex."""
        n = Number(888+111j)
        self.assertEqual(888.0, float(n.real))
        self.assertEqual(111.0, float(n.imag))
        # noinspection PyTypeChecker
        self.assertEqual(888.0+111.0j, complex(n))

    def test_03b_complex_phantom_real(self):
        """Test complex with a zero imaginary --> Number --> real."""
        self.assertEqual('0q82_2A__830457_690400', Number((42+1111j)).qstring())
        self.assertEqual('0q82_2A__80_690200', Number(42+0j).qstring())
        self.assertEqual('0q82_2A', Number(42).qstring())
        self.assertEqual(Number(42), Number((42+0j)))

    def test_03c_complex_phantom_deliberate(self):
        """Zero imaginary parts must be possible to support quaternions, maybe."""
        self.assertNotEqual('0q82_2A', Number('0q82_2A__80_690200').qstring())
        self.assertEqual('0q82_2A__80_690200', Number('0q82_2A__80_690200').qstring())

    def test_03d_complex_phantom_immaterial(self):
        """Zero imaginary parts must not thwart numbers being equal."""
        self.assertEqual(Number('0q82_2A'), Number('0q82_2A__80_690200'))

    def test_03e_complex_zero_imag_normalized(self):
        """A zero imaginary suffix is normalized away."""
        self.assertEqual('0q82_2A__8211_690300', Number(42+17j).qstring())
        self.assertEqual('0q82_2A__8211_690300', Number(42+17j, normalize=True).qstring())

        self.assertEqual('0q82_2A__80_690200', Number(42+0j).qstring())
        self.assertEqual('0q82_2A__80_690200', Number(42+0j, normalize=False).qstring())
        self.assertEqual('0q82_2A',            Number(42+0j, normalize=True).qstring())

    def test_04_real_suffixed(self):
        """Number.real ignores other suffixes."""
        self.assertEqual('0q82_11', Number('0q82_11').real.qstring())
        self.assertEqual('0q82_11', Number('0q82_11__0000').real.qstring())
        self.assertEqual('0q82_11', Number('0q82_11__8201_7F0300').real.qstring())

    def test_05a_conjugate(self):
        """Number.conjugate() passes through when imaginary is zero."""
        self.assertEqual(42.0, complex(Number(42.0).conjugate()))
        self.assertEqual('0q82_2A', Number(42.0).qstring())
        self.assertEqual('0q82_2A', Number(42.0).conjugate().qstring())

    def test_05b_conjugate(self):
        """Number.conjugate() should work like native complex.conjugate()."""
        native_complex = 888+111j
        self.assertEqual(888-111j, native_complex.conjugate())
        self.assertEqual(888-111j, complex(Number(native_complex).conjugate()))
        self.assertEqual(Number(888-111j), Number(888+111j).conjugate())

    def test_05c_conjugate(self):
        """Number.conjugate(), when it passes through, must not return self."""
        qiki_complex = Number(888)
        qiki_conjugate = qiki_complex.conjugate()
        self.assertIsNot(qiki_complex, qiki_conjugate)

    def test_06a_equal(self):
        """Complex equality-comparisons (== !=) should work."""
        self.assertEqual(888+111j, Number(888+111j))
        self.assertNotEqual(888-111j, Number(888+111j))
        self.assertNotEqual(888+111j, Number(888-111j))
        self.assertEqual(888-111j, Number(888-111j))

    def test_06b_compare(self):
        """Complex ordered-comparison < should raise a TypeError, both native and qiki numbers."""
        x, x_bar = 888+111j, 888-111j
        with self.assertRaises(TypeError):   # Comparing native complex numbers raises a TypeError.
            # noinspection PyStatementEffect
            x_bar < x

        n, n_bar = Number(888+111j), Number(888-111j)
        with self.assertRaises(TypeError):   # So should Number() comparisons with a nonzero imaginary.
            _ = n_bar < n
        with self.assertRaises(Number.CompareError):   # By the way, Number.CompareError is a TypeError.
            _ = n_bar < n

    def test_06c_more_or_less_complex_comparisons(self):
        """Complex ordered-comparisons < <= > >= should raise a TypeError, qiki numbers. """
        n, n_bar = Number(888+111j), Number(888-111j)
        with self.assertRaises(TypeError):   # Check all comparison operators.
            _ = n_bar < n
        with self.assertRaises(TypeError):
            _ = n_bar <= n
        with self.assertRaises(TypeError):
            _ = n_bar > n
        with self.assertRaises(TypeError):
            _ = n_bar >= n

    # noinspection PyStatementEffect
    def test_06d_mixed_types_and_mixed_complexities_comparison(self):
        """Doubly mixed ordered-comparison < should raise a Type Error.

        Doubly mixed, meaning:
            1. One side is complex, the other side real.
            2. One side is a qiki.Number, the other a native Python number.
        """
        native_complex1, native_complex2 = 888+111j, 888-111j
        qiki_complex1, qiki_complex2 = Number(native_complex1), Number(native_complex2)
        qiki_real1, qiki_real2 = qiki_complex1.real, qiki_complex2.real
        native_real1, native_real2 = float(qiki_real1), float(qiki_real2)
        self.assertEqual(native_real1, native_complex1.real)
        self.assertEqual(native_real2, native_complex2.real)
        self.assertTrue(qiki_real1 <= qiki_real2)   # Only okay if both imaginaries are zero.
        self.assertTrue(qiki_real1 >= qiki_real2)
        with self.assertRaises(Number.CompareError):   # q vs q -- Neither side can have a nonzero imaginary.
            _ = qiki_complex2 < qiki_real1
        with self.assertRaises(Number.CompareError):
            _ = qiki_real2 < qiki_complex1
        with self.assertRaises(Number.CompareError):   # n vs q
            _ = native_complex2 < qiki_real1
        with self.assertRaises(Number.CompareError):
            _ = native_real2 < qiki_complex1
        with self.assertRaises(Number.CompareError):   # q vs n
            _ = qiki_complex2 < native_real1
        with self.assertRaises(Number.CompareError):
            _ = qiki_real2 < native_complex1
        with self.assertRaises(TypeError):   # n vs n
            # noinspection PyTypeChecker
            _ = native_complex2 < native_real1
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            _ = native_real2 < native_complex1

    # TODO:  Check doubly mixed comparisons for <= > >=

    def test_07a_is_complex(self):
        self.assertFalse(Number(42).is_complex())
        self.assertTrue(Number(42+99j).is_complex())

    def test_07b_zero_imag_isnt_complex(self):
        self.assertFalse(Number(42+0j).is_complex())

    def test_07c_is_real(self):
        self.assertTrue(Number(42).is_real())
        self.assertFalse(Number(42+99j).is_real())

    def test_08_float_complex(self):
        self.assertEqual(42.0, float(Number(42.0)))
        complex_number = Number(42.0+99.0j)
        with self.assertRaises(TypeError):
            float(complex_number)

    def test_09_imag_first(self):
        """
        Number.imag only gets the first imaginary suffix, ignoring others.

        This may pave the way for quaternions.
        """
        n = Number('0q82_07__8209_690300__8205_690300')
        self.assertEqual(7.0, float(n.real))
        self.assertEqual(9.0, float(n.imag))
        n = Number('0q82_07__8205_690300__8209_690300')
        self.assertEqual(7.0, float(n.real))
        self.assertEqual(5.0, float(n.imag))


# noinspection SpellCheckingInspection
class NumberPickleTests(NumberTests):
    """
    This isn't so much testing as revealing what pickle does to a qiki.Number.

    Hint, there's a whole buncha baggage in addition to what __getstate__ and
    __setstate__ generate and consume.
    """

    def test_pickle_protocol_0_class(self):
        self.assertEqual(
            pickle.dumps(Number).decode('latin-1'),
            py23(
                b'ctest_number\n'
                b'NumberAlternate\n'
                b'p0\n'
                b'.',                  # Python 2.X

                b'\x80\x03ctest_number\n'   # Python 3.X
                b'NumberAlternate\n'
                b'q\x00.',
            ).decode('latin-1')
        )
        # NOTE:  The latin-1 decode is not required for the equal comparison.  It's required if
        #        the comparison fails, and the values must be displayed.
        # NOTE:  It's no mystery why NumberAlternate appeared in place of Number when that
        #        class was derived.  It is a mystery why cnumber changed to ctest_number.
        # NOTE:  Another mystery is why a failure of comparison still generates another exception
        #        within that exception.  Possibly on the decode('latin-1').

    def test_pickle_protocol_0_instance(self):
        x314 = Number(3.14)
        self.assertEqual(                     '0q82_0323D70A3D70A3E0',                x314.qstring())
        self.assertEqual(                    b'\x82\x03#\xd7\n=p\xa3\xe0',            x314.raw)
        self.assertEqual(py23( "",  "b") +  "'\\x82\\x03#\\xd7\\n=p\\xa3\\xe0'", repr(x314.raw))
        self.assertEqual(py23(b"", b"b") + b"'\\x82\\x03#\\xd7\\n=p\\xa3\\xe0'", repr(x314.raw).encode('ascii'))
        self.assertEqual(
            pickle.dumps(x314).decode('latin-1'),
            py23(
                b'ccopy_reg\n'
                b'_reconstructor\n'
                b'p0\n'
                b'(ctest_number\n'
                b'NumberAlternate\n'
                b'p1\n'
                b'c__builtin__\n'
                b'object\n'
                b'p2\n'
                b'Ntp3\n'
                b'Rp4\n'
                b'S' + repr(x314.raw).encode('ascii') + b'\n'
                b'p5\n'
                b'b.',                 # Python 2.X

                b'\x80\x03ctest_number\n'   # Python 3.X
                b'NumberAlternate\n'
                b'q\x00)\x81q\x01C\t' + x314.raw + b'q\x02b.'
            ).decode('latin-1')
        )

        y314 = pickle.loads(pickle.dumps(x314))
        self.assertEqual(x314, y314)

    def test_pickle_protocol_2_class(self):
        self.assertEqual(
            pickle.dumps(Number, 2),
            (
                b'\x80\x02ctest_number\n'
                b'NumberAlternate\n'
                b'q\x00.'
            )
        )

    def test_pickle_protocol_2_instance(self):
        x314 = Number(3.14)
        self.assertEqual(x314.qstring(), '0q82_0323D70A3D70A3E0')
        self.assertEqual(x314.raw, b'\x82\x03\x23' b'\xd7\x0a\x3d\x70' b'\xa3' b'\xe0')
        x314_raw_utf8 =        b'\xc2\x82\x03\x23\xc3\x97\x0a\x3d\x70\xc2\xa3\xc3\xa0'

        self.assertEqual(
            pickle.dumps(x314, 2).decode('latin-1'),
            py23(
                b'\x80\x02ctest_number\n'
                b'NumberAlternate\n'
                b'q\x00)\x81q\x01U\t' + x314.raw + b'q\x02b.',   # Python 2.X

                b'\x80\x02ctest_number\n'                             # Python 3.X
                b'NumberAlternate\n'
                b'q\x00)\x81q\x01c_codecs\n'
                b'encode\n'
                b'q\x02X\r\x00\x00\x00' + x314_raw_utf8 + b'q\x03X\x06\x00\x00\x00latin1q\x04\x86q\x05Rq\x06b.'
            ).decode('latin-1')
        )

        # print(repr(pickle.dumps(x314, 2)))
        # PY2:  '\x80\x02cnumber\nNumber\nq\x00)\x81q\x01U\t\x82\x03#\xd7\n=p\xa3\xe0q\x02b.'
        # PY3:  b'\x80\x02cnumber\nNumber\nq\x00)\x81q\x01c_codecs\nencode\nq\x02X\r\x00\x00\x00\xc2\x82\x03#\xc3\x97'
        #       b'\n=p\xc2\xa3\xc3\xa0q\x03X\x06\x00\x00\x00latin1q\x04\x86q\x05Rq\x06b.'

        # print(repr(x314.raw))
        # '\x82\x03#\xd7\n=p\xa3\xe0'

        # As reported by failed assertEqual:
        # PY2:  '\x80\x02cnumber\nNumber\nq\x00)\x81q\x01U\t\x82\x03#\xd7\n=p\xa3\xe0q\x02b.'
        # PY3:  b'\x80\x02cnumber\nNumber\nq\x00)\x81q\x0[126 chars]06b.'

        y314 = pickle.loads(pickle.dumps(x314))
        self.assertEqual(x314, y314)


# noinspection SpellCheckingInspection
class NumberSuffixTests(NumberTests):

    # TODO:  Replace the indiscriminate use of suffix types here with Type.TEST.
    # that's reserved for testing, and has no value implications.
    # (So, for example, a suffix someday for rational numbers might modify
    # the value returned by float(), and not break tests here when it's implemented.)

    def test_plus_suffix_type(self):
        self.assertEqual(Number('0q82_01__7E0100'), Number(1, Suffix(Suffix.Type.TEST)))

    def test_plus_suffix_type_by_class(self):
        self.assertEqual(Number('0q82_01__7E0100'), Number(1, Suffix(Suffix.Type.TEST)))

    def test_plus_suffix_type_and_payload(self):
        self.assertEqual(Number('0q82_01__887E0200'), Number(1, Suffix(Suffix.Type.TEST, b'\x88')))

    def test_plus_suffix_type_and_payload_by_class(self):
        self.assertEqual(Number('0q82_01__887E0200'), Number(1, Suffix(Suffix.Type.TEST, b'\x88')))

    def test_qstring_empty(self):
        """Make sure trailing 00s in qstring literal are not stripped."""
        self.assertEqual(Number('0q82_01__0000'), Number('0q82_01__0000'))
        self.assertEqual('0q82010000', Number('0q82_01__0000').qstring(underscore=0))
        self.assertEqual('0q82012233110300', Number('0q82_01__2233_110300').qstring(underscore=0))

    def test_plus_suffix_empty(self):
        self.assertEqual(Number('0q82_01__0000'), Number(1, Suffix()))

    def test_plus_suffix_payload(self):
        self.assertEqual(Number('0q82_01__3456_120300'), Number(1, Suffix(0x12, b'\x34\x56')))

    def test_plus_suffix_qstring(self):
        self.assertEqual('0q8201030100', Number(1, Suffix(0x03)).qstring(underscore=0))
        self.assertEqual('0q82_01__030100', Number(1).plus_suffix(0x03).qstring())

    def test_plus_suffix_qstring_empty(self):
        self.assertEqual('0q82010000', Number(1).plus_suffix().qstring(underscore=0))
        self.assertEqual('0q82_01__0000', Number(1).plus_suffix().qstring())

    def test_plus_suffix_qstring_payload(self):
        self.assertEqual('0q82014455330300', Number(1).plus_suffix(0x33, b'\x44\x55').qstring(underscore=0))
        self.assertEqual('0q82_01__4455_330300', Number(1).plus_suffix(0x33, b'\x44\x55').qstring())

    def test_minus_suffix(self):
        n = Number('0q82_01__{:02X}0100'.format(Suffix.Type.TEST))
        n_deleted = n.minus_suffix(Suffix.Type.TEST)
        self.assertEqual('0q82_01', n_deleted.qstring())

    def test_constructor_suffix(self):
        self.assertEqual(Number('0q82_01__7E0100'), Number(1, Suffix(Suffix.Type.TEST)))

    def test_constructor_suffixes(self):
        number_fat = Number(
            0,
            Suffix(Suffix.Type.TEST, Number(1)),
            Suffix(Suffix.Type.TEST, Number(2)),
            Suffix(Suffix.Type.TEST, Number(3)),
        )
        self.assertEqual('0q80__8201_7E0300__8202_7E0300__8203_7E0300', number_fat.qstring())

    def test_constructor_suffix_list(self):
        number_fat = Number(
            0,
            [
                Suffix(Suffix.Type.TEST, Number(1)),
                Suffix(Suffix.Type.TEST, Number(2)),
                Suffix(Suffix.Type.TEST, Number(3)),
            ]
        )
        self.assertEqual('0q80__8201_7E0300__8202_7E0300__8203_7E0300', number_fat.qstring())

    def test_constructor_suffix_deep_nested_list(self):
        number_fat = Number(
            0,
            [
                Suffix(Suffix.Type.TEST, Number(1)),
                [
                    Suffix(Suffix.Type.TEST, Number(2)),
                    [
                        Suffix(Suffix.Type.TEST, Number(3)),
                        Suffix(Suffix.Type.TEST, Number(4)),
                        Suffix(Suffix.Type.TEST, Number(5)),
                    ],
                    Suffix(Suffix.Type.TEST, Number(6)),
                ],
                Suffix(Suffix.Type.TEST, Number(7)),
            ],
            Suffix(Suffix.Type.TEST, Number(8)),
        )
        self.assertEqual(
            '0q80__'
            '8201_7E0300__'
            '8202_7E0300__'
            '8203_7E0300__'
            '8204_7E0300__'
            '8205_7E0300__'
            '8206_7E0300__'
            '8207_7E0300__'
            '8208_7E0300', number_fat.qstring())

    def test_constructor_not_suffix(self):
        class SomeType(object):
            pass
        some_type = SomeType()
        with self.assertRaises(Number.ConstructorSuffixError):
            self.assertEqual(Number('0q82_01__7E0100'), Number(1, some_type))

    def test_suffix_equality_impact(self):
        """
        In general, Number suffixes should impact equality.

        That is, a suffixed Number should not equal an unsuffixed number.
        Or two numbers with different suffixes should not be equal.
        (One exception is a complex number with a zero imaginary suffix, that should equal its
        root, real-only version.  That's tested elsewhere.)
        """
        n_plain = Number('0q82_01')
        n_suffixed = Number('0q82_01__7E0100')
        n_another_suffixed = Number('0q82_01__887E0200')

        self.assertTrue(n_plain == n_plain)
        self.assertFalse(n_plain == n_suffixed)
        self.assertFalse(n_suffixed == n_plain)
        self.assertTrue(n_suffixed == n_suffixed)

        self.assertTrue(n_suffixed == n_suffixed)
        self.assertFalse(n_suffixed == n_another_suffixed)
        self.assertFalse(n_another_suffixed == n_suffixed)
        self.assertTrue(n_another_suffixed == n_another_suffixed)

    def test_suffix_equality_other_types(self):
        """
        Look for a bug where Suffix.__eq__(self, other) expects other to be a Suffix.

        Note that self.assertNotEqual() does not invoke Suffix.__eq__().
        """
        self.assertFalse(Suffix(Suffix.Type.TEST) == 0)
        self.assertFalse(0 == Suffix(Suffix.Type.TEST))
        self.assertFalse(Suffix(Suffix.Type.TEST) == object())
        self.assertFalse(object() == Suffix(Suffix.Type.TEST))

    def test_suffix_equality_normalize_root(self):
        """Test that roots of suffixed Numbers are normalized before comparison."""
        self.assertEqual(
            Number('0q82'),
            Number('0q82_01')
        )
        self.assertNotEqual(
            Number('0q82').qstring(),
            Number('0q82_01').qstring()
        )
        self.assertEqual(
            Number('0q82').plus_suffix(Suffix.Type.TEST),
            Number('0q82_01').plus_suffix(Suffix.Type.TEST)
        )
        self.assertNotEqual(
            Number('0q82').plus_suffix(Suffix.Type.TEST).qstring(),
            Number('0q82_01').plus_suffix(Suffix.Type.TEST).qstring()
        )

    def test_suffix_type_inequality(self):
        """Different suffix types make the Numbers different."""
        self.assertNotEqual(
            Number('0q82_01').plus_suffix(Suffix.Type.TEST),
            Number('0q82_01').plus_suffix(Suffix.Type.TEST-1)
        )

    def test_suffix_payload_inequality(self):
        """Different suffix payloads make the Numbers different."""
        self.assertEqual(
            Number('0q82_01').plus_suffix(Suffix.Type.TEST),
            Number('0q82_01').plus_suffix(Suffix.Type.TEST, b'')
        )
        self.assertNotEqual(
            Number('0q82_01').plus_suffix(Suffix.Type.TEST),
            Number('0q82_01').plus_suffix(Suffix.Type.TEST, b'\x88')
        )
        self.assertEqual(
            Number('0q82_01').plus_suffix(Suffix.Type.TEST, b'\x88'),
            Number('0q82_01').plus_suffix(Suffix.Type.TEST, b'\x88')
        )
        self.assertNotEqual(
            Number('0q82_01').plus_suffix(Suffix.Type.TEST, b'\x88'),
            Number('0q82_01').plus_suffix(Suffix.Type.TEST, b'\x88\x88')
        )
        self.assertNotEqual(
            Number('0q82_01').plus_suffix(Suffix.Type.TEST, b'\x11'),
            Number('0q82_01').plus_suffix(Suffix.Type.TEST, b'\x88')
        )

    def test_minus_missing_suffix(self):
        no_imaginary_suffix = Number('0q82_01__8201_7E0300')
        with self.assertRaises(Suffix.NoSuchType):
            no_imaginary_suffix.minus_suffix(Suffix.Type.IMAGINARY)

    def test_minus_suffix_among_many(self):
        n = Number(      '0q82_01__990100__880100__770100')
        self.assertEqual('0q82_01__990100__880100', n.minus_suffix(0x77).qstring())
        self.assertEqual('0q82_01__990100__770100', n.minus_suffix(0x88).qstring())
        self.assertEqual('0q82_01__880100__770100', n.minus_suffix(0x99).qstring())

    def test_minus_multiple_suffixes(self):
        """One call to minus_suffix() removes all suffixes of the given type."""
        n = Number(      '0q82_01__990100__880100__880100__110100__880100__880100__770100')
        self.assertEqual('0q82_01__990100__110100__770100', n.minus_suffix(0x88).qstring())

    def test_minus_suffix_multiple_tries(self):
        """Trying to remove the same suffix twice raises NoSuchType."""
        n = Number('0q82_01__990100__880100__880100__110100__880100__880100__770100')
        with self.assertRaises(Suffix.NoSuchType):
            n.minus_suffix(0x88).minus_suffix(0x88)

    def test_chain_minus_suffix(self):
        n = Number(1).plus_suffix(0x99).plus_suffix(0x88).plus_suffix(0x77)
        self.assertEqual('0q82_01__990100__880100__770100', n.qstring())
        self.assertEqual('0q82_01__770100', n.minus_suffix(0x88).minus_suffix(0x99))
        self.assertEqual('0q82_01__770100', n.minus_suffix(0x99).minus_suffix(0x88))
        self.assertEqual('0q82_01', n.minus_suffix(0x99).minus_suffix(0x88).minus_suffix(0x77))
        self.assertEqual('0q82_01', n.minus_suffix(0x77).minus_suffix(0x88).minus_suffix(0x99))
        self.assertEqual('0q82_01', n.minus_suffix(0x88).minus_suffix(0x77).minus_suffix(0x99))

    def test_suffix_weird_type(self):
        class WeirdType(object):
            pass

        weird_type = WeirdType()
        with self.assertRaises(TypeError):
            Suffix(0x11, weird_type)

    def test_suffix_class(self):
        suffix = Suffix(0x03)
        self.assertEqual(0x03, suffix.type_)
        self.assertEqual(b'', suffix.payload)
        self.assertEqual(b'\x03\x01\x00', suffix.raw)

    def test_suffix_class_empty(self):
        suffix = Suffix()
        self.assertEqual(None, suffix.type_)
        self.assertEqual(b'', suffix.payload)
        self.assertEqual(b'\x00\x00', suffix.raw)

    def test_suffix_class_payload(self):
        suffix = Suffix(33, b'\xDE\xAD\xBE\xEF')
        self.assertEqual(33, suffix.type_)
        self.assertEqual(b'\xDE\xAD\xBE\xEF', suffix.payload)
        self.assertEqual(b'\xDE\xAD\xBE\xEF\x21\x05\x00', suffix.raw)

    def test_suffix_class_equality(self):
        suffix1  = Suffix(0x01)
        another1 = Suffix(0x01)
        suffix3  = Suffix(0x03)
        another3 = Suffix(0x03)
        self.assertTrue(suffix1 == another1)
        self.assertFalse(suffix1 == another3)
        self.assertFalse(suffix3 == another1)
        self.assertTrue(suffix3 == another3)

    def test_suffix_class_equality_payload(self):
        suffix11  = Suffix(0x01, b'\x01\x11\x10')
        suffix13  = Suffix(0x01, b'\x03\x33\x30')
        another13 = Suffix(0x01, b'\x03\x33\x30')
        self.assertTrue(suffix11 == suffix11)
        self.assertFalse(suffix11 == suffix13)
        self.assertFalse(suffix13 == suffix11)
        self.assertTrue(suffix13 == another13)

    def test_suffix_class_qstring(self):
        self.assertEqual('0000', Suffix().qstring())
        self.assertEqual('110100', Suffix(0x11).qstring())
        self.assertEqual('2233110300', Suffix(0x11, b'\x22\x33').qstring(underscore=0))
        self.assertEqual('2233_110300', Suffix(0x11, b'\x22\x33').qstring())
        self.assertEqual('778899_110400', Suffix(type_=0x11, payload=b'\x77\x88\x99').qstring())

    def test_suffixes(self):
        self.assertEqual([], Number(1).suffixes)
        self.assertEqual([Suffix()], Number(1).plus_suffix().suffixes)
        self.assertEqual([Suffix(3)], Number(1).plus_suffix(3).suffixes)
        self.assertEqual(([Suffix(111), Suffix(222)]), Number(1.75).plus_suffix(111).plus_suffix(222).suffixes)

    # def test_parse_suffixes_example_in_docstring(self):
    #     self.assertEqual(
    #         (Number(1),    [Suffix(2),     Suffix(3, b'\x4567')]),
    #          Number(1).plus_suffix(2).plus_suffix(3, b'\x4567').parse_suffixes()
    #     )

    # def test_parse_multiple_suffixes(self):
    #     self.assertEqual(
    #                       ([Suffix(2),     Suffix(3)]),
    #          Number(1).plus_suffix(2).plus_suffix(3).suffixes
    #     )

    def test_suffixes_payload(self):
        self.assertEqual([Suffix(123, b'')], Number(22.25).plus_suffix(123, b'').suffixes)
        self.assertEqual([Suffix(123, b' ')], Number( 22.25).plus_suffix(123, b' ').suffixes)
        self.assertEqual([Suffix(123, b'\xAA\xBB\xCC')], Number(22.25).plus_suffix(123, b'\xAA\xBB\xCC').suffixes)

    def test_suffixes_is_passive(self):
        """Make sure x.suffixes does not modify x."""
        n_original = Number(1.75).plus_suffix(111).plus_suffix(222)
        nbytes_original = len(n_original.raw)
        n = Number(n_original)

        _ = n.suffixes

        self.assertEqual(n_original, n)
        self.assertEqual(nbytes_original, len(n.raw))

    def test_malformed_suffix(self):
        """Nonsense suffixes (or illicit trailing 00-bytes) should raise ValueError exceptions."""

        # TODO:  Should these raise exceptions in the *constructor*?
        #        At least now these don't raise RawError:  n.qstring(), float(n), int(n)

        def bad_to_parse(n, message_fragment):
            # print("Well", n.qstring(), float(n))
            # EXAMPLE:
            #     Well 0q00!? -inf
            #     Well 0q00_00!? -inf
            #     Well 0q22_0100!? -3.60061779735e+221
            #     Well 0q33_4455220400!? -3.04191017326e+180
            #     Well 0q82_019900!? 1.59765625
            #     Well 0q82_01000500!? 1.00007629395
            #     Well 0q82_01000400!? 1.00006103516
            #     Well 0q82_01000300!? 1.00004577637
            with self.assertRaisesRegex(Suffix.RawError, message_fragment):
                list(n._suffix_indexes_backwards())
            with self.assertRaisesRegex(Suffix.RawError, message_fragment):
                _ = n.suffixes
            with self.assertRaisesRegex(Suffix.RawError, message_fragment):
                _ = n.unsuffixed

        def good_to_parse(n):
            list(n._suffix_indexes_backwards())
            _ = n.suffixes
            _ = n.unsuffixed

        bad_to_parse(Number('0q00'), "length underflow")   # Where's the length byte?
        bad_to_parse(Number('0q__0000'), "NAN")   # Can't suffix Number.NAN
        bad_to_parse(Number('0q__220100'), "NAN")   # Can't suffix Number.NAN
        bad_to_parse(Number('0q__334455220400'), "NAN")   # Can't suffix Number.NAN
        bad_to_parse(Number('0q82_01__9900'), "payload overflow")     # Suffix length "underflow"
        bad_to_parse(Number('0q82_01__000500'), "payload overflow")
        bad_to_parse(Number('0q82_01__000400'), "payload overflow")   # Suffix underflows one byte off the left edge.
        bad_to_parse(Number('0q82_01__000300'), "NAN")   # Looks like a suffixed Number.NAN.

        good_to_parse(Number('0q82_01__000200'))   # Actually parsed as 0q82__01000200
        good_to_parse(Number('0q82_01__000100'))
        good_to_parse(Number('0q82_01__0000'))

    def test_suffix_payload_too_long(self):
        self.assertEqual('11'*249 + '_08FA00', Suffix(8, b'\x11' * 249).qstring())
        self.assertEqual('11'*250 + '_08FB00', Suffix(8, b'\x11' * 250).qstring())
        with self.assertRaises(Suffix.PayloadError):
            Suffix(8, b'\x11' * 251)
        with self.assertRaises(Suffix.PayloadError):
            Suffix(8, b'\x11' * 252)

    def test_suffix_payload_type_error(self):
        class SomeType(object):
            pass
        some_type = SomeType()
        with self.assertRaises(Suffix.PayloadError):
            Suffix(Suffix.Type.TEST, some_type)

    def test_suffix_number(self):
        self.assertEqual('0q83_01FF__823F_FF0300', Number(511).plus_suffix(255, Number(63)))
        # TODO:  Should '0q83_01FF__82_3F_FF0300' have an underscore in its payload Number?

    def test_suffix_extract_raw(self):
        self.assertEqual(b'\x33\x44', Number(1).plus_suffix(0x11, b'\x33\x44').suffix(0x11).payload)

    def test_suffix_extract_raw_wrong(self):
        number_with_test_suffix = Number(1).plus_suffix(Suffix.Type.TEST, b'\x33\x44')
        with self.assertRaises(Suffix.NoSuchType):
            _ = number_with_test_suffix.suffix(Suffix.Type.IMAGINARY).payload

    def test_suffix_extract_raw_among_multiple(self):
        self.assertEqual(
            b'\x33\x44',
            Number(1).plus_suffix(0x11, b'\x33\x44').plus_suffix(0x22, b'\x88\x99').suffix(0x11).payload
        )
        self.assertEqual(
            b'\x88\x99',
            Number(1).plus_suffix(0x11, b'\x33\x44').plus_suffix(0x22, b'\x88\x99').suffix(0x22).payload
        )

    def test_suffix_extract_number(self):
        self.assertEqual( Number(88),      Number(1).plus_suffix(0x11, Number(88)).suffix(0x11).number)
        self.assertEqual( Number(-123.75), Number(1).plus_suffix(0x11, Number(-123.75)).suffix(0x11).number)
        self.assertEqual(        -123.75 , Number(1).plus_suffix(0x11, Number(-123.75)).suffix(0x11).number)
        self.assertIs(NumberOriginal, type(Number(1).plus_suffix(0x11, Number(-123.75)).suffix(0x11).number))

    def test_suffix_extract_number_missing(self):
        self.assertEqual(Number(88), Number(1).plus_suffix(0x11, Number(88)).suffix(0x11).number)
        with self.assertRaises(Suffix.NoSuchType):
            _ = Number(1).plus_suffix(0x99, Number(88)).suffix(0x11).number
        with self.assertRaises(Suffix.NoSuchType):
            _ = Number(1).suffix(0x11).number

    # def test_get_suffix_number_default(self):
    #     self.assertEqual(Number(88), Number(1).plus_suffix(0x11, Number(88)).suffix(0x11, Number(99)))
    #     self.assertEqual(Number(99), Number(1).plus_suffix(0x11, Number(88)).suffix(0x22, Number(99)))
    #     self.assertEqual(Number(99), Number(1)                              .suffix(0x22, Number(99)))

    def test_suffix_number_parse(self):
        n = Number(99).plus_suffix(0x11, Number(356))
        suffixes = n.suffixes
        self.assertEqual(1, len(suffixes))
        suffix = suffixes[0]
        self.assertIs(type(suffix), Suffix)
        self.assertEqual(0x11, suffix.type_)
        self.assertEqual(Number(356), suffix.number)

    def test_suffixes_1(self):
        n = Number(99).plus_suffix(Suffix.Type.TEST, Number(356))
        self.assertEqual(1, len(n.suffixes))
        self.assertIs(type(n.suffixes[0]), Suffix)
        self.assertEqual(Number(356), n.suffixes[0].number)

    def test_suffixes_3(self):
        n = Number(99)\
            .plus_suffix(Suffix.Type.TEST, Number(111))\
            .plus_suffix(Suffix.Type.TEST, Number(222))\
            .plus_suffix(Suffix.Type.TEST, Number(333))
        self.assertEqual(3, len(n.suffixes))
        self.assertIs(type(n.suffixes[0]), Suffix)
        self.assertIs(type(n.suffixes[1]), Suffix)
        self.assertIs(type(n.suffixes[2]), Suffix)
        self.assertEqual(Number(111), n.suffixes[0].number)
        self.assertEqual(Number(222), n.suffixes[1].number)
        self.assertEqual(Number(333), n.suffixes[2].number)

    def test_eq_ne_suffix(self):
        self.assertTrue(Suffix(0x11) == Suffix(0x11))
        self.assertFalse(Suffix(0x11) != Suffix(0x11))
        self.assertFalse(Suffix(0x11) == Suffix(0x22))
        self.assertTrue(Suffix(0x11) != Suffix(0x22))
        self.assertEqual(Suffix(0x11), Suffix(0x11))
        self.assertNotEqual(Suffix(0x11), Suffix(0x22))

        self.assertTrue(Suffix(0x22) == Suffix(0x22))
        self.assertFalse(Suffix(0x22) != Suffix(0x22))
        self.assertFalse(Suffix(0x22) == Suffix(0x11))
        self.assertTrue(Suffix(0x22) != Suffix(0x11))
        self.assertEqual(Suffix(0x22), Suffix(0x22))
        self.assertNotEqual(Suffix(0x22), Suffix(0x11))

    def test_get_suffix(self):
        n = Number(99).plus_suffix(0x11).plus_suffix(0x22)
        s11 = n.suffix(0x11)
        s22 = n.suffix(0x22)
        self.assertEqual(s11, Suffix(0x11))
        self.assertEqual(s22, Suffix(0x22))

    def test_nan_suffix_empty(self):
        nan = Number(float('nan'))
        with self.assertRaises(Suffix.RawError):
            nan.plus_suffix()

    def test_nan_suffix_type(self):
        nan = Number(float('nan'))
        with self.assertRaises(Suffix.RawError):
            nan.plus_suffix(0x11)

    def test_nan_suffix_payload(self):
        nan = Number(float('nan'))
        with self.assertRaises(Suffix.RawError):
            nan.plus_suffix(0x11, b'abcd')

    def test_is_suffixed(self):
        self.assertTrue(Number(22, Suffix()).is_suffixed())
        self.assertTrue(Number(22, Suffix(0x11)).is_suffixed())
        self.assertTrue(Number(22, Suffix(0x11, b'abcd')).is_suffixed())
        self.assertTrue(Number(22, Suffix(0x11, Number(42))).is_suffixed())
        self.assertFalse(Number(22).is_suffixed())
        self.assertFalse(Number.NAN.is_suffixed())

    def test_suffix_float(self):
        self.assertEqual(16.0, float(Number('0q82_10')))
        self.assertEqual(16.0, float(Number('0q82_10__0000')))
        self.assertEqual(16.0, float(Number('0q82_10__7F0100')))
        self.assertEqual(16.0, float(Number('0q82_10__FFFFFF_7F0400')))
        self.assertEqual(16.0, float(Number('0q82_10__123456_7F0400')))
        self.assertEqual(16.0625, float(Number('0q82_1010')))

    def test_unsuffixed(self):
        suffixed_word = Number(42).plus_suffix(Suffix.Type.TEST)
        self.assertEqual(Number(42), suffixed_word.unsuffixed)

    def test_unsuffixed_clone(self):
        """
        Make sure n.unsuffixed is a clone, so modifying it never risks modifying the original.

        Make sure the .unsuffixed property never returns self, even when there are no suffixes.
        """
        n1 = Number(42)
        n2 = n1.unsuffixed
        self.assertIsNot(n1, n2)

    # def test_parse_root(self):
    #     def assert_root_consistent(n):
    #         self.assertEqual(n.parse_root(), n.parse_suffixes()[0])
    #     assert_root_consistent(Number('0q'))
    #     assert_root_consistent(Number('0q82_10'))
    #     assert_root_consistent(Number('0q82_10__0000'))
    #     assert_root_consistent(Number('0q82_10__FFFFFF_7F0400'))
    #     assert_root_consistent(Number('0q82_10__123456_7F0400'))

    def test__suffix_indexes_backwards(self):
        self.assertEqual(    [], list(Number('0q')._suffix_indexes_backwards()))
        self.assertEqual(    [], list(Number('0q82_10')._suffix_indexes_backwards()))
        self.assertEqual(   [2], list(Number('0q82_10__0000')._suffix_indexes_backwards()))
        self.assertEqual(   [2], list(Number('0q82_10__FFFFFF_7F0400')._suffix_indexes_backwards()))
        self.assertEqual(   [2], list(Number('0q82_10__123456_7F0400')._suffix_indexes_backwards()))
        self.assertEqual([8, 2], list(Number('0q82_10__123456_7F0400__0000')._suffix_indexes_backwards()))
        self.assertEqual([8, 2], list(Number('0q82_10__123456_7F0400__789ABC_7F0400')._suffix_indexes_backwards()))
        self.assertEqual([4, 2], list(Number('0q82_10__0000__789ABC_7F0400')._suffix_indexes_backwards()))

    def test__suffix_indexes_backwards_NAN(self):
        with self.assertRaisesRegex(Suffix.RawError, r'NAN'):
            list(Number('0q__0000')._suffix_indexes_backwards())
        with self.assertRaisesRegex(Suffix.RawError, r'NAN'):
            list(Number('0q__123456_7F0400')._suffix_indexes_backwards())

    def test__suffix_indexes_backwards_overflow(self):
        self.assertEqual([1], list(Number('0q80__0000')._suffix_indexes_backwards()))
        self.assertEqual([1], list(Number('0q80__7F0100')._suffix_indexes_backwards()))
        self.assertEqual([1], list(Number('0q80__12_7F0200')._suffix_indexes_backwards()))
        self.assertEqual([1], list(Number('0q80__1234_7F0300')._suffix_indexes_backwards()))
        self.assertEqual([1], list(Number('0q80__123456_7F0400')._suffix_indexes_backwards()))
        with self.assertRaisesRegex(Suffix.RawError, r'NAN'):
            list(Number('0q__80123456_7F0500')._suffix_indexes_backwards())
        with self.assertRaisesRegex(Suffix.RawError, r'payload overflow'):
            list(Number('0q80__123456_7F0600')._suffix_indexes_backwards())
        with self.assertRaisesRegex(Suffix.RawError, r'payload overflow'):
            list(Number('0q80__123456_7F0700')._suffix_indexes_backwards())
        with self.assertRaisesRegex(Suffix.RawError, r'payload overflow'):
            list(Number('0q80__123456_7F8800')._suffix_indexes_backwards())
        with self.assertRaisesRegex(Suffix.RawError, r'payload overflow'):
            list(Number('0q80__123456_7FFF00')._suffix_indexes_backwards())

    def test__suffix_indexes_backwards_underflow(self):
        self.assertEqual([1], list(Number('0q80__0000')._suffix_indexes_backwards()))
        with self.assertRaisesRegex(Suffix.RawError, r'length underflow'):
            list(Number('0q__00')._suffix_indexes_backwards())
        with self.assertRaisesRegex(Suffix.RawError, r'length underflow'):
            list(Number('0q__00__123456_7F0400')._suffix_indexes_backwards())

    def test_suffix_affecting_float(self):
        self.assertEqual(42.0, float(Number(42)))
        self.assertEqual(42.0, float(Number(42, Suffix(Suffix.Type.TEST))))
        self.assertEqual(42.0, float(Number(42, Suffix(Suffix.Type.TEST, Number(100)))))

    def test_suffix_affecting_int(self):
        self.assertEqual(42, int(Number(42)))
        self.assertEqual(42, int(Number(42, Suffix(Suffix.Type.TEST))))
        self.assertEqual(42, int(Number(42, Suffix(Suffix.Type.TEST, Number(100)))))

        self.assertEqual(65536, int(Number(65536)))
        self.assertEqual(65536, int(Number(65536, Suffix(Suffix.Type.TEST))))
        self.assertEqual(65536, int(Number(65536, Suffix(Suffix.Type.TEST, Number(100)))))


# noinspection SpellCheckingInspection
class NumberDictionaryKeyTests(NumberTests):
    """qiki.Number() should work as a dictionary key."""
    def setUp(self):
        super(NumberDictionaryKeyTests, self).setUp()
        self.d = dict()
        self.d[Number(2)] = 'dos'
        self.d[Number(5)] = 'cinco'

    def test_dict_lookup(self):
        self.assertEqual('dos', self.d[Number(2)])
        self.assertEqual('cinco', self.d[Number(5)])   # Number.__hash__ makes this work

    def test_dict_key_error(self):
        with self.assertRaises(KeyError):
            # noinspection PyStatementEffect
            self.d[Number(8)]

    def test_dict_int_behavior(self):
        with self.assertRaises(KeyError):   # Because hash(2) != hash(Number(2))
            # noinspection PyStatementEffect
            self.d[2]
        with self.assertRaises(KeyError):
            # noinspection PyStatementEffect
            self.d[5]
        self.assertTrue(2 == Number(2))
        self.assertTrue(5 == Number(5))
        # Does this lead to confusion?  Equal things that don't behave the same?  Effing separate but equal??
        # This violates the statement at https://docs.python.org/2/library/functions.html#hash
        # "Numeric values that compare equal have the same hash value
        # (even if they are of different types, as is the case for 1 and 1.0)."

    def test_number_hash_isnt_bijective(self):
        self.assertFalse(hash(2) == hash(Number(2)))
        self.assertFalse(hash(5) == hash(Number(5)))
        # This might be fixed if Number.__hash__() returned __int__() when is_whole()
        # But floats should never be granted that courtesy.

    def test_dict_float_behavior(self):
        self.assertTrue(2 == 2.0)
        self.assertTrue(5 == 5.0)
        with self.assertRaises(KeyError):
            # noinspection PyStatementEffect
            self.d[2.0]
        with self.assertRaises(KeyError):
            # noinspection PyStatementEffect
            self.d[5.0]

    def test_dict_int_versus_float(self):
        self.d[2.0] = 'deux'
        self.d[5.0] = 'cinq'
        self.d[2] = 'два'
        self.d[5] = 'пять'
        self.assertEqual('dos', self.d[Number(2)])
        self.assertEqual('cinco', self.d[Number(5)])
        self.assertEqual('два', self.d[2.0])
        self.assertEqual('пять', self.d[5.0])   # See, floats and ints are equal AND behave the same.
        self.assertEqual('два', self.d[2])
        self.assertEqual('пять', self.d[5])

        self.d[2] = 'два'
        self.d[5] = 'пять'
        self.d[2.0] = 'deux'
        self.d[5.0] = 'cinq'
        self.assertEqual('dos', self.d[Number(2)])
        self.assertEqual('cinco', self.d[Number(5)])
        self.assertEqual('deux', self.d[2])
        self.assertEqual('cinq', self.d[5])
        self.assertEqual('deux', self.d[2.0])
        self.assertEqual('cinq', self.d[5.0])

        self.assertTrue(2 == 2.0 == hash(2) == hash(2.0))
        self.assertTrue(5 == 5.0 == hash(5) == hash(5.0))   # Oh.


################### New test GROUPS go above here ##################################


# noinspection SpellCheckingInspection
class NumberUtilitiesTests(NumberTests):
    """
    Testing utility functions in number.py.
    """

    # noinspection PyUnresolvedReferences
    def test_01_name_of_zone(self):
        self.assertEqual('TRANSFINITE', Zone.name_from_code[Zone.TRANSFINITE])
        self.assertEqual('TRANSFINITE', Zone.name_from_code[Number(float('+inf')).zone])
        self.assertEqual('NAN', Zone.name_from_code[Zone.NAN])
        self.assertEqual('NAN', Zone.name_from_code[Number.NAN.zone])
        self.assertEqual('NAN', Zone.name_from_code[Number().zone])
        self.assertEqual('ZERO', Zone.name_from_code[Zone.ZERO])
        self.assertEqual('ZERO', Zone.name_from_code[Number(0).zone])

        # TODO:  Test that Zone.name_from_code['actual_member_function'] raises IndexError.
        # Also exception on Zone.name_from_code['name'].
        # Also exception on any of the following:
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



    def test_sets_exclusive(self):
        self.assertTrue (sets_exclusive({1,2,3}, {4,5,6}))
        self.assertFalse(sets_exclusive({1,2,3}, {3,5,6}))
        self.assertTrue (sets_exclusive({1,2,3}, {4,5,6}, {7,8,9}))
        self.assertFalse(sets_exclusive({1,2,3}, {4,5,6}, {7,8,1}))

    def test_union_of_distinct_sets(self):
        self.assertEqual({1,2,3,4,5,6}, union_of_distinct_sets({1,2,3}, {4,5,6}))
        if not sys.flags.optimize:
            with self.assertRaises(AssertionError):
                union_of_distinct_sets({1,2,3}, {3,4,5})



    def test_01_hex_from_integer(self):
        self.assertEqual('05', hex_from_integer(0x5))
        self.assertEqual('55', hex_from_integer(0x55))
        self.assertEqual('0555', hex_from_integer(0x555))
        self.assertEqual('5555', hex_from_integer(0x5555))
        self.assertEqual('055555', hex_from_integer(0x55555))
        self.assertEqual('555555', hex_from_integer(0x555555))
        self.assertEqual('05555555', hex_from_integer(0x5555555))
        self.assertEqual('55555555', hex_from_integer(0x55555555))
        self.assertEqual(  '555555555555555555', hex_from_integer(0x555555555555555555))
        self.assertEqual('05555555555555555555', hex_from_integer(0x5555555555555555555))
        self.assertEqual('AAAAAAAA', hex_from_integer(0xAAAAAAAA).upper())

    def test_03_string_from_hex(self):
        self.assertEqual(b'',                                 string_from_hex(''))
        self.assertEqual(b'\x00',                             string_from_hex('00'))
        self.assertEqual(b'\xFF',                             string_from_hex('FF'))
        self.assertEqual(b'hello',                            string_from_hex('68656C6C6F'))
        self.assertEqual(b'\x01\x23\x45\x67\x89\xAB\xCD\xEF', string_from_hex('0123456789ABCDEF'))
        self.assertEqual(b'\x01\x23\x45\x67\x89\xAB\xCD\xEF', string_from_hex('0123456789abcdef'))

    # noinspection PyUnresolvedReferences
    def test_03_string_from_hex_errors(self):

        with self.assertRaises(string_from_hex.Error):
            string_from_hex('GH')   # nonhex
        with self.assertRaises(string_from_hex.Error):
            string_from_hex('89XX')   # hex then nonhex
        with self.assertRaises(string_from_hex.Error):
            string_from_hex('000')   # not even
        with self.assertRaises(string_from_hex.Error):
            string_from_hex('DE AD')   # space

        with self.assertRaises(ValueError):
            string_from_hex('GH')   # nonhex
        with self.assertRaises(ValueError):
            string_from_hex('89XX')   # hex then nonhex
        with self.assertRaises(ValueError):
            string_from_hex('000')   # not even
        with self.assertRaises(ValueError):
            string_from_hex('DE AD')   # space

    def test_hex_from_string(self):
        self.assertEqual('',                 hex_from_string(b''))
        self.assertEqual('00',               hex_from_string(b'\x00'))
        self.assertEqual('FF',               hex_from_string(b'\xFF'))
        self.assertEqual('68656C6C6F',       hex_from_string(b'hello'))
        self.assertEqual('0123456789ABCDEF', hex_from_string(b'\x01\x23\x45\x67\x89\xAB\xCD\xEF',))



    def test_01_exp256(self):
        self.assertEqual(1, exp256(0))
        self.assertEqual(256, exp256(1))
        self.assertEqual(65536, exp256(2))
        self.assertEqual(16777216, exp256(3))
        self.assertEqual(4294967296, exp256(4))
        self.assertEqual(1208925819614629174706176, exp256(10))
        self.assertEqual(1461501637330902918203684832716283019655932542976, exp256(20))
        self.assertEqual(2**800, exp256(100))
        self.assertEqual(2**8000, exp256(1000))

    def test_01_log256(self):
        self.assertEqual(0, log256(1))
        self.assertEqual(0, log256(2))
        self.assertEqual(0, log256(3))
        self.assertEqual(0, log256(4))
        self.assertEqual(0, log256(255))
        self.assertEqual(1, log256(256))
        self.assertEqual(1, log256(257))
        self.assertEqual(1, log256(65535))
        self.assertEqual(2, log256(65536))
        self.assertEqual(2, log256(65537))
        self.assertEqual(2, log256(16777215))
        self.assertEqual(3, log256(16777216))
        self.assertEqual(3, log256(16777217))
        self.assertEqual(3, log256(4294967295))
        self.assertEqual(4, log256(4294967296))
        self.assertEqual(4, log256(4294967297))

    def test_01_shift_leftward(self):
        self.assertEqual(0b001000000, shift_leftward(0b000010000, 2))
        self.assertEqual(0b000100000, shift_leftward(0b000010000, 1))
        self.assertEqual(0b000010000, shift_leftward(0b000010000, 0))
        self.assertEqual(0b000001000, shift_leftward(0b000010000,-1))
        self.assertEqual(0b000000100, shift_leftward(0b000010000,-2))

    def test_01_floats_really_same(self):
        self.assertFloatSame(1.0, 1.0)
        self.assertFloatNotSame(1.0, 0.0)
        self.assertFloatNotSame(1.0, float('nan'))
        self.assertFloatNotSame(float('nan'), 1.0)
        self.assertFloatSame(float('nan'), float('nan'))

        self.assertFloatSame(+0.0, +0.0)
        self.assertFloatNotSame(+0.0, -0.0)
        self.assertFloatNotSame(-0.0, +0.0)
        self.assertFloatSame(-0.0, -0.0)



    def test_01_left_pad00(self):
        self.assertEqual(b'abc', left_pad00(b'abc', 1))
        self.assertEqual(b'abc', left_pad00(b'abc', 2))
        self.assertEqual(b'abc', left_pad00(b'abc', 3))
        self.assertEqual(b'\x00abc', left_pad00(b'abc', 4))
        self.assertEqual(b'\x00\x00abc', left_pad00(b'abc', 5))
        self.assertEqual(b'\x00\x00\x00abc', left_pad00(b'abc', 6))

    def test_01_right_strip00(self):
        self.assertEqual(b'abc', right_strip00(b'abc'))
        self.assertEqual(b'abc', right_strip00(b'abc\x00'))
        self.assertEqual(b'abc', right_strip00(b'abc\x00\x00'))
        self.assertEqual(b'abc', right_strip00(b'abc\x00\x00\x00'))



    def test_01_pack_integer(self):
        """Test both _pack_big_integer and its less-efficient but more-universal variant, _pack_big_integer_Mike_Boers
        """
        def both_pack_methods(packed_bytes, number, nbytes):
            self.assertEqual(packed_bytes, pack_big_integer_via_hex(number,nbytes))
            self.assertEqual(packed_bytes, pack_integer(number,nbytes))

        both_pack_methods(                b'\x00', 0,1)
        both_pack_methods(    b'\x00\x00\x00\x00', 0,4)
        both_pack_methods(    b'\x00\x00\x00\x01', 1,4)
        both_pack_methods(    b'\x00\x00\x00\x64', 100,4)
        both_pack_methods(    b'\x00\x00\xFF\xFE', 65534,4)
        both_pack_methods(    b'\xFF\xFF\xFF\xFE', 4294967294,4)

        both_pack_methods(b'\x00\xFF\xFF\xFF\xFE', 4294967294,5)
        both_pack_methods(b'\x00\xFF\xFF\xFF\xFF', 4294967295,5)
        both_pack_methods(b'\x01\x00\x00\x00\x00', 4294967296,5)
        both_pack_methods(b'\x01\x00\x00\x00\x01', 4294967297,5)
        both_pack_methods(b'\x01\x00\x00\x00\x02', 4294967298,5)

        both_pack_methods(    b'\xFF\xFF\xFF\xFF', -1,4)
        both_pack_methods(b'\xFF\xFF\xFF\xFF\xFF', -1,5)

        both_pack_methods(b'\xFF\xFF\xFF\x00\x02', -65534,5)

        both_pack_methods(b'\xFF\x80\x00\x00\x01', -2147483647,5)
        both_pack_methods(b'\xFF\x80\x00\x00\x00', -2147483648,5)
        both_pack_methods(b'\xFF\x7F\xFF\xFF\xFF', -2147483649,5)
        both_pack_methods(b'\xFF\x7F\xFF\xFF\xFE', -2147483650,5)

        both_pack_methods(b'\xFF\x00\x00\x00\x01', -4294967295,5)
        both_pack_methods(b'\xFF\x00\x00\x00\x00', -4294967296,5)
        both_pack_methods(b'\xFE\xFF\xFF\xFF\xFF', -4294967297,5)
        both_pack_methods(b'\xFE\xFF\xFF\xFF\xFE', -4294967298,5)

    def test_01_pack_small_integer_not_enough_nbytes(self):
        """
        small int, enforces low nbytes, but doesn't matter for Number's purposes
        """
        self.assertEqual(b'\x11', pack_integer(0x1111,1))
        self.assertEqual(b'\x11\x11', pack_integer(0x1111,2))
        self.assertEqual(b'\x00\x11\x11', pack_integer(0x1111,3))
        self.assertEqual(b'\x00\x00\x11\x11', pack_integer(0x1111,4))
        self.assertEqual(b'\x00\x00\x00\x11\x11', pack_integer(0x1111,5))

    def test_01_pack_integer_not_enough_nbytes_negative(self):
        """
        small int, enforces low nbytes, but doesn't matter for Number's purposes
        """
        self.assertEqual(b'\xAB', pack_integer(-0x5555,1))
        self.assertEqual(b'\xAA\xAB', pack_integer(-0x5555,2))
        self.assertEqual(b'\xFF\xAA\xAB', pack_integer(-0x5555,3))
        self.assertEqual(b'\xFF\xFF\xAA\xAB', pack_integer(-0x5555,4))
        self.assertEqual(b'\xFF\xFF\xFF\xAA\xAB', pack_integer(-0x5555,5))

    def test_01_pack_big_integer_not_enough_nbytes(self):
        """
        big int, ignores low nbytes, but doesn't matter for Number's purposes
        """
        self.assertEqual(b'\x11\x11\x11\x11\x11', pack_integer(0x1111111111,4))
        self.assertEqual(b'\x11\x11\x11\x11\x11', pack_integer(0x1111111111,5))
        self.assertEqual(b'\x00\x11\x11\x11\x11\x11', pack_integer(0x1111111111,6))

    def test_01_pack_integer_auto_nbytes(self):
        self.assertEqual(b'\x01', pack_integer(0x01))
        self.assertEqual(b'\x04', pack_integer(0x04))
        self.assertEqual(b'\xFF', pack_integer(0xFF))
        self.assertEqual(b'\x01\x00', pack_integer(0x100))
        self.assertEqual(b'\x01\x01', pack_integer(0x101))
        self.assertEqual(b'\xFF\xFF', pack_integer(0xFFFF))
        self.assertEqual(b'\x01\x00\x00', pack_integer(0x10000))
        self.assertEqual(b'\x01\x00\x01', pack_integer(0x10001))

    def test_01_pack_integer_auto_nbytes_negative(self):
        self.assertEqual(b'\xFF', pack_integer(-0x01))
        self.assertEqual(b'\xFC', pack_integer(-0x04))
        self.assertEqual(b'\x01', pack_integer(-0xFF))  # an UNSIGNED negative number in two's complement
        self.assertEqual(b'\xFF\x01', pack_integer(-0xFF,2))  # (nbytes+=1 to get a sign bit)
        self.assertEqual(b'\xFF\x00', pack_integer(-0x100))
        self.assertEqual(b'\xFE\xFF', pack_integer(-0x101))
        self.assertEqual(b'\x00\x01', pack_integer(-0xFFFF))
        self.assertEqual(b'\xFF\x00\x00', pack_integer(-0x10000))
        self.assertEqual(b'\xFE\xFF\xFF', pack_integer(-0x10001))

    def test_01_unpack_big_integer(self):
        self.assertEqual(0, unpack_big_integer(b''))
        self.assertEqual(0x1234, unpack_big_integer(b'\x12\x34'))
        self.assertEqual( 0x807F99DEADBEEF00, unpack_big_integer(    b'\x80\x7F\x99\xDE\xAD\xBE\xEF\x00'))
        self.assertEqual( 0xFFFFFFFFFFFFFF77, unpack_big_integer(    b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x77'))
        self.assertEqual( 0xFFFFFFFFFFFFFFFE, unpack_big_integer(    b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE'))
        self.assertEqual( 0xFFFFFFFFFFFFFFFF, unpack_big_integer(    b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'))
        self.assertEqual(0x10000000000000000, unpack_big_integer(b'\x01\x00\x00\x00\x00\x00\x00\x00\x00'))
        self.assertEqual(0x10000000000000001, unpack_big_integer(b'\x01\x00\x00\x00\x00\x00\x00\x00\x01'))
        self.assertEqual(0x10000000000000022, unpack_big_integer(b'\x01\x00\x00\x00\x00\x00\x00\x00\x22'))
        self.assertEqual(0x807F99DEADBEEF00BADEFACE00, unpack_big_integer(
                                                 b'\x80\x7F\x99\xDE\xAD\xBE\xEF\x00\xBA\xDE\xFA\xCE\x00'))

    def test_01_unpack_big_integer_by_brute(self):
        self.assertEqual(0, unpack_big_integer_by_brute(b''))
        self.assertEqual(0x1234, unpack_big_integer_by_brute(b'\x12\x34'))
        self.assertEqual(0x807F99DEADBEEF00BADEFACE00, unpack_big_integer_by_brute(
            b'\x80\x7F\x99\xDE\xAD\xBE\xEF\x00\xBA\xDE\xFA\xCE\x00'
        ))

    def test_01_unpack_big_integer_by_struct(self):
        self.assertEqual(0, unpack_big_integer_by_struct(b''))
        self.assertEqual(0x00, unpack_big_integer_by_struct(b'\x00'))
        self.assertEqual(0x1234, unpack_big_integer_by_struct(b'\x12\x34'))
        self.assertEqual(0xFFFFFFFFFFFFFFFE, unpack_big_integer_by_struct(b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE'))
        self.assertEqual(0xFFFFFFFFFFFFFFFF, unpack_big_integer_by_struct(b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'))
        with self.assertRaises(Exception):
            unpack_big_integer_by_struct(b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF')
        with self.assertRaises(Exception):
            unpack_big_integer_by_struct(b'ninebytes')



    def test_02_type_name(self):
        self.assertEqual(     'int',             type_name(3))
        self.assertEqual(py23('unicode', 'str'), type_name(u'string'))
        self.assertEqual(     'complex',         type_name(3+33j))

        # noinspection PyClassHasNoInit
        class OldStyleClass:
            pass

        class NewStyleClass(object):
            pass

        old_style_instance = OldStyleClass()
        new_style_instance = NewStyleClass()
        self.assertEqual('OldStyleClass', type_name(old_style_instance))
        self.assertEqual('NewStyleClass', type_name(new_style_instance))
        self.assertEqual(py23('classobj', 'type'), type_name(OldStyleClass))
        self.assertEqual('type', type_name(NewStyleClass))

        # noinspection PyClassHasNoInit,PyPep8Naming
        class instance:
            pass
        instance_instance = instance()
        self.assertEqual('instance', type_name(instance_instance))

        # noinspection PyPep8Naming
        class instance(object):
            pass
        instance_instance = instance()
        self.assertEqual('instance', type_name(instance_instance))

    def test_02_type_name_oops(self):

        class SomeOtherClass(object):
            pass
        # noinspection PyPep8Naming

        class instance(object):
            __class__ = SomeOtherClass

        instance_instance = instance()
        self.assertEqual('SomeOtherClass', type_name(instance_instance))


class PythonTests(NumberTests):
    """
    Testing internal Python features.

    Checking assumptions about Python itself.
    """

    def test_00_python_float_equality_weirdness(self):
        self.assertEqual(+0.0, -0.0)
        self.assertNotEqual(float('nan'), float('nan'))

    def test_00_python_ldexp(self):
        """ldexp() does more than invert frexp() -- it doesn't require a normalized mantissa"""
        self.assertEqual(   1.0, math.ldexp(   .5, 1))
        self.assertEqual(  -1.0, math.ldexp(  -.5, 1))
        self.assertEqual(   3.0, math.ldexp(  .75, 2))
        self.assertEqual( 100.0, math.ldexp(   25, 2))
        self.assertEqual( 625.0, math.ldexp( 2500, -2))
        self.assertEqual(-625.0, math.ldexp(-2500, -2))

    def test_00_python_int_floors_toward_zero(self):
        self.assertEqual(2, int(Number(2.0)))
        self.assertEqual(2, int(Number(2.000001)))
        self.assertEqual(2, int(Number(2.1)))
        self.assertEqual(2, int(Number(2.9)))
        self.assertEqual(2, int(Number(2.999999)))
        self.assertEqual(3, int(Number(3.0)))

        self.assertEqual(-2, int(Number(-2.0)))
        self.assertEqual(-2, int(Number(-2.000001)))
        self.assertEqual(-2, int(Number(-2.1)))
        self.assertEqual(-2, int(Number(-2.9)))
        self.assertEqual(-2, int(Number(-2.999999)))
        self.assertEqual(-3, int(Number(-3.0)))

    def test_00_python_weird_big_math(self):
        self.assertEqual((1 << 1000),          1.0715086071862673e+301)   # What does this?  Python math?  optimization?  assert comparison?  assert message?  Windows-only??
        self.assertEqual((1 << 1000)-1,         10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375)
        self.assertEqual(     pow(2,1000),     1.0715086071862673e+301)
        self.assertEqual(math.pow(2,1000),     1.0715086071862673e+301)
        self.assertEqual(     pow(2,1000)-1,    10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375)
        self.assertEqual(math.pow(2,1000)-1,   1.0715086071862673e+301)
        self.assertTrue (     pow(2,1000)-1 ==  10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375)
        self.assertTrue (math.pow(2,1000)-1 == 1.0715086071862673e+301)

    def test_00_python_binary_shift_negative_left(self):
        self.assertEqual( -2, -2 << 0)
        self.assertEqual( -4, -2 << 1)
        self.assertEqual( -8, -2 << 2)
        self.assertEqual(-16, -2 << 3)
        self.assertEqual(-32, -2 << 4)
        self.assertEqual(-64, -2 << 5)

        self.assertEqual(-1, -1 << 0)
        self.assertEqual(-2, -1 << 1)
        self.assertEqual(-4, -1 << 2)
        self.assertEqual(-8, -1 << 3)

        self.assertEqual(-1267650600228229401496703205376, -1 << 100)

    def test_00_python_binary_shift_negative_right(self):
        self.assertEqual(-1, -1 >> 0)
        self.assertEqual(-1, -1 >> 1)
        self.assertEqual(-1, -1 >> 2)
        self.assertEqual(-1, -1 >> 3)

        self.assertEqual(-16, -16 >> 0)
        self.assertEqual( -8, -16 >> 1)
        self.assertEqual( -4, -16 >> 2)
        self.assertEqual( -2, -16 >> 3)
        self.assertEqual( -1, -16 >> 4)
        self.assertEqual( -1, -16 >> 5)
        self.assertEqual( -1, -16 >> 6)
        self.assertEqual( -1, -16 >> 7)

        self.assertEqual(-2, -65536 >> 15)
        self.assertEqual(-1, -65536 >> 16)
        self.assertEqual(-1, -65536 >> 17)

        self.assertEqual(-2, -16777216 >> 23)
        self.assertEqual(-1, -16777216 >> 24)
        self.assertEqual(-1, -16777216 >> 25)

        self.assertEqual(-2, -4294967296 >> 31)
        self.assertEqual(-1, -4294967296 >> 32)
        self.assertEqual(-1, -4294967296 >> 33)

        self.assertEqual(-2, -1267650600228229401496703205376 >> 99)
        self.assertEqual(-1, -1267650600228229401496703205376 >> 100)
        self.assertEqual(-1, -1267650600228229401496703205376 >> 101)

    def test_00_python_binary_shift_left(self):
        self.assertEqual(256, 1 << 8)
        self.assertEqual(256*256, 1 << 8*2)
        self.assertEqual(256*256*256, 1 << 8*3)
        self.assertEqual(256*256*256*256, 1 << 8*4)
        self.assertEqual(256*256*256*256*256, 1 << 8*5)
        self.assertEqual(256*256*256*256*256*256, 1 << 8*6)
        self.assertEqual(        281474976710656, 1 << 8*6)
        self.assertEqual(256*256*256*256*256*256*256*256*256*256*256*256*256*256*256*256*256*256*256*256, 1 << 8*20)
        self.assertEqual(                              1461501637330902918203684832716283019655932542976, 1 << 8*20)

    def test_00_python_binary_string_comparison(self):
        self.assertTrue(b'\x81' < b'\x82')
        self.assertTrue(b'\x80' < b'\x81')
        self.assertTrue(b'\x7F' < b'\x80')
        self.assertTrue(b'\x7E' < b'\x7F')

        self.assertFalse(b'\x80' < b'\x80')
        self.assertFalse(b'\x7F' < b'\x7F')
        self.assertFalse(b'\x82' < b'\x82')
        self.assertTrue( b'\x82' < b'\x82\x00')
        self.assertFalse(b'\x82\x00' < b'\x82')

        self.assertTrue( b'\x00' == b'\x00')
        self.assertFalse(b'\x00' <  b'\x00')

        self.assertFalse(b'\x00' == b'\x00\x00')
        self.assertTrue( b'\x00' <  b'\x00\x00')

        self.assertFalse(b'\x00' == b'\x00\x01')
        self.assertTrue( b'\x00' <  b'\x00\x01')

        self.assertFalse(b'\x00' == b'\x00\xFF')
        self.assertTrue( b'\x00' <  b'\x00\xFF')

        self.assertTrue( b'\x00\x41' == b'\x00\x41')
        self.assertFalse(b'\x00\x41' <  b'\x00\x41')

        self.assertFalse(b'\x00\x41' == b'\x00\x42')
        self.assertTrue( b'\x00\x41' <  b'\x00\x42')

        self.assertTrue(b'\x82' == b'\x82')
        self.assertTrue(b'\x81' == b'\x81')
        self.assertTrue(b'\x80' == b'\x80')
        self.assertTrue(b'\x7F' == b'\x7F')

        self.assertFalse(b'' == b'\x00')   # Unlike C-language
        self.assertFalse(b'' == b'\x80')
        self.assertFalse(b'\x80' == b'\x81')
        self.assertFalse(b'\x82' == b'\x82\x00')

    def test_02_big_int_unittest_equality(self):
        """Do Python integers and assertEqual handle googol with finesse?

        See also test_unittest_equality()."""
        googol        = int('100000000000000000000000000000000000000000000000000'
                             '00000000000000000000000000000000000000000000000000')
        googol_plus_1 = int('100000000000000000000000000000000000000000000000000'
                             '00000000000000000000000000000000000000000000000001')
        self.assertEqual   (googol       , googol)
        self.assertNotEqual(googol       , googol_plus_1)
        self.assertNotEqual(googol_plus_1, googol)
        self.assertEqual   (googol_plus_1, googol_plus_1)

    def test_02_big_int_op_equality(self):
        """Do Python integers and the == operator handle googol with finesse?

        See also test_op_equality()."""
        googol        = int('100000000000000000000000000000000000000000000000000'
                             '00000000000000000000000000000000000000000000000000')
        googol_plus_1 = int('100000000000000000000000000000000000000000000000000'
                             '00000000000000000000000000000000000000000000000001')
        self.assertTrue (googol        == googol)
        self.assertFalse(googol        == googol_plus_1)
        self.assertFalse(googol_plus_1 == googol)
        self.assertTrue (googol_plus_1 == googol_plus_1)

    def test_03_nan_comparisons(self):
        self.assertFalse(float('nan') <  float('nan'))
        self.assertFalse(float('nan') <= float('nan'))
        self.assertFalse(float('nan') == float('nan'))
        self.assertTrue (float('nan') != float('nan'))
        self.assertFalse(float('nan') >  float('nan'))
        self.assertFalse(float('nan') >= float('nan'))

        self.assertIsNot(float('nan'), float('nan'))
        self.assertIsInstance(float('nan'), float)

    def test_04_numbers(self):
        an_int = int()
        a_float = float()
        a_complex = complex()

        self.assertIsInstance(an_int, numbers.Number)
        self.assertIsInstance(an_int, numbers.Complex)
        self.assertIsInstance(an_int, numbers.Real)
        self.assertIsInstance(an_int, numbers.Rational)
        self.assertIsInstance(an_int, numbers.Integral)

        self.assertIsInstance(a_float, numbers.Number)
        self.assertIsInstance(a_float, numbers.Complex)
        self.assertIsInstance(a_float, numbers.Real)
        self.assertNotIsInstance(a_float, numbers.Rational)
        self.assertNotIsInstance(a_float, numbers.Integral)

        self.assertIsInstance(a_complex, numbers.Number)
        self.assertIsInstance(a_complex, numbers.Complex)
        self.assertNotIsInstance(a_complex, numbers.Real)
        self.assertNotIsInstance(a_complex, numbers.Rational)
        self.assertNotIsInstance(a_complex, numbers.Integral)


def py23(if2, if3_or_greater):
    """
    Python-2-specific value.  Versus Python-3-or-later-specific value.

    Sensibly returns a value that stands a reasonable chance of not breaking on Python 4,
    if there ever is such a thing.  That is, assumes Python 4 will be more like 3 than 2.
    SEE:  http://astrofrog.github.io/blog/2016/01/12/stop-writing-python-4-incompatible-code/
    """
    if six.PY2:
        return if2
    else:
        return if3_or_greater


if __name__ == '__main__':
    import unittest
    unittest.main()


# TODO:  Why does this appear sometimes after OK:
#        ##teamcity[testSuiteFinished timestamp='2018-07-11T19:44:11.171'
#        locationHint='python<D:\PyCharmProjects\qiki-python>://test_number'
#        name='test_number' nodeId='1' parentNodeId='0']
