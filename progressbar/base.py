"""Sentinels for "no length known" and "no value given".

Both sentinels are *classes*, not instances, and both are falsey. That
is the whole point of `FalseMeta`: it lets the rest of the library write
`if self.max_value:` and have that mean "has a known, usable length",
without a separate `is UnknownLength` check at every site. See
`ProgressBar.data` and the update-gate logic in `progressbar.bar` for
the call sites that rely on it.
"""

from __future__ import annotations

from typing import IO, TextIO


class FalseMeta(type):
    """Metaclass making its classes evaluate as false.

    Applied to the sentinels below so they can stand in for a missing
    value in a boolean test rather than needing an identity comparison.
    """

    @classmethod
    def __bool__(cls) -> bool:  # pragma: no cover
        """Report the class itself as falsey."""
        return False


class UnknownLength(metaclass=FalseMeta):
    """The total amount of work is not knowable in advance.

    Passed as `max_value` for an iterable with no `__len__` (a
    generator, a stream) so the bar renders progress without a
    percentage or an ETA.
    """


class Undefined(metaclass=FalseMeta):
    """No value was supplied, where `None` is itself meaningful."""


assert IO is not None
assert TextIO is not None

__all__ = (
    'IO',
    'FalseMeta',
    'TextIO',
    'Undefined',
    'UnknownLength',
)
