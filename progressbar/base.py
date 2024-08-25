from __future__ import annotations

from typing.io import IO, TextIO  # type: ignore


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


assert IO is not None
assert TextIO is not None
