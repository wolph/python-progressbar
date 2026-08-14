"""Tests for the sync engine's ordered `map` over threads."""

from __future__ import annotations

import io
import operator
import threading
import time

import pytest

from progressbar._parallel import _sync


def _double(value: int) -> int:
    return value * 2


def _sleep_inverse(value: int) -> int:
    # Later items finish first, scrambling completion order.
    time.sleep((5 - value) * 0.02)
    return value


async def _async_double(value: int) -> int:  # pragma: no cover - never runs
    return value * 2


class TestMap:
    def test_ordered_results(self) -> None:
        assert _sync.map(_double, range(10), bar=False) == [
            value * 2 for value in range(10)
        ]

    def test_multiple_iterables_zip(self) -> None:
        assert _sync.map(operator.add, [1, 2], [10, 20], bar=False) == [
            11,
            22,
        ]

    def test_empty_input(self) -> None:
        assert _sync.map(_double, [], bar=False) == []

    @pytest.mark.no_freezegun
    def test_order_preserved_under_scrambled_completion(self) -> None:
        assert _sync.map(
            _sleep_inverse, range(5), workers=5, bar=False
        ) == list(range(5))

    def test_single_worker(self) -> None:
        assert _sync.map(_double, range(5), workers=1, bar=False) == [
            0,
            2,
            4,
            6,
            8,
        ]

    def test_small_buffersize_completes(self) -> None:
        assert _sync.map(
            _double, range(20), workers=2, buffersize=2, bar=False
        ) == [value * 2 for value in range(20)]

    def test_generator_input(self) -> None:
        assert _sync.map(
            _double, (value for value in range(5)), bar=False
        ) == [0, 2, 4, 6, 8]

    def test_coroutine_function_rejected(self) -> None:
        with pytest.raises(TypeError, match='amap'):
            _sync.map(_async_double, range(3), bar=False)

    def test_bar_false_produces_no_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _sync.map(_double, range(3), bar=False)
        captured = capsys.readouterr()
        assert captured.out == ''
        assert captured.err == ''

    def test_typo_kwarg_raises(self) -> None:
        with pytest.raises(TypeError, match='worker'):
            _sync.map(_double, range(3), worker=8)

    def test_bar_renders_progress(self) -> None:
        stream = io.StringIO()
        _sync.map(_double, range(3), fd=stream)
        assert '3' in stream.getvalue()
        assert stream.getvalue().endswith('\n')

    def test_runs_in_worker_threads(self) -> None:
        main_thread: threading.Thread = threading.current_thread()
        seen: set[str] = set()

        def _record(value: int) -> int:
            seen.add(threading.current_thread().name)
            return value

        _sync.map(_record, range(10), workers=2, bar=False)
        assert main_thread.name not in seen


class TestResolveExecutor:
    def test_thread_pool_created_and_owned(self) -> None:
        executor, owned, workers = _sync.resolve_executor(
            'thread',
            3,
            initializer=None,
            initargs=(),
            mp_context=None,
            max_tasks_per_child=None,
            thread_name_prefix='',
        )
        try:
            assert owned is True
            assert workers == 3
            assert executor.submit(_double, 2).result() == 4
        finally:
            executor.shutdown()

    def test_unknown_pool_raises(self) -> None:
        with pytest.raises(ValueError, match='bogus'):
            _sync.resolve_executor(
                'bogus',
                None,
                initializer=None,
                initargs=(),
                mp_context=None,
                max_tasks_per_child=None,
                thread_name_prefix='',
            )
