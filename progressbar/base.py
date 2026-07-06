from __future__ import annotations

from typing import IO, TextIO


class FalseMeta(type):
    @classmethod
    def __bool__(cls) -> bool:  # pragma: no cover
        return False


class UnknownLength(metaclass=FalseMeta):
    pass


class Undefined(metaclass=FalseMeta):
    pass


assert IO is not None
assert TextIO is not None

__all__ = (
    'IO',
    'FalseMeta',
    'TextIO',
    'Undefined',
    'UnknownLength',
)
