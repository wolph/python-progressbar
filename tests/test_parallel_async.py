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


class TestAimap:
    @pytest.mark.no_freezegun
    def test_ordered_despite_scrambled_completion(self) -> None:
        async def _staggered(value: int) -> int:
            await asyncio.sleep((5 - value) * 0.02)
            return value

        async def _run() -> list[int]:
            return [
                value
                async for value in _async.aimap(
                    _staggered, range(5), bar=False
                )
            ]

        assert asyncio.run(_run()) == list(range(5))

    @pytest.mark.no_freezegun
    def test_early_break_with_aclosing(self) -> None:
        import contextlib

        async def _run() -> list[int]:
            collected: list[int] = []
            async with contextlib.aclosing(
                _async.aimap(
                    _async_double, range(10), concurrency=2, bar=False
                )
            ) as iterator:
                async for value in iterator:
                    collected.append(value)
                    if len(collected) == 2:
                        break
            return collected

        assert asyncio.run(_run()) == [0, 2]


class TestAimapUnordered:
    @pytest.mark.no_freezegun
    def test_yields_pairs_in_completion_order(self) -> None:
        async def _staggered(value: int) -> int:
            await asyncio.sleep((5 - value) * 0.02)
            return value

        async def _run() -> list[tuple[int, int]]:
            return [
                pair
                async for pair in _async.aimap_unordered(
                    _staggered, range(5), bar=False
                )
            ]

        pairs: list[tuple[int, int]] = asyncio.run(_run())
        assert sorted(pairs) == [(value, value) for value in range(5)]
        assert pairs[0] == (4, 4)

    def test_multi_iterable_pairs_use_args_tuple(self) -> None:
        async def _add(left: int, right: int) -> int:
            return left + right

        async def _run() -> list[tuple[typing.Any, int]]:
            return [
                pair
                async for pair in _async.aimap_unordered(
                    _add, [1, 2], [10, 20], bar=False
                )
            ]

        assert sorted(asyncio.run(_run())) == [
            ((1, 10), 11),
            ((2, 20), 22),
        ]


class TestGather:
    def test_ordered_results(self) -> None:
        async def _run() -> list[int]:
            return await _async.gather(
                _async_double(1),
                _async_double(2),
                _async_double(3),
                bar=False,
            )

        assert asyncio.run(_run()) == [2, 4, 6]

    def test_empty_returns_empty_list(self) -> None:
        async def _run() -> list[typing.Any]:
            return await _async.gather()

        assert asyncio.run(_run()) == []

    def test_return_exceptions(self) -> None:
        async def _run() -> list[typing.Any]:
            return await _async.gather(
                _async_double(1),
                _boom_on_two(2),
                _async_double(3),
                return_exceptions=True,
                bar=False,
            )

        results: list[typing.Any] = asyncio.run(_run())
        assert results[0] == 2
        assert isinstance(results[1], ValueError)
        assert results[2] == 6

    def test_fail_fast_by_default(self) -> None:
        async def _run() -> list[typing.Any]:
            return await _async.gather(
                _async_double(1), _boom_on_two(2), bar=False
            )

        with pytest.raises(ValueError, match='boom'):
            asyncio.run(_run())


class TestAsyncPool:
    @pytest.mark.no_freezegun
    def test_bounds_concurrency(self) -> None:
        running: list[int] = [0]
        seen_max: list[int] = [0]

        async def _tracked(value: int) -> int:
            running[0] += 1
            seen_max[0] = max(seen_max[0], running[0])
            await asyncio.sleep(0.02)
            running[0] -= 1
            return value

        async def _run() -> list[int]:
            async with _async.AsyncPool(2, bar=False) as pool:
                return await pool.map(_tracked, range(8))

        assert asyncio.run(_run()) == list(range(8))
        assert seen_max[0] <= 2

    def test_defaults_merge_and_override(self) -> None:
        async def _run() -> list[typing.Any]:
            async with _async.AsyncPool(2, bar=False) as pool:
                return await pool.map(
                    _boom_on_two, range(4), on_error='return'
                )

        results: list[typing.Any] = asyncio.run(_run())
        assert isinstance(results[2], ValueError)

    def test_imap_methods(self) -> None:
        async def _run() -> tuple[list[int], list[tuple[int, int]]]:
            async with _async.AsyncPool(2, bar=False) as pool:
                ordered: list[int] = [
                    value async for value in pool.imap(_async_double, range(3))
                ]
                pairs: list[tuple[int, int]] = sorted(
                    [
                        pair
                        async for pair in pool.imap_unordered(
                            _async_double, range(3)
                        )
                    ]
                )
            return ordered, pairs

        ordered, pairs = asyncio.run(_run())
        assert ordered == [0, 2, 4]
        assert pairs == [(0, 0), (1, 2), (2, 4)]


class TestMultiBarMode:
    def test_async_workers_see_their_task_bar(self) -> None:
        from progressbar._parallel import _common

        seen: list[bool] = []

        async def _check(value: int) -> int:
            seen.append(_common.current_task_bar() is not None)
            return value

        async def _run() -> list[int]:
            return await _async.amap(
                _check, range(3), bar='multi', fd=io.StringIO()
            )

        assert asyncio.run(_run()) == [0, 1, 2]
        assert seen == [True, True, True]


class TestExternalCancellation:
    def test_self_cancelling_task_surfaces(self) -> None:
        async def _self_cancel(value: int) -> int:
            if value == 1:
                task = asyncio.current_task()
                assert task is not None
                task.cancel()
                await asyncio.sleep(1)
            return value

        async def _run() -> list[int]:
            return await _async.amap(
                _self_cancel, range(3), concurrency=1, bar=False
            )

        # A cancellation this run did not initiate must surface, never
        # silently drop the item.
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(_run())


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
