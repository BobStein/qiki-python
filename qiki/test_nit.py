"""
Unit tests for Nit, Integer
"""


import binascii
import unittest

import nit
from nit import N


class IntegerTests(unittest.TestCase):

    def test_integer_bytes(self):
        self.assertEqual(b'\x01\x01', nit.Integer(257).bytes)
        self.assertEqual(b'\x01\x00', nit.Integer(256).bytes)
        self.assertEqual(b'\x00\xFF', nit.Integer(255).bytes)

        self.assertEqual(b'\x00\x81', nit.Integer(129).bytes)
        self.assertEqual(b'\x00\x80', nit.Integer(128).bytes)
        self.assertEqual(b'\x7F', nit.Integer(127).bytes)
        self.assertEqual(b'\x7E', nit.Integer(126).bytes)

        self.assertEqual(b'\x2A', nit.Integer(42).bytes)

        self.assertEqual(b'\x81', nit.Integer(-127).bytes)
        self.assertEqual(b'\xFF\x80', nit.Integer(-128).bytes)

        self.assertEqual(b'\xFE\xFF', nit.Integer(-257).bytes)

    def test_googol(self):
        googol = nit.Integer(10**100)
        self.assertEqual(
            b'\x12\x49\xAD\x25\x94\xC3\x7C\xEB\x0B\x27\x84\xC4\xCE\x0B\xF3\x8A\xCE\x40\x8E\x21\x1A'
            b'\x7C\xAA\xB2\x43\x08\xA8\x2E\x8F\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            googol.bytes
        )
        # NOTE:  In case you didn't know googol in hex:
        self.assertEqual(
            0x1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10000000000000000000000000,
            10**100
        )

    def test_integer_nits(self):
        self.assertEqual([], nit.Integer(257).nits)


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
        lex.add(nit.Text("forty four"))
        self.assertEqual([11, 22, 33, "forty four"], [n for n in lex])


class LexTraverse(unittest.TestCase):

    def test_one_level(self):
        lex = nit.LexMemory()
        lex.add(nit.Text("foo"))
        lex.add(nit.Integer(42))

        nit_tree_iterator = lex.nit_tree()
        nit_list = list(nit_tree_iterator)
        repr_bytes_list = [hex_from_bytes(n.bytes) for n in nit_list]
        self.assertEqual(['666F6F', '2A'], repr_bytes_list)

    def test_two_level(self):
        lex = nit.LexMemory()
        lex.add(nit.Integer(0x11))
        lex.add(nit.Integer(0x22))
        lex.add(nit.LexMemory([nit.Integer(0x33), nit.Integer(0x44)]))

        nit_tree_iterator = lex.nit_tree()
        nit_list = list(nit_tree_iterator)
        repr_bytes_list = [hex_from_bytes(n.bytes) for n in nit_list]
        self.assertEqual(['11', '22', '', '33', '44'], repr_bytes_list)


class NClass(unittest.TestCase):

    def test_nat(self):
        self.assertEqual(b'', N().bytes)
        self.assertEqual([], N().nits)

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


def hex_from_bytes(string_of_8_bit_bytes):
    """Encode an 8-bit binary (base-256) string into a hexadecimal string."""
    return binascii.hexlify(string_of_8_bit_bytes).decode().upper()
assert 'BEEF' == hex_from_bytes(b'\xBE\xEF')
