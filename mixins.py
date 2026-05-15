from collections.abc import Sequence


class SingleElementList(Sequence):
    def __init__(self, value):
        self._value = value
    def __len__(self):
        return 1
    def __getitem__(self, index):
        if index != 0:
            raise IndexError("Index out of range")
        return self._value

class SequenceToStringMixin:
    def __repr__(self) -> str:
        contents = ", ".join(repr(item) for item in self)
        return f"[{contents}]"

class SingleElementListWithRepr(SingleElementList, SequenceToStringMixin):
    pass

class DictWithRepr(SequenceToStringMixin, dict):
    pass

if __name__ == "__main__":
    s = SingleElementListWithRepr(1)
    for x in reversed(s):
        print(x)

    print(1 in s)
    print(s)

    d = {1:2, 2:4}
    print(d)

    d = DictWithRepr(d)
    print(d)