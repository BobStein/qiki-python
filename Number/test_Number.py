"""
Testing qiki Number.py
"""

from Number import Number
import django.test
import math
import sys
import pickle
import textwrap
import six

class NumberTestCase(django.test.TestCase):

    def setUp(self):
        pass

    def test_raw(self):
        n = Number('0q82')
        self.assertEqual('\x82', n.raw)

    def test_raw_unicode(self):
        n = Number(u'0q82')
        self.assertEqual('\x82', n.raw)

    def test_hex(self):
        n = Number('0q82')
        self.assertEqual('82', n.hex())

    def test_str(self):
        n = Number('0q83_03E8')
        self.assertEqual("0q83_03E8", str(n))

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

    def test_repr(self):
        n =               Number('0q83_03E8')
        self.assertEqual("Number('0q83_03E8')", repr(n))

    def test_nan(self):
        self.assertEqual('0q', str(Number.NAN))
        self.assertEqual('', Number.NAN.raw)
        self.assertEqual('', Number.NAN.hex())
        self.assertEqual('nan', str(float(Number.NAN)))
        self.assertTrue(Number._floats_really_same(float('nan'), float(Number.NAN)))

    def test_nan_equality(self):
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
        with self.assertRaises(ValueError):
            number_has_no_qantissa.qantissa()

    def test_qexponent_unsupported(self):
        number_has_no_qexponent = Number(0)
        with self.assertRaises(ValueError):
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
        self.assertEqual(1.0, float(Number('0q82_00000000')))
        self.assertEqual(1.0, float(Number('0q82_00')))
        self.assertEqual(1.0, float(Number('0q82')))

    def test_alias_one_neg(self):
        self.assertEqual(-1.0, float(Number('0q7D_FF')))
        self.assertEqual(-1.0, float(Number('0q7D_FF00')))
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
        self.assertEqual(256.0, float(Number('0q83_00000000')))
        self.assertEqual(256.0, float(Number('0q83_00')))
        self.assertEqual(256.0, float(Number('0q83')))

        self.assertEqual(65536.0, float(Number('0q84_01')))
        self.assertEqual(65536.0, float(Number('0q84_00FFFFFF')))
        self.assertEqual(65536.0, float(Number('0q84_00C0')))
        self.assertEqual(65536.0, float(Number('0q84_0080')))
        self.assertEqual(65536.0, float(Number('0q84_0040')))
        self.assertEqual(65536.0, float(Number('0q84_00000000')))
        self.assertEqual(65536.0, float(Number('0q84_00')))
        self.assertEqual(65536.0, float(Number('0q84')))

    def test_alias_negative(self):
        self.assertEqual(-256.0, float(Number('0q7C_FF')))
        self.assertEqual(-256.0, float(Number('0q7C_FF00')))
        self.assertEqual(-256.0, float(Number('0q7C_FF3C7A38A1F250DE7E9071')))
        self.assertEqual(-256.0, float(Number('0q7C_FF40')))
        self.assertEqual(-256.0, float(Number('0q7C_FF80')))
        self.assertEqual(-256.0, float(Number('0q7C_FFC0')))
        self.assertEqual(-256.0, float(Number('0q7C_FFF0')))
        self.assertEqual(-256.0, float(Number('0q7C_FFFF')))
        self.assertEqual(-256.0, float(Number('0q7D')))

        self.assertEqual(-65536.0, float(Number('0q7B_FF')))
        self.assertEqual(-65536.0, float(Number('0q7B_FF00')))
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
        self.assertEqual(1.0/256.0, float(Number('0q81FF_00000000')))
        self.assertEqual(1.0/256.0, float(Number('0q81FF_00')))
        self.assertEqual(1.0/256.0, float(Number('0q81FF')))

        self.assertEqual(1.0/65536.0, float(Number('0q81FE_01')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_00FFFFFF')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_00C0')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_0080')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_0040')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_00000000')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE_00')))
        self.assertEqual(1.0/65536.0, float(Number('0q81FE')))

    def test_alias_negative_fractional(self):
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FF')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FF00')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FF3C7A38A1F250DE7E9071')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FF40')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FF80')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FFC0')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FFF0')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E00_FFFF')))
        self.assertEqual(-1.0/256.0, float(Number('0q7E01')))

        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FF')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FF00')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FF3C7A38A1F250DE7E9071')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FF40')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FF80')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FFC0')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FFF0')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E01_FFFF')))
        self.assertEqual(-1.0/65536.0, float(Number('0q7E02')))

    def test_ints_and_strings(self):

        def i__s(i,s):   # why a buncha calls to i__s() is superior to a 2D tuple:  so the stack trace identifies the line with the failing data
            assert isinstance(i, (int, long))
            assert isinstance(s, six.string_types)
            i_new = int(Number(s))
            s_new = str(Number(i))
            self.assertEqual(i, i_new, "%d != %d <--Number--- '%s'" %         (i, i_new,       s))
            self.assertEqual(s_new, s,       "%d ---Number--> '%s' != '%s'" % (i,       s_new, s))

        i__s(   2**1000-1,'0qFE_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__s(   2**1000-2,'0qFE_FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFE')
        i__s(   2**999+1, '0qFE_8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(   2**999,   '0qFE_80')
        i__s(   2**999-1, '0qFE_7FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__s(   2**998+1, '0qFE_4000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(   2**998,   '0qFE_40')
        i__s(   2**998-1, '0qFE_3FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')
        i__s( 256**124,   '0qFE_01')
        i__s( 256**123,   '0qFD_01')
        i__s(   2**500,   '0qC0_10')
        i__s(   2**496,   '0qC0_01')
        i__s(  10**100+1, '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10000000000000000000000001')   # googol + 1
        i__s(  10**100,   '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10')                           # googol
        i__s(  10**100-1, '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F0FFFFFFFFFFFFFFFFFFFFFFFFF')   # googol - 1
        i__s(1766847064778384329583297500742918515827483896875618958121606201292619776L,'0qA0_01')
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
        i__s(-2147483649L,'0q7A_7FFFFFFF')
        i__s(-4294967294, '0q7A_00000002')
        i__s(-4294967295, '0q7A_00000001')
        i__s(-4294967296, '0q79_FF')
        i__s(-4294967297, '0q79_FEFFFFFFFF')
        i__s(-4294967298, '0q79_FEFFFFFFFE')
        i__s(  -2**125,   '0q6E_E0')
        i__s(  -2**250,   '0q5E_FC')
        i__s(  -2**375,   '0q4F_80')
        i__s(  -204586912993508866875824356051724947013540127877691549342705710506008362275292159680204380770369009821930417757972504438076078534117837065833032974336L,
                          '0q3F_FF')
        i__s(  -2**496,   '0q3F_FF')
        i__s(  -3273390607896141870013189696827599152216642046043064789483291368096133796404674554883270092325904157150886684127560071009217256545885393053328527589376L,
                          '0q3F_F0')
        i__s(  -2**500,   '0q3F_F0')
        i__s(  -2**625,   '0q2F_FE')
        i__s(  -2**750,   '0q20_C0')
        i__s(  -2**875,   '0q10_F8')
        i__s(  -5357543035931336604742125245300009052807024058527668037218751941851755255624680612465991894078479290637973364587765734125935726428461570217992288787349287401967283887412115492710537302531185570938977091076523237491790970633699383779582771973038531457285598238843271083830214915826312193418602834034687L,
                          '0q01_8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(  -2**999+1, '0q01_8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(  -5357543035931336604742125245300009052807024058527668037218751941851755255624680612465991894078479290637973364587765734125935726428461570217992288787349287401967283887412115492710537302531185570938977091076523237491790970633699383779582771973038531457285598238843271083830214915826312193418602834034688L,
                          '0q01_80')
        i__s(  -2**999,   '0q01_80')
        i__s(  -10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375L,
                          '0q01_0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')
        i__s(  -2**1000+1,'0q01_0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001')

    def test_integer_nan(self):
        nan = Number(float('nan'))
        with self.assertRaises(ValueError):
            int(nan)

    def test_integer_infinity(self):
        pinf = Number(float('+inf'))
        with self.assertRaises(OverflowError):
            int(pinf)
        ninf = Number(float('-inf'))
        with self.assertRaises(OverflowError):
            int(ninf)

    def test_integer_infinitesimal(self):
        self.assertEqual(0, int(Number('0q807F')))
        self.assertEqual(0, int(Number('0q80')))
        self.assertEqual(0, int(Number('0q7F81')))
        self.assertEqual('0q80', Number(0).qstring())

    def assertEqualSets(self, s1, s2):
        if s1 != s2:
            self.fail("Left extras:\n\t%s\nRight extras:\n\t%s\n" % (
                '\n\t'.join((str(z) for z in (s1-s2))),
                '\n\t'.join((str(z) for z in (s2-s1))),
            ))

    def test_zone_sets(self):
        self.assertEqualSets(Number.ZONE_ALL, Number._ZONE_ALL_BY_FINITENESS)
        self.assertEqualSets(Number.ZONE_ALL, Number._ZONE_ALL_BY_ZERONESS)
        self.assertEqualSets(Number.ZONE_ALL, Number._ZONE_ALL_BY_REASONABLENESS)

    def test_zone(self):
        self.assertEqual(Number.Zone.TRANSFINITE,         Number('0qFF81').zone)
        self.assertEqual(Number.Zone.LUDICROUS_LARGE,     Number('0qFF00FFFF_5F5E00FF').zone)
        self.assertEqual(Number.Zone.POSITIVE,            Number('0q82_2A').zone)
        self.assertEqual(Number.Zone.ONE,                 Number('0q82_01').zone)
        self.assertEqual(Number.Zone.ONE,                 Number('0q82').zone)
        self.assertEqual(Number.Zone.FRACTIONAL,          Number('0q81FF_80').zone)
        self.assertEqual(Number.Zone.LUDICROUS_SMALL,     Number('0q80FF0000_FA0A1F01').zone)
        self.assertEqual(Number.Zone.INFINITESIMAL,       Number('0q807F').zone)
        self.assertEqual(Number.Zone.ZERO,                Number('0q80').zone)
        self.assertEqual(Number.Zone.INFINITESIMAL_NEG,   Number('0q7F81').zone)
        self.assertEqual(Number.Zone.LUDICROUS_SMALL_NEG, Number('0q7F00FFFF_5F5E00FF').zone)
        self.assertEqual(Number.Zone.FRACTIONAL_NEG,      Number('0q7E00_80').zone)
        self.assertEqual(Number.Zone.ONE_NEG,             Number('0q7E').zone)
        self.assertEqual(Number.Zone.ONE_NEG,             Number('0q7D_FF').zone)
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

    def test_float_qigits_default_nonsticky(self):
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1)))
        self.assertEqual('0q82_0119999A', str(Number(1.1, qigits=4)))
        self.assertEqual('0q82_01199999999999A0', str(Number(1.1)))

    def test_float_qigits_neg(self):
        self.assertEqual('0q7D_FEE6666667', str(Number(-1.1, qigits=5)))
        self.assertEqual('0q7D_FEE666666667', str(Number(-1.1, qigits=6)))
        self.assertEqual('0q7D_FEE66666666667', str(Number(-1.1, qigits=7)))
        self.assertEqual('0q7D_FEE6666666666660', str(Number(-1.1, qigits=8)))   # float's 52-bit significand
        self.assertEqual('0q7D_FEE6666666666660', str(Number(-1.1, qigits=9)))   # TODO: test rounding for negatives

    def test_floats_and_strings(self):

        def f__s(x_in, s_out, s_in_opt=None):
            assert isinstance(x_in,      float),                                 "f__s(%s,_) should be a float"  % type(x_in).__name__
            assert isinstance(s_out,    six.string_types),                       "f__s(_,%s) should be a string" % type(s_out).__name__
            assert isinstance(s_in_opt, six.string_types) or s_in_opt is None, "f__s(_,_,%s) should be a string" % type(s_in_opt).__name__
            x_out = x_in
            s_in = s_out if s_in_opt is None else s_in_opt

            try:
                x_new = float(Number(s_in))
            except Exception as e:
                print("%s(%s) <--Number--- %s" % (e.__class__.__name__, e.message, s_in))
                raise
            match_x = Number._floats_really_same(x_new, x_out)

            try:
                s_new = str(Number(x_in))
            except Exception as e:
                print("%.17e ---Number--> %s(%s)" % (x_in, e.__class__.__name__, e.message))
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

        class context:   # variables that are local to test_floats_and_strings(), but global to f__s()
            the_first = True
            after_zone_boundary = False

        def zone_boundary():
            context.after_zone_boundary = True


        f__s(float('+inf'),               '0qFF_81')
        zone_boundary()
        f__s(float('+inf'),               '0qFF_81', '0qFF00FFFF_5F5E00FF_01')   # 2**99999999, a ludicrously large positive number
        zone_boundary()
        f__s(math.pow(2,999),             '0qFE_80')
        f__s(       1e100+1.0,            '0qAB_1249AD2594C37D', '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10000000000000000000000001')   # googol+1 (though float can't distinguish)
        f__s(       1e100,                '0qAB_1249AD2594C37D', '0qAB_1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10')   # googol
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

        f__s(      1111.111111111111313,  '0q83_04571C71C71C72')
        f__s(      1111.111111111111111,  '0q83_04571C71C71C71C0')   # float has about 17 significant digits

        f__s(      1111.1111111,          '0q83_04571C71C6ECB9')
        f__s(      1024.0,                '0q83_04')
        f__s(       512.0,                '0q83_02')
        f__s(       258.0,                '0q83_0102')
        f__s(       257.0,                '0q83_0101')
        f__s(       256.0,                '0q83_01')
        f__s(       256.0,                '0q83_01', '0q83')   # alias for +256
        f__s(       255.5,                '0q82_FF80')
        f__s(       255.0,                '0q82_FF')
        f__s(       254.0,                '0q82_FE')
        f__s(       128.0,                '0q82_80')
        f__s(         2.5,                '0q82_0280')
        f__s(         2.4,                '0q82_0266666666666660')
        f__s(         2.3,                '0q82_024CCCCCCCCCCCC0')
        f__s(         2.2,                '0q82_0233333333333340')
        f__s(         2.1,                '0q82_02199999999999A0')
        f__s(         2.0,                '0q82_02')
        f__s(         1.875,              '0q82_01E0')
        f__s(         1.75,               '0q82_01C0')
        f__s(         1.5,                '0q82_0180')
        f__s(         1.25,               '0q82_0140')
        f__s(         1.125,              '0q82_0120')
        f__s(         1.1,                '0q82_01199999999999A0')
        f__s(         1.0625,             '0q82_0110')
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
        zone_boundary()
        f__s(         1.0,                '0q82_01')
        f__s(         1.0,                '0q82_01',  '0q82')   # alias for +1
        zone_boundary()
        f__s(         0.99999237060546875,'0q81FF_FFFF80')
        f__s(         0.9998779296875,    '0q81FF_FFF8')
        f__s(         0.998046875,        '0q81FF_FF80')
        f__s(         0.96875,            '0q81FF_F8')
        f__s(         0.9375,             '0q81FF_F0')
        f__s(         0.875,              '0q81FF_E0')
        f__s(         0.75,               '0q81FF_C0')
        f__s(         0.5,                '0q81FF_80')
        f__s(         0.25,               '0q81FF_40')
        f__s(         0.125,              '0q81FF_20')
        f__s(         0.0625,             '0q81FF_10')
        f__s(         0.03125,            '0q81FF_08')
        f__s(         0.015625,           '0q81FF_04')
        f__s(         0.01171875,         '0q81FF_03')
        f__s(         0.0078125,          '0q81FF_02')
        f__s(         0.0039520263671875, '0q81FF_0103') # 259/65536
        f__s(         0.003936767578125,  '0q81FF_0102') # 258/65536
        f__s(         0.0039215087890625, '0q81FF_0101') # 257/65536
        f__s(         0.00390625,         '0q81FF_01')   # 256/65536       aka 1/256
        f__s(         0.00390625,         '0q81FF_01', '0q81FF')   # alias for 1/256
        f__s(         0.0038909912109375, '0q81FE_FF')   # 255/65536
        f__s(         0.003875732421875,  '0q81FE_FE')   # 254/65536
        f__s(         0.0038604736328125, '0q81FE_FD')   # 253/65536
        f__s(         0.001953125,        '0q81FE_80')
        f__s(         0.0009765625,       '0q81FE_40')
        f__s(         0.00048828125,      '0q81FE_20')
        f__s(         0.000244140625,     '0q81FE_10')
        f__s(         0.0001220703125,    '0q81FE_08')
        f__s(         0.00006103515625,   '0q81FE_04')
        f__s(         0.000030517578125,  '0q81FE_02')
        f__s(         0.0000152587890625, '0q81FE_01')
        f__s(math.pow(256, -2),           '0q81FE_01')
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
        f__s(         0.0,                '0q80',  '0q80FF0000_FA0A1F01_01')   # 2**-99999999, a ludicrously small positive number
        zone_boundary()
        f__s(         0.0,                '0q80',  '0q807F')   # +infinitessimal
        zone_boundary()
        f__s(         0.0,                '0q80')
        zone_boundary()
        f__s(         -0.0,               '0q80',  '0q7F81')   # -infinitessimal
        zone_boundary()
        f__s(         -0.0,               '0q80',  '0q7F00FFFF_5F5E00FF_01')   # -2**-99999999, a ludicrously small negative number
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
        zone_boundary()
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
        f__s(        -1.1,                '0q7D_FEE6666666666660')  # TODO: more rational weirdos
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
        f__s(-math.pow(2,1000),           '0q00_FF', '0q01')   # this bug goes over the edge -- until TODO: Ludicrous Numbers are supported
        zone_boundary()
        f__s(float('-inf'),               '0q00_7F', '0q00FF0000_FA0A1F01_01')   # -2**99999999, a ludicrously large negative number
        zone_boundary()
        f__s(float('-inf'),               '0q00_7F')
        zone_boundary()
        f__s(float('nan'),                '0q')

    def test_copy_constructor(self):
        self.assertEqual('0q83_03E8', str(Number(Number('0q83_03E8'))))
        self.assertEqual('0q7C_FEFF', str(Number(Number('0q7C_FEFF'))))

    def test_sizeof(self):
        self.assertIn(sys.getsizeof(Number('0q')), (28, 32))  # depends on Zone.__slots__ containing _zone or not
        self.assertIn(sys.getsizeof(Number('0q80')), (28, 32))
        self.assertIn(sys.getsizeof(Number('0q83_03E8')), (28, 32))
        self.assertIn(sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8')), (28, 32))
        self.assertIn(sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8')), (28, 32))

        self.assertEqual(21, sys.getsizeof(Number('0q').raw))
        self.assertEqual(22, sys.getsizeof(Number('0q80').raw))
        self.assertEqual(23, sys.getsizeof(Number('0q82_01').raw))
        self.assertEqual(24, sys.getsizeof(Number('0q83_03E8').raw))
        self.assertEqual(25, sys.getsizeof(Number('0q82_018888').raw))
        self.assertEqual(45, sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8').raw))
        self.assertEqual(144,sys.getsizeof(Number('0q83_03E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8E8').raw))

        self.assertEqual(21, sys.getsizeof(''))
        self.assertEqual(22, sys.getsizeof('\x80'))
        self.assertEqual(24, sys.getsizeof('\x83\x03\xE8'))
        self.assertEqual(45, sys.getsizeof('\x83\x03\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8\xE8'))

    def assertIses(self, number_able, is_zero = None, all_true = None, all_false = None):
        number = Number(number_able)
        if is_zero is not None:
            self.assertEqual(is_zero, number.is_zero())

    def someday_test_is(self):
        self.assertTrue(Number('0q80').iszero())
        self.assertFalse(Number('0q80').nonzero())
        self.assertIses('0q80', is_zero=True,  all_true=('zero'),     all_false=('infinite', 'negative', 'positive'))
        self.assertIses('0q82', is_zero=False, all_true=('positive'), all_false=('infinite', 'negative', 'zero'))
        self.assertIses('0q7E', is_zero=False, all_true=('negative'), all_false=('infinite', 'zero', 'positive'))
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

    def test_uneven_hex(self):
        if getattr(Number, "WE_ARE_BEING_SUPER_STRICT_ABOUT_THERE_BEING_AN_EVEN_NUMBER_OF_HEX_DIGITS", False):
            with self.assertRaises(ValueError):
                Number('0q8')
            with self.assertRaises(ValueError):
                Number('0q8_')
            with self.assertRaises(ValueError):
                Number('0q_8')
            with self.assertRaises(ValueError):
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

        with self.assertRaises(ValueError):
            Number('0q8X')
        with self.assertRaises(ValueError):
            Number('0q82_FG')

    def test_bad_string_prefix(self):
        Number('0q')
        Number('0q80')
        with self.assertRaises(ValueError):
            Number('')
        with self.assertRaises(ValueError):
            Number('00q80')
        with self.assertRaises(ValueError):
            Number('q80')
        with self.assertRaises(ValueError):
            Number('80')
        with self.assertRaises(ValueError):
            Number('80')

    def test_from_int_negative(self):
        self.assertEqual('0q80',    str(Number(-0)))
        self.assertEqual('0q7D_FF',    str(Number(-1)))
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
        with self.assertRaises(ValueError):
             Number('\x82\x01')
        self.assertEqual(Number(1), Number.from_raw('\x82\x01'))

    def test_from_raw(self):
        self.assertEqual('',             Number.from_raw('').raw)
        self.assertEqual('\x80',         Number.from_raw('\x80').raw)
        self.assertEqual('\x83\x03\xE8', Number.from_raw('\x83\x03\xE8').raw)

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
        self.assertFalse(Number(1.0) ==        (0.0))
        self.assertTrue (Number(0.0) ==        (0.0))
        self.assertFalse(Number(0.0) ==        (1.0))
        self.assertTrue (Number(1.0) !=        (0.0))
        self.assertFalse(Number(0.0) !=        (0.0))
        self.assertTrue (Number(0.0) !=        (1.0))

        self.assertFalse(Number(1.0) <        (0.0))
        self.assertFalse(Number(0.0) <        (0.0))
        self.assertTrue (Number(0.0) <        (1.0))
        self.assertFalse(Number(1.0) <=       (0.0))
        self.assertTrue (Number(0.0) <=       (0.0))
        self.assertTrue (Number(0.0) <=       (1.0))
        self.assertTrue (Number(1.0) >        (0.0))
        self.assertFalse(Number(0.0) >        (0.0))
        self.assertFalse(Number(0.0) >        (1.0))
        self.assertTrue (Number(1.0) >=       (0.0))
        self.assertTrue (Number(0.0) >=       (0.0))
        self.assertFalse(Number(0.0) >=       (1.0))

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

    def test_pickle(self):
        self.assertIn(pickle.dumps(Number), (
            textwrap.dedent("""\
                cNumber.Number
                Number
                p0
                ."""),   # when run via qiki_take_one
            textwrap.dedent("""\
                cNumber
                Number
                p0
                ."""),   # when run via number_playground
        ))

        x314 = Number(3.14)
        self.assertIn(pickle.dumps(x314), (
            textwrap.dedent("""\
                ccopy_reg
                _reconstructor
                p0
                (cNumber.Number
                Number
                p1
                c__builtin__
                object
                p2
                Ntp3
                Rp4
                S%s
                p5
                b.""") % repr(x314.raw),
            textwrap.dedent("""\
                ccopy_reg
                _reconstructor
                p0
                (cNumber
                Number
                p1
                c__builtin__
                object
                p2
                Ntp3
                Rp4
                S%s
                p5
                b.""") % repr(x314.raw),
        ))

        y314 = pickle.loads(pickle.dumps(x314))
        self.assertEqual(x314, y314)



    ################## testing internal methods ###########################

    def test_pack_integer(self):
        """Test both _pack_big_integer and its less-efficient but more-universal variant, _pack_big_integer_Mike_Boers
        """
        def test_both_methods(packed_bytes, number, nbytes):
            self.assertEqual(packed_bytes, Number._pack_big_integer_Mike_Boers(number,nbytes))
            self.assertEqual(packed_bytes, Number._pack_integer(number,nbytes))

        test_both_methods(                '\x00', 0,1)
        test_both_methods(    '\x00\x00\x00\x00', 0,4)
        test_both_methods(    '\x00\x00\x00\x01', 1,4)
        test_both_methods(    '\x00\x00\x00\x64', 100,4)
        test_both_methods(    '\x00\x00\xFF\xFE', 65534L,4)
        test_both_methods(    '\xFF\xFF\xFF\xFE', 4294967294,4)

        test_both_methods('\x00\xFF\xFF\xFF\xFE', 4294967294,5)
        test_both_methods('\x00\xFF\xFF\xFF\xFF', 4294967295,5)
        test_both_methods('\x01\x00\x00\x00\x00', 4294967296,5)
        test_both_methods('\x01\x00\x00\x00\x01', 4294967297,5)
        test_both_methods('\x01\x00\x00\x00\x02', 4294967298,5)

        test_both_methods(    '\xFF\xFF\xFF\xFF', -1,4)
        test_both_methods('\xFF\xFF\xFF\xFF\xFF', -1,5)

        test_both_methods('\xFF\xFF\xFF\x00\x02', -65534,5)

        test_both_methods('\xFF\x80\x00\x00\x01', -2147483647,5)
        test_both_methods('\xFF\x80\x00\x00\x00', -2147483648,5)
        test_both_methods('\xFF\x7F\xFF\xFF\xFF', -2147483649,5)
        test_both_methods('\xFF\x7F\xFF\xFF\xFE', -2147483650,5)

        test_both_methods('\xFF\x00\x00\x00\x01', -4294967295,5)
        test_both_methods('\xFF\x00\x00\x00\x00', -4294967296,5)
        test_both_methods('\xFE\xFF\xFF\xFF\xFF', -4294967297,5)
        test_both_methods('\xFE\xFF\xFF\xFF\xFE', -4294967298,5)

    def test_pack_small_integer_not_enough_nbytes(self):
        """
        small int, enforces low nbytes, but doesn't matter for Number's purposes
        """
        self.assertEqual('\x11', Number._pack_integer(0x1111,1))
        self.assertEqual('\x11\x11', Number._pack_integer(0x1111,2))
        self.assertEqual('\x00\x11\x11', Number._pack_integer(0x1111,3))
        self.assertEqual('\x00\x00\x11\x11', Number._pack_integer(0x1111,4))
        self.assertEqual('\x00\x00\x00\x11\x11', Number._pack_integer(0x1111,5))

    def test_pack_integer_not_enough_nbytes_negative(self):
        """
        small int, enforces low nbytes, but doesn't matter for Number's purposes
        """
        self.assertEqual('\xAB', Number._pack_integer(-0x5555,1))
        self.assertEqual('\xAA\xAB', Number._pack_integer(-0x5555,2))
        self.assertEqual('\xFF\xAA\xAB', Number._pack_integer(-0x5555,3))
        self.assertEqual('\xFF\xFF\xAA\xAB', Number._pack_integer(-0x5555,4))
        self.assertEqual('\xFF\xFF\xFF\xAA\xAB', Number._pack_integer(-0x5555,5))

    def test_pack_big_integer_not_enough_nbytes(self):
        """
        big int, ignores low nbytes, but doesn't matter for Number's purposes
        """
        self.assertEqual('\x11\x11\x11\x11\x11', Number._pack_integer(0x1111111111,4))
        self.assertEqual('\x11\x11\x11\x11\x11', Number._pack_integer(0x1111111111,5))
        self.assertEqual('\x00\x11\x11\x11\x11\x11', Number._pack_integer(0x1111111111,6))

    def test_pack_integer_auto_nbytes(self):
        self.assertEqual('\x01', Number._pack_integer(0x01))
        self.assertEqual('\x04', Number._pack_integer(0x04))
        self.assertEqual('\xFF', Number._pack_integer(0xFF))
        self.assertEqual('\x01\x00', Number._pack_integer(0x100))
        self.assertEqual('\x01\x01', Number._pack_integer(0x101))
        self.assertEqual('\xFF\xFF', Number._pack_integer(0xFFFF))
        self.assertEqual('\x01\x00\x00', Number._pack_integer(0x10000))
        self.assertEqual('\x01\x00\x01', Number._pack_integer(0x10001))

    def test_pack_integer_auto_nbytes_negative(self):
        self.assertEqual('\xFF', Number._pack_integer(-0x01))
        self.assertEqual('\xFC', Number._pack_integer(-0x04))
        self.assertEqual('\x01', Number._pack_integer(-0xFF))  # an UNSIGNED negative number in two's complement
        self.assertEqual('\xFF\x01', Number._pack_integer(-0xFF,2))  # (nbytes+=1 to get a sign bit)
        self.assertEqual('\xFF\x00', Number._pack_integer(-0x100))
        self.assertEqual('\xFE\xFF', Number._pack_integer(-0x101))
        self.assertEqual('\x00\x01', Number._pack_integer(-0xFFFF))
        self.assertEqual('\xFF\x00\x00', Number._pack_integer(-0x10000))
        self.assertEqual('\xFE\xFF\xFF', Number._pack_integer(-0x10001))

    def test_unpack_big_integer(self):
        self.assertEqual(0L, Number._unpack_big_integer(''))
        self.assertEqual(0x1234L, Number._unpack_big_integer('\x12\x34'))
        self.assertEqual( 0x807F99DEADBEEF00L, Number._unpack_big_integer(    '\x80\x7F\x99\xDE\xAD\xBE\xEF\x00'))
        self.assertEqual( 0xFFFFFFFFFFFFFF77L, Number._unpack_big_integer(    '\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x77'))
        self.assertEqual( 0xFFFFFFFFFFFFFFFEL, Number._unpack_big_integer(    '\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE'))
        self.assertEqual( 0xFFFFFFFFFFFFFFFFL, Number._unpack_big_integer(    '\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'))
        self.assertEqual(0x10000000000000000L, Number._unpack_big_integer('\x01\x00\x00\x00\x00\x00\x00\x00\x00'))
        self.assertEqual(0x10000000000000001L, Number._unpack_big_integer('\x01\x00\x00\x00\x00\x00\x00\x00\x01'))
        self.assertEqual(0x10000000000000022L, Number._unpack_big_integer('\x01\x00\x00\x00\x00\x00\x00\x00\x22'))
        self.assertEqual(0x807F99DEADBEEF00BADEFACE00L, Number._unpack_big_integer('\x80\x7F\x99\xDE\xAD\xBE\xEF\x00\xBA\xDE\xFA\xCE\x00'))

    def test_unpack_big_integer_by_brute(self):
        self.assertEqual(0L, Number._unpack_big_integer_by_brute(''))
        self.assertEqual(0x1234L, Number._unpack_big_integer_by_brute('\x12\x34'))
        self.assertEqual(0x807F99DEADBEEF00BADEFACE00L, Number._unpack_big_integer_by_brute('\x80\x7F\x99\xDE\xAD\xBE\xEF\x00\xBA\xDE\xFA\xCE\x00'))

    def test_unpack_big_integer_by_struct(self):
        self.assertEqual(0L, Number._unpack_big_integer_by_struct(''))
        self.assertEqual(0x00L, Number._unpack_big_integer_by_struct('\x00'))
        self.assertEqual(0x1234L, Number._unpack_big_integer_by_struct('\x12\x34'))
        self.assertEqual(0xFFFFFFFFFFFFFFFEL, Number._unpack_big_integer_by_struct('\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE'))
        self.assertEqual(0xFFFFFFFFFFFFFFFFL, Number._unpack_big_integer_by_struct('\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'))
        with self.assertRaises(Exception):
            Number._unpack_big_integer_by_struct('\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF')
        with self.assertRaises(Exception):
            Number._unpack_big_integer_by_struct('ninebytes')

    def test_exp256(self):
        self.assertEqual(1, Number._exp256(0))
        self.assertEqual(256, Number._exp256(1))
        self.assertEqual(65536, Number._exp256(2))
        self.assertEqual(4294967296L, Number._exp256(4))
        self.assertEqual(1208925819614629174706176L, Number._exp256(10))
        self.assertEqual(2**800, Number._exp256(100))

    def test_hex_even(self):
        self.assertEqual('05', Number._hex_even(0x5))
        self.assertEqual('55', Number._hex_even(0x55))
        self.assertEqual('0555', Number._hex_even(0x555))
        self.assertEqual('5555', Number._hex_even(0x5555))
        self.assertEqual('055555', Number._hex_even(0x55555))
        self.assertEqual('555555', Number._hex_even(0x555555))
        self.assertEqual('05555555', Number._hex_even(0x5555555))
        self.assertEqual('55555555', Number._hex_even(0x55555555))
        self.assertEqual(  '555555555555555555', Number._hex_even(0x555555555555555555))
        self.assertEqual('05555555555555555555', Number._hex_even(0x5555555555555555555))
        self.assertEqual('AAAAAAAA', Number._hex_even(0xAAAAAAAA).upper())

    def test_left_pad00(self):
        self.assertEqual('abc', Number._left_pad00('abc', 1))
        self.assertEqual('abc', Number._left_pad00('abc', 2))
        self.assertEqual('abc', Number._left_pad00('abc', 3))
        self.assertEqual('\x00abc', Number._left_pad00('abc', 4))
        self.assertEqual('\x00\x00abc', Number._left_pad00('abc', 5))
        self.assertEqual('\x00\x00\x00abc', Number._left_pad00('abc', 6))

    def test_right_strip00(self):
        self.assertEqual('abc', Number._right_strip00('abc'))
        self.assertEqual('abc', Number._right_strip00('abc\x00'))
        self.assertEqual('abc', Number._right_strip00('abc\x00\x00'))
        self.assertEqual('abc', Number._right_strip00('abc\x00\x00\x00'))

    def test_floats_really_same(self):
        self.assertTrue (Number._floats_really_same(1.0, 1.0))
        self.assertFalse(Number._floats_really_same(1.0, 0.0))
        self.assertFalse(Number._floats_really_same(1.0, float('nan')))
        self.assertFalse(Number._floats_really_same(float('nan'), 1.0))
        self.assertTrue (Number._floats_really_same(float('nan'), float('nan')))

        self.assertTrue (Number._floats_really_same(+0.0, +0.0))
        self.assertFalse(Number._floats_really_same(+0.0, -0.0))
        self.assertFalse(Number._floats_really_same(-0.0, +0.0))
        self.assertTrue (Number._floats_really_same(-0.0, -0.0))

    def test_python_float_equality_weirdnesses(self):
        self.assertEqual(+0.0, -0.0)
        self.assertNotEqual(float('nan'), float('nan'))


    ################## checking python assumptions ###########################

    def test_python_int_floors_toward_zero(self):
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

    def test_python_weird_big_math(self):
        self.assertEqual((1L << 1000),             1.0715086071862673e+301)   # What does this?  Python math?  optimization?  assert comparison?  assert message?  Windows-only??
        self.assertEqual((1L << 1000)-1L,           10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375L)

        self.assertEqual(     pow(2,1000),          1.0715086071862673e+301)
        self.assertEqual(math.pow(2,1000),          1.0715086071862673e+301)

        self.assertEqual(    pow(2,1000)-1L,        10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375L)
        self.assertEqual(math.pow(2,1000)-1L,       1.0715086071862673e+301)

        self.assertTrue (    pow(2,1000)-1L      == 10715086071862673209484250490600018105614048117055336074437503883703510511249361224931983788156958581275946729175531468251871452856923140435984577574698574803934567774824230985421074605062371141877954182153046474983581941267398767559165543946077062914571196477686542167660429831652624386837205668069375L)
        self.assertTrue (math.pow(2,1000)-1L     == 1.0715086071862673e+301)

    def test_python_binary_shift_negative_left(self):
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

        self.assertEqual(-1267650600228229401496703205376L, -1 << 100)

    def test_python_binary_shift_negative_right(self):
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

        self.assertEqual(-2, -65536 >> 15)
        self.assertEqual(-1, -65536 >> 16)

        self.assertEqual(-2, -16777216 >> 23)
        self.assertEqual(-1, -16777216 >> 24)

        self.assertEqual(-2L, -4294967296L >> 31)
        self.assertEqual(-1L, -4294967296L >> 32)

        self.assertEqual(-2L, -1267650600228229401496703205376L >> 99)
        self.assertEqual(-1L, -1267650600228229401496703205376L >> 100)

    def test_python_binary_shift_left(self):
        self.assertEqual(256, 1 << 8)
        self.assertEqual(256*256, 1 << 8*2)
        self.assertEqual(256*256*256, 1 << 8*3)
        self.assertEqual(256*256*256*256, 1 << 8*4)
        self.assertEqual(256*256*256*256*256, 1 << 8*5)
        self.assertEqual(256*256*256*256*256*256, 1 << 8*6)
        self.assertEqual(       281474976710656L, 1 << 8*6)
        self.assertEqual(256*256*256*256*256*256*256*256*256*256*256*256*256*256*256*256*256*256*256*256, 1 << 8*20)
        self.assertEqual(                             1461501637330902918203684832716283019655932542976L, 1 << 8*20)

    def test_python_binary_string_comparison(self):
        self.assertTrue('\x81' < '\x82')
        self.assertTrue('\x80' < '\x81')
        self.assertTrue('\x7F' < '\x80')
        self.assertTrue('\x7E' < '\x7F')

        self.assertFalse('\x80' < '\x80')
        self.assertFalse('\x7F' < '\x7F')
        self.assertFalse('\x82' < '\x82')
        self.assertTrue( '\x82' < '\x82\x00')
        self.assertFalse('\x82\x00' < '\x82')

        self.assertTrue( '\x00' == '\x00')
        self.assertFalse('\x00' <  '\x00')

        self.assertFalse('\x00' == '\x00\x00')
        self.assertTrue( '\x00' <  '\x00\x00')

        self.assertFalse('\x00' == '\x00\x01')
        self.assertTrue( '\x00' <  '\x00\x01')

        self.assertFalse('\x00' == '\x00\xFF')
        self.assertTrue( '\x00' <  '\x00\xFF')

        self.assertTrue( '\x00\x41' == '\x00\x41')
        self.assertFalse('\x00\x41' <  '\x00\x41')

        self.assertFalse('\x00\x41' == '\x00\x42')
        self.assertTrue( '\x00\x41' <  '\x00\x42')

        self.assertTrue('\x82' == '\x82')
        self.assertTrue('\x81' == '\x81')
        self.assertTrue('\x80' == '\x80')
        self.assertTrue('\x7F' == '\x7F')

        self.assertFalse('' == '\x00')
        self.assertFalse('' == '\x80')
        self.assertFalse('\x80' == '\x81')
        self.assertFalse('\x82' == '\x82\x00')

if __name__ == '__main__':
    import unittest
    unittest.main()   # TODO: why 0 tests?
