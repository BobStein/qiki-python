"""
Nit - a most basic and generic and simple object:  a nit contains bytes and nits.
"""


class Nit:
    """
    A nit contains bytes and nits.
        nit.bytes
        nit.nits

    bytes are a sequence of 8-bit bytes.
    bytes may represent:
        a utf-8 encoded string
        the signed, big-endian, base-256 digits of an integer
        anything else

    Today, a nit knows:
        how many bytes it has (len(nit.bytes))
        how many nits it has (len(nit.nits))
    Though perhaps someday either bytes or nits could be an iterable stream.
    """
    @property
    def bytes(self):
        raise NotImplementedError("{class_name} should implement a bytes property".format(
            class_name=type(self).__name__)
        )

    @property
    def nits(self):
        raise NotImplementedError("{class_name} should implement a nits property".format(
            class_name=type(self).__name__)
        )

    @staticmethod
    def is_nat(x):
        """NAT is Not A Thang, when both bytes and nits are empty."""
        return len(x.bytes) == 0 and len(x.nits) == 0

    def recurse(self):
        for each_nit in self.nits:
            yield each_nit
            if len(each_nit.nits) > 0:
                # NOTE:  The following loop is the equivalent of:  yield from each_nit.recurse()
                for sub_nit in each_nit.recurse():
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
        list_of_nit_like_things = []
        self._native_type = type(_bytes)
        if isinstance(_bytes, type(None)):
            self._bytes = b''
        elif isinstance(_bytes, int):
            self._bytes = Integer(_bytes).bytes
        elif isinstance(_bytes, str):
            self._bytes = Text(_bytes).bytes
        elif isinstance(_bytes, bytes):
            self._bytes = _bytes
        elif isinstance(_bytes, list):
            self.__init__(*_bytes, *args)   # unwrap the list -- recursively
            # NOTE:  So N([1,2,3]) is the same as N(1,2,3)
            #        Cute huh?  Wish I could remember the cute reason to do this...
        elif isinstance(_bytes, N):
            # NOTE:  The main purpose of this copy constructor is so all the args
            #        can be passed through this constructor (which is a recursion of course).
            #        This gives the option:  arguments for the nits can be either
            #        N instances or things suitable for passing to the N constructor.
            #        So N(1,2,3) is shorthand for N(1,N(2),N(3))
            #        In other words, sub-nits are always themselves nits, but if they have no
            #        sub-sub-nits, then N() expressions can be abbreviated to just the content of
            #        the bytes.
            self._bytes = _bytes.bytes
            self._native_type = _bytes._native_type
            self._nits += _bytes._nits
        elif isinstance(_bytes, Nit):
            # NOTE:  The purpose of THIS copy constructor is to catch the Nit subclasses that
            #        are not a subclass of N.  (That is, kin but not descendents.)
            self._bytes = _bytes.bytes
            self._native_type = type(_bytes)
            # NOTE:  This original type will not be reconstituted by native_bytes.  So if it has
            #        a custom .to_json() method that will not be called when something that contains
            #        it is converted to JSON by json_encode().
            self._nits += _bytes.nits
        else:
            raise TypeError("Cannot N({bytes_type}):  {bytes_value}".format(
                bytes_type=type(_bytes).__name__,
                bytes_value=repr(_bytes),
            ))

        list_of_nit_like_things += list(args)
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

    def render_bytes(self):
        """Render the bytes part according to the native-type it came from."""
        if self.is_nat(self):
            rendering = ''
        elif isinstance(None, self._native_type):
            # NOTE:  The reason we need to check isinstance(None) when we've already checked
            #        is_nat() is the case where a nit has some nits but empty bytes.  That's not a
            #        nat.  And conveniently it's a special case where repr() need to produce "None"
            #        for the bytes, so we can put in the nits after it.
            rendering = repr(None)
        elif issubclass(self._native_type, int):
            rendering = repr(int(Integer.from_nit(self)))
        elif issubclass(self._native_type, str):
            rendering = repr(str(Text.from_nit(self)))
        elif issubclass(self._native_type, bytes):
            rendering = repr(self.bytes)
        elif issubclass(self._native_type, Nit):
            rendering = repr(self.bytes)
            # NOTE:  We can get here via the copy constructor from a sibling subclass of Nit.
            #        e.g. N(NitSubclass(...)) where NitSubclass is a subclass of Nit but not N.
            #        We cannot reconstitute the original object (as we could for N(Integer(42)))
            #        so let's just render the raw bytes.
        else:
            raise TypeError("Cannot render bytes that came from a " + repr(self._native_type))
        return rendering

    def native_bytes(self):
        """Reconstitute the original object that was digested to make the bytes part"""
        if isinstance(None, self._native_type):
            native = None
        elif issubclass(self._native_type, int):
            native = int(Integer.from_nit(self))
        elif issubclass(self._native_type, str):
            native = str(Text.from_nit(self))
        elif issubclass(self._native_type, bytes):
            native = self.bytes
        else:
            raise TypeError("Cannot reconstitute a " + repr(self._native_type))
        return native

    def __repr__(self):
        bytes_repr = self.render_bytes()
        nit_reprs = [repr(nit) for nit in self.nits]
        nits_addendum = ''.join(', ' + nit_repr for nit_repr in nit_reprs)
        return 'N({bytes}{nits})'.format(
            bytes=bytes_repr,
            nits=nits_addendum
        )

    def to_json(self):
        if len(self.nits) == 0:
            return self.native_bytes()
        else:
            return [self.native_bytes(), *self.nits]

    def __int__(self):
        if issubclass(self._native_type, int):
            return int(Integer.from_nit(self))
        elif hasattr(self._native_type, '__name__'):
            raise TypeError("int() cannot convert a N({})".format(self._native_type.__name__))
        else:
            raise TypeError("int() cannot convert a {}".format(type(self).__name__))

    def __str__(self):
        if issubclass(self._native_type, str) and len(self.nits) == 0:
            return str(Text.from_nit(self))
        elif issubclass(self._native_type, int) and len(self.nits) == 0:
            return str(int(Integer.from_nit(self)))
        else:
            return repr(self)

    def __hash__(self):
        return hash((self.bytes, tuple(self.nits)))
        # THANKS:  hash of a combination, https://stackoverflow.com/a/56915493/673991

    @property
    def bytes(self):
        return self._bytes

    @property
    def nits(self):
        return self._nits

    # FALSE WARNING:  Function name should be lowercase
    # noinspection PyPep8Naming
    def N(self, *args):
        """Append one additional sub-nit.  (Which may itself have sub-nits.)"""
        return N(self, N(*args))


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
        native_integer = super(Integer, cls).from_bytes(nit.bytes, byteorder='big', signed=True)
        # THANKS:  super() in and on a class method, https://stackoverflow.com/a/1269224/673991
        nit_integer = cls(native_integer)
        return nit_integer

    def __repr__(self):
        return "nit.Integer({})".format(super(Integer, self).__repr__())
        # EXAMPLE:  nit.Integer(42)


