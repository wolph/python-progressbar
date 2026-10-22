from __future__ import annotations

import io
import sys
from collections.abc import Iterator

import pytest
from test_stream import reset_wrapped_streams

import progressbar
from progressbar import utils


@pytest.fixture(autouse=True)
def clean_streams() -> Iterator[None]:
    reset_wrapped_streams()
    yield
    reset_wrapped_streams()


class _SelfRemovingListener:
    def __init__(self, listeners: set[object]) -> None:
        self.listeners: set[object] = listeners
        self.calls: int = 0

    def update(self) -> None:
        self.calls += 1
        self.listeners.discard(self)
        self.listeners.add(_NoopListener())


class _NoopListener:
    def update(self) -> None:
        pass


def test_listener_mutation_during_write_does_not_raise() -> None:
    target: io.StringIO = io.StringIO()
    listeners: set[object] = set()
    listener: _SelfRemovingListener = _SelfRemovingListener(listeners)
    listeners.add(listener)
    wrapper: utils.WrappingIO = utils.WrappingIO(
        target,
        capturing=True,
        listeners=listeners,  # type: ignore[arg-type]
    )

    wrapper.write('line\n')

    assert listener.calls == 1
    assert listener not in listeners


def test_empty_listener_set_is_shared() -> None:
    listeners: set[object] = set()
    wrapper: utils.WrappingIO = utils.WrappingIO(
        io.StringIO(),
        listeners=listeners,  # type: ignore[arg-type]
    )
    assert wrapper.listeners is listeners


def test_stop_capturing_never_goes_negative() -> None:
    streams: utils.StreamWrapper = progressbar.streams
    assert streams.capturing == 0
    streams.stop_capturing()
    streams.stop_capturing()
    assert streams.capturing == 0
    streams.start_capturing()
    assert streams.capturing == 1
    streams.stop_capturing()
    assert streams.capturing == 0


def test_unwrap_while_capturing_flushes_dropped_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    streams: utils.StreamWrapper = progressbar.streams
    real: io.StringIO = io.StringIO()
    monkeypatch.setattr(streams, 'original_stdout', real)

    wrapper: utils.WrappingIO = streams.wrap_stdout()
    streams.start_capturing()
    try:
        assert wrapper.capturing
        sys.stdout.write('held\n')
        assert real.getvalue() == ''

        streams.unwrap_stdout()

        assert sys.stdout is real
        assert not wrapper.capturing
        assert wrapper.buffer.getvalue() == ''
        assert real.getvalue() == 'held\n'
        assert not streams.wrapped_excepthook
    finally:
        streams.stop_capturing()


def test_excepthook_flag_is_boolean() -> None:
    streams: utils.StreamWrapper = progressbar.streams
    streams.wrap_stdout()
    streams.wrap_stderr()
    assert streams.wrapped_excepthook is True
    streams.unwrap_stdout()
    assert streams.wrapped_excepthook is True
    streams.unwrap_stderr()
    assert streams.wrapped_excepthook is False


def test_unwrap_stdout_without_wrapper_restores_original() -> None:
    streams: utils.StreamWrapper = progressbar.streams
    assert not isinstance(streams.stdout, utils.WrappingIO)
    streams.unwrap_stdout()
    assert streams.wrapped_stdout == 0
    assert sys.stdout is streams.original_stdout


# ---- round-3 take-backs -------------------------------------------------


def test_wrapper_snapshots_listeners_under_the_shared_lock() -> None:
    streams: utils.StreamWrapper = progressbar.streams
    wrapper: utils.WrappingIO = streams.wrap_stdout()
    try:
        assert wrapper.lock is streams.listeners_lock
    finally:
        streams.unwrap_stdout()


def test_standalone_wrapper_has_its_own_lock() -> None:
    wrapper: utils.WrappingIO = utils.WrappingIO(io.StringIO())
    assert wrapper.lock.acquire(blocking=False)
    wrapper.lock.release()


def test_streamwrapper_survives_deepcopy_and_pickle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import copy
    import pickle

    monkeypatch.setattr(sys, 'stdout', io.StringIO())
    monkeypatch.setattr(sys, 'stderr', io.StringIO())
    original: utils.StreamWrapper = utils.StreamWrapper()
    clone: utils.StreamWrapper = copy.deepcopy(original)
    assert clone.lock is not original.lock
    assert clone.lock.acquire(blocking=False)
    clone.lock.release()
    restored: utils.StreamWrapper = pickle.loads(pickle.dumps(original))
    assert restored.lock.acquire(blocking=False)
    restored.lock.release()


