"""
Nit - most basic and generic object
"""


class Nit:

    @property
    def bytes(self):
        raise NotImplementedError(f"{self.__class__.__name__} should implement a bytes property")

    @property
    def nits(self):
        raise NotImplementedError(f"{self.__class__.__name__} should implement a nits property")

    @staticmethod
    def is_nat(x):
        return len(x.bytes) == 0 and len(x.nits) == 0


class Integer(int, Nit):

    @property
    def bytes(self):
        num_bits = self.bit_length()
        num_bytes = 1 + num_bits // 8
        return self.to_bytes(length=num_bytes, byteorder='big', signed=True)
        # NOTE:  The bytes aren't stored as bytes, but they can be made available as bytes

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
        raise NotImplementedError(f"{self.__class__.__name__} should implement nits")


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
