"""Process/interpreter pool support, chunking and executor passthrough."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import sys
import typing

import pytest

from progressbar._parallel import (
    _common,
    _sync,
)

# Process tests pay real spawn cost; keep batches small.
_INIT_VALUE: int = 0


def _square(value: int) -> int:
    return value * value


def _boom_on_two(value: int) -> int:
    if value == 2:
        raise ValueError('boom')
    return value


def _init_worker(value: int) -> None:
    global _INIT_VALUE  # noqa: PLW0603 - the per-worker setup contract
    _INIT_VALUE = value


def _read_init(_: int) -> int:
    return _INIT_VALUE


class TestProcessPool:
    def test_ordered_results(self) -> None:
        assert _sync.map(_square, range(12), pool='process', bar=False) == [
            value * value for value in range(12)
        ]

    def test_explicit_chunksize(self) -> None:
        assert _sync.map(
            _square, range(10), pool='process', chunksize=3, bar=False
        ) == [value * value for value in range(10)]

    def test_auto_chunksize_engaged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[typing.Any, int]] = []
        original: typing.Callable[[typing.Any, int], int] = (
            _common.auto_chunksize
        )

        def _spy(total: typing.Any, workers: int) -> int:
            calls.append((total, workers))
            return original(total, workers)

        monkeypatch.setattr(_sync._common, 'auto_chunksize', _spy)
        _sync.map(_square, range(4), pool='process', workers=2, bar=False)
        assert calls == [(4, 2)]

    def test_auto_chunksize_not_used_for_threads(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fail(total: typing.Any, workers: int) -> int:
            raise AssertionError('auto_chunksize must not run for threads')

        monkeypatch.setattr(_sync._common, 'auto_chunksize', _fail)
        _sync.map(_square, range(4), pool='thread', bar=False)

    def test_initializer_reaches_workers(self) -> None:
        results = _sync.map(
            _read_init,
            range(4),
            pool='process',
            workers=2,
            initializer=_init_worker,
            initargs=(42,),
            bar=False,
        )
        assert results == [42, 42, 42, 42]

    def test_mp_context(self) -> None:
        context = multiprocessing.get_context('spawn')
        assert _sync.map(
            _square,
            range(4),
            pool='process',
            workers=2,
            mp_context=context,
            bar=False,
        ) == [0, 1, 4, 9]

    @pytest.mark.skipif(
        sys.version_info < (3, 11),
        reason='max_tasks_per_child needs Python 3.11+',
    )
    def test_max_tasks_per_child(self) -> None:
        assert _sync.map(
            _square,
            range(4),
            pool='process',
            workers=2,
            max_tasks_per_child=2,
            bar=False,
        ) == [0, 1, 4, 9]

    def test_chunked_on_error_return_keeps_partial_chunk(self) -> None:
        results = _sync.map(
            _boom_on_two,
            range(6),
            pool='process',
            chunksize=3,
            on_error='return',
            bar=False,
        )
        # Item 2 fails inside the first chunk; 0, 1 and the whole
        # second chunk survive (per-item catch, no data loss).
        assert results[0] == 0
        assert results[1] == 1
        assert isinstance(results[2], ValueError)
        assert results[3:] == [3, 4, 5]

    def test_chunked_on_error_raise(self) -> None:
        with pytest.raises(ValueError, match='boom'):
            _sync.map(
                _boom_on_two,
                range(6),
                pool='process',
                chunksize=3,
                bar=False,
            )


class TestInterpreterPool:
    @pytest.mark.skipif(
        sys.version_info < (3, 14),
        reason='InterpreterPoolExecutor needs Python 3.14+',
    )
    def test_interpreter_pool_runs(self) -> None:  # pragma: no cover
        assert _sync.map(
            _square, range(4), pool='interpreter', workers=2, bar=False
        ) == [0, 1, 4, 9]

    @pytest.mark.skipif(
        sys.version_info >= (3, 14),
        reason='the ValueError applies before Python 3.14',
    )
    def test_interpreter_pool_rejected_before_314(self) -> None:
        with pytest.raises(ValueError, match=r'3\.14'):
            _sync.map(_square, range(4), pool='interpreter', bar=False)


class TestExecutorInstance:
    def test_used_but_not_shut_down(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            assert _sync.map(_square, range(5), pool=executor, bar=False) == [
                0,
                1,
                4,
                9,
                16,
            ]
            # Still usable afterwards: the engine must not shut it down.
            assert executor.submit(_square, 3).result() == 9

    def test_construction_kwargs_rejected(self) -> None:
        with (
            concurrent.futures.ThreadPoolExecutor(2) as executor,
            pytest.raises(ValueError, match='initializer'),
        ):
            _sync.map(
                _square,
                range(3),
                pool=executor,
                initializer=_init_worker,
                initargs=(1,),
                bar=False,
            )


class TestPoolValidation:
    def test_unknown_pool_string(self) -> None:
        with pytest.raises(ValueError, match='bogus'):
            _sync.map(_square, range(3), pool='bogus', bar=False)

    def test_thread_pool_rejects_process_options(self) -> None:
        with pytest.raises(ValueError, match='process pools'):
            _sync.map(
                _square,
                range(3),
                pool='thread',
                mp_context=multiprocessing.get_context('spawn'),
                bar=False,
            )

    def test_process_pool_rejects_thread_options(self) -> None:
        with pytest.raises(ValueError, match='thread pools'):
            _sync.map(
                _square,
                range(3),
                pool='process',
                thread_name_prefix='x',
                bar=False,
            )
