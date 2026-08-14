"""The asyncio engine: `amap` and its call-strategy handling."""

from __future__ import annotations

import asyncio
import io
import operator
import typing

import pytest

from progressbar._parallel import _async


async def _async_double(value: int) -> int:
    return value * 2


def _sync_double(value: int) -> int:
    return value * 2


def _returns_awaitable(value: int) -> typing.Awaitable[int]:
    return _async_double(value)


async def _boom_on_two(value: int) -> int:
    if value == 2:
        raise ValueError('boom')
    return value


class TestAmap:
    def test_async_fn_ordered(self) -> None:
        async def _run() -> list[int]:
            return await _async.amap(_async_double, range(10), bar=False)

        assert asyncio.run(_run()) == [value * 2 for value in range(10)]

    @pytest.mark.no_freezegun
    def test_ordered_despite_scrambled_completion(self) -> None:
        async def _staggered(value: int) -> int:
            await asyncio.sleep((5 - value) * 0.02)
            return value

        async def _run() -> list[int]:
            return await _async.amap(_staggered, range(5), bar=False)

        assert asyncio.run(_run()) == list(range(5))

    @pytest.mark.no_freezegun
    def test_sync_fn_wrapped_in_thread(self) -> None:
        async def _run() -> list[int]:
            return await _async.amap(_sync_double, range(5), bar=False)

        assert asyncio.run(_run()) == [0, 2, 4, 6, 8]

    @pytest.mark.no_freezegun
    def test_sync_fn_returning_awaitable_is_awaited(self) -> None:
        async def _run() -> list[int]:
            return await _async.amap(_returns_awaitable, range(4), bar=False)

        assert asyncio.run(_run()) == [0, 2, 4, 6]

    def test_multiple_iterables_zip(self) -> None:
        async def _add(left: int, right: int) -> int:
            return left + right

        async def _run() -> list[int]:
            return await _async.amap(_add, [1, 2], [10, 20], bar=False)

        assert asyncio.run(_run()) == [11, 22]

    def test_empty(self) -> None:
        async def _run() -> list[int]:
            return await _async.amap(_async_double, [], bar=False)

        assert asyncio.run(_run()) == []

    @pytest.mark.no_freezegun
    def test_concurrency_capped(self) -> None:
        running: list[int] = [0]
        seen_max: list[int] = [0]

        async def _tracked(value: int) -> int:
            running[0] += 1
            seen_max[0] = max(seen_max[0], running[0])
            await asyncio.sleep(0.02)
            running[0] -= 1
            return value

        async def _run() -> list[int]:
            return await _async.amap(
                _tracked, range(10), concurrency=2, bar=False
            )

        assert asyncio.run(_run()) == list(range(10))
        assert seen_max[0] <= 2

    def test_workers_alias(self) -> None:
        async def _run() -> list[int]:
            return await _async.amap(
                _async_double, range(4), workers=2, bar=False
            )

        assert asyncio.run(_run()) == [0, 2, 4, 6]


class TestAmapErrors:
    def test_fail_fast(self) -> None:
        async def _run() -> list[int]:
            return await _async.amap(
                _boom_on_two, range(10), concurrency=1, bar=False
            )

        with pytest.raises(ValueError, match='boom'):
            asyncio.run(_run())

    def test_on_error_return(self) -> None:
        async def _run() -> list[typing.Any]:
            return await _async.amap(
                _boom_on_two, range(5), on_error='return', bar=False
            )

        results: list[typing.Any] = asyncio.run(_run())
        assert results[1] == 1
        assert isinstance(results[2], ValueError)
        assert results[4] == 4

    @pytest.mark.no_freezegun
    def test_timeout_cancels_cleanly(self) -> None:
        async def _slow(value: int) -> int:
            await asyncio.sleep(30)
            return value  # pragma: no cover - always cancelled

        async def _run() -> list[int]:
            return await _async.amap(
                _slow,
                range(4),
                timeout=0.2,
                poll_interval=0.05,
                bar=False,
            )

        with pytest.raises(asyncio.TimeoutError):
            asyncio.run(_run())
        # asyncio.run closing the loop without warnings proves the
        # outstanding tasks were cancelled and awaited.

    def test_invalid_on_error(self) -> None:
        async def _run() -> list[int]:
            return await _async.amap(
                _async_double, range(3), on_error='ignore', bar=False
            )

        with pytest.raises(ValueError, match='on_error'):
            asyncio.run(_run())


class TestKeepAlive:
    @pytest.mark.no_freezegun
    def test_bar_ticks_during_long_task(self) -> None:
        stream = io.StringIO()

        async def _slow(value: int) -> int:
            await asyncio.sleep(0.4)
            return value

        async def _run() -> list[int]:
            return await _async.amap(
                _slow, range(2), poll_interval=0.05, fd=stream
            )

        assert asyncio.run(_run()) == [0, 1]
        # Multiple renders happened while the tasks slept: the output
        # contains far more than the start + finish frames. Count
        # rendered frames by their timer text -- the line separator
        # depends on stream/tty detection.
        assert stream.getvalue().count('Elapsed Time') > 3


class TestCallStrategy:
    def test_detects_coroutine_function(self) -> None:
        assert _async._call_strategy(_async_double) == 'async'

    def test_detects_partial_of_coroutine_function(self) -> None:
        import functools

        partial = functools.partial(_async_double)
        assert _async._call_strategy(partial) == 'async'

    def test_sync_fallback(self) -> None:
        assert _async._call_strategy(_sync_double) == 'sync'
        assert _async._call_strategy(operator.add) == 'sync'
