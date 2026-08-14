"""The `@parallel` decorator: batch verbs attached to plain functions."""

from __future__ import annotations

import asyncio
import pickle

import pytest

from progressbar._parallel import _decorator


@_decorator.parallel(workers=2, bar=False)
def _double(value: int) -> int:
    return value * 2


@_decorator.parallel(workers=2, bar=False)
def _square(value: int) -> int:
    return value * value


class TestDecoratedFunction:
    def test_direct_call_unchanged(self) -> None:
        assert _double(21) == 42

    def test_map_with_config_defaults(self) -> None:
        assert _double.map(range(5)) == [0, 2, 4, 6, 8]

    def test_per_call_override_beats_config(self) -> None:
        # The config sets bar=False; overriding on_error per call works
        # alongside it.
        assert _double.map(range(3), workers=1) == [0, 2, 4]

    def test_imap_variants(self) -> None:
        assert list(_double.imap(range(3))) == [0, 2, 4]
        pairs = sorted(_double.imap_unordered(range(3)))
        assert pairs == [(0, 0), (1, 2), (2, 4)]

    def test_starmap(self) -> None:
        assert _double.starmap([(1,), (2,)]) == [2, 4]

    def test_amap(self) -> None:
        async def _run() -> list[int]:
            return await _double.amap(range(3))

        assert asyncio.run(_run()) == [0, 2, 4]

    def test_async_iterators(self) -> None:
        async def _run() -> tuple[list[int], list[tuple[int, int]]]:
            ordered = [value async for value in _double.aimap(range(3))]
            pairs = sorted(
                [pair async for pair in _double.aimap_unordered(range(3))]
            )
            return ordered, pairs

        ordered, pairs = asyncio.run(_run())
        assert ordered == [0, 2, 4]
        assert pairs == [(0, 0), (1, 2), (2, 4)]


class TestPicklability:
    def test_pickle_round_trip_preserves_identity(self) -> None:
        # Attributes attach to the original function object, so pickle
        # by qualified name still works -- required for pool='process'.
        assert pickle.loads(pickle.dumps(_square)) is _square

    def test_process_pool_map(self) -> None:
        assert _square.map(range(4), pool='process') == [0, 1, 4, 9]


class TestDecorationErrors:
    def test_lambda_rejected(self) -> None:
        with pytest.raises(TypeError, match='named function'):
            _decorator.parallel()(lambda value: value)

    def test_bound_method_rejected(self) -> None:
        class _Thing:
            def method(self) -> None: ...

        with pytest.raises(TypeError, match='named function'):
            _decorator.parallel()(_Thing().method)

    def test_non_callable_rejected(self) -> None:
        with pytest.raises(TypeError, match='named function'):
            _decorator.parallel()(42)  # type: ignore[arg-type]
