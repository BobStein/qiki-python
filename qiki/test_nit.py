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
        # NOTE:  In case you didn't know googol in hex:
        self.assertEqual(
            0x1249AD2594C37CEB0B2784C4CE0BF38ACE408E211A7CAAB24308A82E8F10000000000000000000000000,
            10**100
        )

    def test_integer_nits(self):
        self.assertEqual([], nit.Integer(257).nits)

    def test_equality(self):
        self.assertEqual(nit.Integer(42), nit.Integer(42))
        self.assertNotEqual(nit.Integer(42), nit.Integer(42000))

    def test_from_nit(self):
        self.assertEqual(nit.Integer(0x2A), nit.Integer.from_nit(nit.Text('\x2A')))
        self.assertNotEqual(nit.Integer(0x2A), nit.Integer.from_nit(nit.Text('\x2B')))


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
        """These forms of the N() constructor don't make anything."""
        with self.assertRaises(TypeError):
            N(())
        with self.assertRaises(TypeError):
            N([])
        with self.assertRaises(TypeError):
            N({})
        with self.assertRaises(TypeError):
            N(object())

        class SomeRandoType:
            pass
        with self.assertRaises(TypeError):
            N(SomeRandoType())

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

    def test_equality(self):
        self.assertEqual(N(42), N(42))
        self.assertNotEqual(N(42), N(42000))

    def test_equality_integer(self):
        self.assertEqual(             N(42), nit.Integer(42))
        self.assertEqual(   nit.Integer(42),           N(42))
        self.assertNotEqual(          N(42), nit.Integer(42000))
        self.assertNotEqual(nit.Integer(42),           N(42000))

    def test_equality_text_v_integer(self):
        self.assertEqual(N("\x2A"), N(0x2A))
        self.assertNotEqual(N("\x2A"), N(0x2B))

    def test_repr_nat(self):
        self.assertEqual("N()", repr(N()))
        self.assertEqual("N()", repr(N(None)))
        self.assertEqual("N()", repr(N('')))

    def test_repr_integer(self):
        self.assertEqual("N(42)", repr(N(42)))

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

    def test_nits_implicit_N(self):
        """
        The sub-nit parameters don't have to be actual nits.

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

    def test_copy_constructor_nested(self):
        self.assertEqual("N('foo', N('bar', N('baz')))", repr(N('foo', N('bar', N('baz')))))
        self.assertEqual("N('foo', N('bar', N('baz')))", repr(N(N('foo', N('bar', N('baz'))))))
        self.assertEqual("N('foo', N('bar', N('baz')))", repr(N(N(N('foo', N('bar', N('baz')))))))

    def test_concatenating_nits(self):
        """Copy constructor combined with additional nits."""
        self.assertEqual(N(1, 2,3,4,5,6), N(N(1,2,3), 4,5,6))

        nits123 = (1,2,3)
        nits456 = (4,5,'six')
        self.assertEqual(N('foo', 1,2,3,4,5,'six'), N(N('foo', *nits123), *nits456))

    def test_sibling_nit_class(self):
        """N() should be able to handle a different subclass of Nit."""

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


def hex_from_bytes(string_of_8_bit_bytes):
    """Encode an 8-bit binary (base-256) string into a hexadecimal string."""
    return binascii.hexlify(string_of_8_bit_bytes).decode().upper()
assert 'BEEF1234' == hex_from_bytes(b'\xBE\xEF\x12\x34')