class Text(str, Nit):

    @property
    def bytes(self):

        return self.encode('utf-8')
        # EXAMPLE:  UnicodeEncodeError: 'utf-8' codec can't encode characters in position 17-18:
        #           surrogates not allowed
        #           position 17-18 of the line in question:
        #               '\ud83d\udca9 \ud83d\udcaa \n<br>"moo\'foo&times;'   # noqa
        # NOTE:  This happens when Python interprets the output of json.dumps().  This highlights
        #        the only JSON string literal syntax that's not also Python string literal syntax.
        #        It is the use of a surrogate pair of unicode characters from the Basic Multilingual
        #        Plane (plane 0) to represent a unicode character from a supplementary plane
        #        (plane 1-16).  JavaScript, forever hamstrung by its internal 16-bit representation
        #        of strings as arrays of unicode BMP characters, also handles this scheme with some
        #        intelligence, printing the two characters as one, though they still contribute 2 to
        #        .length. Python wants nothing to do with all this. Internally Python 3 stores up to
        #        32 bits for every character. Instead of Python interpreting a surrogate pair output
        #        by json.dumps(), it should pass it to json.loads().
        # THANKS:  "there is a bug upstream", https://stackoverflow.com/a/38147966/673991

        # return self.encode('utf-8', 'surrogateescape')   # noqa
        # NO THANKS:  same error as above, "surrogates not allowed"
        #             https://stackoverflow.com/q/27366479/673991

        # return self.encode('utf-8', 'replace')
        # THANKS:  possible solution or kicking-can-down-the-unicode-road for the error message
        #          UnicodeEncodeError: 'utf-8' codec can't encode: surrogates not allowed
        #          https://stackoverflow.com/a/61458976/673991

        # NOTE:  An ultimate solution might be to convert surrogate pairs in the Text() constructor.
        #            2 == len("\ud808\udf45")
        #            1 == len("\ud808\udf45".encode('utf-16', 'surrogatepass').decode('utf-16'))
        #        Or this could be dumb.
        # KUDOS:  "a more detailed explanation", https://stackoverflow.com/a/54549164/673991

    @property
    def nits(self):
        return []

    @classmethod
    def from_nit(cls, nit):
        native_text = nit.bytes.decode('utf-8')
        nit_text = cls(native_text)
        return nit_text

    def __repr__(self):
        return "nit.Text({})".format(super(Text, self).__repr__(),)
        # EXAMPLE:  nit.Text('foo')


class Lex(Nit):
    """A Nit that may be too big to store all its sub-nits in memory."""

    @property
    def bytes(self):
        return b''

    @property
    def nits(self):
        raise NotImplementedError("{class_name} should implement nits".format(
            class_name=type(self).__name__)
        )


class LexMemory(Lex):
    """I said *MAY* be too big.  This lex actually does store its sub-nits in memory."""
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
