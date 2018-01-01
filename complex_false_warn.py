import typing

class Moo: pass


class NotComplex(object):
    pass

def return_1j:
    return 1j

class OneComplex(object, Moo):  __complex__ = return_1j


class YesComplex(object, Moo):
    def __complex__(self): return 1j


print(complex(OneComplex()))   # Should not generate a warning.
print(complex(YesComplex()))   # Should not generate a warning.
print("(1+2j)")                # same output

print(complex(NotComplex()))   # Should generate warning "Unexpected type(s)" and raise a TypeError.
