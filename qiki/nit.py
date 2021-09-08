"""
Nit - most basic and generic object
"""

import sys


class Nit:

    @property
    def bytes(self):
        raise NotImplementedError(f"{type(self).__name__} should implement a bytes property")

    @property
    def nits(self):
        raise NotImplementedError(f"{type(self).__name__} should implement a nits property")

    @staticmethod
    def is_nat(x):
        return len(x.bytes) == 0 and len(x.nits) == 0

    def nit_tree(self):
        for each_nit in self.nits:
            yield each_nit
            if len(each_nit.nits) > 0:
                # yield from each_nit.nit_tree()
                for sub_nit in each_nit.nit_tree():
                    yield sub_nit


class N(Nit):
    """
    Nit factory - make a Nit instance out of a native object.

    _bytes - can be missing or None or integer or string or bytes
    args - sub-nits
    """
    def __init__(self, _bytes=None, *args):
        # TODO:  This would break:  N(N())  Should it?
        #        I.e. should there be a way to have nits but no bytes?
        #        Other than N(None, N())
        self._bytes = _bytes or b''
        self._nits = []
        self._native_type = type(_bytes)
        if isinstance(_bytes, type(None)):
            self._bytes = b''
        elif isinstance(_bytes, int):
            self._bytes = Integer(_bytes).bytes
        elif isinstance(_bytes, str):
            self._bytes = Text(_bytes).bytes
        elif isinstance(_bytes, bytes):
            self._bytes = _bytes
        elif isinstance(_bytes, N):
            # NOTE:  The main purpose of this copy constructor is so all the args
            #        can be passed through this constructor (which is a recursion of course).
            #        This gives the option:  arguments for the nits can be either
            #        N instances or things suitable for passing to the N constructor.
            #        So N(1,2,3) is the same as N(1,N(2),N(3))
            self._bytes = _bytes.bytes
            self._native_type = _bytes._native_type
            self._nits += _bytes._nits
        elif isinstance(_bytes, Nit):
            # NOTE:  The purpose of THIS copy constructor is to catch the Nit subclasses that
            #        are not a subclass of N.
            self._bytes = _bytes.bytes

            self._nits += _bytes.nits
        else:
            raise TypeError("Cannot N({bytes_type})".format(bytes_type=type(_bytes).__name__))

        list_of_nit_like_things = list(args)
        list_of_nits = [N(nit) for nit in list_of_nit_like_things]
        self._nits += list_of_nits

    def __eq__(self, other):
        """Am I equal to another Nit?"""
        try:
            other_bytes = other.bytes
            other_nits = other.nits
        except AttributeError:
            return False
        return self.bytes == other_bytes and self.nits == other_nits

    def __ne__(self, other):
        """Am I unequal to another Nit?"""
        eq_result = self.__eq__(other)
        if eq_result is NotImplemented:
            return NotImplemented
        return not eq_result

    def __repr__(self):
        if self.is_nat(self):
            bytes_repr = ''
        elif isinstance(None, self._native_type):
            # NOTE:  The reason we need to check isinstance(None) when we've already checked
            #        is_nat() is the case where a nit has some nits but empty bytes.  That's not a
            #        nat.  And conveniently it's a special case where repr() need to produce "None"
            #        for the bytes, so we can put in the nits after it.
            bytes_repr = repr(None)
        elif issubclass(self._native_type, int):
            bytes_repr = repr(int(Integer.from_nit(self)))
        elif issubclass(self._native_type, str):
            bytes_repr = repr(str(Text.from_nit(self)))
        elif issubclass(self._native_type, bytes):
            bytes_repr = repr(self.bytes)
        elif issubclass(self._native_type, Nit):
            bytes_repr = repr(self.bytes)
            # NOTE:  We got here via the copy constructor from a sibling subclass of Nit.
            #        e.g. N(NitSubclass(...))
            #        We cannot reconstitute the original object (as we could repr() the int
            #        for N(Integer(42))) so let's just report raw bytes and nits.
        else:
            raise TypeError("N.repr cannot handle a " + repr(self._native_type))
        nit_reprs = [repr(nit) for nit in self.nits]
        nits_addendum = ''.join(', ' + nit_repr for nit_repr in nit_reprs)
        return 'N({bytes}{nits})'.format(
            bytes=bytes_repr,
            nits=nits_addendum
        )

    @property
    def bytes(self):
        return self._bytes

    @property
    def nits(self):
        return self._nits


class Integer(int, Nit):

    @property
    def bytes(self):
        """
        Generate two's complement, big endian, binary bytes to represent the integer.

        The 8-bit value of each byte is a base-256 digit, most significant first.
        A minimum number of bytes are generated, for example just one for -127 to +127.
        Except these edge cases generate an extra byte:  -128, -32768, -2**23, -2**31, ...
        That is, Integer(-128).bytes is FF 80 when it could theoretically be just 80.
        Similarly Integer(-32768).bytes is FF 80 00 not 80 00.
        """
        num_bits = self.bit_length()
        num_bytes = 1 + (num_bits // 8)
        return self.to_bytes(length=num_bytes, byteorder='big', signed=True)
        # NOTE:  This nit is stored as a Python int, not bytes.
        #        But the bytes can be made available by converting them from the internal int.

    @property
    def nits(self):
        return []

    @classmethod
    def from_nit(cls, nit):
        native_integer = super(Integer, cls).from_bytes(nit.bytes, 'big')
        # THANKS:  super() in and on a class method, https://stackoverflow.com/a/1269224/673991
        nit_integer = cls(native_integer)
        return nit_integer

    def __repr__(self):
        module_name = sys.modules[__name__].__name__
        return "{module_name}.{class_name}({value})".format(
            module_name=module_name,
            class_name=type(self).__name__,
            value=super(Integer, self).__repr__()
        )
        # EXAMPLE:  nit.Integer(42)


class Text(str, Nit):

    @property
    def bytes(self):
        return self.encode('utf-8')

    @property
    def nits(self):
        return []

    @classmethod
    def from_nit(cls, nit):
        native_text = nit.bytes.decode('utf-8')
        nit_text = cls(native_text)
        return nit_text

    def __repr__(self):
        module_name = sys.modules[__name__].__name__
        return "{module_name}.{class_name}({value})".format(
            module_name=module_name,
            class_name=type(self).__name__,
            value=super(Text, self).__repr__()
        )
        # EXAMPLE:  nit.Text('foo')


class Lex(Nit):

    @property
    def bytes(self):
        return b''

    @property
    def nits(self):
        raise NotImplementedError(f"{type(self).__name__} should implement nits")


class LexMemory(Lex):

    def __init__(self, nits=None):
        if nits is None:
            self._nits = []
        else:
            self._nits = nits

    @property
    def nits(self):
        return self._nits

    def __len__(self):
        return len(self._nits)

    def __getitem__(self, item):
        if item < 0:
            raise IndexError("Underflow")
        else:
            return self._nits[item]

    def add(self, nit):
        self._nits.append(nit)
