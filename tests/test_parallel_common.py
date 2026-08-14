"""Tests for the shared plumbing behind the parallel execution verbs."""

from __future__ import annotations

import typing

import pytest
from progressbar._parallel import _common

import progressbar
from progressbar import base


def _boom_on_two(value: int) -> int:
    """Module-level worker: raises on input 2, else returns the input."""
    if value == 2:
        raise ValueError('boom')
    return value


def _unsized() -> typing.Iterator[int]:
    yield from (1, 2, 3)


class TestDetectTotal:
    def test_sized(self) -> None:
        assert _common.detect_total(([1, 2, 3],)) == 3

    def test_length_hint(self) -> None:
        # A list_iterator has no __len__ but supports __length_hint__.
        assert _common.detect_total((iter([1, 2]),)) == 2

    def test_unsized(self) -> None:
        assert _common.detect_total((_unsized(),)) is base.UnknownLength

    def test_multiple_iterables_take_min(self) -> None:
        assert _common.detect_total(([1, 2, 3], [1, 2])) == 2

    def test_mixed_sized_and_unsized(self) -> None:
        assert _common.detect_total(([1, 2], _unsized())) is base.UnknownLength

    def test_no_iterables(self) -> None:
        assert _common.detect_total(()) == 0


class TestValidateBarKwargs:
    def test_known_keys_pass(self) -> None:
        _common.validate_bar_kwargs({'prefix': 'x', 'max_value': 10})

    def test_typo_raises(self) -> None:
        with pytest.raises(TypeError, match='worker'):
            _common.validate_bar_kwargs({'worker': 8})

    def test_known_names_present(self) -> None:
        names: frozenset[str] = _common.known_bar_kwargs(
            progressbar.ProgressBar
        )
        assert {'poll_interval', 'max_value', 'widgets'} <= names
        assert 'self' not in names


class TestResolveWorkers:
    def test_explicit(self) -> None:
        assert _common.resolve_workers(7, 'thread') == 7

    def test_thread_default_capped(self) -> None:
        assert 1 <= _common.resolve_workers(None, 'thread') <= 32

    def test_process_default(self) -> None:
        assert _common.resolve_workers(None, 'process') >= 1


class TestBufferAndChunkDefaults:
    def test_default_buffersize(self) -> None:
        assert _common.default_buffersize(8) == 32
        assert _common.default_buffersize(1) == 16

    def test_auto_chunksize_unknown_total(self) -> None:
        assert _common.auto_chunksize(base.UnknownLength, 8) == 1

    def test_auto_chunksize_scales(self) -> None:
        assert _common.auto_chunksize(100_000, 8) == 781

    def test_auto_chunksize_small_batch(self) -> None:
        assert _common.auto_chunksize(10, 8) == 1

    def test_auto_chunksize_capped(self) -> None:
        assert _common.auto_chunksize(10_000_000, 1) == 1_000


class TestIterChunks:
    def test_single_iterable(self) -> None:
        chunks: list[list[tuple[int, ...]]] = list(
            _common.iter_chunks(([1, 2, 3, 4, 5],), 2)
        )
        assert chunks == [[(1,), (2,)], [(3,), (4,)], [(5,)]]

    def test_zips_multiple_iterables(self) -> None:
        chunks = list(_common.iter_chunks(([1, 2], ['a', 'b']), 10))
        assert chunks == [[(1, 'a'), (2, 'b')]]

    def test_lazy(self) -> None:
        # Consuming one chunk must not consume the whole source.
        source: typing.Iterator[int] = iter(range(100))
        first: list[tuple[int, ...]] = next(_common.iter_chunks((source,), 3))
        assert first == [(0,), (1,), (2,)]
        assert next(source) < 10


class TestItemOf:
    def test_single(self) -> None:
        assert _common.item_of((42,), single=True) == 42

    def test_multiple(self) -> None:
        assert _common.item_of((1, 2), single=False) == (1, 2)


class TestRunChunk:
    def test_catch_returns_outcomes(self) -> None:
        outcomes: list[tuple[bool, typing.Any]] = _common.run_chunk(
            _boom_on_two, [(1,), (2,), (3,)], catch=True
        )
        assert [ok for ok, _ in outcomes] == [True, False, True]
        assert outcomes[0] == (True, 1)
        assert isinstance(outcomes[1][1], ValueError)

    def test_no_catch_aborts_chunk(self) -> None:
        with pytest.raises(ValueError, match='boom'):
            _common.run_chunk(_boom_on_two, [(1,), (2,), (3,)], catch=False)

    def test_catch_lets_keyboard_interrupt_escape(self) -> None:
        def _interrupt(_: int) -> None:
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            _common.run_chunk(_interrupt, [(1,)], catch=True)


class TestCurrentTaskBar:
    def test_default_is_none(self) -> None:
        assert _common.current_task_bar() is None

    def test_with_task_bar_binds_and_restores(self) -> None:
        marker: progressbar.ProgressBar = progressbar.ProgressBar(max_value=1)
        seen: list[progressbar.ProgressBar | None] = []

        def _inner() -> str:
            seen.append(_common.current_task_bar())
            return 'done'

        wrapped: typing.Callable[[], str] = _common.with_task_bar(
            marker, _inner
        )
        assert wrapped() == 'done'
        assert seen == [marker]
        assert _common.current_task_bar() is None
