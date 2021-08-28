"""
Nit - most basic and generic object
"""


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
    def __init__(self, _bytes=None, _nits=None):
        self._bytes = _bytes or b''
        if isinstance(_bytes, type(None)):
            self._bytes = b''
        elif isinstance(_bytes, int):
            self._bytes = Integer(_bytes).bytes
        elif isinstance(_bytes, str):
            self._bytes = Text(_bytes).bytes
        elif isinstance(_bytes, bytes):
            self._bytes = _bytes
        else:
            raise TypeError("Cannot N({bytes_type})".format(bytes_type=type(_bytes).__name__))
        self._nits = _nits or []

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


class Text(str, Nit):

    @property
    def bytes(self):
        return self.encode('utf-8')

    @property
    def nits(self):
        return []


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
