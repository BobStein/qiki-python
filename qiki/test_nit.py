"""
Unit tests for Nit, Integer
"""


import binascii
import json
import unittest

import nit
from nit import N


class IntegerTests(unittest.TestCase):

    def test_integer_bytes(self):
        self.assertEqual(b'\x01\x00\x02', nit.Integer(65538).bytes)
        self.assertEqual(b'\x01\x00\x01', nit.Integer(65537).bytes)
        self.assertEqual(b'\x01\x00\x00', nit.Integer(65536).bytes)
        self.assertEqual(b'\x00\xFF\xFF', nit.Integer(65535).bytes)
        self.assertEqual(b'\x00\xFF\xFE', nit.Integer(65534).bytes)

        self.assertEqual(b'\x00\x80\x02', nit.Integer(32770).bytes)
        self.assertEqual(b'\x00\x80\x01', nit.Integer(32769).bytes)
        self.assertEqual(b'\x00\x80\x00', nit.Integer(32768).bytes)
        self.assertEqual(    b'\x7F\xFF', nit.Integer(32767).bytes)
        self.assertEqual(    b'\x7F\xFE', nit.Integer(32766).bytes)

        self.assertEqual(    b'\x01\x02', nit.Integer(258).bytes)
        self.assertEqual(    b'\x01\x01', nit.Integer(257).bytes)
        self.assertEqual(    b'\x01\x00', nit.Integer(256).bytes)
        self.assertEqual(    b'\x00\xFF', nit.Integer(255).bytes)
        self.assertEqual(    b'\x00\xFE', nit.Integer(254).bytes)

        self.assertEqual(    b'\x00\x81', nit.Integer(129).bytes)
        self.assertEqual(    b'\x00\x80', nit.Integer(128).bytes)
        self.assertEqual(        b'\x7F', nit.Integer(127).bytes)
        self.assertEqual(        b'\x7E', nit.Integer(126).bytes)

        self.assertEqual(        b'\x2A', nit.Integer(42).bytes)

        self.assertEqual(        b'\x02', nit.Integer(2).bytes)
        self.assertEqual(        b'\x01', nit.Integer(1).bytes)
        self.assertEqual(        b'\x00', nit.Integer(0).bytes)
        self.assertEqual(        b'\xFF', nit.Integer(-1).bytes)
        self.assertEqual(        b'\xFE', nit.Integer(-2).bytes)

        self.assertEqual(        b'\x83', nit.Integer(-125).bytes)
        self.assertEqual(        b'\x82', nit.Integer(-126).bytes)
        self.assertEqual(        b'\x81', nit.Integer(-127).bytes)
        self.assertEqual(    b'\xFF\x80', nit.Integer(-128).bytes)   # Notice the superfluous byte?
        self.assertEqual(    b'\xFF\x7F', nit.Integer(-129).bytes)
        self.assertEqual(    b'\xFF\x7E', nit.Integer(-130).bytes)

        self.assertEqual(    b'\xFF\x02', nit.Integer(-254).bytes)
        self.assertEqual(    b'\xFF\x01', nit.Integer(-255).bytes)
        self.assertEqual(    b'\xFF\x00', nit.Integer(-256).bytes)
        self.assertEqual(    b'\xFE\xFF', nit.Integer(-257).bytes)
        self.assertEqual(    b'\xFE\xFE', nit.Integer(-258).bytes)

        self.assertEqual(    b'\x80\x02', nit.Integer(-32766).bytes)
        self.assertEqual(    b'\x80\x01', nit.Integer(-32767).bytes)
        self.assertEqual(b'\xFF\x80\x00', nit.Integer(-32768).bytes)   # Another superfluous byte
        self.assertEqual(b'\xFF\x7F\xFF', nit.Integer(-32769).bytes)
        self.assertEqual(b'\xFF\x7F\xFE', nit.Integer(-32770).bytes)

    def test_integer_type(self):
        self.assertEqual("Integer", type(nit.Integer(42)).__name__)
        self.assertTrue(issubclass(type(nit.Integer(42)), int))
        self.assertTrue(issubclass(type(nit.Integer(42)), nit.Nit))
        self.assertFalse(issubclass(type(nit.Integer(42)), N))

    def test_googol(self):
        googol = nit.Integer(10**100)
        self.assertEqual(
            b'\x12\x49\xAD\x25\x94\xC3\x7C\xEB\x0B\x27\x84\xC4\xCE\x0B\xF3\x8A\xCE\x40\x8E\x21\x1A'
            b'\x7C\xAA\xB2\x43\x08\xA8\x2E\x8F\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            googol.bytes
        )
        # NOTE:  In case you did not memorize googol in hex:
        self.assertEqual(
            0x1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10000000000000000000000000,
            10**100
        )

    def test_googol_plus_one(self):
        googol_plus_one = nit.Integer(10**100 + 1)
        self.assertEqual(
            b'\x12\x49\xAD\x25\x94\xC3\x7C\xEB\x0B\x27\x84\xC4\xCE\x0B\xF3\x8A\xCE\x40\x8E\x21\x1A'
            b'\x7C\xAA\xB2\x43\x08\xA8\x2E\x8F\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01',
            googol_plus_one.bytes
        )

    def test_python_int_unlimited_precision(self):
        self.assertNotEqual(10**100, 10**100 + 1)

    def test_python_float_limited_precision(self):
        self.assertEqual(1e100, 1e100 + 1)

    def test_integer_nits(self):
        self.assertEqual([], nit.Integer(257).nits)

    def test_equality(self):
        self.assertEqual(nit.Integer(42), nit.Integer(42))
        self.assertNotEqual(nit.Integer(42), nit.Integer(42000))

    def test_from_nit(self):
        self.assertEqual(nit.Integer(0x2A), nit.Integer.from_nit(nit.Text('\x2A')))
        self.assertNotEqual(nit.Integer(0x2A), nit.Integer.from_nit(nit.Text('\x2B')))

    def test_negative(self):
        self.assertEqual(1, nit.Integer(1))
        self.assertEqual(-1, nit.Integer(-1))
        self.assertNotEqual(1, nit.Integer(-1))
        self.assertNotEqual(1, nit.Integer(-1))

    def test_int_cast_int(self):
        self.assertEqual(42, nit.Integer(42))
        self.assertEqual(42, int(nit.Integer(42)))


