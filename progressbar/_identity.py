"""Private identity-based tracking that never calls application hash hooks."""

from __future__ import annotations

import collections.abc
import typing

_Key = typing.TypeVar('_Key')
_Value = typing.TypeVar('_Value')


class IdentityMap(collections.abc.MutableMapping[_Key, _Value]):
    """Track bars by identity without calling their hash or equality hooks."""

    def __init__(self) -> None:
        self._items: dict[int, tuple[_Key, _Value]] = {}

    def __getstate__(self) -> list[tuple[_Key, _Value]]:
        """Serialise retained objects without their process-local ids."""
        return list(self._items.values())

    def __setstate__(self, state: list[tuple[_Key, _Value]]) -> None:
        """Rebuild ids after pickle or deepcopy restores the objects."""
        self._items = {id(key): (key, value) for key, value in state}

    def __getitem__(self, key: _Key) -> _Value:
        """Return the value belonging to this exact bar."""
        return self._items[id(key)][1]

    def __setitem__(self, key: _Key, value: _Value) -> None:
        """Retain the bar alongside its value to prevent id reuse."""
        self._items[id(key)] = (key, value)

    def __delitem__(self, key: _Key) -> None:
        """Remove this exact bar's entry."""
        del self._items[id(key)]

    def __iter__(self) -> collections.abc.Iterator[_Key]:
        """Iterate the retained bars."""
        return (item[0] for item in self._items.values())

    def __len__(self) -> int:
        """Return the number of tracked bars."""
        return len(self._items)


class IdentitySet(collections.abc.MutableSet[_Key]):
    """Remember labelled bars without calling application hash hooks."""

    def __init__(self) -> None:
        self._items: dict[int, _Key] = {}

    def __getstate__(self) -> list[_Key]:
        """Serialise retained objects without their process-local ids."""
        return list(self._items.values())

    def __setstate__(self, state: list[_Key]) -> None:
        """Rebuild ids after pickle or deepcopy restores the objects."""
        self._items = {id(value): value for value in state}

    def __contains__(self, value: object) -> bool:
        """Check whether this exact object is remembered."""
        return id(value) in self._items

    def __iter__(self) -> collections.abc.Iterator[_Key]:
        """Iterate remembered bars."""
        return iter(self._items.values())

    def __len__(self) -> int:
        """Return the number of remembered bars."""
        return len(self._items)

    def add(self, value: _Key) -> None:
        """Retain a labelled bar by identity."""
        self._items[id(value)] = value

    def discard(self, value: _Key) -> None:
        """Forget a labelled bar if it was remembered."""
        self._items.pop(id(value), None)
