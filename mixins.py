from collections.abc import Sequence


class SingleElementList(Sequence):
    """
    A minimal implementation of the Sequence protocol for a single-element collection.
    
    This class demonstrates how to wrap a single value in a container that 
    behaves like a read-only list of length 1.
    """

    def __init__(self, value):
        """
        Initialize the list with a single value.
        
        Args:
            value: The object to be stored in the list.
        """
        self._value = value

    def __len__(self):
        """
        Returns the length of the list, which is always 1.
        
        Returns:
            int: Always 1.
        """
        return 1

    def __getitem__(self, index):
        """
        Provides index-based access. Only index 0 is valid.
        
        Args:
            index (int): The index to access.
            
        Raises:
            IndexError: If index is anything other than 0.
            
        Returns:
            Any: The stored value.
        """
        if index != 0:
            raise IndexError("SingleElementList only contains one item at index 0.")
        return self._value


class SequenceToStringMixin:
    """
    A mixin class that provides a standardized __repr__ for sequence-like objects.
    
    When mixed into a class that implements the Sequence protocol (like 
    having an __iter__ method), this class automatically provides a 
    clean string representation similar to a Python list: [item1, item2, ...].
    """

    def __repr__(self) -> str:
        """
        Generate a string representation of the sequence contents.
        
        Returns:
            str: A string in the format '[val1, val2, ...]'.
        """
        # Iterate over self (assuming the host class is iterable) and join reprs.
        contents = ", ".join(repr(item) for item in self)
        return f"[{contents}]"


class SingleElementListWithRepr(SingleElementList, SequenceToStringMixin):
    """
    A concrete implementation of a single-element list that uses the string mixin.
    """
    pass


class DictWithRepr(SequenceToStringMixin, dict):
    """
    A dictionary subclass that uses the SequenceToStringMixin for its representation.
    
    Note: Since dict iterates over its keys, this repr will show a list of keys.
    """
    pass


if __name__ == "__main__":
    # Internal demonstration of Mixins.
    
    # 1. Test SingleElementListWithRepr
    s = SingleElementListWithRepr(100)
    print("Testing SingleElementListWithRepr:")
    print(f"List content (repr): {s}")
    print(f"Is 100 in list? {100 in s}")
    for x in reversed(s):
        print(f"Reversed iteration: {x}")

    # 2. Test DictWithRepr
    d = DictWithRepr({1: "One", 2: "Two"})
    print("\nTesting DictWithRepr (shows keys only):")
    print(f"Dictionary keys as sequence: {d}")
