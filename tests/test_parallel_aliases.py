"""`starmap`, the tqdm-style aliases and progress-aware `as_completed`."""

from __future__ import annotations

import concurrent.futures
import io
import operator
import time

import pytest

from progressbar._parallel import _sync


def _add(left: int, right: int) -> int:
    return left + right


def _double(value: int) -> int:
    return value * 2


class TestStarmap:
    def test_unpacks_argument_tuples(self) -> None:
        assert _sync.starmap(operator.add, [(1, 2), (3, 4)], bar=False) == [
            3,
            7,
        ]

    def test_process_pool(self) -> None:
        assert _sync.starmap(
            _add, [(1, 2), (3, 4)], pool='process', workers=2, bar=False
        ) == [3, 7]

    def test_empty(self) -> None:
        assert _sync.starmap(operator.add, [], bar=False) == []


class TestTqdmStyleAliases:
    def test_thread_map(self) -> None:
        assert _sync.thread_map(_double, range(5), bar=False) == [
            0,
            2,
            4,
            6,
            8,
        ]

    def test_process_map(self) -> None:
        assert _sync.process_map(_double, range(5), workers=2, bar=False) == [
            0,
            2,
            4,
            6,
            8,
        ]

    def test_pool_kwarg_rejected(self) -> None:
        with pytest.raises(TypeError, match='pool'):
            _sync.thread_map(_double, range(3), pool='process', bar=False)
        with pytest.raises(TypeError, match='pool'):
            _sync.process_map(_double, range(3), pool='thread', bar=False)


class TestAsCompleted:
    def _futures(
        self, executor: concurrent.futures.ThreadPoolExecutor
    ) -> list[concurrent.futures.Future[int]]:
        return [executor.submit(_double, value) for value in range(5)]

    def test_yields_every_future_with_a_bar(self) -> None:
        stream = io.StringIO()
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            futures = self._futures(executor)
            seen = list(_sync.as_completed(futures, fd=stream))
        assert sorted(fut.result() for fut in seen) == [0, 2, 4, 6, 8]
        assert '5' in stream.getvalue()
        assert stream.getvalue().endswith('\n')

    @pytest.mark.no_freezegun
    def test_timeout_raises(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(1) as executor:
            blocker = executor.submit(time.sleep, 3)
            with pytest.raises(concurrent.futures.TimeoutError):
                list(
                    _sync.as_completed(
                        [blocker],
                        timeout=0.2,
                        poll_interval=0.05,
                        bar=False,
                    )
                )
            blocker.cancel()

    def test_early_break_leaves_futures_untouched(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            futures = self._futures(executor)
            for _future in _sync.as_completed(futures, bar=False):
                break
            # Not cancelled: the caller owns these futures.
            assert sorted(fut.result() for fut in futures) == [
                0,
                2,
                4,
                6,
                8,
            ]

    def test_empty(self) -> None:
        assert list(_sync.as_completed([], bar=False)) == []
