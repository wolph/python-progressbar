"""Lazy ordered `imap` and completion-order `imap_unordered`."""

from __future__ import annotations

import contextlib
import operator
import threading
import time
import typing

import pytest

from progressbar._parallel import _sync

_executed: set[int] = set()
_executed_lock: threading.Lock = threading.Lock()


def _double(value: int) -> int:
    return value * 2


def _record(value: int) -> int:
    with _executed_lock:
        _executed.add(value)
    return value


def _sleep_inverse(value: int) -> int:
    # Later items finish first, scrambling completion order.
    time.sleep((5 - value) * 0.03)
    return value


def _boom_on_two(value: int) -> int:
    if value == 2:
        raise ValueError('boom')
    return value


class TestImap:
    def test_yields_results_in_input_order(self) -> None:
        assert list(_sync.imap(_double, range(10), bar=False)) == [
            value * 2 for value in range(10)
        ]

    @pytest.mark.no_freezegun
    def test_ordered_despite_scrambled_completion(self) -> None:
        assert list(
            _sync.imap(_sleep_inverse, range(5), workers=5, bar=False)
        ) == list(range(5))

    def test_lazy(self) -> None:
        iterator: typing.Generator[typing.Any, None, None] = _sync.imap(
            _double, range(10), workers=1, bar=False
        )
        assert next(iterator) == 0
        iterator.close()

    def test_on_error_return_yields_exceptions_in_place(self) -> None:
        results: list[typing.Any] = list(
            _sync.imap(_boom_on_two, range(4), on_error='return', bar=False)
        )
        assert results[0] == 0
        assert isinstance(results[2], ValueError)
        assert results[3] == 3

    def test_on_error_raise_raises_at_iteration(self) -> None:
        iterator = _sync.imap(_boom_on_two, range(4), workers=1, bar=False)
        with pytest.raises(ValueError, match='boom'):
            list(iterator)


class TestImapUnordered:
    @pytest.mark.no_freezegun
    def test_yields_pairs_in_completion_order(self) -> None:
        pairs: list[tuple[int, int]] = list(
            _sync.imap_unordered(
                _sleep_inverse, range(5), workers=5, bar=False
            )
        )
        assert sorted(pairs) == [(value, value) for value in range(5)]
        # The fastest item (highest input) completes and is seen first.
        assert pairs[0] == (4, 4)

    def test_multi_iterable_pairs_use_args_tuple(self) -> None:
        pairs = list(
            _sync.imap_unordered(
                operator.add, [1, 2], [10, 20], workers=1, bar=False
            )
        )
        assert sorted(pairs) == [((1, 10), 11), ((2, 20), 22)]

    def test_on_error_return_pairs_exceptions(self) -> None:
        pairs = dict(
            _sync.imap_unordered(
                _boom_on_two, range(4), on_error='return', bar=False
            )
        )
        assert isinstance(pairs[2], ValueError)
        assert pairs[3] == 3


class TestGeneratorCleanup:
    def test_early_break_stops_submission(self) -> None:
        _executed.clear()
        for item, _result in _sync.imap_unordered(
            _record, range(100), workers=1, buffersize=2, bar=False
        ):
            if item >= 1:
                break
        # workers=1, window=2: only the in-window items ever ran; the
        # other ~97 must have been cancelled by the generator close.
        time.sleep(0.2)  # let any straggler drain before asserting
        assert len(_executed) <= 5

    def test_contextlib_closing_recipe(self) -> None:
        with contextlib.closing(
            _sync.imap(_double, range(10), workers=1, bar=False)
        ) as iterator:
            assert next(iterator) == 0