class TextTests(unittest.TestCase):

    def test_letter_bytes(self):
        self.assertEqual(b'foo', nit.Text("foo").bytes)

    def test_control_bytes(self):
        self.assertEqual(b'over\r\nunder', nit.Text("over\r\nunder").bytes)

    def test_nul_bytes(self):
        self.assertEqual(b'before\x00after', nit.Text("before\x00after").bytes)

    def test_european_bytes(self):
        self.assertEqual(b'Bi\xc5\xa1evo', nit.Text("Biševo").bytes)
        self.assertEqual("Biševo", nit.Text("Biševo"))
        self.assertIsInstance(nit.Text("Biševo"), str)
        self.assertIsInstance(nit.Text("Biševo"), nit.Nit)

    def test_equality(self):
        self.assertEqual(nit.Text("foo"), nit.Text("foo"))
        self.assertNotEqual(nit.Text("foo"), nit.Text("fee"))

    def test_from_nit(self):
        self.assertEqual(nit.Text('\x2A'), nit.Text.from_nit(nit.Integer(0x2A)))
        self.assertNotEqual(nit.Text('\x2A'), nit.Text.from_nit(nit.Integer(0x2B)))

    def test_from_nit_invalid(self):
        will_probably_never_be_valid_utf8 = b'\xFF'
        # SEE:  max 4-byte UTF-8, https://datatracker.ietf.org/doc/html/rfc3629#section-3
        # SEE:  old 6-byte UTF-8, https://datatracker.ietf.org/doc/html/rfc2279#section-2
        with self.assertRaises(UnicodeDecodeError):
            nit.Text.from_nit(N(will_probably_never_be_valid_utf8))

        # NOTE:  There is no __ascii__ method.  Yet.  But the builtin ascii() still somehow does a
        #        surprisingly useful thing.  It must go to town on the .__repr__() output.
        # SEE:  ascii(my_object), "For custom objects, the ascii() function internally calls the
        #       __repr__() function, but makes sure to escape non-ASCII characters."
        #       https://www.askpython.com/python/built-in-methods/python-ascii-function

    def test_ways_to_stringify_double_quote(self):
        double = '\x22'
        single = '\x27'
        backslash = '\x5C'
        self.assertEqual(                     double,                 str(double))
        self.assertEqual(            single + double + single,       repr(double))
        self.assertEqual(            single + double + single,      ascii(double))
        self.assertEqual(double + backslash + double + double, json.dumps(double))

    def test_ways_to_stringify_single_quote(self):
        double = '\x22'
        single = '\x27'
        self.assertEqual(                     single,                 str(single))
        self.assertEqual(            double + single + double,       repr(single))
        self.assertEqual(            double + single + double,      ascii(single))
        self.assertEqual(            double + single + double, json.dumps(single))

    def test_ways_to_stringify_single_and_double_quote(self):
        double = '\x22'
        single = '\x27'
        backslash = '\x5C'
        self.assertEqual(                     single + double,                 str(single + double))
        self.assertEqual(single + backslash + single + double + single,       repr(single + double))
        self.assertEqual(single + backslash + single + double + single,      ascii(single + double))
        self.assertEqual(double + single + backslash + double + double, json.dumps(single + double))

    def test_ways_to_stringify_backslash(self):
        double = '\x22'
        single = '\x27'
        backslash = '\x5C'
        self.assertEqual(                     backslash,                 str(backslash))
        self.assertEqual(single + backslash + backslash + single,       repr(backslash))
        self.assertEqual(single + backslash + backslash + single,      ascii(backslash))
        self.assertEqual(double + backslash + backslash + double, json.dumps(backslash))

    # FALSE WARNING:  Typo: In word (hexadecimal)
    # noinspection SpellCheckingInspection
    def test_ways_to_stringify_control(self):
        self.assertEqual(           "abc\x00def",                  str('abc\x00def'))
        self.assertEqual(         "'abc\\x00def'",                repr('abc\x00def'))
        self.assertEqual(         "'abc\\x00def'",               ascii('abc\x00def'))
        self.assertEqual(       '"abc\\u0000def"',          json.dumps('abc\x00def'))

        self.assertEqual(           "abc\x01def",                  str('abc\x01def'))
        self.assertEqual(         "'abc\\x01def'",                repr('abc\x01def'))
        self.assertEqual(         "'abc\\x01def'",               ascii('abc\x01def'))
        self.assertEqual(       '"abc\\u0001def"',          json.dumps('abc\x01def'))

        self.assertEqual(           "abc\x0Adef",                  str('abc\x0Adef'))
        self.assertEqual(           "'abc\\ndef'",                repr('abc\x0Adef'))
        self.assertEqual(           "'abc\\ndef'",               ascii('abc\x0Adef'))
        self.assertEqual(           '"abc\\ndef"',          json.dumps('abc\x0Adef'))

        self.assertEqual(           "abc\x1Fdef",                  str('abc\x1Fdef'))
        self.assertEqual(         "'abc\\x1fdef'",                repr('abc\x1Fdef'))
        self.assertEqual(         "'abc\\x1fdef'",               ascii('abc\x1Fdef'))
        self.assertEqual(       '"abc\\u001fdef"',          json.dumps('abc\x1Fdef'))

    # noinspection SpellCheckingInspection
    def test_ways_to_stringify_unicode_latin_1(self):
        self.assertEqual(           "abc\xA0def",                  str('abc\xA0def'))
        self.assertEqual(         "'abc\\xa0def'",                repr('abc\xA0def'))   # weirdo
        self.assertEqual(         "'abc\\xa0def'",               ascii('abc\xA0def'))
        self.assertEqual(       '"abc\\u00a0def"',          json.dumps('abc\xA0def'))

        self.assertEqual(           "abc\xA1def",                  str('abc\xA1def'))
        self.assertEqual(          "'abc\xA1def'",                repr('abc\xA1def'))
        self.assertEqual(         "'abc\\xa1def'",               ascii('abc\xA1def'))
        self.assertEqual(       '"abc\\u00a1def"',          json.dumps('abc\xA1def'))

        self.assertEqual(           "abc\xB2def",                  str('abc\xB2def'))
        self.assertEqual(          "'abc\xB2def'",                repr('abc\xB2def'))
        self.assertEqual(         "'abc\\xb2def'",               ascii('abc\xB2def'))
        self.assertEqual(       '"abc\\u00b2def"',          json.dumps('abc\xB2def'))

        self.assertEqual(           "abc\xC3def",                  str('abc\xC3def'))
        self.assertEqual(          "'abc\xC3def'",                repr('abc\xC3def'))
        self.assertEqual(         "'abc\\xc3def'",               ascii('abc\xC3def'))
        self.assertEqual(       '"abc\\u00c3def"',          json.dumps('abc\xC3def'))

        self.assertEqual(           "abc\xFFdef",                  str('abc\xFFdef'))
        self.assertEqual(          "'abc\xFFdef'",                repr('abc\xFFdef'))
        self.assertEqual(         "'abc\\xffdef'",               ascii('abc\xFFdef'))
        self.assertEqual(       '"abc\\u00ffdef"',          json.dumps('abc\xFFdef'))

        self.assertEqual(           "abc\xA0def",         str(nit.Text('abc\xA0def')))
        self.assertEqual("nit.Text('abc\\xa0def')",      repr(nit.Text('abc\xA0def')))
        self.assertEqual("nit.Text('abc\\xa0def')",     ascii(nit.Text('abc\xA0def')))
        self.assertEqual(       '"abc\\u00a0def"', json.dumps(nit.Text('abc\xA0def')))

        self.assertEqual(           "abc\xF9def",         str(nit.Text('abc\xF9def')))
        self.assertEqual( "nit.Text('abc\xF9def')",      repr(nit.Text('abc\xF9def')))
        self.assertEqual("nit.Text('abc\\xf9def')",     ascii(nit.Text('abc\xF9def')))
        self.assertEqual(       '"abc\\u00f9def"', json.dumps(nit.Text('abc\xF9def')))

        self.assertEqual(           "abc\xF9def",                str(N('abc\xF9def')))
        self.assertEqual(        "N('abc\xF9def')",             repr(N('abc\xF9def')))
        self.assertEqual(       "N('abc\\xf9def')",            ascii(N('abc\xF9def')))

    def test_ways_to_stringify_unicode_bmp(self):
        self.assertEqual(           "abc\u1234def",                  str('abc\u1234def'))
        self.assertEqual(          "'abc\u1234def'",                repr('abc\u1234def'))
        self.assertEqual(         "'abc\\u1234def'",               ascii('abc\u1234def'))
        self.assertEqual(         '"abc\\u1234def"',          json.dumps('abc\u1234def'))

        self.assertEqual(           "abc\u1234def",         str(nit.Text('abc\u1234def')))
        self.assertEqual( "nit.Text('abc\u1234def')",      repr(nit.Text('abc\u1234def')))
        self.assertEqual("nit.Text('abc\\u1234def')",     ascii(nit.Text('abc\u1234def')))
        self.assertEqual(         '"abc\\u1234def"', json.dumps(nit.Text('abc\u1234def')))

        self.assertEqual(           "abc\u1234def",                str(N('abc\u1234def')))
        self.assertEqual(        "N('abc\u1234def')",             repr(N('abc\u1234def')))
        self.assertEqual(       "N('abc\\u1234def')",            ascii(N('abc\u1234def')))

    def test_ways_to_stringify_unicode_supplementary_plane_1(self):
        self.assertEqual(           "abc\U00012345def",                  str('abc\U00012345def'))
        self.assertEqual(          "'abc\U00012345def'",                repr('abc\U00012345def'))
        self.assertEqual(         "'abc\\U00012345def'",               ascii('abc\U00012345def'))
        self.assertEqual(      '"abc\\ud808\\udf45def"',          json.dumps('abc\U00012345def'))

        self.assertEqual(           "abc\U00012345def",         str(nit.Text('abc\U00012345def')))
        self.assertEqual( "nit.Text('abc\U00012345def')",      repr(nit.Text('abc\U00012345def')))
        self.assertEqual("nit.Text('abc\\U00012345def')",     ascii(nit.Text('abc\U00012345def')))
        self.assertEqual(      '"abc\\ud808\\udf45def"', json.dumps(nit.Text('abc\U00012345def')))

        self.assertEqual(           "abc\U00012345def",                str(N('abc\U00012345def')))
        self.assertEqual(        "N('abc\U00012345def')",             repr(N('abc\U00012345def')))
        self.assertEqual(       "N('abc\\U00012345def')",            ascii(N('abc\U00012345def')))

    # noinspection SpellCheckingInspection
    def test_ways_to_stringify_unicode_supplementary_plane_16(self):
        self.assertEqual(           "abc\U00103456def",                  str('abc\U00103456def'))
        self.assertEqual(         "'abc\\U00103456def'",                repr('abc\U00103456def'))
        self.assertEqual(         "'abc\\U00103456def'",               ascii('abc\U00103456def'))
        self.assertEqual(      '"abc\\udbcd\\udc56def"',          json.dumps('abc\U00103456def'))

        self.assertEqual(           "abc\U00103456def",         str(nit.Text('abc\U00103456def')))
        self.assertEqual("nit.Text('abc\\U00103456def')",      repr(nit.Text('abc\U00103456def')))
        self.assertEqual("nit.Text('abc\\U00103456def')",     ascii(nit.Text('abc\U00103456def')))
        self.assertEqual(      '"abc\\udbcd\\udc56def"', json.dumps(nit.Text('abc\U00103456def')))

        self.assertEqual(           "abc\U00103456def",                str(N('abc\U00103456def')))
        self.assertEqual(       "N('abc\\U00103456def')",             repr(N('abc\U00103456def')))
        self.assertEqual(       "N('abc\\U00103456def')",            ascii(N('abc\U00103456def')))

    # noinspection SpellCheckingInspection
    def test_repr_on_unicode_planes_0_to_16(self):
        self.assertEqual( "'abc\U00001111def'", repr('abc\U00001111def'))   # plane 0, aka the BMP
        self.assertEqual( "'abc\U00011111def'", repr('abc\U00011111def'))
        self.assertEqual( "'abc\U00021111def'", repr('abc\U00021111def'))   # plane 2 defined char
        self.assertEqual("'abc\\U0002ffffdef'", repr('abc\U0002FFFFdef'))   # plane 2 undefined char
        self.assertEqual( "'abc\U00031111def'", repr('abc\U00031111def'))   # plane 3 defined char
        self.assertEqual( "'abc\U00031300def'", repr('abc\U00031300def'))
        self.assertEqual( "'abc\U00031320def'", repr('abc\U00031320def'))
        self.assertEqual( "'abc\U00031340def'", repr('abc\U00031340def'))
        self.assertEqual( "'abc\U00031348def'", repr('abc\U00031348def'))
        self.assertEqual( "'abc\U0003134Adef'", repr('abc\U0003134Adef'))   # plane 3 defined char
        self.assertEqual("'abc\\U0003134bdef'", repr('abc\U0003134Bdef'))   # plane 3 undefined char
        self.assertEqual("'abc\\U0003134cdef'", repr('abc\U0003134Cdef'))
        self.assertEqual("'abc\\U0003134fdef'", repr('abc\U0003134Fdef'))
        self.assertEqual("'abc\\U00031350def'", repr('abc\U00031350def'))
        self.assertEqual("'abc\\U00031360def'", repr('abc\U00031360def'))
        self.assertEqual("'abc\\U00031380def'", repr('abc\U00031380def'))
        self.assertEqual("'abc\\U000313ffdef'", repr('abc\U000313FFdef'))
        self.assertEqual("'abc\\U00031400def'", repr('abc\U00031400def'))
        self.assertEqual("'abc\\U00031500def'", repr('abc\U00031500def'))
        self.assertEqual("'abc\\U00031800def'", repr('abc\U00031800def'))
        self.assertEqual("'abc\\U00031fffdef'", repr('abc\U00031FFFdef'))
        self.assertEqual("'abc\\U00032111def'", repr('abc\U00032111def'))
        self.assertEqual("'abc\\U00034111def'", repr('abc\U00034111def'))
        self.assertEqual("'abc\\U00038111def'", repr('abc\U00038111def'))
        self.assertEqual("'abc\\U0003ffffdef'", repr('abc\U0003FFFFdef'))   # plane 3 undefined char
        self.assertEqual("'abc\\U00041111def'", repr('abc\U00041111def'))   # plane 4
        self.assertEqual("'abc\\U00051111def'", repr('abc\U00051111def'))
        self.assertEqual("'abc\\U00061111def'", repr('abc\U00061111def'))
        self.assertEqual("'abc\\U00071111def'", repr('abc\U00071111def'))
        self.assertEqual("'abc\\U00081111def'", repr('abc\U00081111def'))
        self.assertEqual("'abc\\U00091111def'", repr('abc\U00091111def'))
        self.assertEqual("'abc\\U000a1111def'", repr('abc\U000A1111def'))
        self.assertEqual("'abc\\U000b1111def'", repr('abc\U000B1111def'))
        self.assertEqual("'abc\\U000c1111def'", repr('abc\U000C1111def'))
        self.assertEqual("'abc\\U000d1111def'", repr('abc\U000D1111def'))
        self.assertEqual("'abc\\U000e1111def'", repr('abc\U000E1111def'))
        self.assertEqual("'abc\\U000f1111def'", repr('abc\U000F1111def'))
        self.assertEqual("'abc\\U00101111def'", repr('abc\U00101111def'))   # plane 16

        # NOTE:  In summary:
        #        str() passes through everyting, it escapes nothing.
        #        repr() and ascii() usually add single-quotes.  And escape them with backslash.
        #        repr() and ascii() may switch to double-quotes on strings with single quotes.
        #        json.dumps() always adds double-quotes.   And escapes them with backslash.
        #        ascii() escapes everything below space ' ' U+0020, or above tilde '~' U+007E.
        #        repr() passes most characters.
        #        repr() escapse NBSP, non-break space, U+00A0 with backslash-x-two-digits.
        #        repr() passes defined characters in planes 0,1,2,3, escapes the undefined ones.
        #        repr() escapes characters in planes 4-16 with backslash-U-eight-digits.
        #               The character \U00103456 used above is in plane 16.
        #               Planes 4-13 are unassigned, but planes 14-16 are sort-of assigned, and still
        #               their characters are escaped by repr().  But I only tried a few.
        #        ascii() will escape all these ways:  \' \\ \r \n \xNN \uNNNN \UNNNNNNNN
        #        repr() will too, but less often, e.g. \xa0 \ue0e0 \U00101010
        #        repr() and ascii() never escape double-quotes, as far as I could find.
        #        json.dumps() escapes double quotes and never single quotes.
        #        json.dumps(), like ascii(), escapes everything outside space-tilde.
        #        json.dumps() only has these escapes
        #        json.dumps() escapes plane 1-16 characters with a surrogate pair.
        #        repr() and ascii() will preserve the class names N() or nit.Text().
        #        repr() and ascii() render the string part the same, whether class-wrapped or not.
        #        str() or json.dumps() treats those classes transparently as strings.
        # SEE:  unicode supplementary planes, https://www.compart.com/en/unicode/plane
        # SEE:  unicode supplementary planes, https://en.wikipedia.org/wiki/Plane_(Unicode)#Overview

    def test_cannot_json_encode_N_instances(self):
        with self.assertRaises(TypeError):
            json.dumps(N())
        with self.assertRaises(TypeError):
            json.dumps(N(' '))

    def test_python_itself_on_unicode_plane_16(self):
        self.assertEqual("abc\U00101111def", eval("'abc\\U00101111def'"))

    def test_python_itself_on_unicode_plane_17(self):
        with self.assertRaises(SyntaxError):
            eval("'abc\\U00111111def'")


