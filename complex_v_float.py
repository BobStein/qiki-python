class YesFloat(object):
    def __float__(self):
        return 4.2


class NotFloat(object):
    pass


print(float(YesFloat()))   # Does not generate a warning.
print("4.2")               # same output

print(float(NotFloat()))   # Generates warning "Unexpected type(s)" and raises a TypeError.
