class YesComplex(object):
    def __complex__(self):
        return 1+2j


class NotComplex(object):
    pass


print(complex(YesComplex()))   # Should not generate a warning.
print("(1+2j)")                # same output






print(complex(NotComplex()))   # Should generate warning "Unexpected type(s)" and raise a TypeError.
