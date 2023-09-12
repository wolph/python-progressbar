from python_utils import types


class FalseMeta(type):
    @classmethod
    def __bool__(cls):  # pragma: no cover
        return False

    @classmethod
    def __cmp__(cls, other):  # pragma: no cover
        return -1

    __nonzero__ = __bool__


class UnknownLength(metaclass=FalseMeta):
    pass


class Undefined(metaclass=FalseMeta):
    pass


try:  # pragma: no cover
    IO = types.IO  # type: ignore
    TextIO = types.TextIO  # type: ignore
except AttributeError:  # pragma: no cover
    from typing.io import IO, TextIO  # type: ignore

assert IO is not None
assert TextIO is not None