def test_unwrap_tolerates_a_stream_without_flush(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class WriteOnly:
        def write(self, text: str) -> int:
            return len(text)

    streams: utils.StreamWrapper = progressbar.streams
    target: WriteOnly = WriteOnly()
    monkeypatch.setattr(streams, 'original_stdout', target)
    monkeypatch.setattr(streams, 'stdout', target)
    monkeypatch.setattr(sys, 'stdout', target)
    streams.wrap_stdout()
    streams.unwrap_stdout()  # must not raise
    assert sys.stdout is target


def test_subclass_without_super_init_can_wrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoSuper(utils.StreamWrapper):
        def __init__(self, out: io.StringIO) -> None:
            self.stdout = self.original_stdout = out
            self.stderr = self.original_stderr = io.StringIO()
            self.original_excepthook = sys.excepthook
            self.listeners = set()
            self.logging_handlers = []

    hook = sys.excepthook
    wrapper: NoSuper = NoSuper(io.StringIO())
    try:
        wrapper.wrap_stdout()
    finally:
        wrapper.unwrap_stdout()
        monkeypatch.setattr(sys, 'excepthook', hook)


# ---- round-3 closing fixes ---------------------------------------------


def test_wrapping_io_and_a_redirecting_bar_deepcopy_and_pickle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import copy
    import pickle

    wrapper: utils.WrappingIO = utils.WrappingIO(io.StringIO())
    clone: utils.WrappingIO = copy.deepcopy(wrapper)
    assert clone.lock is not wrapper.lock
    assert clone.lock.acquire(blocking=False)
    clone.lock.release()
    restored: utils.WrappingIO = pickle.loads(pickle.dumps(wrapper))
    assert restored.lock.acquire(blocking=False)
    restored.lock.release()

    streams: utils.StreamWrapper = progressbar.streams
    target: io.StringIO = io.StringIO()
    errors: io.StringIO = io.StringIO()
    monkeypatch.setattr(streams, 'original_stdout', target)
    monkeypatch.setattr(streams, 'stdout', target)
    monkeypatch.setattr(sys, 'stdout', target)
    monkeypatch.setattr(streams, 'original_stderr', errors)
    monkeypatch.setattr(streams, 'stderr', errors)
    monkeypatch.setattr(sys, 'stderr', errors)
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        max_value=5, redirect_stdout=True, fd=io.StringIO()
    )
    bar.start()
    try:
        copy.deepcopy(bar)
        copy.deepcopy(streams)  # while wrapping
    finally:
        bar.finish()


def test_captured_write_never_waits_for_the_streamwrapper_lock() -> None:
    import threading

    streams: utils.StreamWrapper = progressbar.streams
    wrapper: utils.WrappingIO = streams.wrap_stdout()
    try:
        assert wrapper.lock is streams.listeners_lock
        assert wrapper.lock is not streams.lock
        streams.lock.acquire()
        done: threading.Event = threading.Event()

        def write() -> None:
            wrapper.capturing = True
            wrapper.write('line\n')
            done.set()

        thread: threading.Thread = threading.Thread(target=write)
        thread.start()
        assert done.wait(2.0), 'write() blocked on streams.lock'
        thread.join()
    finally:
        streams.lock.release()
        streams.unwrap_stdout()


def test_unwrap_tolerates_a_stream_whose_flush_raises_anything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DeletedWidget:  # PyQt 'wrapped C/C++ object has been deleted' shape
        closed: bool = False

        def write(self, text: str) -> int:
            return len(text)

        def flush(self) -> None:
            raise RuntimeError('wrapped C/C++ object has been deleted')

    streams: utils.StreamWrapper = progressbar.streams
    target: DeletedWidget = DeletedWidget()
    monkeypatch.setattr(streams, 'original_stdout', target)
    monkeypatch.setattr(streams, 'stdout', target)
    monkeypatch.setattr(sys, 'stdout', target)
    streams.wrap_stdout()
    streams.unwrap_stdout()  # must not raise
    assert sys.stdout is target