class LexBasics(unittest.TestCase):

    def test_lex_empty(self):
        lex = nit.LexMemory()
        self.assertEqual(0, len(lex.nits))

    def test_lex_nits(self):
        lex = nit.LexMemory([nit.Integer(42), nit.Integer(-1)])
        self.assertEqual(2, len(lex))
        self.assertEqual(42, lex[0])
        self.assertEqual(-1, lex[1])

    def test_lex_nits_overflow(self):
        lex = nit.LexMemory([nit.Integer(42), nit.Integer(-1)])
        with self.assertRaises(IndexError):
            _ = lex[2]

    def test_lex_nits_underflow(self):
        lex = nit.LexMemory([nit.Integer(42), nit.Integer(-1)])
        with self.assertRaises(IndexError):
            _ = lex[-1]

    def test_lex_add(self):
        lex = nit.LexMemory([nit.Integer(11), nit.Integer(22)])
        self.assertEqual(2, len(lex))
        lex.add(nit.Integer(33))
        self.assertEqual(3, len(lex))
        self.assertEqual(33, lex[2])

    def test_lex_iterate(self):
        lex = nit.LexMemory([nit.Integer(11), nit.Integer(22)])
        self.assertEqual([11, 22], [n for n in lex])
        lex.add(nit.Integer(33))
        lex.add(nit.Text("forty-four"))
        self.assertEqual([11, 22, 33, "forty-four"], [n for n in lex])


