"""Pin the sync engine's error, timeout and interrupt contracts."""

from __future__ import annotations

import concurrent.futures
import io
import threading
import time

import pytest

from progressbar._parallel import _sync

_executed: set[int] = set()
_executed_lock: threading.Lock = threading.Lock()


def _boom(value: int) -> int:
    if value == 3:
        raise ValueError('boom')
    return value * 2


def _record_and_boom(value: int) -> int:
    with _executed_lock:
        _executed.add(value)
    if value == 0:
        raise ValueError('early boom')
    return value


def _raise_interrupt(value: int) -> int:
    if value == 1:
        raise KeyboardInterrupt
    return value


def _sleep_long(value: int) -> int:
    # Long enough to trip the 0.3s deadline, short enough that the two
    # straggler worker threads drain quickly in the background.
    time.sleep(3)
    return value


class TestFailFast:
    def test_raises_original_exception(self) -> None:
        with pytest.raises(ValueError, match='boom'):
            _sync.map(_boom, range(10), workers=2, bar=False)

    def test_cancels_pending_work(self) -> None:
        _executed.clear()
        with pytest.raises(ValueError, match='early boom'):
            _sync.map(
                _record_and_boom,
                range(50),
                workers=1,
                buffersize=2,
                bar=False,
            )
        # workers=1 runs items sequentially; item 0 fails, so at most
        # the already-submitted window (2 chunks) ever executed.
        assert len(_executed) <= 3

    def test_keyboard_interrupt_propagates(self) -> None:
        with pytest.raises(KeyboardInterrupt):
            _sync.map(_raise_interrupt, range(10), workers=1, bar=False)

    def test_keyboard_interrupt_propagates_with_on_error_return(
        self,
    ) -> None:
        # `on_error='return'` must never swallow an interrupt.
        with pytest.raises(KeyboardInterrupt):
            _sync.map(
                _raise_interrupt,
                range(10),
                workers=1,
                on_error='return',
                bar=False,
            )


class TestOnErrorReturn:
    def test_exceptions_in_place(self) -> None:
        results = _sync.map(_boom, range(5), on_error='return', bar=False)
        assert results[0] == 0
        assert results[2] == 4
        assert isinstance(results[3], ValueError)
        assert results[4] == 8

    def test_invalid_on_error_rejected(self) -> None:
        with pytest.raises(ValueError, match='on_error'):
            _sync.map(_boom, range(3), on_error='ignore', bar=False)


class TestTimeout:
    @pytest.mark.no_freezegun
    def test_timeout_raises_and_cancels(self) -> None:
        start: float = time.monotonic()
        with pytest.raises(concurrent.futures.TimeoutError, match='timeout'):
            _sync.map(
                _sleep_long,
                range(4),
                workers=2,
                timeout=0.3,
                poll_interval=0.05,
                bar=False,
            )
        # The engine must give up at the deadline instead of waiting
        # for the 3-second workers: running tasks are documented as
        # uncancellable but the shutdown must not block on them.
        assert time.monotonic() - start < 2


class TestBarFinalState:
    def test_error_finishes_bar_on_own_line(self) -> None:
        stream = io.StringIO()
        with pytest.raises(ValueError, match='boom'):
            _sync.map(_boom, range(10), workers=1, fd=stream)
        assert stream.getvalue().endswith('\n')

    def test_error_does_not_jump_to_full(self) -> None:
        stream = io.StringIO()
        with pytest.raises(ValueError, match='boom'):
            _sync.map(_boom, range(10), workers=1, buffersize=1, fd=stream)
        final_line: str = stream.getvalue().rstrip('\n').rsplit('\r', 1)[-1]
        assert '10 of 10' not in final_line
