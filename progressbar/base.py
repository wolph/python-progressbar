# -*- mode: python; coding: utf-8 -*-
from python_utils import types


class FalseMeta(type):
    def __bool__(self):  # pragma: no cover
        return False

    def __cmp__(self, other):  # pragma: no cover
        return -1

    __nonzero__ = __bool__


class UnknownLength(metaclass=FalseMeta):
    pass


class Undefined(metaclass=FalseMeta):
    pass


try:  # pragma: no cover
    IO = types.IO  # type: ignore
    TextIO = types.TextIO  # type: ignore
except AttributeError:
    from typing.io import IO, TextIO  # type: ignore

assert IO
assert TextIO