class LexRecurse(unittest.TestCase):

    def test_one_level(self):
        lex = nit.LexMemory()
        lex.add(nit.Text("foo"))
        lex.add(nit.Integer(42))

        nit_tree_iterator = lex.recurse()
        nit_list = list(nit_tree_iterator)
        list_of_bytes_in_hex = [hex_from_bytes(n.bytes) for n in nit_list]
        self.assertEqual(['666F6F', '2A'], list_of_bytes_in_hex)

    def test_two_level(self):
        lex = nit.LexMemory()
        lex.add(nit.Integer(0x11))
        lex.add(nit.Integer(0x22))
        lex.add(nit.LexMemory([nit.Integer(0x33), nit.Integer(0x44)]))

        nit_tree_iterator = lex.recurse()
        nit_list = list(nit_tree_iterator)
        list_of_bytes_in_hex = [hex_from_bytes(n.bytes) for n in nit_list]
        self.assertEqual(['11', '22', '', '33', '44'], list_of_bytes_in_hex)


class NClassTests(unittest.TestCase):

    def test_nat(self):
        """Method 1 to make a NAT with N()."""
        self.assertEqual(b'', N().bytes)
        self.assertEqual([], N().nits)

    def test_nat_explicit_none(self):
        """Method 2 to make a NAT."""
        self.assertEqual(b'', N(None).bytes)
        self.assertEqual([], N(None).nits)

    def test_nat_explicit_empty_string(self):
        """Method 3 to make a NAT."""
        self.assertEqual(b'', N('').bytes)
        self.assertEqual([], N('').nits)

        # TODO:  Probably N(float('nan')) will be a NAT too, but we're not doing floats yet.
        #        Pretty sure no integer will ever convert to a NAT.  Like the string '' will.

    def test_integer(self):
        self.assertEqual(b'\x2A', N(42).bytes)
        self.assertEqual([], N(42).nits)

        self.assertEqual(b'\x2A', N(nit.Integer(42)).bytes)
        self.assertEqual([], N(nit.Integer(42)).nits)

    def test_text(self):
        self.assertEqual(b'foo', N("foo").bytes)
        self.assertEqual([], N("foo").nits)

        self.assertEqual(b'foo', N(nit.Text("foo")).bytes)
        self.assertEqual([], N(nit.Text("foo")).nits)

    def test_bytes_literal(self):
        self.assertEqual(b'bar', N(b"bar").bytes)
        self.assertEqual([], N(b"bar").nits)

    def test_constructor_type_error(self):
        """These forms of the N() constructor do not make anything."""
        with self.assertRaises(TypeError):
            N(())
        with self.assertRaises(TypeError):
            N({})
        with self.assertRaises(TypeError):
            N(object())

        class SomeRandoType:
            pass
        with self.assertRaises(TypeError):
            N(SomeRandoType())

    def test_repr_nat(self):
        self.assertEqual("N()", repr(N()))
        self.assertEqual("N()", repr(N(None)))
        self.assertEqual("N()", repr(N('')))

    def test_repr_integer(self):
        self.assertEqual("N(42)", repr(N(42)))

    def test_repr_integer_negative(self):
        self.assertEqual("N(1)", repr(N(1)))
        self.assertEqual("N(0)", repr(N(0)))
        self.assertEqual("N(0)", repr(N(-0)))
        self.assertEqual("N(-1)", repr(N(-1)))
        self.assertEqual("N(-2)", repr(N(-2)))

        self.assertEqual("N(-42)", repr(N(-42)))

        self.assertEqual("N(-254)", repr(N(-254)))
        self.assertEqual("N(-255)", repr(N(-255)))
        self.assertEqual("N(-256)", repr(N(-256)))
        self.assertEqual("N(-257)", repr(N(-257)))

        self.assertEqual("N(-65534)", repr(N(-65534)))
        self.assertEqual("N(-65535)", repr(N(-65535)))
        self.assertEqual("N(-65536)", repr(N(-65536)))
        self.assertEqual("N(-65537)", repr(N(-65537)))

    def test_N_negative_bug(self):
        """At one point N(-1) == N(255)."""
        self.assertEqual(   N(-1),  N(-1))
        self.assertNotEqual(N(255), N(-1))
        self.assertNotEqual(N(-1),  N(255))
        self.assertEqual   (N(255), N(255))

        self.assertEqual(    b'\xFF', N(-1).bytes)
        self.assertEqual(b'\x00\xFF', N(255).bytes)

    def test_repr_integer_class(self):
        """N() is smart about nit.Integer() standing in for int."""
        self.assertEqual(          "N(42)",             repr(N(42)))
        self.assertEqual(          "N(42)", repr(N(nit.Integer(42))))
        self.assertEqual("nit.Integer(42)",    repr(nit.Integer(42)))
        # TODO:  Or should this be "nit.Integer(42)"?

        self.assertIs(int,                      type(42))
        self.assertIs(int,                         N(42)._native_type)
        self.assertIs(N,          type(N(nit.Integer(42))))
        self.assertIs(nit.Integer,  type(nit.Integer(42)))
        self.assertIs(nit.Integer,     N(nit.Integer(42))._native_type)
        self.assertIs(nit.Integer, N(N(N(nit.Integer(42))))._native_type)

    def test_repr_text(self):
        self.assertEqual("N('foo')", repr(N("foo")))
        self.assertEqual(
               "N('\xFF\\x00\xBE\xEF*\\r\\n')",
            repr(N("\xFF\x00\xBE\xEF\x2A\x0D\x0A"))
        )
        self.assertEqual(
                "N('\u0391\U0001F600')",
            repr(N("\u0391\U0001F600"))
        )

    def test_repr_text_class(self):
        """N() is smart about nit.Text() standing in for str."""
        self.assertEqual(       "N('foo')",          repr(N('foo')))
        self.assertEqual(       "N('foo')", repr(N(nit.Text('foo'))))
        self.assertEqual("nit.Text('foo')",   repr(nit.Text('foo')))

        self.assertIs(str,                type('foo'))
        self.assertIs(str,                   N('foo')._native_type)
        self.assertIs(N,       type(N(nit.Text('foo'))))
        self.assertIs(nit.Text,  type(nit.Text('foo')))
        self.assertIs(nit.Text,     N(nit.Text('foo'))._native_type)
        self.assertIs(nit.Text, N(N(N(nit.Text('foo'))))._native_type)

    def test_repr_bytes(self):
        # FALSE WARNING:  Typo: In word b'foo   # noqa
        # noinspection SpellCheckingInspection
        self.assertEqual(
            "N(b'foo bar baz')",
            repr(N(b"foo bar baz"))
        )
        self.assertEqual(
            "N(b'\\xff\\x00\\xde\\xad\\xbe\\xef')",
            repr(N(b"\xFF\x00\xDE\xAD\xBE\xEF"))
        )

    def test_repr_nits(self):
        self.assertEqual("N('foo', N('bar'), N(42))", repr(N("foo", N("bar"), N(42))))

    def test_repr_nits_with_empty_bytes(self):
        self.assertEqual("N()", repr(N()))
        self.assertEqual("N()", repr(N(None)))
        self.assertEqual("N(None, N(42))", repr(N(None, N(42))))

    def test_str_integer(self):
        self.assertEqual("42", str(N(42)))
        # TODO:  Should str(N(42)) be just '42'?
        #        and str(N(1,2)) be 'N(1,N(2))'?
        #        reminiscent of the possibilities for the args parameters to N()

    def test_str_text(self):
        self.assertEqual("foo", str(N('foo')))

    def test_copy_constructor(self):
        self.assertEqual("N('foo')", repr(N('foo')))
        self.assertEqual("N('foo')", repr(N(N('foo'))))
        self.assertEqual("N('foo')", repr(N(N(N('foo')))))
        self.assertEqual("N('foo')", repr(N(N(N(N('foo'))))))

        self.assertEqual("N(42)", repr(N(42)))
        self.assertEqual("N(42)", repr(N(N(42))))
        self.assertEqual("N(42)", repr(N(N(N(42)))))
        self.assertEqual("N(42)", repr(N(N(N(N(42))))))

        self.assertEqual("N()", repr(N()))
        self.assertEqual("N()", repr(N(N())))
        self.assertEqual("N()", repr(N(N(N()))))
        self.assertEqual("N()", repr(N(N(N(N())))))

    def test_repr_with_emtpy_text_sub_nit(self):
        self.assertEqual("N('foo', N('bar'), N(), N('baz'))", repr(N('foo', 'bar', '', 'baz')))

    def test_equality(self):
        self.assertEqual(N(42), N(42))
        self.assertNotEqual(N(42), N(42000))

    def test_equality_integer(self):
        self.assertEqual(             N(42), nit.Integer(42))
        self.assertEqual(   nit.Integer(42),           N(42))
        self.assertNotEqual(          N(42), nit.Integer(42000))
        self.assertNotEqual(nit.Integer(42),           N(42000))

    def test_equality_nat(self):
        self.assertEqual(N(), N(''))
        self.assertEqual(N(''), N())
        # NOTE:  There is no way N() can make nat from an integer.

    def test_equality_text_v_integer(self):
        self.assertEqual(N("\x2A"), N(0x2A))
        self.assertNotEqual(N("\x2A"), N(0x2B))

    def test_nits_implicit_N(self):
        """
        The sub-nit parameters do not have to be actual nits.

        They just have to be something that N() can make into a nit.
        """
        self.assertEqual("N('foo', N('bar'), N(42), N())", repr(N("foo", "bar", 42, None)))

    def test_nits_implicit_type_error(self):
        class UnknownType:
            pass
        with self.assertRaises(TypeError):
            N(42, UnknownType())
        with self.assertRaises(TypeError):
            N(42, object())
        with self.assertRaises(TypeError):
            N(42, N('foo', 'bar', UnknownType(), 'baz'))
        with self.assertRaises(TypeError):
            N(42, N('foo', 'bar', object(), 'baz'))

    def test_nested(self):
        nested = N(
            'a',
            N('b'),
            N('c', N('d')),
            N('e')
        )
        self.assertEqual(b'a',  nested.bytes)
        self.assertEqual(3, len(nested.nits))
        self.assertEqual(b'b',  nested.nits[0].bytes)
        self.assertEqual(0, len(nested.nits[0].nits))
        self.assertEqual(b'c',  nested.nits[1].bytes)
        self.assertEqual(1, len(nested.nits[1].nits))
        self.assertEqual(b'd',  nested.nits[1].nits[0].bytes)
        self.assertEqual(0, len(nested.nits[1].nits[0].nits))
        self.assertEqual(b'e',  nested.nits[2].bytes)
        self.assertEqual(0, len(nested.nits[2].nits))

    def test_equality_nested(self):
        self.assertEqual(N(1),                               N(1))
        self.assertEqual(N(1, N(2)),                         N(1, N(2)))
        self.assertEqual(N(1, N(2, N(3))),                   N(1, N(2, N(3))))
        self.assertEqual(N(1, N(2, N(3, N(4)))),             N(1, N(2, N(3, N(4)))))
        self.assertEqual(N(1, N(2, N(3, N(4), N(5)))),       N(1, N(2, N(3, N(4), N(5)))))
        self.assertEqual(N(1, N(2, N(3, N(4), N(5)), N(6))), N(1, N(2, N(3, N(4), N(5)), N(6))))

        self.assertNotEqual(N(1),                               N(11))
        self.assertNotEqual(N(1, N(2)),                         N(1, N(22)))
        self.assertNotEqual(N(1, N(2, N(3))),                   N(1, N(2, N(33))))
        self.assertNotEqual(N(1, N(2, N(3, N(4)))),             N(1, N(2, N(3, N(44)))))
        self.assertNotEqual(N(1, N(2, N(3, N(4), N(5)), N(6))), N(1, N(2, N(3, N(4), N(5)), N(66))))
        self.assertNotEqual(N(1, N(2, N(3, N(4), N(5)), N(6))), N(1, N(2, N(3, N(4), N(55)), N(6))))
        self.assertNotEqual(N(1, N(2, N(3, N(4), N(5)), N(6))), N(1, N(2, N(3, N(44), N(5)), N(6))))
        self.assertNotEqual(N(1, N(2, N(3, N(4), N(5)), N(6))), N(1, N(2, N(33, N(4), N(5)), N(6))))
        self.assertNotEqual(N(1, N(2, N(3, N(4), N(5)), N(6))), N(1, N(22, N(3, N(4), N(5)), N(6))))
        self.assertNotEqual(N(1, N(2, N(3, N(4), N(5)), N(6))), N(11, N(2, N(3, N(4), N(5)), N(6))))

    def test_repr_nested(self):
        self.assertEqual(           "N(3, N(4))",             repr(N(3, N(4))))
        self.assertEqual("N(1, N(2), N(3, N(4)))", repr(N(1, N(2), N(3, N(4)))))

    def test_str_nested(self):
        self.assertEqual(           "N(3, N(4))",             str(N(3, N(4))))
        self.assertEqual("N(1, N(2), N(3, N(4)))", str(N(1, N(2), N(3, N(4)))))

    def test_copy_constructor_nested(self):
        self.assertEqual("N('foo', N('bar', N('baz')))", repr(N('foo', N('bar', N('baz')))))
        self.assertEqual("N('foo', N('bar', N('baz')))", repr(N(N('foo', N('bar', N('baz'))))))
        self.assertEqual("N('foo', N('bar', N('baz')))", repr(N(N(N('foo', N('bar', N('baz')))))))

    def test_concatenating_nits(self):
        """Copy constructor combined with additional nits."""
        self.assertEqual(N(1, 2,3,4,5,6), N(N(1, 2,3), 4,5,6))

        nits123 = (1,2,3)
        nits456 = (4,5,'six')
        self.assertEqual(N('foo', 1,2,3,4,5,'six'), N(N('foo', *nits123), *nits456))

    def test_sibling_nit_class(self):
        """N() should be able to handle an unfamiliar subclass of Nit."""

        class OtherNit(nit.Nit):
            def __init__(self, _bytes, _nits):
                self._bytes = _bytes
                self._nits = _nits

            @property
            def bytes(self):
                return self._bytes

            @property
            def nits(self):
                return self._nits

        self.assertEqual(b'foo', OtherNit(b'foo', []).bytes)
        self.assertEqual([],     OtherNit(b'foo', []).nits)
        self.assertEqual(b'bar', OtherNit(b'foo', [OtherNit(b'bar', [])]).nits[0].bytes)

        self.assertEqual(b'foo', N(OtherNit(b'foo', [])).bytes)
        self.assertEqual([],     N(OtherNit(b'foo', [])).nits)
        self.assertEqual(b'bar', N(OtherNit(b'foo', [OtherNit(b'bar', [])])).nits[0].bytes)

        # FALSE WARNING:  Typo: In word b'foo   # spelling # noqa
        # noinspection SpellCheckingInspection
        self.assertEqual("N(b'foo')", repr(N(OtherNit(b'foo', []))))

    def test_n_method(self):
        self.assertEqual("N(42)", repr(N(42)))

        self.assertEqual("N(42, N(99))", repr(N(42, 99)))      # 2-level
        self.assertEqual("N(42, N(99))", repr(N(42, N(99))))   # 2-level
        self.assertEqual("N(42, N(99))", repr(N(42).N(99)))    # 2-level

        self.assertEqual("N(42, N(99), N(98), N(97))", repr(N(42, 99, 98, 97)))      # 2-level
        self.assertEqual("N(42, N(99, N(98), N(97)))", repr(N(42, N(99, 98, 97))))   # 3-level
        self.assertEqual("N(42, N(99, N(98), N(97)))", repr(N(42).N(99, 98, 97)))    # 3-level

        self.assertEqual("N(1, N(2), N(3), N(4), N(5), N(6))", repr(N(1,2,3,4,5,6)))
        self.assertEqual("N(1, N(2), N(3), N(4, N(5), N(6)))", repr(N(1,2,3,N(4,5,6))))
        self.assertEqual("N(1, N(2), N(3), N(4, N(5), N(6)))", repr(N(1,2,3).N(4,5,6)))
        self.assertEqual("N(11, N(22, N(33)))", repr(N(11, N(22, N(33)))))
        self.assertEqual("N(11, N(22, N(33)))", repr(N(11).N(22, N(33))))

    def test_n_method_chained(self):
        self.assertEqual("N(1, N(2), N(3))", repr(N(1).N(2).N(3)))

    def test_n_method_is_factory_not_modifier_in_place(self):
        n1 = N(1)
        n12 = n1.N(2)
        self.assertEqual("N(1)", repr(n1))
        self.assertEqual("N(1, N(2))", repr(n12))

    def test_int_cast_int(self):
        self.assertNotEqual(42, N(42))
        self.assertEqual(42, int(N(42)))
        self.assertEqual(42, int(nit.Integer(42)))

    def test_int_cast_text(self):
        """
        It seems inconsistent that you can cast a nit.Text() to an int, but you cannot cast an N().

        The reason is, int(N('42')) is ambiguous.
        Did you want to interpret N('42').bytes as an int?  That would be 13362.
        Because 13362 == ord('4')*256 + ord('2')
        Or '42'?  That would of course be 42.
        So N() remembers the type it came from
        but it chokes on trying to convert it to a different type.
        """
        self.assertEqual(42, int(nit.Text('42')))
        with self.assertRaises(TypeError):
            int(N('42'))   # ambiguous
        self.assertEqual(42, int(str(N('42'))))   # clear:  decimal string converted to integer
        self.assertEqual(42, int(nit.Integer.from_nit(N('*'))))   # clear:  text-bytes interpreted
                                                                  #         as integer-bytes

    def test_text_cast_int(self):
        """
        More inconsistency with converting N() types:  you CAN convert to str.

        str(N(42)) could conceivably become '*', because N(42) == N('*').
        But that is a stretch so we let that slide.
        """
        self.assertEqual('nit.Integer(42)', str(nit.Integer(42)))
        self.assertEqual(            '42',            str(N(42)))

    def test_text_cast_text(self):
        self.assertNotEqual('foo', N('foo'))
        self.assertEqual('foo', str(N('foo')))
        self.assertEqual('foo', str(nit.Text('foo')))

    def test_hash(self):
        self.assertEqual(hash(N(42)), hash(N(42)))
        self.assertNotEqual(hash(N(42)), hash(N(43)))

        self.assertEqual(hash(N(1,2,3)), hash(N(1,2,3)))
        self.assertNotEqual(hash(N(1,2,3)), hash(N(1,2,4)))
        self.assertNotEqual(hash(N(1,2,3)), hash(N(1,3,2)))
        self.assertNotEqual(hash(N(1,2,3)), hash(N(3,2,1)))

    def test_render_bytes(self):
        self.assertEqual("42",       N(42)   .render_bytes())
        self.assertEqual("42", N(N(N(N(42)))).render_bytes())
        self.assertEqual("'foo'",       N('foo')   .render_bytes())
        self.assertEqual("'foo'", N(N(N(N('foo')))).render_bytes())
        self.assertEqual("b'foo'", N(b'foo').render_bytes())   # spelling # noqa
        self.assertEqual("", N().render_bytes())
        self.assertEqual("", N(None).render_bytes())
        self.assertEqual("", N('').render_bytes())
        self.assertEqual("' '", N(' ').render_bytes())
        # TODO:  Resolve the discontinuity between N('') and N(' ')
        #        Should N('') render '""'?  Different from N()?!?
        #        Then there are two kinds of nat.  And that seems dumb.

    def test_list_input(self):
        self.assertEqual(N(1,2,3),                N([1,2,3]))
        self.assertEqual("N(1, N(2), N(3))", repr(N([1,2,3])))
        self.assertEqual("N(1, N(2), N(3))", repr( N(1,2,3)))

        self.assertEqual(N("forty", "two"),           N(["forty", "two"]))
        self.assertEqual("N('forty', N('two'))", repr(N(["forty", "two"])))
        self.assertEqual("N('forty', N('two'))", repr( N("forty", "two")))

    def test_list_input_nested(self):
        self.assertEqual(N(1,2,3,[4,5,6]),                          N([1,2,3,[4,5,6]]))
        self.assertEqual("N(1, N(2), N(3), N(4, N(5), N(6)))", repr(N([1,2,3,[4,5,6]])))
        self.assertEqual("N(1, N(2), N(3), N(4, N(5), N(6)))", repr( N(1,2,3,[4,5,6])))

    def test_list_empty(self):
        self.assertEqual(N(),        N([]))
        self.assertEqual("N()", repr(N([])))
        self.assertEqual("N()", repr( N()))

    def test_native_bytes(self):
        self.assertEqual(42, N(42).native_bytes())
        self.assertEqual('forty two', N('forty two').native_bytes())
        self.assertEqual(None, N(None).native_bytes())

    def test_to_json_no_nits(self):
        self.assertEqual(42, N(42).to_json())
        self.assertEqual('foo', N('foo').to_json())

    def test_to_json(self):
        self.assertEqual([1, N(2), N(3)], N(1,2,3).to_json())

    def test_to_json_nested(self):
        self.assertEqual([1, N(2), N(3), N(4, N(5), N(6))], N(1,2,3,N(4,5,6)).to_json())

    def test_encode_json(self):
        self.assertEqual(            '[1, 2, 3]', self.json_encode(N(1, 2, 3)))
        self.assertEqual('["foo", "bar", "baz"]', self.json_encode(N('foo', 'bar', 'baz')))
        self.assertEqual(                 'null', self.json_encode(N()))
        self.assertEqual(    '[42, "foo", null]', self.json_encode(N(42, 'foo', None)))

    def test_encode_json_nested(self):
        self.assertEqual(
            '[1, 2, 3, ["foo", "bar"], 4, 5, 6]',
            self.json_encode(N(1, 2, 3, N('foo', 'bar'), 4, 5, 6))
        )

    @staticmethod
    def json_encode(thing, **kwargs):
        """JSON encode any object with a .to_json() method."""

        class EncoderClass(json.JSONEncoder):
            def default(self, x):
                if hasattr(x, 'to_json') and callable(x.to_json):
                    return x.to_json()
                else:
                    return super(EncoderClass, self).default(x)

        return json.dumps(thing, cls=EncoderClass, **kwargs)

    def test_n_is_not_exactly_an_array(self):
        """
        There is a subtlety about passing nits to N() as the first argument.

        A nit contains bytes and nits.
        The bytes are always a "scalar" such as None, int, str.  The bytes are never a nit.

        So the first argument to N() always supplies the bytes.
        If it has sub-nits, they become sub-nits of the result.

        Notice how N(1,2,3) gets dismembered.  Then two nits are appended onto it.
        So N(2) ends up as a sub-nit, but N(5) becomes a sub-sub-nit.
        """
        self.assertEqual(
            N(1, N(2), N(3), N(4,5,6), N(7,8,9)),
            N(N(1,2,3),      N(4,5,6), N(7,8,9))
        )


