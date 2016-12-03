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
import textwrap
import unittest

from number import *


# Slow tests:
TEST_INC_ON_ALL_POWERS_OF_TWO = False   # E.g. 0q86_01.inc() == 0q86_010000000001 (12 seconds on slow laptops)


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
            self.fail("Left extras:\n\t%s\nRight extras:\n\t%s\n" % (
                '\n\t'.join((Number.name_of_zone[z] for z in (s1-s2))),
                '\n\t'.join((Number.name_of_zone[z] for z in (s2-s1))),
            ))

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


# TODO:  Why does PyCharm warn Number.ZERO "Unresolved attribute reference 'ZERO' for class 'Number'"?
# noinspection SpellCheckingInspection,PyUnresolvedReferences
class NumberBasicTests(NumberTests):

    def test_raw(self):
        n = Number('0q82')
        self.assertEqual(b'\x82', n.raw)

    def test_raw_from_unicode(self):
        n = Number(u'0q82')
        self.assertEqual(b'\x82', n.raw)

    def test_raw_from_byte_string(self):
        self.assertEqual(Number(1), Number(u'0q82'))
        if six.PY2:
            # THANKS:  http://astrofrog.github.io/blog/2016/01/12/stop-writing-python-4-incompatible-code/
            self.assertEqual(Number(u'0q82'), Number(b'0q82'))
            self.assertEqual(       u'0q82',         b'0q82')
        else:
            self.assertNotEqual(    u'0q82',         b'0q82')
            with self.assertRaises(TypeError):
                Number(b'0q82')

    def test_unsupported_type(self):
        class SomeType(object):
            pass
        with self.assertRaises(TypeError):
            Number(SomeType)
        with self.assertRaises(Number.ConstructorTypeError):
            Number(SomeType)

    def test_hex(self):
        n = Number('0q82')
        self.assertEqual('82', n.hex())

    def test_str(self):
        n = Number('0q83_03E8')
        self.assertEqual("0q83_03E8", str(n))
        self.assertEqual('str', type(str(n)).__name__)

    def test_unicode(self):
        n = Number('0q83_03E8')
        if six.PY2:
            # noinspection PyCompatibility
            self.assertEqual('0q83_03E8', unicode(n))
            # noinspection PyCompatibility
            self.assertEqual('unicode', type(unicode(n)).__name__)
        else:
            with self.assertRaises(NameError):
                # noinspection PyCompatibility
                unicode(n)

    def test_unicode_output(self):
        n = Number('0q83_03E8')
        self.assertEqual(u"0q83_03E8", six.text_type(n))
        self.assertIsInstance(six.text_type(n), six.text_type)

    def test_unicode_input(self):
        n = Number(u'0q83_03E8')
        self.assertEqual("0q83_03E8", str(n))
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
        self.assertFloatSame(+0.0, float(Number('0q81')))
        self.assertFloatSame(-0.0, float(Number('0q7EFF')))

    def test_from_qstring(self):
        n = Number.from_qstring('0q82')
        self.assertEqual('0q82', n.qstring())
        with self.assertRaises(Number.ConstructorValueError):
            Number.from_qstring('qqqqq')

    def test_from_bytearray(self):
        self.assertEqual(Number('0q82_2A'), Number.from_bytearray(bytearray(b'\x82\x2A')))

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
        self.assertEqual("x'822A'", Number('0q82_2A').mysql())

    # TODO: test from_mysql and to_mysql using SELECT and @-variables -- maybe in test_word.py because it already has a db connection.

    # Blob literal surtaxes:
    # ----------------------
    # mysql: x'822A' or 0x822A
    # mssql: 0x822A
    # sqlite or DB2: x'822A'
    # postgre: E'\x82\x2A'
    # c or java or javascript: "\x82\x2A"

    def test_repr(self):
        n =               Number('0q83_03E8')
        self.assertEqual("Number('0q83_03E8')", repr(n))

    def test_zero(self):
        self.assertEqual('0q80', str(Number.ZERO))
        self.assertEqual(0, int(Number.ZERO))
        self.assertEqual(0.0, float(Number.ZERO))

    # yes_inspection PyUnresolvedReferences
    def test_nan(self):
        self.assertEqual('0q', str(Number.NAN))
        self.assertEqual(b'', Number.NAN.raw)
        self.assertEqual('', Number.NAN.hex())
        self.assertEqual('nan', str(float(Number.NAN)))
        self.assertFloatSame(float('nan'), float(Number.NAN))

    def test_nan_default(self):
        self.assertEqual('0q', Number().qstring())

    # yes_inspection PyUnresolvedReferences
    def test_nan_equality(self):
        # TODO:  Is this right?  Number.NAN comparisons behave like any other number, not like float('nan')?
        # SEE:  http://stackoverflow.com/questions/1565164/what-is-the-rationale-for-all-comparisons-returning-false-for-ieee754-nan-values
        # TODO:  Any comparisons with NAN raise Number.Incomparable("...use is_nan() instead...").
        nan = Number.NAN
        self.assertEqual(nan, Number.NAN)
        self.assertEqual(nan, Number(None))
        self.assertEqual(nan, Number('0q'))
        self.assertEqual(nan, Number(float('nan')))
        self.assertEqual(nan, float('nan'))

    # yes_inspection PyUnresolvedReferences
    def test_nan_inequality(self):
        nan = Number.NAN
        self.assertNotEqual(nan, Number(0))
        self.assertNotEqual(nan, 0)
        self.assertNotEqual(nan, float('inf'))

    # # noinspection PyUnresolvedReferences
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

    def test_qantissa_positive(self):
        self.assertEqual((0x03E8,2), Number('0q83_03E8').qantissa())
        self.assertEqual((0x03E8,2), Number('0q83_03E8').qantissa())
        self.assertEqual((0x0101,2), Number('0q83_0101').qantissa())
        self.assertEqual((  0x01,1), Number('0q83_01').qantissa())
        self.assertEqual((  0x00,0), Number('0q83').qantissa())
        self.assertEqual((  0xFF,1), Number('0q82_FF').qantissa())
        self.assertEqual((  0xFA,1), Number('0q7D_FA').qantissa())

    def test_qantissa_negative(self):
        self.assertEqual((0xFE,1), Number('0q7D_FE').qantissa())
        self.assertEqual((0x01,1), Number('0q7D_01').qantissa())
        self.assertEqual((0xFEFFFFFA,4), Number('0q7A_FEFFFFFA').qantissa())
        self.assertEqual((0x00000001,4), Number('0q7A_00000001').qantissa())

    def test_qantissa_fractional(self):
        self.assertEqual(  (0x80,1), Number('0q81FF_80').qantissa())
        self.assertEqual(  (0x40,1), Number('0q81FF_40').qantissa())
        self.assertEqual((0x4220,2), Number('0q81FF_4220').qantissa())

    def test_qantissa_fractional_neg(self):
        self.assertEqual(  (0x01,1), Number('0q7E00_01').qantissa())
        self.assertEqual(  (0x80,1), Number('0q7E00_80').qantissa())
        self.assertEqual(  (0xC0,1), Number('0q7E00_C0').qantissa())
        self.assertEqual(  (0xFF,1), Number('0q7E00_FF').qantissa())
        self.assertEqual(  (0xFF,1), Number('0q7E01_FF').qantissa())
        self.assertEqual((0xFF80,2), Number('0q7E01_FF80').qantissa())

    def test_qantissa_unsupported(self):
        number_has_no_qantissa = Number(0)
        with self.assertRaises(Number.QanValueError):
            number_has_no_qantissa.qantissa()

    def test_qexponent_unsupported(self):
        number_has_no_qexponent = Number(0)
        with self.assertRaises(Number.QexValueError):
            number_has_no_qexponent.qexponent()

    def test_qexponent_positive(self):
        self.assertEqual(1, Number('0q82_01000001').qexponent())
        self.assertEqual(1, Number('0q82_02').qexponent())
        self.assertEqual(1, Number('0q82_FF').qexponent())
        self.assertEqual(2, Number('0q83_01').qexponent())
        self.assertEqual(3, Number('0q84_01').qexponent())
        self.assertEqual(4, Number('0q85_01').qexponent())
        self.assertEqual(5, Number('0q86_01').qexponent())
        self.assertEqual(6, Number('0q87_01').qexponent())
        self.assertEqual(124, Number('0qFD_01').qexponent())
        self.assertEqual(125, Number('0qFE_01').qexponent())

    def test_qexponent_negative(self):
        self.assertEqual(6, Number('0q78').qexponent())
        self.assertEqual(5, Number('0q79').qexponent())
        self.assertEqual(4, Number('0q7A').qexponent())
        self.assertEqual(3, Number('0q7B').qexponent())
        self.assertEqual(2, Number('0q7C').qexponent())
        self.assertEqual(1, Number('0q7D').qexponent())

        self.assertEqual(125, Number('0q01').qexponent())
        self.assertEqual(124, Number('0q02').qexponent())

    def test_qexponent_fractional(self):
        self.assertEqual(   0, Number('0q81FF_80').qexponent())
        self.assertEqual(   0, Number('0q81FF_01').qexponent())
        self.assertEqual(  -1, Number('0q81FE_01').qexponent())
        self.assertEqual(  -2, Number('0q81FD_01').qexponent())
        self.assertEqual(-123, Number('0q8184_01').qexponent())
        self.assertEqual(-124, Number('0q8183_01').qexponent())

    def test_qexponent_fractional_neg(self):
        self.assertEqual(   0, Number('0q7E00_01').qexponent())   # -.996
        self.assertEqual(   0, Number('0q7E00_80').qexponent())   # -.5
        self.assertEqual(   0, Number('0q7E00_FF').qexponent())   # -.004
        self.assertEqual(  -1, Number('0q7E01_FF').qexponent())
        self.assertEqual(  -2, Number('0q7E02_FF').qexponent())
        self.assertEqual(-123, Number('0q7E7B_FF').qexponent())
        self.assertEqual(-124, Number('0q7E7C_FF').qexponent())

    def test_alias_one(self):
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

    def test_integers_and_q_strings(self):

        def i__s(i, s):   # why a buncha calls to i__s() is superior to a 2D tuple:  so the stack trace identifies the line with the failing data
            assert isinstance(i, six.integer_types)
            assert isinstance(s, six.string_types)
            i_new = int(Number(s))
            s_new = str(Number(i))
            self.assertEqual(s_new, s,       "%d ---Number--> '%s' != '%s'" % (i,       s_new, s))
            self.assertEqual(i, i_new, "%d != %d <--Number--- '%s'" %         (i, i_new,       s))

            out_of_sequence=[]
            if not context.the_first:
                integers_oos =        i      >        context.i_last
                strings_oos  = Number(s).raw > Number(context.s_last).raw
                if integers_oos:
                    out_of_sequence.append(
                        "Integers out of sequence: {i_below:d} should be less than {i_above:d}".format(
                            i_below=i,
                            i_above=context.i_last
                        )
                    )
                if strings_oos:
                    out_of_sequence.append(
                        "Q-strings out of sequence: {s_below} should be less than {s_above}".format(
                            s_below=s,
                            s_above=context.s_last
                        )
                    )
                if out_of_sequence:
                    self.fail("\n".join(out_of_sequence))

            context.i_last = i
            context.s_last = s
            context.the_first = False

        # noinspection PyClassHasNoInit,PyPep8Naming
        class context:   # variables that are local to test_ints_and_strings(), but global to i__s()
            the_first = True

        # i__s(  2**65536,         '0qFF00FFFF00010000_01')   # TODO:  Ludicrous Numbers.
        # i__s(  2**65535,         '0qFF00FFFF_01')
        # i__s(256**128,           '0qFF000080_01')
        # i__s(  2**1024,          '0qFF000080_01')
        # i__s(  2**1000,          '0qFF00007D_01')   # XXX:  Or 0qFF00007E_01?  Because radix point is all the way left, i.e. qan is fractional
        i__s(   2**1000-1,'0qFE_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__s(   10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375,
                          '0qFE_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__s(   2**1000-2,'0qFE_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFE')
        i__s(   2**999+1, '0qFE_8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(   2**999,   '0qFE_80')
        i__s(   2**999-1, '0qFE_7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__s(   2**998+1, '0qFE_4000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(   2**998,   '0qFE_40')
        i__s(   2**998-1, '0qFE_3FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__s(  10**300+1, '0qFE_17E43C8800759BA59C08E14C7CD7AAD86A4A458109F91C21C571DBE84D52D936F44ABE8A3D5B48C100959D9D0B6CC856B3ADC93B67AEA8F8E067D2C8D04BC177F7B4287A6E3FCDA36FA3B3342EAEB442E15D450952F4DD1000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(  10**300,   '0qFE_17E43C8800759BA59C08E14C7CD7AAD86A4A458109F91C21C571DBE84D52D936F44ABE8A3D5B48C100959D9D0B6CC856B3ADC93B67AEA8F8E067D2C8D04BC177F7B4287A6E3FCDA36FA3B3342EAEB442E15D450952F4DD10')   # Here googol cubed has 37 stripped 00-qigits, or 296 bits.
        i__s(  10**300-1, '0qFE_17E43C8800759BA59C08E14C7CD7AAD86A4A458109F91C21C571DBE84D52D936F44ABE8A3D5B48C100959D9D0B6CC856B3ADC93B67AEA8F8E067D2C8D04BC177F7B4287A6E3FCDA36FA3B3342EAEB442E15D450952F4DD0FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__s( 256**124,   '0qFE_01')
        i__s(   2**992,   '0qFE_01')
        i__s(41855804968213567224547853478906320725054875457247406540771499545716837934567817284890561672488119458109166910841919797858872862722356017328064756151166307827869405370407152286801072676024887272960758524035337792904616958075776435777990406039363527010043736240963055342423554029893064011082834640896,
                          '0qFE_01')
        i__s( 256**123,   '0qFD_01')
        i__s(   2**984,   '0qFD_01')
        i__s(   2**504,   '0qC1_01')
        i__s(   2**503,   '0qC0_80')
        i__s(   2**500,   '0qC0_10')
        i__s(   2**496,   '0qC0_01')
        i__s(  10**100+1, '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10000000000000000000000001')   # googol + 1  (integers can distinguish these)
        i__s(  10**100,   '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10')                           # googol
        i__s(  10**100-1, '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F0FFFFFFFFFFFFFFFFFFFFFFFFF')   # googol - 1
        i__s(1766847064778384329583297500742918515827483896875618958121606201292619777,'0qA0_01000000000000000000000000000000000000000000000000000000000001')
        i__s(1766847064778384329583297500742918515827483896875618958121606201292619776,'0qA0_01')
        i__s(5192296858534827628530496329220096,'0q90_01')
        i__s(20282409603651670423947251286016,'0q8F_01')
        i__s(10000000000000000000000001,'0q8C_084595161401484A000001')
        i__s(10000000000000000000000000,'0q8C_084595161401484A')
        i__s(18446744073709551618,'0q8A_010000000000000002')
        i__s(18446744073709551617,'0q8A_010000000000000001')
        i__s(18446744073709551616,'0q8A_01')
        i__s(18446744073709551615,'0q89_FFFFFFFFFFFFFFFF')
        i__s(18446744073709551614,'0q89_FFFFFFFFFFFFFFFE')
        i__s(72057594037927936,'0q89_01')
        i__s(281474976710656,'0q88_01')
        i__s(1099511627776,'0q87_01')
        i__s(68719476736, '0q86_10')
        i__s(68719476735, '0q86_0FFFFFFFFF')
        i__s(10000000001, '0q86_02540BE401')
        i__s(10000000000, '0q86_02540BE4')
        i__s( 4294967299, '0q86_0100000003')
        i__s( 4294967298, '0q86_0100000002')
        i__s( 4294967297, '0q86_0100000001')
        i__s( 4294967296, '0q86_01')
        i__s( 4294967295, '0q85_FFFFFFFF')
        i__s( 2147483649, '0q85_80000001')
        i__s( 2147483648, '0q85_80')
        i__s( 2147483647, '0q85_7FFFFFFF')
        i__s(  268435457, '0q85_10000001')
        i__s(  268435456, '0q85_10')
        i__s(  268435455, '0q85_0FFFFFFF')
        i__s(   16777217, '0q85_01000001')
        i__s(   16777216, '0q85_01')
        i__s(   16777215, '0q84_FFFFFF')
        i__s(    1048577, '0q84_100001')
        i__s(    1048576, '0q84_10')
        i__s(    1048575, '0q84_0FFFFF')
        i__s(      65538, '0q84_010002')
        i__s(      65537, '0q84_010001')
        i__s(      65536, '0q84_01')
        i__s(      65535, '0q83_FFFF')
        i__s(       4097, '0q83_1001')
        i__s(       4096, '0q83_10')
        i__s(       4095, '0q83_0FFF')
        i__s(       1729, '0q83_06C1')
        i__s(        257, '0q83_0101')
        i__s(        256, '0q83_01')
        i__s(        255, '0q82_FF')
        i__s(          3, '0q82_03')
        i__s(          2, '0q82_02')
        i__s(          1, '0q82_01')
        i__s(          0, '0q80')
        i__s(         -1, '0q7D_FF')
        i__s(         -2, '0q7D_FE')
        i__s(         -3, '0q7D_FD')
        i__s(         -4, '0q7D_FC')
        i__s(         -8, '0q7D_F8')
        i__s(        -16, '0q7D_F0')
        i__s(        -32, '0q7D_E0')
        i__s(        -64, '0q7D_C0')
        i__s(       -128, '0q7D_80')
        i__s(       -252, '0q7D_04')
        i__s(       -253, '0q7D_03')
        i__s(       -254, '0q7D_02')
        i__s(       -255, '0q7D_01')
        i__s(       -256, '0q7C_FF')
        i__s(       -257, '0q7C_FEFF')
        i__s(       -258, '0q7C_FEFE')
        i__s(       -259, '0q7C_FEFD')
        i__s(       -260, '0q7C_FEFC')
        i__s(       -511, '0q7C_FE01')
        i__s(       -512, '0q7C_FE')
        i__s(       -513, '0q7C_FDFF')
        i__s(      -1023, '0q7C_FC01')
        i__s(      -1024, '0q7C_FC')
        i__s(      -1025, '0q7C_FBFF')
        i__s(     -65534, '0q7C_0002')
        i__s(     -65535, '0q7C_0001')
        i__s(     -65536, '0q7B_FF')
        i__s(     -65537, '0q7B_FEFFFF')
        i__s(     -65538, '0q7B_FEFFFE')
        i__s(  -16777214, '0q7B_000002')
        i__s(  -16777215, '0q7B_000001')
        i__s(  -16777216, '0q7A_FF')
        i__s(  -16777217, '0q7A_FEFFFFFF')
        i__s(  -16777218, '0q7A_FEFFFFFE')
        i__s(-2147483647, '0q7A_80000001')
        i__s(-2147483648, '0q7A_80')
        i__s(-2147483649, '0q7A_7FFFFFFF')
        i__s(-4294967294, '0q7A_00000002')
        i__s(-4294967295, '0q7A_00000001')
        i__s(-4294967296, '0q79_FF')
        i__s(-4294967297, '0q79_FEFFFFFFFF')
        i__s(-4294967298, '0q79_FEFFFFFFFE')
        i__s(  -2**125,   '0q6E_E0')
        i__s(  -2**250,   '0q5E_FC')
        i__s(  -2**375,   '0q4F_80')
        i__s(  -204586912993508866875824356051724947013540127877691549342705710506008362275292159680204380770369009821930417757972504438076078534117837065833032974336,
                          '0q3F_FF')
        i__s(  -2**496,   '0q3F_FF')
        i__s(  -3273390607896141870013189696827599152216642046043064789483291368096133796404674554883270092325904157150886684127560071009217256545885393053328527589376,
                          '0q3F_F0')
        i__s(  -2**500,   '0q3F_F0')
        i__s(  -2**625,   '0q2F_FE')
        i__s(  -2**750,   '0q20_C0')
        i__s(  -2**875,   '0q10_F8')
        i__s(  -5357543035931336604742125245300009052807024058527668037218751941851755255624680612465991894078479290637973364587765734125935726428461570217992288787349287401967283887412115492710537302531185570938977091076523237491790970633699383779582771973038531457285598238843271083830214915826312193418602834034687,
                          '0q01_8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(  -2**999+1, '0q01_8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(  -5357543035931336604742125245300009052807024058527668037218751941851755255624680612465991894078479290637973364587765734125935726428461570217992288787349287401967283887412115492710537302531185570938977091076523237491790970633699383779582771973038531457285598238843271083830214915826312193418602834034688,
                          '0q01_80')
        i__s(  -2**999,   '0q01_80')
        i__s(int('-1071508607186267320948425049060001810561404811705533607443750388370351051124936122493198378815695858'
                 '12759467291755314682518714528569231404359845775746985748039345677748242309854210746050623711418779541'
                 '82153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375'
                 ),       '0q01_000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
                          '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
                          '00000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(  -2**1000+1,'0q01_000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
                          '00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'
                          '00000000000000000000000000000000000000000000000000000000000000000000001')

    def test_integer_nan(self):
        nan = Number(float('nan'))
        with self.assertRaises(ValueError):
            int(nan)

    def test_integer_infinity(self):
        positive_infinity = Number(float('+inf'))
        with self.assertRaises(OverflowError):
            int(positive_infinity)
        negative_infinity = Number(float('-inf'))
        with self.assertRaises(OverflowError):
            int(negative_infinity)

    def test_integer_infinitesimal(self):
        self.assertEqual(0, int(Number('0q807F')))
        self.assertEqual(0, int(Number('0q80')))
        self.assertEqual(0, int(Number('0q7F81')))
        self.assertEqual('0q80', Number(0).qstring())

    def test_sets_exclusive(self):
        self.assertTrue (sets_exclusive({1,2,3}, {4,5,6}))
        self.assertFalse(sets_exclusive({1,2,3}, {3,5,6}))
        self.assertTrue (sets_exclusive({1,2,3}, {4,5,6}, {7,8,9}))
        self.assertFalse(sets_exclusive({1,2,3}, {4,5,6}, {7,8,1}))

    def test_zone_union(self):
        self.assertEqual({1,2,3,4,5,6}, union_of_distinct_sets({1,2,3}, {4,5,6}))
        if not sys.flags.optimize:
            with self.assertRaises(AssertionError):
                union_of_distinct_sets({1,2,3}, {3,4,5})

    # noinspection PyUnresolvedReferences
    def test_zone_sets(self):
        self.assertEqualSets(Number.ZONE_ALL, Number._ZONE_ALL_BY_FINITENESS)
        self.assertEqualSets(Number.ZONE_ALL, Number._ZONE_ALL_BY_REASONABLENESS)
        self.assertEqualSets(Number.ZONE_ALL, Number._ZONE_ALL_BY_ZERONESS)
        self.assertEqualSets(Number.ZONE_ALL, Number._ZONE_ALL_BY_BIGNESS)
        self.assertEqualSets(Number.ZONE_ALL, Number._ZONE_ALL_BY_WHOLENESS)

    def test_zone(self):
        self.assertEqual(Number.Zone.TRANSFINITE,         Number('0qFF81').zone)
        self.assertEqual(Number.Zone.LUDICROUS_LARGE,     Number('0qFF00FFFF_5F5E00FF').zone)
        self.assertEqual(Number.Zone.POSITIVE,            Number('0q82_2A').zone)
        self.assertEqual(Number.Zone.POSITIVE,            Number('0q82_01').zone)
        self.assertEqual(Number.Zone.POSITIVE,            Number('0q82').zone)
        self.assertEqual(Number.Zone.FRACTIONAL,          Number('0q81FF_80').zone)
        self.assertEqual(Number.Zone.LUDICROUS_SMALL,     Number('0q80FF0000_FA0A1F01').zone)
        self.assertEqual(Number.Zone.INFINITESIMAL,       Number('0q807F').zone)
        self.assertEqual(Number.Zone.ZERO,                Number('0q80').zone)
        self.assertEqual(Number.Zone.INFINITESIMAL_NEG,   Number('0q7F81').zone)
        self.assertEqual(Number.Zone.LUDICROUS_SMALL_NEG, Number('0q7F00FFFF_5F5E00FF').zone)
        self.assertEqual(Number.Zone.FRACTIONAL_NEG,      Number('0q7E00_80').zone)
        self.assertEqual(Number.Zone.NEGATIVE,            Number('0q7E').zone)
        self.assertEqual(Number.Zone.NEGATIVE,            Number('0q7D_FF').zone)
        self.assertEqual(Number.Zone.NEGATIVE,            Number('0q7D_D6').zone)
        self.assertEqual(Number.Zone.LUDICROUS_LARGE_NEG, Number('0q00FF0000_FA0A1F01').zone)
        self.assertEqual(Number.Zone.TRANSFINITE_NEG,     Number('0q007F').zone)
        self.assertEqual(Number.Zone.NAN,                 Number('0q').zone)

    def test_float_qigits(self):
        self.assertEqual('0q82_01', str(Number(1.1, qigits=1)))
        self.assertEqual('0q82_011A', str(Number(1.1, qigits=2)))
        self.assertEqual('0q82_01199A', str(Number(1.1, qigits=3)))
        self.assertEqual('0q82_0119999A', str(Number(1.1, qigits=4)))
        self.assertEqual('0q82_011999999A', str(Number(1.1, qigits=5)))
        self.assertEqual('0q82_01199999999A', str(Number(1.1, qigits=6)))
        self.assertEqual('0q82_0119999999999A', str(Number(1.1, qigits=7)))
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1, qigits=8)))   # so float has about 7 significant qigits
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1, qigits=9)))
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1, qigits=15)))

    def test_float_qigits_default(self):
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1)))
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1, qigits=None)))
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1, qigits=-1)))
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1, qigits=0)))

    def test_float_qigits_default_not_sticky(self):
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1)))
        self.assertEqual('0q82_0119999A', str(Number(1.1, qigits=4)))
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1)))

    def test_float_qigits_fractional(self):
        self.assertEqual('0q81FF_199999999A', str(Number(0.1, qigits=5)))
        self.assertEqual('0q81FF_19999999999A', str(Number(0.1, qigits=6)))
        self.assertEqual('0q81FF_1999999999999A', str(Number(0.1, qigits=7)))
        self.assertEqual('0q81FF_1999999999999A', str(Number(0.1, qigits=8)))
        self.assertEqual('0q81FF_1999999999999A', str(Number(0.1, qigits=9)))

        self.assertEqual('0q81FF_3333333333', str(Number(0.2, qigits=5)))
        self.assertEqual('0q81FF_333333333333', str(Number(0.2, qigits=6)))
        self.assertEqual('0q81FF_33333333333334', str(Number(0.2, qigits=7)))
        self.assertEqual('0q81FF_33333333333334', str(Number(0.2, qigits=8)))
        self.assertEqual('0q81FF_33333333333334', str(Number(0.2, qigits=9)))
        # Ending in 34 is not a bug.
        # The 7th qigit above gets rounded to 34, not in Number, but when float was originally decoded from 0.2.
        # That's because the IEEE-754 53-bit (double precision) float significand can only fit 7 of those bits there.
        # The 1st qigit uses 6 bits.  Middle 5 qigits use all 8 bits.  So 6+(5*8)+7 = 53.
        # So Number faithfully stored all 53 bits from the float.

    def test_float_qigits_fractional_neg(self):
        self.assertEqual('0q7E00_E666666666', str(Number(-0.1, qigits=5)))
        self.assertEqual('0q7E00_E66666666666', str(Number(-0.1, qigits=6)))
        self.assertEqual('0q7E00_E6666666666666', str(Number(-0.1, qigits=7)))
        self.assertEqual('0q7E00_E6666666666666', str(Number(-0.1, qigits=8)))
        self.assertEqual('0q7E00_E6666666666666', str(Number(-0.1, qigits=9)))

        self.assertEqual('0q7E00_CCCCCCCCCD', str(Number(-0.2, qigits=5)))
        self.assertEqual('0q7E00_CCCCCCCCCCCD', str(Number(-0.2, qigits=6)))
        self.assertEqual('0q7E00_CCCCCCCCCCCCCC', str(Number(-0.2, qigits=7)))
        self.assertEqual('0q7E00_CCCCCCCCCCCCCC', str(Number(-0.2, qigits=8)))
        self.assertEqual('0q7E00_CCCCCCCCCCCCCC', str(Number(-0.2, qigits=9)))

    def test_float_qigits_neg(self):
        self.assertEqual('0q7D_FEE6666666', str(Number(-1.1, qigits=5)))
        self.assertEqual('0q7D_FEE666666666', str(Number(-1.1, qigits=6)))
        self.assertEqual('0q7D_FEE66666666666', str(Number(-1.1, qigits=7)))
        self.assertEqual('0q7D_FEE6666666666660', str(Number(-1.1, qigits=8)))   # float's 53-bit significand:  2+8+8+8+8+8+8+3 = 53
        self.assertEqual('0q7D_FEE6666666666660', str(Number(-1.1, qigits=9)))

        self.assertEqual('0q7D_FECCCCCCCD', str(Number(-1.2, qigits=5)))
        self.assertEqual('0q7D_FECCCCCCCCCD', str(Number(-1.2, qigits=6)))
        self.assertEqual('0q7D_FECCCCCCCCCCCD', str(Number(-1.2, qigits=7)))
        self.assertEqual('0q7D_FECCCCCCCCCCCCD0', str(Number(-1.2, qigits=8)))
        self.assertEqual('0q7D_FECCCCCCCCCCCCD0', str(Number(-1.2, qigits=9)))

    def test_float_qigits_negative_one_bug(self):
        self.assertEqual('0q7D_FF', str(Number(-1.0)))
        self.assertEqual('0q7D_FF', str(Number(-1.0, qigits=9)))
        self.assertEqual('0q7D_FF', str(Number(-1.0, qigits=8)))
        self.assertEqual('0q7D_FF', str(Number(-1.0, qigits=7)))   # not 0q7D_FF000000000001
        self.assertEqual('0q7D_FF', str(Number(-1.0, qigits=6)))
        self.assertEqual('0q7D_FF', str(Number(-1.0, qigits=5)))
        self.assertEqual('0q7D_FF', str(Number(-1.0, qigits=4)))
        self.assertEqual('0q7D_FF', str(Number(-1.0, qigits=3)))
        self.assertEqual('0q7D_FF', str(Number(-1.0, qigits=2)))
        self.assertEqual('0q7D_FF', str(Number(-1.0, qigits=1)))

    def test_floats_and_q_strings(self):

        def f__s(x_in, s_out, s_in_opt=None):
            assert isinstance(x_in,      float),                                 "f__s(%s,_) should be a float"  % type(x_in).__name__
            assert isinstance(s_out,    six.string_types),                       "f__s(_,%s) should be a string" % type(s_out).__name__
            assert isinstance(s_in_opt, six.string_types) or s_in_opt is None, "f__s(_,_,%s) should be a string" % type(s_in_opt).__name__
            x_out = x_in
            s_in = s_out if s_in_opt is None else s_in_opt

            try:
                x_new = float(Number(s_in))
            except Exception as e:
                print("%s(%s) <--Number--- %s" % (e.__class__.__name__, str(e), s_in))
                raise
            match_x = floats_really_same(x_new, x_out)

            try:
                s_new = str(Number(x_in))
            except Exception as e:
                print("%.17e ---Number--> %s(%s)" % (x_in, e.__class__.__name__, str(e)))
                raise
            match_s = s_new == s_out

            if not match_x or not match_s:
                report = "\n"
                if not match_x:
                    s_shoulda = str(Number(x_out, qigits = 7))
                    report += "Number(%s) ~~ " % s_shoulda
                report += "%.17e %s %.17e <--- Number(%s).__float__()" % (
                    x_out,
                    '==' if match_x else '!!!=',
                    x_new,
                    s_in,
                )
                report += "\nNumber._from_float(%.17e) ---> %s %s %s" % (
                    x_in,
                    s_new,
                    '==' if match_s else '!!!=',
                    s_out,
                )
                self.fail(report)

            if not context.the_first:
                float_oos =       x_in       >        context.x_in_last
                qin_oos  = Number(s_in ).raw > Number(context.s_in_last ).raw
                qout_oos = Number(s_out).raw > Number(context.s_out_last).raw
                if float_oos: self.fail("Float out of sequence: %.17e should be less than %.17e" % (x_in, context.x_in_last))
                if qin_oos:   self.fail("Qiki Number input out of sequence: %s should be less than %s" % (s_in, context.s_in_last))
                if qout_oos:  self.fail("Qiki Number output out of sequence: %s should be less than %s" % (s_out, context.s_out_last))

                this_zone = Number(s_in).zone
                last_zone =  Number(context.s_in_last).zone
                if not context.after_zone_boundary and this_zone != last_zone:
                    self.fail("%s is in a different zone than %s -- need zone_boundary()?" % (context.s_in_last, s_in))
                if context.after_zone_boundary and this_zone == last_zone:
                    self.fail("%s is in the same zone as %s -- remove zone_boundary()?" % (context.s_in_last, s_in))

            context.x_in_last = x_in
            context.s_in_last = s_in
            context.s_out_last = s_out

            context.the_first = False
            context.after_zone_boundary = False

        # noinspection PyClassHasNoInit,PyPep8Naming
        class context:   # variables that are local to test_floats_and_strings(), but global to f__s()
            the_first = True
            after_zone_boundary = False

        def zone_boundary():
            context.after_zone_boundary = True


        f__s(float('+inf'),               '0qFF_81')
        zone_boundary()
        f__s(float('+inf'),               '0qFF_81', '0qFF00FFFF_5F5E00FF_01')   # 2**99999999, a ludicrously large positive number
        f__s(float('+inf'),               '0qFF_81', '0qFF000080_01')   # A smidgen too big for floating point
        # m__s(mpmath.power(2,1024),        '0qFF000080_01')   # A smidgen too big for floating point
        # f__s(1.7976931348623157e+308,     '0qFF00007F_FFFFFFFFFFFFF8')   # Largest IEEE-754 64-bit floating point number -- a little ways into Number.Zone.LUDICROUS_LARGE
        # f__s(math.pow(2,1000),            '0qFF00007D_01')   # TODO:  Smallest Ludicrously Large integer, +2 ** +1000.
        zone_boundary()
        f__s(1.0715086071862672e+301,     '0qFE_FFFFFFFFFFFFF8')   # Largest reasonable number that floating point can represent, 2**1000 - 2**947
        f__s(5.3575430359313366e+300,     '0qFE_80')
        f__s(math.pow(2,999),             '0qFE_80')   # Largest reasonable integral power of 2
        f__s(       1e100+1.0,            '0qAB_1249AD2594C37D', '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10000000000000000000000001')   # googol+1 (though float can't distinguish)
        f__s(       1e100,                '0qAB_1249AD2594C37D', '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10')   # googol, or as close to it as float can get
        f__s(       1e25,                 '0q8C_0845951614014880')
        f__s(       1e10,                 '0q86_02540BE4')
        f__s(4294967296.0,                '0q86_01')
        f__s(4294967296.0,                '0q86_01', '0q86')   # 0q86 is an alias for +256**4, the official code being 0q86_01
        f__s(  16777216.0,                '0q85_01')
        f__s(     65536.0,                '0q84_01')
        f__s(     32768.0,                '0q83_80')
        f__s(     16384.0,                '0q83_40')
        f__s(      8192.0,                '0q83_20')
        f__s(      4096.0,                '0q83_10')
        f__s(      2048.0,                '0q83_08')
        f__s(      1234.567890123456789,  '0q83_04D291613F43F8')
        f__s(      1234.5678901234,       '0q83_04D291613F43B980')
        f__s(      1234.56789,            '0q83_04D291613D31B9C0')
        f__s(      1111.1111112,          '0q83_04571C71C89A3840')
        f__s(      1111.111111111111313,  '0q83_04571C71C71C72')    # XXX: use numpy.nextafter(1111.111111111111111, 1) or something -- http://stackoverflow.com/a/6163157/673991
        f__s(      1111.111111111111111,  '0q83_04571C71C71C71C0')  # float has just under 17 significant digits
        f__s(      1111.1111111,          '0q83_04571C71C6ECB9')
        f__s(      1024.0,                '0q83_04')
        f__s(      1000.0,                '0q83_03E8')
        f__s(       512.0,                '0q83_02')
        f__s(       258.0,                '0q83_0102')
        f__s(       257.0,                '0q83_0101')
        f__s(       256.0,                '0q83_01')
        f__s(       256.0,                '0q83_01', '0q83')   # alias for +256
        f__s(       256.0,                '0q83_01', '0q82_FFFFFFFFFFFFFC')
        f__s(       255.9999999999999801, '0q82_FFFFFFFFFFFFF8')     # 53 bits in the float mantissa
        f__s(       255.5,                '0q82_FF80')
        f__s(       255.0,                '0q82_FF')
        f__s(       254.0,                '0q82_FE')
        f__s(       216.0,                '0q82_D8')
        f__s(       128.0,                '0q82_80')
        f__s(       100.0,                '0q82_64')
        f__s(math.pi*2,                   '0q82_06487ED5110B46')
        f__s(math.pi,                     '0q82_03243F6A8885A3')
        f__s(         3.0,                '0q82_03')
        f__s(math.exp(1),                 '0q82_02B7E151628AED20')
        f__s(         2.5,                '0q82_0280')
        f__s(         2.4,                '0q82_0266666666666660')
        f__s(         2.3,                '0q82_024CCCCCCCCCCCC0')
        f__s(         2.2,                '0q82_0233333333333340')
        f__s(         2.1,                '0q82_02199999999999A0')
        f__s(         2.0,                '0q82_02')
        f__s(         1.875,              '0q82_01E0')
        f__s(         1.75,               '0q82_01C0')
        f__s(math.sqrt(3),                '0q82_01BB67AE8584CAA0')
        f__s(         1.6666666666666666, '0q82_01AAAAAAAAAAAAA0')
        f__s((1+math.sqrt(5))/2,          '0q82_019E3779B97F4A80')   # golden ratio
        f__s(         1.6,                '0q82_01999999999999A0')
        f__s(         1.5333333333333333, '0q82_0188888888888880')
        f__s(         1.5,                '0q82_0180')
        f__s(         1.4666666666666666, '0q82_0177777777777770')
        f__s(math.sqrt(2),                '0q82_016A09E667F3BCD0')
        f__s(         1.4,                '0q82_0166666666666660')
        f__s(         1.3333333333333333, '0q82_0155555555555550')
        f__s(         1.3,                '0q82_014CCCCCCCCCCCD0')
        f__s(         1.2666666666666666, '0q82_0144444444444440')
        f__s(         1.25,               '0q82_0140')
        f__s(         1.2,                '0q82_0133333333333330')
        f__s(         1.1333333333333333, '0q82_0122222222222220')
        f__s(         1.125,              '0q82_0120')
        f__s(         1.1,                '0q82_01199999999999A0')
        f__s(         1.0666666666666666, '0q82_0111111111111110')
        f__s(         1.0625,             '0q82_0110')
        f__s(math.pow(2, 1/12.0),         '0q82_010F38F92D979630')   # semitone (twelfth of an octave)
        f__s(         1.03125,            '0q82_0108')
        f__s(         1.015625,           '0q82_0104')
        f__s(         1.01,               '0q82_01028F5C28F5C290')
        f__s(         1.0078125,          '0q82_0102')
        f__s(         1.00390625,         '0q82_0101')
        f__s(         1.001953125,        '0q82_010080')
        f__s(         1.001,              '0q82_01004189374BC6A0')
        f__s(         1.0009765625,       '0q82_010040')
        f__s(         1.00048828125,      '0q82_010020')
        f__s(         1.000244140625,     '0q82_010010')
        f__s(         1.0001,             '0q82_0100068DB8BAC710')
        f__s(         1.00001,            '0q82_010000A7C5AC4720')
        f__s(         1.000001,           '0q82_01000010C6F7A0B0')
        f__s(         1.0000001,          '0q82_01000001AD7F29B0')
        f__s(         1.00000001,         '0q82_010000002AF31DC0')
        f__s(         1.000000001,        '0q82_01000000044B83')
        f__s(         1.0000000001,       '0q82_01000000006DF380')
        f__s(         1.00000000001,      '0q82_01000000000AFEC0')
        f__s(         1.000000000001,     '0q82_0100000000011980')
        f__s(         1.0000000000001,    '0q82_0100000000001C20')
        f__s(         1.00000000000001,   '0q82_01000000000002D0')
        f__s(         1.000000000000001,  '0q82_0100000000000050')
        f__s(         1.00000000000000067,'0q82_0100000000000030')
        f__s(         1.00000000000000067,'0q82_0100000000000030', '0q82_01000000000000280001')
        f__s(         1.00000000000000044,'0q82_0100000000000020', '0q82_0100000000000028')
        f__s(         1.00000000000000044,'0q82_0100000000000020')
        f__s(         1.00000000000000044,'0q82_0100000000000020', '0q82_0100000000000018')
        f__s(         1.00000000000000022,'0q82_0100000000000010', '0q82_0100000000000017FFFF')  # alternated rounding?
        f__s(         1.00000000000000022,'0q82_0100000000000010')
        f__s(         1.00000000000000022,'0q82_0100000000000010', '0q82_01000000000000080001')
        f__s(         1.0                ,'0q82_01',               '0q82_0100000000000008') # so float granularity [1.0,2.0) is 2**-52 ~~ 22e-17
        f__s(         1.0,                '0q82_01')
        f__s(         1.0,                '0q82_01',  '0q82')   # alias for +1
        zone_boundary()
        f__s(         0.99999237060546875,'0q81FF_FFFF80')
        f__s(         0.9998779296875,    '0q81FF_FFF8')
        f__s(         0.999,              '0q81FF_FFBE76C8B43958')     # 999/1000
        f__s(         0.998046875,        '0q81FF_FF80')
        f__s(         0.998,              '0q81FF_FF7CED916872B0')     # 998/1000
        f__s(         0.9972222222222222, '0q81FF_FF49F49F49F4A0')     # 359/360
        f__s(         0.9944444444444445, '0q81FF_FE93E93E93E940')     # 358/360
        f__s(         0.99,               '0q81FF_FD70A3D70A3D70')     # 99/100
        f__s(         0.98,               '0q81FF_FAE147AE147AE0')     # 98/100
        f__s(         0.96875,            '0q81FF_F8')
        f__s(         0.9375,             '0q81FF_F0')
        f__s(         0.875,              '0q81FF_E0')
        f__s(         0.75,               '0q81FF_C0')
        f__s(math.sqrt(0.5),              '0q81FF_B504F333F9DE68')
        f__s(         0.5,                '0q81FF_80')
        f__s(         0.25,               '0q81FF_40')
        f__s(         0.125,              '0q81FF_20')
        f__s(         0.0625,             '0q81FF_10')
        f__s(         0.03125,            '0q81FF_08')
        f__s(         0.02,               '0q81FF_051EB851EB851EC0')   # 2/200
        f__s(         0.015625,           '0q81FF_04')
        f__s(         0.01171875,         '0q81FF_03')
        f__s(         0.01,               '0q81FF_028F5C28F5C28F60')   # 1/100
        f__s(         0.0078125,          '0q81FF_02')
        f__s(         0.005555555555555556,'0q81FF_016C16C16C16C170')  # 2/360
        f__s(         0.0039520263671875, '0q81FF_0103')               # 259/65536
        f__s(         0.003936767578125,  '0q81FF_0102')               # 258/65536
        f__s(         0.0039215087890625, '0q81FF_0101')               # 257/65536
        f__s(         0.00390625,         '0q81FF_01')                 # 256/65536 aka 1/256
        f__s(         0.00390625,         '0q81FF_01', '0q81FF')       # 1/256 alias
        f__s(         0.0038909912109375, '0q81FE_FF')                 # 255/65536
        f__s(         0.003875732421875,  '0q81FE_FE')                 # 254/65536
        f__s(         0.0038604736328125, '0q81FE_FD')                 # 253/65536
        f__s(         0.002777777777777778,'0q81FE_B60B60B60B60B8')    # 1/360
        f__s(         0.002,              '0q81FE_83126E978D4FE0')     # 2/1000
        f__s(         0.001953125,        '0q81FE_80')
        f__s(         0.001,              '0q81FE_4189374BC6A7F0')     # 1/1000 = 0x0.004189374BC6A7EF9DB22D0E560 4189374BC6A7EF9DB22D0E560 ...
        f__s(         0.0009765625,       '0q81FE_40')
        f__s(         0.00048828125,      '0q81FE_20')
        f__s(         0.000244140625,     '0q81FE_10')
        f__s(         0.0001220703125,    '0q81FE_08')
        f__s(         0.00006103515625,   '0q81FE_04')
        f__s(         0.000030517578125,  '0q81FE_02')
        f__s(math.pow(256, -2),           '0q81FE_01')
        f__s(         0.0000152587890625, '0q81FE_01')                 # 1/65536
        f__s(         0.0000152587890625, '0q81FE_01', '0q81FE')       # 1/65536 alias
        f__s(         0.00000762939453125,'0q81FD_80')
        f__s(math.pow(256, -3),           '0q81FD_01')
        f__s(math.pow(256, -4),           '0q81FC_01')
        f__s(math.pow(256, -10),          '0q81F6_01')
        f__s(math.pow(256, -100),         '0q819C_01')
        f__s(math.pow(256, -100),         '0q819C_01', '0q819C')   # alias for 256**-100
        f__s(math.pow(  2, -991),         '0q8184_02')
        f__s(math.pow(  2, -992),         '0q8184_01')
        f__s(math.pow(256, -124),         '0q8184_01')
        f__s(math.pow(  2, -993),         '0q8183_80')
        f__s(math.pow(  2, -994),         '0q8183_40')
        f__s(math.pow(  2, -998),         '0q8183_04')
        f__s(math.pow(  2, -999),         '0q8183_02')
        f__s(math.pow(  2, -1000),        '0q8183_01')
        f__s(math.pow(256, -125),         '0q8183_01')
        zone_boundary()
        f__s(         0.0,                '0q80',  '0q80FF0000_FF4143E0_01')   # +2**-99999999, a ludicrously small positive number
        zone_boundary()
        f__s(         0.0,                '0q80',  '0q807F')   # +infinitesimal
        zone_boundary()
        f__s(         0.0,                '0q80')
        zone_boundary()
        f__s(        -0.0,                '0q80',  '0q7F81')   # -infinitesimal
        zone_boundary()
        f__s(        -0.0,                '0q80',  '0q7F00FFFF_00BEBC1F_80')   # -2**-99999999, a ludicrously small negative number
        zone_boundary()
        f__s(-math.pow(256, -125),        '0q7E7C_FF')
        f__s(-math.pow(  2, -1000),       '0q7E7C_FF')
        f__s(-math.pow(  2, -999),        '0q7E7C_FE')
        f__s(-math.pow(  2, -998),        '0q7E7C_FC')
        f__s(-math.pow(  2, -994),        '0q7E7C_C0')
        f__s(-math.pow(  2, -993),        '0q7E7C_80')
        f__s(-math.pow(256, -124),        '0q7E7B_FF')
        f__s(-math.pow(  2, -992),        '0q7E7B_FF')
        f__s(-math.pow(  2, -991),        '0q7E7B_FE')
        f__s(-math.pow(256, -100),        '0q7E63_FF', '0q7E64')   # alias for -256**-100
        f__s(-math.pow(256, -100),        '0q7E63_FF')
        f__s(-math.pow(256, -10),         '0q7E09_FF')
        f__s(-math.pow(256, -4),          '0q7E03_FF')
        f__s(-math.pow(256, -3),          '0q7E02_FF')
        f__s(        -0.00000762939453125,'0q7E02_80')
        f__s(        -0.0000152587890625, '0q7E01_FF', '0q7E02')   # alias for -256**-2
        f__s(-math.pow(256, -2),          '0q7E01_FF')
        f__s(        -0.0000152587890625, '0q7E01_FF')
        f__s(        -0.000030517578125,  '0q7E01_FE')
        f__s(        -0.00006103515625,   '0q7E01_FC')
        f__s(        -0.0001220703125,    '0q7E01_F8')
        f__s(        -0.000244140625,     '0q7E01_F0')
        f__s(        -0.00048828125,      '0q7E01_E0')
        f__s(        -0.0009765625,       '0q7E01_C0')
        f__s(        -0.001953125,        '0q7E01_80')
        f__s(        -0.001953125,        '0q7E01_80')
        f__s(        -0.0038604736328125, '0q7E01_03')   # -253/65536
        f__s(        -0.003875732421875,  '0q7E01_02')   # -254/65536
        f__s(        -0.0038909912109375, '0q7E01_01')   # -255/65536
        f__s(        -0.00390625,         '0q7E00_FF', '0q7E01')   # alias for -1/256 aka -256**-1
        f__s(        -0.00390625,         '0q7E00_FF')   # -256/65536      aka -1/256
        f__s(        -0.0039215087890625, '0q7E00_FEFF') # -257/65536
        f__s(        -0.003936767578125,  '0q7E00_FEFE') # -258/65536
        f__s(        -0.0039520263671875, '0q7E00_FEFD') # -259/65536
        f__s(        -0.0078125,          '0q7E00_FE')
        f__s(        -0.01171875,         '0q7E00_FD')
        f__s(        -0.015625,           '0q7E00_FC')
        f__s(        -0.03125,            '0q7E00_F8')
        f__s(        -0.0625,             '0q7E00_F0')
        f__s(        -0.125,              '0q7E00_E0')
        f__s(        -0.25,               '0q7E00_C0')
        f__s(        -0.5,                '0q7E00_80')
        f__s(        -0.75,               '0q7E00_40')
        f__s(        -0.875,              '0q7E00_20')
        f__s(        -0.9375,             '0q7E00_10')
        f__s(        -0.96875,            '0q7E00_08')
        f__s(        -0.998046875,        '0q7E00_0080')
        f__s(        -0.9998779296875,    '0q7E00_0008')
        f__s(        -0.99999237060546875,'0q7E00_000080')
        zone_boundary()
        f__s(        -1.0,                '0q7D_FF', '0q7E')   # alias for -1
        f__s(        -1.0,                '0q7D_FF')
        f__s(        -1.000001,           '0q7D_FEFFFFEF39085F50')
        f__s(        -1.00000762939453125,'0q7D_FEFFFF80')
        f__s(        -1.0001220703125,    '0q7D_FEFFF8')
        f__s(        -1.000244140625,     '0q7D_FEFFF0')
        f__s(        -1.00048828125,      '0q7D_FEFFE0')
        f__s(        -1.0009765625,       '0q7D_FEFFC0')
        f__s(        -1.001953125,        '0q7D_FEFF80')
        f__s(        -1.00390625,         '0q7D_FEFF')
        f__s(        -1.0078125,          '0q7D_FEFE')
        f__s(        -1.015625,           '0q7D_FEFC')
        f__s(        -1.03125,            '0q7D_FEF8')
        f__s(        -1.0625,             '0q7D_FEF0')
        f__s(        -1.1,                '0q7D_FEE6666666666660')  # TODO:  Try more rational weirdos
        f__s(        -1.125,              '0q7D_FEE0')
        f__s(        -1.25,               '0q7D_FEC0')
        f__s(        -1.5,                '0q7D_FE80')
        f__s(        -1.75,               '0q7D_FE40')
        f__s(        -1.875,              '0q7D_FE20')
        f__s(        -1.9375,             '0q7D_FE10')
        f__s(        -1.96875,            '0q7D_FE08')
        f__s(        -1.998046875,        '0q7D_FE0080')
        f__s(        -1.9998779296875,    '0q7D_FE0008')
        f__s(        -1.99999237060546875,'0q7D_FE000080')
        f__s(        -2.0,                '0q7D_FE')
        f__s(        -2.00000762939453125,'0q7D_FDFFFF80')
        f__s(        -2.25,               '0q7D_FDC0')
        f__s(        -2.5,                '0q7D_FD80')
        f__s(        -2.75,               '0q7D_FD40')
        f__s(        -3.0,                '0q7D_FD')
        f__s(        -3.06249999999999645,'0q7D_FCF00000000001')
        f__s(        -3.0625,             '0q7D_FCF0')
        f__s(        -3.062500000000005,  '0q7D_FCEFFFFFFFFFFEA0')
        f__s(        -4.0,                '0q7D_FC')
        f__s(        -8.0,                '0q7D_F8')
        f__s(       -16.0,                '0q7D_F0')
        f__s(       -32.0,                '0q7D_E0')
        f__s(       -64.0,                '0q7D_C0')
        f__s(      -128.0,                '0q7D_80')
        f__s(      -255.0,                '0q7D_01')
        f__s(      -255.5,                '0q7D_0080')
        f__s(      -255.98046875,         '0q7D_0005')
        f__s(      -255.984375,           '0q7D_0004')
        f__s(      -255.98828125,         '0q7D_0003')
        f__s(      -255.9921875,          '0q7D_0002')
        f__s(      -255.99609375,         '0q7D_0001')
        f__s(      -255.999984741210938,  '0q7D_000001')
        f__s(      -255.999999940395355,  '0q7D_00000001')
        f__s(      -255.999999999767169,  '0q7D_0000000001')
        f__s(      -255.999999999999091,  '0q7D_000000000001')
        f__s(      -255.999999999999943,  '0q7D_00000000000010')
        f__s(      -255.999999999999972,  '0q7D_00000000000008')
        f__s(      -256.0,                '0q7C_FF', '0q7D')   # alias for -256
        f__s(      -256.0,                '0q7C_FF')
        f__s(      -256.00390625,         '0q7C_FEFFFF')
        f__s(      -256.0078125,          '0q7C_FEFFFE')
        f__s(      -256.01171875,         '0q7C_FEFFFD')
        f__s(      -256.015625,           '0q7C_FEFFFC')
        f__s(      -256.01953125,         '0q7C_FEFFFB')
        f__s(      -257.0,                '0q7C_FEFF')
        f__s(      -512.0,                '0q7C_FE')
        f__s(     -1024.0,                '0q7C_FC')
        f__s(     -2048.0,                '0q7C_F8')
        f__s(     -4096.0,                '0q7C_F0')
        f__s(     -8192.0,                '0q7C_E0')
        f__s(    -16384.0,                '0q7C_C0')
        f__s(    -32768.0,                '0q7C_80')
        f__s(    -65536.0,                '0q7B_FF', '0q7C')   # alias for -256**2
        f__s(    -65536.0,                '0q7B_FF')
        f__s(   -131072.0,                '0q7B_FE')
        f__s(-4294967296.0,               '0q79_FF')
        f__s(-math.pow(2,992),            '0q01_FF', '0q02')   # alias for -256**124
        f__s(-math.pow(2,992),            '0q01_FF')
        f__s(-math.pow(2,996),            '0q01_F0')
        f__s(-math.pow(2,997),            '0q01_E0')
        f__s(-math.pow(2,998),            '0q01_C0')
        f__s(-math.pow(2,999),            '0q01_80')
        f__s(-1.0715086071862672e+301,    '0q01_00000000000008')   # Lowest (furthest from zero) reasonable number that floating point can represent
        zone_boundary()
        # f__s(math.pow(2,1000),            '0q00FFFF83_01')   # TODO:  -2 ** +1000 == Closest to zero, negative, Ludicrously Large integer.
        zone_boundary()
        f__s(float('-inf'),               '0q00_7F', '0q00FF0000_FA0A1F01_01')   # -2**99999999, a ludicrously large negative number
        zone_boundary()
        f__s(float('-inf'),               '0q00_7F')
        zone_boundary()
        f__s(float('nan'),                '0q')

    def test_copy_constructor(self):
        self.assertEqual('0q83_03E8', Number(Number('0q83_03E8')).qstring())
        self.assertEqual('0q7C_FEFF', Number(Number('0q7C_FEFF')).qstring())

    def test_copy_constructor_ancestored(self):
        """Propagate up the type hierarchy."""

        class SonOfNumber(Number):
            pass

        self.assertEqual('0q83_03E8', Number(SonOfNumber('0q83_03E8')).qstring())
        self.assertEqual('0q7C_FEFF', str(Number(SonOfNumber('0q7C_FEFF'))))

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
        source.raw = Number(9).raw
        self.assertEqual('0q82_01', destination.qstring())

    def test_assignment_by_reference(self):
        """Make sure assignment copies by reference, not by value."""
        # TODO:  Make Number an immutable class, so assignment is by value?
        # SEE:  Immuutable object, http://stackoverflow.com/q/4828080/673991
        source = Number(1)
        destination = source
        source.raw = Number(9).raw
        self.assertEqual('0q82_09', destination.qstring())

    def test_sizeof(self):
        self.assertIn(sys.getsizeof(Number('0q')), (28, 32))  # depends on Zone.__slots__ containing _zone or not
        self.assertIn(sys.getsizeof(Number('0q80')), (28, 32))
        self.assertIn(sys.getsizeof(Number('0q83_03E8')), (28, 32))
        self.assertIn(sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8')), (28, 32))
        self.assertIn(sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8')), (28, 32))

        self.assertEqual(py23( 21, 17), sys.getsizeof(Number('0q').raw))
        self.assertEqual(py23( 22, 18), sys.getsizeof(Number('0q80').raw))
        self.assertEqual(py23( 23, 19), sys.getsizeof(Number('0q82_01').raw))
        self.assertEqual(py23( 24, 20), sys.getsizeof(Number('0q83_03E8').raw))
        self.assertEqual(py23( 25, 21), sys.getsizeof(Number('0q82_018888').raw))
        self.assertEqual(py23( 45, 41), sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8').raw))
        self.assertEqual(py23(144,140), sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8').raw))

        self.assertEqual(py23(21, 17), sys.getsizeof(b''))
        self.assertEqual(py23(22, 18), sys.getsizeof(b'\x80'))
        self.assertEqual(py23(24, 20), sys.getsizeof(b'\x83\x03\xE8'))
        self.assertEqual(py23(45, 41), sys.getsizeof(b'\x83\x03\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8'))

    def test_uneven_hex(self):
        if getattr(Number, "WE_ARE_BEING_SUPER_STRICT_ABOUT_THERE_BEING_AN_EVEN_NUMBER_OF_HEX_DIGITS", False):
            with self.assertRaises(Number.ConstructorValueError):
                Number('0q8')
            with self.assertRaises(Number.ConstructorValueError):
                Number('0q8_')
            with self.assertRaises(Number.ConstructorValueError):
                Number('0q_8')
            with self.assertRaises(Number.ConstructorValueError):
                Number('0q82_028')
            Number('0q82_0280')
        else:
            Number('0q8')
            Number('0q8_')
            Number('0q_8')
            self.assertEqual(
                Number('0q82_028'),
                Number('0q82_0280')
            )

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
        """Testing the examples (for Python float()) by Eric Leschinski.

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

        # Also

        with self.assertRaises(Number.ConstructorValueError):
            Number("2+2")
        with self.assertRaises(Number.ConstructorValueError):
            Number("0-0")
        with self.assertRaises(Number.ConstructorValueError):
            Number("0 0")
        with self.assertRaises(Number.ConstructorValueError):
            Number("--0")

        if six.PY2:
            self.assertEqual(-42, Number("- 42"))   # int() is guilty, float() is innocent.
        else:
            with self.assertRaises(Number.ConstructorValueError):
                Number("- 42")

        with self.assertRaises(Number.ConstructorValueError):
            Number("       ")
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

    def test_from_int_negative(self):
        self.assertEqual('0q80',    str(Number(-0)))
        self.assertEqual('0q7D_FF', str(Number(-1)))
        self.assertEqual('0q7D_FE', str(Number(-2)))
        self.assertEqual('0q7D_FD', str(Number(-3)))
        self.assertEqual('0q7D_FC', str(Number(-4)))
        self.assertEqual('0q7D_01', str(Number(-255)))
        self.assertEqual('0q7C_FF', str(Number(-256)))
        self.assertEqual('0q7C_FEFF', str(Number(-257)))

    def test_from_int(self):
        self.assertEqual('0q80', str(Number(0)))
        self.assertEqual('0q82_01', str(Number(1)))
        self.assertEqual('0q82_02', str(Number(2)))
        self.assertEqual('0q82_03', str(Number(3)))
        self.assertEqual('0q82_FF', str(Number(255)))
        self.assertEqual('0q83_01', str(Number(256)))
        self.assertEqual('0q83_0101', str(Number(257)))
        self.assertEqual('0q8C_01', str(Number(256*256*256*256*256*256*256*256*256*256)))
        self.assertEqual('0q8B_FFFFFFFFFFFFFFFFFFFF', str(Number(256*256*256*256*256*256*256*256*256*256-1)))
        self.assertEqual('0q8C_0100000000000000000001', str(Number(256*256*256*256*256*256*256*256*256*256+1)))

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

    # def test_from_bytearray(self):
    #     self.assertEqual(six.binary_type, type(                          Number(2)      .raw))
    #     self.assertEqual(six.binary_type, type(Number.from_raw(bytearray(Number(2).raw)).raw))
    #     self.assertEqual('0q82_42', Number.from_raw(          b'\x82\x42' ).qstring())
    #     self.assertEqual('0q82_42', Number.from_raw(bytearray(b'\x82\x42')).qstring())

    def test_number_subclasses_number(self):
        self.assertTrue(issubclass(Number, numbers.Number))

    def test_number_is_a_number(self):
        n = Number(1)
        self.assertIsInstance(n, numbers.Number)


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
        self.assertFalse(      (1.0) == Number(0.0))
        self.assertTrue (      (0.0) == Number(0.0))
        self.assertFalse(      (0.0) == Number(1.0))

        self.assertTrue (      (1.0) != Number(0.0))
        self.assertFalse(      (0.0) != Number(0.0))
        self.assertTrue (      (0.0) != Number(1.0))

        self.assertFalse(      (1.0) <  Number(0.0))
        self.assertFalse(      (0.0) <  Number(0.0))
        self.assertTrue (      (0.0) <  Number(1.0))

        self.assertFalse(      (1.0) <= Number(0.0))
        self.assertTrue (      (0.0) <= Number(0.0))
        self.assertTrue (      (0.0) <= Number(1.0))

        self.assertTrue (      (1.0) >  Number(0.0))
        self.assertFalse(      (0.0) >  Number(0.0))
        self.assertFalse(      (0.0) >  Number(1.0))

        self.assertTrue (      (1.0) >= Number(0.0))
        self.assertTrue (      (0.0) >= Number(0.0))
        self.assertFalse(      (0.0) >= Number(1.0))

    def test_unittest_equality(self):
        """Do qiki.Number and assertEqual() handle googol with finesse?

        See also test_02_big_int_unittest_equality()."""
        googol        = Number(10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000)
        googol_plus_1 = Number(10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001)
        self.assertEqual   (googol       , googol)
        self.assertNotEqual(googol       , googol_plus_1)
        self.assertNotEqual(googol_plus_1, googol)
        self.assertEqual   (googol_plus_1, googol_plus_1)

    def test_op_equality(self):
        """Do qiki.Number and its own equality operator handle googol with finesse?

        See also test_02_big_int_op_equality()."""
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

    def test_googol_raw_string(self):
        """Googol is big huh!  How big is it?  How long is the qstring?"""
        googol = Number(10**100)
        googol_plus_one = googol + Number(1)
        googol_minus_one = googol - Number(1)
        self.assertEqual(31, len(googol.raw))             # So 1e100 needs 31 qigits
        self.assertEqual(43, len(googol_plus_one.raw))    # But 1e100+1 needs 43 qigits.
        self.assertEqual(43, len(googol_minus_one.raw))   # Because 1e100 has 12 stripped 00 qigits.

    def test_googol_cubed_raw_string(self):
        """Googol cubed is really big huh!!  How long is the qstring?"""
        g_cubed = Number(10**300)
        g_cubed_plus_one = g_cubed + Number(1)
        g_cubed_minus_one = g_cubed - Number(1)
        self.assertEqual(89, len(g_cubed.raw))              # So 1e300 needs 89 qigits
        self.assertEqual(126, len(g_cubed_plus_one.raw))    # But 1e300+1 needs 126 qigits.
        self.assertEqual(126, len(g_cubed_minus_one.raw))   # Because 1e300 has 37 stripped 00 qigits.

    def test_biggie_raw_string(self):
        """How long is the raw string for "biggie" the biggest reasonable integer?"""
        biggie_minus_one = Number(2**1000 - 1)
        self.assertEqual(126, len(biggie_minus_one.raw))   # So biggie needs 126 qigits

    def test_incomparable(self):
        # noinspection PyClassHasNoInit
        class SomeType:
            pass

        with self.assertRaises(Number.Incomparable):   Number(1) <  SomeType()
        with self.assertRaises(Number.Incomparable):   Number(1) <= SomeType()
        self.assertFalse(                              Number(1) == SomeType())
        self.assertTrue(                               Number(1) != SomeType())
        with self.assertRaises(Number.Incomparable):   Number(1) >  SomeType()
        with self.assertRaises(Number.Incomparable):   Number(1) >= SomeType()
        with self.assertRaises(Number.Incomparable):   SomeType() <  Number(1)
        with self.assertRaises(Number.Incomparable):   SomeType() <= Number(1)
        self.assertFalse(                              SomeType() == Number(1))
        self.assertTrue(                               SomeType() != Number(1))
        with self.assertRaises(Number.Incomparable):   SomeType() >  Number(1)
        with self.assertRaises(Number.Incomparable):   SomeType() >= Number(1)


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
        self.assertTrue (Number('0q8A_010000000000000001').is_whole())
        self.assertTrue (Number('0q8A_0100000000000000010000').is_whole())
        self.assertFalse(Number('0q8A_0100000000000000010001').is_whole())
        self.assertFalse(Number('0q8A_01000000000000000180').is_whole())
        self.assertTrue (Number('0q8A_01000000000000000200').is_whole())
        self.assertTrue (Number('0q8A_010000000000000002').is_whole())

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

    # noinspection PyUnresolvedReferences,PyUnusedLocal
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

        Make sure the operation works, as well as it's 'r' (right) alternate.
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
        Proove that 0q8A_010000000000000001 is too big to be a float, accurately.

        So we can proove Number math isn't simply float math.
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
        self.binary_op(operator.__truediv__, 7.0, 42.0, 6.0)
        self.binary_op(operator.__truediv__, 1.5, 3.75, 2.5)
        self.binary_op(operator.__truediv__, 1+2j, -5+10j, 3+4j)

    def test_div(self):
        if six.PY2:
            self.assertTrue(hasattr(operator, '__div__'))
            self.binary_op(operator.__div__, 7, 42, 6)
            self.binary_op(operator.__div__, Number('0q8A_010000000000000001'),
                                             Number('0q92_0100000000000000020000000000000001'),
                                             Number('0q8A_010000000000000001'))
        else:
            self.assertFalse(hasattr(operator, '__div__'))

    def test_pow(self):
        self.binary_op(operator.__pow__, 65536, 2, 16)
        self.binary_op(operator.__pow__, 3.375, 1.5, 3.0)
        self.binary_op(operator.__pow__, Number('0qFE_80'), Number(2), Number(999))

    def test_add_assign(self):
        # So apparently implementing __add__ means you get __iadd__ for free.
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

    if TEST_INC_ON_ALL_POWERS_OF_TWO:
        def test_inc_powers_of_2(self):   # This takes take a long time, about 2 seconds
            power_of_two = 1
            for binary_exponent in range(0,1000):
                self.assert_inc_works_on(power_of_two-2)
                self.assert_inc_works_on(power_of_two-1)
                self.assert_inc_works_on(power_of_two)
                self.assert_inc_works_on(power_of_two+1)
                self.assert_inc_works_on(power_of_two+2)
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
        """Number.real should never return self."""
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
        n, n_bar = Number(x), Number(x_bar)
        with self.assertRaises(TypeError):   # Comparing native complex numbers raises a TypeError.
            # noinspection PyStatementEffect
            x_bar < x
        with self.assertRaises(TypeError):   # So should Number() comparisons with a nonzero imaginary.
            n_bar < n

    def test_06c_more_or_less_complex_comparisons(self):
        """Complex ordered-comparisons < <= > >= should raise a TypeError, qiki numbers. """
        x, x_bar = 888+111j, 888-111j
        n, n_bar = Number(x), Number(x_bar)
        with self.assertRaises(TypeError):   # Check all comparison operators.
            n_bar < n
        with self.assertRaises(TypeError):
            n_bar <= n
        with self.assertRaises(TypeError):
            n_bar > n
        with self.assertRaises(TypeError):
            n_bar >= n

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
        with self.assertRaises(Number.Incomparable):   # q vs q -- Neither side of a comparison can have a nonzero imaginary.
            qiki_complex2 < qiki_real1
        with self.assertRaises(Number.Incomparable):
            qiki_real2 < qiki_complex1
        with self.assertRaises(Number.Incomparable):   # n vs q
            native_complex2 < qiki_real1
        with self.assertRaises(Number.Incomparable):
            native_real2 < qiki_complex1
        with self.assertRaises(Number.Incomparable):   # q vs n
            qiki_complex2 < native_real1
        with self.assertRaises(Number.Incomparable):
            qiki_real2 < native_complex1
        with self.assertRaises(TypeError):   # n vs n
            native_complex2 < native_real1
        with self.assertRaises(TypeError):
            native_real2 < native_complex1

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
        """Number.imag only gets the first imaginary suffix, ignoring others."""
        n = Number('0q82_07__8209_690300__8205_690300')
        self.assertEqual(7.0, float(n.real))
        self.assertEqual(9.0, float(n.imag))
        n = Number('0q82_07__8205_690300__8209_690300')
        self.assertEqual(7.0, float(n.real))
        self.assertEqual(5.0, float(n.imag))


# noinspection SpellCheckingInspection
class NumberPickleTests(NumberTests):
    """ This isn't so much testing as revealing what pickle does to a qiki.Number.

    Hint, there's a whole buncha baggage in addition to what __getstate__ and
    __setstate__ generate and consume."""

    def test_pickle_protocol_0_class(self):
        if six.PY2:
            self.assertEqual(
                pickle.dumps(Number),
                textwrap.dedent("""\
                    cnumber
                    Number
                    p0
                    ."""
                ),   # when run via qiki-python or number_playground
            )
        else:
            self.assertEqual(
                pickle.dumps(Number),
                b"\x80\x03cnumber\nNumber\nq\x00.",   # Python 3.X
            )

    def test_pickle_protocol_0_instance(self):
        x314 = Number(3.14)
        self.assertEqual(x314.qstring(), '0q82_0323D70A3D70A3E0')
        if six.PY2:
            self.assertEqual(
                pickle.dumps(x314),
                textwrap.dedent(b"""\
                    ccopy_reg
                    _reconstructor
                    p0
                    (cnumber
                    Number
                    p1
                    c__builtin__
                    object
                    p2
                    Ntp3
                    Rp4
                    S{x314_raw_repr}
                    p5
                    b."""
                ).format(x314_raw_repr=repr(x314.raw)),   # via qiki-python or number_playground
            )
        else:
            self.assertEqual(
                pickle.dumps(x314),
                b'\x80\x03cnumber\nNumber\nq\x00)\x81q\x01C\t' +
                x314.raw +
                b'q\x02b.'
            )

        y314 = pickle.loads(pickle.dumps(x314))
        self.assertEqual(x314, y314)

    def test_pickle_protocol_2_class(self):
        self.assertEqual(pickle.dumps(Number, 2), b'\x80\x02cnumber\nNumber\nq\x00.')

    def test_pickle_protocol_2_instance(self):
        x314 = Number(3.14)
        self.assertEqual(x314.qstring(), '0q82_0323D70A3D70A3E0')
        self.assertEqual(x314.raw, b'\x82\x03#\xd7\n=p\xa3\xe0')
        x314_raw_utf8 = b'\xc2\x82\x03#\xc3\x97\n=p\xc2\xa3\xc3\xa0'

        if six.PY2:
            self.assertEqual(
                pickle.dumps(x314, 2),
                (
                    b'\x80\x02cnumber\nNumber\nq\x00)\x81q\x01U\t' +
                    x314.raw +
                    b'q\x02b.'
                )
            )
        else:
            self.assertEqual(
                # XXX:  Is this ridonculously messed up, in that the raw string is being utf-8 encoded??
                pickle.dumps(x314, 2),
                (
                    b'\x80\x02cnumber\nNumber\nq\x00)\x81q\x01c_codecs\nencode\nq\x02X\r\x00\x00\x00' +
                    x314_raw_utf8 +
                    b'q\x03X\x06\x00\x00\x00latin1q\x04\x86q\x05Rq\x06b.'
                )
            )

        # print(repr(pickle.dumps(x314, 2)))
        # PY2:  '\x80\x02cnumber\nNumber\nq\x00)\x81q\x01U\t\x82\x03#\xd7\n=p\xa3\xe0q\x02b.'
        # PY3:  b'\x80\x02cnumber\nNumber\nq\x00)\x81q\x01c_codecs\nencode\nq\x02X\r\x00\x00\x00\xc2\x82\x03#\xc3\x97\n=p\xc2\xa3\xc3\xa0q\x03X\x06\x00\x00\x00latin1q\x04\x86q\x05Rq\x06b.'

        # print(repr(x314.raw))
        # '\x82\x03#\xd7\n=p\xa3\xe0'

        # As reported by failed assertEqual:
        # PY2:  '\x80\x02cnumber\nNumber\nq\x00)\x81q\x01U\t\x82\x03#\xd7\n=p\xa3\xe0q\x02b.'
        # PY3:  b'\x80\x02cnumber\nNumber\nq\x00)\x81q\x0[126 chars]06b.'

        y314 = pickle.loads(pickle.dumps(x314))
        self.assertEqual(x314, y314)


# noinspection SpellCheckingInspection
class NumberSuffixTests(NumberTests):

    # TODO:  Replace the indiscriminate use of suffix types here with a single
    # suffix type, e.g. Number.Suffix.TYPE_NOP,
    # that's reserved for testing, and has no value implications.
    # (So, for example, a suffix someday for rational numbers might modify
    # the value returned by float(), and not break tests here when it's implemented.)

    def test_add_suffix_type(self):
        self.assertEqual(Number('0q82_01__7E0100'), Number(1).add_suffix(Number.Suffix.TYPE_TEST))

    def test_add_suffix_type_by_class(self):
        self.assertEqual(Number('0q82_01__7E0100'), Number(1).add_suffix(Number.Suffix(Number.Suffix.TYPE_TEST)))

    def test_add_suffix_type_and_payload(self):
        self.assertEqual(Number('0q82_01__887E0200'), Number(1).add_suffix(Number.Suffix.TYPE_TEST, b'\x88'))

    def test_add_suffix_type_and_payload_by_class(self):
        self.assertEqual(Number('0q82_01__887E0200'), Number(1).add_suffix(Number.Suffix(Number.Suffix.TYPE_TEST, b'\x88')))

    def test_qstring_empty(self):
        """Make sure trailing 00s in qstring literal are not stripped."""
        self.assertEqual(Number('0q82_01__0000'), Number('0q82_01__0000'))
        self.assertEqual('0q82010000', Number('0q82_01__0000').qstring(underscore=0))
        self.assertEqual('0q82012233110300', Number('0q82_01__2233_110300').qstring(underscore=0))

    def test_add_suffix_empty(self):
        self.assertEqual(Number('0q82_01__0000'), Number(1).add_suffix())

    def test_add_suffix_payload(self):
        self.assertEqual(Number('0q82_01__3456_120300'), Number(1).add_suffix(0x12, b'\x34\x56'))

    def test_add_suffix_qstring(self):
        self.assertEqual('0q8201030100', Number(1).add_suffix(0x03).qstring(underscore=0))
        self.assertEqual('0q82_01__030100', Number(1).add_suffix(0x03).qstring())

    def test_add_suffix_qstring_empty(self):
        self.assertEqual('0q82010000', Number(1).add_suffix().qstring(underscore=0))
        self.assertEqual('0q82_01__0000', Number(1).add_suffix().qstring())

    def test_add_suffix_qstring_payload(self):
        self.assertEqual('0q82014455330300', Number(1).add_suffix(0x33, b'\x44\x55').qstring(underscore=0))
        self.assertEqual('0q82_01__4455_330300', Number(1).add_suffix(0x33, b'\x44\x55').qstring())

    def test_delete_suffix(self):
        n = Number('0q82_01__{:02X}0100'.format(Number.Suffix.TYPE_TEST))
        n_deleted = Number(n)
        n_deleted.delete_suffix(Number.Suffix.TYPE_TEST)
        self.assertEqual('0q82_01', n_deleted.qstring())

    def test_suffix_equality_impact(self):
        """
        In general, Number suffixes should impact equality.

        That is, a suffixed Number should not equal an unsuffixed number, not even its root.
        Or two numbers with different suffixes should not be equal.
        One exception is a complex number with a zero imaginary suffix, that should equal its
        root, real-only version.
        """
        n_plain = Number('0q82_01')
        n_suffixed = Number('0q82_01__7F0100')
        n_another_suffixed = Number('0q82_01__887F0200')

        self.assertTrue(n_plain == n_plain)
        self.assertFalse(n_plain == n_suffixed)
        self.assertFalse(n_suffixed == n_plain)
        self.assertTrue(n_suffixed == n_suffixed)

        self.assertTrue(n_suffixed == n_suffixed)
        self.assertFalse(n_suffixed == n_another_suffixed)
        self.assertFalse(n_another_suffixed == n_suffixed)
        self.assertTrue(n_another_suffixed == n_another_suffixed)

    def test_delete_suffix_among_many(self):
        n = Number('0q82_01__990100__880100__770100')
        n77 = Number(n)
        n77.delete_suffix(0x77)
        n88 = Number(n)
        n88.delete_suffix(0x88)
        n99 = Number(n)
        n99.delete_suffix(0x99)
        self.assertEqual('0q82_01__990100__880100', str(n77))
        self.assertEqual('0q82_01__990100__770100', str(n88))
        self.assertEqual('0q82_01__880100__770100', str(n99))

    def test_delete_suffix_multiple(self):
        n = Number('0q82_01__990100__880100__880100__110100__880100__880100__770100')
        n88 = Number(n)
        n88.delete_suffix(0x88)
        self.assertEqual('0q82_01__990100__110100__770100', str(n88))

    def test_delete_missing_suffix(self):
        n = Number('0q82_01__8201_7F0300')
        with self.assertRaises(Number.Suffix.NoSuchType):
            n.delete_suffix(Number.Suffix.TYPE_IMAGINARY)

    # noinspection PyClassHasNoInit
    def test_suffix_weird_type(self):
        class WeirdType:
            pass

        weird_type = WeirdType()
        with self.assertRaises(TypeError):
            Number.Suffix(0x11, weird_type)

    def test_suffix_class(self):
        suffix = Number.Suffix(0x03)
        self.assertEqual(0x03, suffix.type_)
        self.assertEqual(b'', suffix.payload)
        self.assertEqual(b'\x03\x01\x00', suffix.raw)

    def test_suffix_class_empty(self):
        suffix = Number.Suffix()
        self.assertEqual(None, suffix.type_)
        self.assertEqual(b'', suffix.payload)
        self.assertEqual(b'\x00\x00', suffix.raw)

    def test_suffix_class_payload(self):
        suffix = Number.Suffix(33, b'\xDE\xAD\xBE\xEF')
        self.assertEqual(33, suffix.type_)
        self.assertEqual(b'\xDE\xAD\xBE\xEF', suffix.payload)
        self.assertEqual(b'\xDE\xAD\xBE\xEF\x21\x05\x00', suffix.raw)

    def test_suffix_class_equality(self):
        suffix1  = Number.Suffix(0x01)
        another1 = Number.Suffix(0x01)
        suffix3  = Number.Suffix(0x03)
        another3 = Number.Suffix(0x03)
        self.assertTrue(suffix1 == another1)
        self.assertFalse(suffix1 == another3)
        self.assertFalse(suffix3 == another1)
        self.assertTrue(suffix3 == another3)

    def test_suffix_class_equality_payload(self):
        suffix11  = Number.Suffix(0x01, b'\x01\x11\x10')
        suffix13  = Number.Suffix(0x01, b'\x03\x33\x30')
        another13 = Number.Suffix(0x01, b'\x03\x33\x30')
        self.assertTrue(suffix11 == suffix11)
        self.assertFalse(suffix11 == suffix13)
        self.assertFalse(suffix13 == suffix11)
        self.assertTrue(suffix13 == another13)

    def test_suffix_class_qstring(self):
        self.assertEqual('0000', Number.Suffix().qstring())
        self.assertEqual('110100', Number.Suffix(0x11).qstring())
        self.assertEqual('2233110300', Number.Suffix(0x11, b'\x22\x33').qstring(underscore=0))
        self.assertEqual('2233_110300', Number.Suffix(0x11, b'\x22\x33').qstring())
        self.assertEqual('778899_110400', Number.Suffix(type_=0x11, payload=b'\x77\x88\x99').qstring())

    def test_parse_suffixes(self):
        self.assertEqual((Number(1), ), Number(1).parse_suffixes())
        self.assertEqual((Number(1), Number.Suffix()), Number(1).add_suffix().parse_suffixes())
        self.assertEqual((Number(1), Number.Suffix(3)), Number(1).add_suffix(3).parse_suffixes())
        self.assertEqual(
            (Number(1.75), Number.Suffix(111), Number.Suffix(222)),
            Number( 1.75).add_suffix(    111).add_suffix(    222).parse_suffixes()
        )

    def test_parse_suffixes_example_in_docstring(self):
        self.assertEqual(
            (Number(1), Number.Suffix(2), Number.Suffix(3, b'\x4567')),
             Number(1)    .add_suffix(2)    .add_suffix(3, b'\x4567').parse_suffixes()
        )

    def test_parse_multiple_suffixes(self):
        self.assertEqual(
            (Number(1), Number.Suffix(2), Number.Suffix(3)),
             Number(1)    .add_suffix(2)    .add_suffix(3).parse_suffixes()
        )

    def test_parse_suffixes_payload(self):
        self.assertEqual(
            (Number(22.25), Number.Suffix(123, b'')),
            Number( 22.25).add_suffix(    123, b'').parse_suffixes()
        )
        self.assertEqual(
            (Number(22.25), Number.Suffix(123, b' ')),
            Number( 22.25).add_suffix(    123, b' ').parse_suffixes()
        )
        self.assertEqual(
            (Number(22.25), Number.Suffix(123, b'\xAA\xBB\xCC')),
            Number( 22.25).add_suffix(    123, b'\xAA\xBB\xCC').parse_suffixes()
        )

    def test_parse_suffixes_is_passive(self):
        """Make sure x.parse_suffixes() does not modify x."""
        n_original = Number(1.75).add_suffix(111).add_suffix(222)
        nbytes_original = len(n_original.raw)
        n = Number(n_original)

        n.parse_suffixes()

        self.assertEqual(n_original, n)
        self.assertEqual(nbytes_original, len(n.raw))

    def test_malformed_suffix(self):
        """Nonsense suffixes (or illicit trailing 00-bytes) should raise ValueError exceptions."""
        with self.assertRaises(Number.SuffixValueError):
            Number('0q00').parse_suffixes()   # Where's the length byte?
        with self.assertRaises(Number.SuffixValueError):
            Number('0q0000').parse_suffixes()   # Can't suffix Number.NAN
        with self.assertRaises(Number.SuffixValueError):
            Number('0q220100').parse_suffixes()   # Can't suffix Number.NAN
        with self.assertRaises(Number.SuffixValueError):
            Number('0q334455_220400').parse_suffixes()   # Can't suffix Number.NAN
        with self.assertRaises(Number.SuffixValueError):
            Number('0q82_01__9900').parse_suffixes()
        with self.assertRaises(Number.SuffixValueError):
            Number('0q82_01__000400').parse_suffixes()
        with self.assertRaises(Number.SuffixValueError):
            Number('0q82_01__000300').parse_suffixes()   # Looks like suffixed Number.NAN.
        Number('0q82_01__000200').parse_suffixes()   # Yucky, but indistinguishable from valid
        Number('0q82_01__000100').parse_suffixes()
        Number('0q82_01__0000').parse_suffixes()

    def test_suffix_payload_too_long(self):
        self.assertEqual('11'*249 + '_08FA00', Number.Suffix(8, b'\x11' * 249).qstring())
        self.assertEqual('11'*250 + '_08FB00', Number.Suffix(8, b'\x11' * 250).qstring())
        with self.assertRaises(Number.SuffixValueError):
            Number.Suffix(8, b'\x11' * 251)
        with self.assertRaises(Number.SuffixValueError):
            Number.Suffix(8, b'\x11' * 252)

    def test_suffix_number(self):
        self.assertEqual('0q83_01FF__823F_FF0300', Number(511).add_suffix(255, Number(63)))
        # TODO:  Should '0q83_01FF__82_3F_FF0300' have an underscore in its payload Number?

    def test_suffix_extract_raw(self):
        self.assertEqual(b'\x33\x44', Number(1).add_suffix(0x11, b'\x33\x44').get_suffix_payload(0x11))

    def test_suffix_extract_raw_wrong(self):
        number_with_test_suffix = Number(1).add_suffix(Number.Suffix.TYPE_TEST, b'\x33\x44')
        with self.assertRaises(Number.Suffix.NoSuchType):
            number_with_test_suffix.get_suffix_payload(Number.Suffix.TYPE_IMAGINARY)

    def test_suffix_extract_raw_among_multiple(self):
        self.assertEqual(
            b'\x33\x44',
            Number(1).add_suffix(0x11, b'\x33\x44').add_suffix(0x22, b'\x88\x99').get_suffix_payload(0x11)
        )
        self.assertEqual(
            b'\x88\x99',
            Number(1).add_suffix(0x11, b'\x33\x44').add_suffix(0x22, b'\x88\x99').get_suffix_payload(0x22)
        )

    def test_suffix_extract_number(self):
        self.assertEqual(Number(88), Number(1).add_suffix(0x11, Number(88)).get_suffix_number(0x11))
        self.assertEqual(Number(-123.75), Number(1).add_suffix(0x11, Number(-123.75)).get_suffix_number(0x11))
        self.assertEqual(       -123.75 , Number(1).add_suffix(0x11, Number(-123.75)).get_suffix_number(0x11))
        self.assertIs(       Number, type(Number(1).add_suffix(0x11, Number(-123.75)).get_suffix_number(0x11)))

    def test_suffix_extract_number_missing(self):
        self.assertEqual(Number(88), Number(1).add_suffix(0x11, Number(88)).get_suffix_number(0x11))
        with self.assertRaises(Number.Suffix.NoSuchType):
            Number(1).add_suffix(0x99, Number(88)).get_suffix_number(0x11)
        with self.assertRaises(Number.Suffix.NoSuchType):
            Number(1).get_suffix_number(0x11)

    def test_suffix_number_parse(self):
        n = Number(99).add_suffix(0x11, Number(356))
        (idn, suffix) = n.parse_suffixes()
        self.assertIs(type(idn), Number)
        self.assertIs(type(suffix), Number.Suffix)
        self.assertEqual(Number(356), suffix.payload_number())

    def test_get_suffix(self):
        n = Number(99).add_suffix(0x11).add_suffix(0x22)
        s11 = n.get_suffix(0x11)
        s22 = n.get_suffix(0x22)
        self.assertEqual(s11, Number.Suffix(0x11))
        self.assertNotEqual(s11, Number.Suffix(0x22))
        self.assertEqual(s22, Number.Suffix(0x22))
        self.assertNotEqual(s22, Number.Suffix(0x11))

    def test_nan_suffix_empty(self):
        nan = Number(float('nan'))
        with self.assertRaises(Number.SuffixValueError):
            nan.add_suffix()

    def test_nan_suffix_type(self):
        nan = Number(float('nan'))
        with self.assertRaises(Number.SuffixValueError):
            nan.add_suffix(0x11)

    def test_nan_suffix_payload(self):
        nan = Number(float('nan'))
        with self.assertRaises(Number.SuffixValueError):
            nan.add_suffix(0x11, b'abcd')

    def test_is_suffixed(self):
        self.assertTrue(Number(22).add_suffix().is_suffixed())
        self.assertTrue(Number(22).add_suffix(0x11).is_suffixed())
        self.assertTrue(Number(22).add_suffix(0x11, b'abcd').is_suffixed())
        self.assertTrue(Number(22).add_suffix(0x11, Number(42)).is_suffixed())
        self.assertFalse(Number(22).is_suffixed())
        # noinspection PyUnresolvedReferences
        self.assertFalse(Number.NAN.is_suffixed())

    def test_suffix_float(self):
        self.assertEqual(16.0, float(Number('0q82_10')))
        self.assertEqual(16.0, float(Number('0q82_10__0000')))
        self.assertEqual(16.0, float(Number('0q82_10__7F0100')))
        self.assertEqual(16.0, float(Number('0q82_10__FFFFFF_7F0400')))
        self.assertEqual(16.0, float(Number('0q82_10__123456_7F0400')))
        self.assertEqual(16.0625, float(Number('0q82_1010')))

    def test_root(self):
        suffixed_word = Number(42).add_suffix(Number.Suffix.TYPE_TEST)
        self.assertEqual(Number(42), suffixed_word.root())


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

    def test_01_shift_leftward(self):
        self.assertEqual(0b000010000, shift_leftward(0b000010000, 0))
        self.assertEqual(0b000100000, shift_leftward(0b000010000, 1))
        self.assertEqual(0b000001000, shift_leftward(0b000010000,-1))

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
        self.assertEqual(0x807F99DEADBEEF00BADEFACE00, unpack_big_integer(b'\x80\x7F\x99\xDE\xAD\xBE\xEF\x00\xBA\xDE\xFA\xCE\x00'))

    def test_01_unpack_big_integer_by_brute(self):
        self.assertEqual(0, unpack_big_integer_by_brute(b''))
        self.assertEqual(0x1234, unpack_big_integer_by_brute(b'\x12\x34'))
        self.assertEqual(0x807F99DEADBEEF00BADEFACE00, unpack_big_integer_by_brute(b'\x80\x7F\x99\xDE\xAD\xBE\xEF\x00\xBA\xDE\xFA\xCE\x00'))

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

    # noinspection PyUnresolvedReferences
    def test_01_name_of_zone(self):
        self.assertEqual('TRANSFINITE', Number.name_of_zone[Number.Zone.TRANSFINITE])
        self.assertEqual('TRANSFINITE', Number.name_of_zone[Number(float('+inf')).zone])
        self.assertEqual('NAN', Number.name_of_zone[Number.Zone.NAN])
        self.assertEqual('NAN', Number.name_of_zone[Number.NAN.zone])
        self.assertEqual('NAN', Number.name_of_zone[Number().zone])
        self.assertEqual('ZERO', Number.name_of_zone[Number.Zone.ZERO])
        self.assertEqual('ZERO', Number.name_of_zone[Number(0).zone])


class PythonTests(NumberTests):
    """
    Testing internal Python features.

    Checking assumptions about Python itself.
    """

    def test_00_python_float_equality_weirdnesses(self):
        self.assertEqual(+0.0, -0.0)
        self.assertNotEqual(float('nan'), float('nan'))

    def test_00_python_ldexp(self):
        self.assertEqual(1.0, math.ldexp(.5, 1))
        self.assertEqual(-1.0, math.ldexp(-.5, 1))
        self.assertEqual(3.0, math.ldexp(.75, 2))
        self.assertEqual(100.0, math.ldexp(25, 2))   # ldexp() does more than invert frexp() -- it doesn't require a normalized mantissa
        self.assertEqual(625.0, math.ldexp(2500, -2))
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
        self.assertEqual((1 << 1000),              1.0715086071862673e+301)   # What does this?  Python math?  optimization?  assert comparison?  assert message?  Windows-only??
        self.assertEqual((1 << 1000)-1,             10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375)
        self.assertEqual(     pow(2,1000),         1.0715086071862673e+301)
        self.assertEqual(math.pow(2,1000),         1.0715086071862673e+301)
        self.assertEqual(     pow(2,1000)-1,        10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375)
        self.assertEqual(math.pow(2,1000)-1,       1.0715086071862673e+301)
        self.assertTrue (     pow(2,1000)-1      == 10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375)
        self.assertTrue (math.pow(2,1000)-1     == 1.0715086071862673e+301)

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

        self.assertFalse(b'' == b'\x00')
        self.assertFalse(b'' == b'\x80')
        self.assertFalse(b'\x80' == b'\x81')
        self.assertFalse(b'\x82' == b'\x82\x00')

    def test_02_big_int_unittest_equality(self):
        """Do Python integers and assertEqual handle googol with finesse?

        See also test_unittest_equality()."""
        googol        = 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
        googol_plus_1 = 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001
        self.assertEqual   (googol       , googol)
        self.assertNotEqual(googol       , googol_plus_1)
        self.assertNotEqual(googol_plus_1, googol)
        self.assertEqual   (googol_plus_1, googol_plus_1)

    def test_02_big_int_op_equality(self):
        """Do Python integers and the == operator handle googol with finesse?

        See also test_op_equality()."""
        googol        = 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
        googol_plus_1 = 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001
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


def py23(if2, if3_or_greater):
    if six.PY2:
        return if2
    else:
        return if3_or_greater

if __name__ == '__main__':
    import unittest
    unittest.main()


# TODO:  Don't test verbatim against str().  Test .qstring() instead.
# Because now '0q82_01' == str(Number(1))
# But someday maybe '1' == str(Number(1))
