import six.moves


print(list(six.moves.range(7)))   # Should not generate a warning
print(six.PY2)


print("[0, 1, 2, 3, 4, 5, 6]")    # same output