class IntegerVersusTextTests(unittest.TestCase):

    def test_integer_v_text_bytes_an_introduction(self):
        """The bytes of a nit can represent either an integer or text."""
        self.assertEqual( '\x2A',   '*')
        self.assertEqual(b'\x2A', N('*').bytes)
        self.assertEqual(b'\x2A', N(42).bytes)
        self.assertEqual(  0x2A,    42)

        self.assertEqual(b'\x2E', N('.').bytes)
        self.assertEqual(b'\x2E', N(46).bytes)

        self.assertEqual(b'\x2A\x2A', N('**').bytes)
        self.assertEqual(b'\x2A\x2A', N(10794).bytes)

        self.assertEqual(b'\x66\x6F\x72\x74\x79\x2D\x74\x77\x6F', N('forty-two').bytes)
        self.assertEqual(b'\x66\x6F\x72\x74\x79\x2D\x74\x77\x6F', N(1889598504667731752815).bytes)

    def test_integer_v_text_N_equality_operator(self):
        """
        Nits created by N can be considered equal even if they came from different types.

        That is because the class-N equality operator only looks at bytes and sub-nits.
        """
        self.assertEqual(N(42), N('*'))
        self.assertEqual(N(46), N('.'))

        self.assertNotEqual(N(42), N('.'))
        self.assertNotEqual(N(46), N('*'))

        self.assertEqual(   N(10794), N('**'))
        self.assertNotEqual(N(10795), N('**'))

        self.assertEqual(N(1889598504667731752815), N('forty-two'))
        self.assertEqual(N(1889598504667731752816), N('forty-twp'))

    def test_integer_v_text_explicit_nit_equality_operator(self):
        """
        The explicit types nit.Integer() and nit.Text() are compared as native types, NOT nits.
        """
        self.assertNotEqual(nit.Integer(42), nit.Text('*'))

        self.assertEqual(nit.Integer(42), nit.Integer(42))
        self.assertEqual(nit.Integer(42),             42)

        self.assertEqual(nit.Text('*'), nit.Text('*'))
        self.assertEqual(nit.Text('*'),          '*')

    def test_integer_v_text_mixed_types(self):
        """Mixed types are compared as nits.  Similar to comparing N(int) with N(str) above."""
        self.assertEqual(          N(42), nit.Text('*'))
        self.assertEqual(nit.Integer(42),        N('*'))

        self.assertEqual(nit.Text('*'),           N(42))
        self.assertEqual(       N('*'), nit.Integer(42))

    def test_integer_can_equal_text_N_nested(self):
        self.assertEqual(
            N(42,  N('A'), N(10,   N('foo'))),
            N('*', N(65),  N('\n', N(6713199))),
        )
        self.assertNotEqual(
            N(42,  N('A'), N(10,   N('foo'))),
            N('*', N(65),  N('\n', N(6713198))),
        )

    def test_integer_can_equal_text_N_edgy(self):
        self.assertEqual(N('\x00'), N(0))

    def test_integer_never_equals_text_typed(self):
        self.assertNotEqual(nit.Integer(42), nit.Text('*'))
        self.assertNotEqual(nit.Integer(46), nit.Text('.'))

        self.assertNotEqual(nit.Integer(42), nit.Text('42'))
        self.assertNotEqual(nit.Integer(46), nit.Text('46'))

    def test_integer_equals_native_type(self):
        self.assertEqual(42, nit.Integer(42))
        self.assertEqual(46, nit.Integer(46))

        self.assertEqual(nit.Integer(42), 42)
        self.assertEqual(nit.Integer(46), 46)

    def test_text_equals_native_type(self):
        self.assertEqual('42', nit.Text('42'))
        self.assertEqual('46', nit.Text('46'))

        self.assertEqual(nit.Text('42'), '42')
        self.assertEqual(nit.Text('46'), '46')


def hex_from_bytes(string_of_8_bit_bytes):
    """Encode an 8-bit binary (base-256) string into a hexadecimal string."""
    return binascii.hexlify(string_of_8_bit_bytes).decode().upper()
assert 'BEEF1234' == hex_from_bytes(b'\xBE\xEF\x12\x34')
