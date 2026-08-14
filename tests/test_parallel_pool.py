"""The reusable `Pool` layer over the sync verbs."""

from __future__ import annotations

import concurrent.futures

import pytest

from progressbar._parallel import _sync


def _double(value: int) -> int:
    return value * 2


def _boom(value: int) -> int:
    raise ValueError('boom')


class TestPoolLifecycle:
    def test_lazy_executor(self) -> None:
        pool = _sync.Pool(2)
        assert pool._executor is None  # noqa: SLF001
        pool.shutdown()

    def test_executor_reused_across_calls(self) -> None:
        with _sync.Pool(2) as pool:
            first = pool.executor
            pool.map(_double, range(3), bar=False)
            pool.map(_double, range(3), bar=False)
            assert pool.executor is first

    def test_context_manager_shuts_down(self) -> None:
        with _sync.Pool(2) as pool:
            pool.map(_double, range(3), bar=False)
            executor = pool.executor
        with pytest.raises(RuntimeError):
            executor.submit(_double, 1)

    def test_adopted_executor_not_shut_down(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            with _sync.Pool(executor=executor) as pool:
                assert pool.map(_double, range(3), bar=False) == [0, 2, 4]
            # Leaving the Pool context must not kill the adopted
            # executor -- the caller owns it.
            assert executor.submit(_double, 2).result() == 4

    def test_invalid_kind_rejected_eagerly(self) -> None:
        with pytest.raises(ValueError, match='bogus'):
            _sync.Pool(2, 'bogus')

    def test_workers_with_executor_rejected(self) -> None:
        with (
            concurrent.futures.ThreadPoolExecutor(2) as executor,
            pytest.raises(ValueError, match='executor'),
        ):
            _sync.Pool(2, executor=executor)


class TestPoolVerbs:
    def test_map(self) -> None:
        with _sync.Pool(2) as pool:
            assert pool.map(_double, range(5), bar=False) == [
                0,
                2,
                4,
                6,
                8,
            ]

    def test_imap(self) -> None:
        with _sync.Pool(2) as pool:
            assert list(pool.imap(_double, range(5), bar=False)) == [
                0,
                2,
                4,
                6,
                8,
            ]

    def test_imap_unordered(self) -> None:
        with _sync.Pool(2) as pool:
            pairs = sorted(pool.imap_unordered(_double, range(3), bar=False))
            assert pairs == [(0, 0), (1, 2), (2, 4)]

    def test_starmap(self) -> None:
        with _sync.Pool(2) as pool:
            assert pool.starmap(_double_args, [(1,), (2,)], bar=False) == [
                2,
                4,
            ]


def _double_args(value: int) -> int:
    return value * 2


class TestPoolDefaults:
    def test_constructor_defaults_apply(self) -> None:
        with _sync.Pool(2, bar=False, on_error='return') as pool:
            results = pool.map(_boom, range(2))
            assert all(isinstance(result, ValueError) for result in results)

    def test_per_call_override_beats_default(self) -> None:
        with (
            _sync.Pool(2, bar=False, on_error='return') as pool,
            pytest.raises(ValueError, match='boom'),
        ):
            pool.map(_boom, range(2), on_error='raise')

    def test_process_kind(self) -> None:
        with _sync.Pool(2, 'process') as pool:
            assert pool.map(_double, range(4), bar=False) == [0, 2, 4, 6]
