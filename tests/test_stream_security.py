from __future__ import annotations

import io
import logging
import sys
import threading
import typing
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
        clones: list[object] = [copy.deepcopy(bar), copy.deepcopy(streams)]
    finally:
        bar.finish()
    # A copy of a started bar is a started bar: its __del__ would finish()
    # it later, at gc time, and unwrap the singleton under some other test
    for clone in clones:
        for listener in getattr(clone, 'listeners', [clone]):
            listener._finished = True


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


# ---- second review round (Codex findings 1-4) ---------------------------


class _LockProbeHandler(logging.Handler):
    """Record, per log record, whether `lock` was free at emit time."""

    def __init__(self, lock: threading.RLock) -> None:
        super().__init__(level=logging.DEBUG)
        self.watched = lock  # not `self.lock`: that is the handler's own
        self.free: list[bool] = []

    def emit(self, record: logging.LogRecord) -> None:
        result: list[bool] = []

        def probe() -> None:
            got: bool = self.watched.acquire(timeout=1.0)
            if got:
                self.watched.release()
            result.append(got)

        thread: threading.Thread = threading.Thread(target=probe)
        thread.start()
        thread.join()
        self.free.append(result[0])


def test_logging_never_happens_under_the_transition_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RaisingFlush(io.StringIO):
        armed: bool = False

        def flush(self) -> None:
            if self.armed:
                raise RuntimeError('gone')

    streams: utils.StreamWrapper = utils.StreamWrapper()
    original: RaisingFlush = RaisingFlush()
    streams.original_stdout = original
    streams.stdout = original
    monkeypatch.setattr(sys, 'stdout', original)
    handler: _LockProbeHandler = _LockProbeHandler(streams.lock)
    logger: logging.Logger = logging.getLogger('progressbar.utils')
    logger.addHandler(handler)
    old_level: int = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        streams.wrap_stdout()  # logs 'wrapping excepthook'
        streams.start_capturing()
        print('buffered')
        original.armed = True
        streams.unwrap_stdout()  # logs 'Could not deliver ...'
        streams.stop_capturing()
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
    assert len(handler.free) >= 2
    assert all(handler.free), handler.free


def test_targets_are_never_written_under_the_transition_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    streams: utils.StreamWrapper = utils.StreamWrapper()
    seen: list[bool] = []

    class LockProbeTarget(io.StringIO):
        def write(self, text: str) -> int:
            result: list[bool] = []

            def probe() -> None:
                got: bool = streams.lock.acquire(timeout=1.0)
                if got:
                    streams.lock.release()
                result.append(got)

            thread: threading.Thread = threading.Thread(target=probe)
            thread.start()
            thread.join()
            seen.append(result[0])
            return super().write(text)

    target: LockProbeTarget = LockProbeTarget()
    streams.original_stdout = target
    streams.stdout = target
    monkeypatch.setattr(sys, 'stdout', target)
    streams.wrap_stdout()
    streams.start_capturing()
    print('one')
    streams.stop_capturing()  # delivers 'one' to the target
    streams.start_capturing()
    print('two')
    streams.unwrap_stdout()  # delivers 'two' to the target
    assert target.getvalue() == 'one\ntwo\n'
    assert len(seen) >= 2
    assert all(seen), seen


class NamedIO(utils.WrappingIO):  # pickle needs a module-level class
    __slots__ = ('name',)

    def __init__(self, target: io.StringIO, name: str) -> None:
        super().__init__(target)
        self.name = name


class NamedStreams(utils.StreamWrapper):
    __slots__ = ('name',)

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


def test_pickle_and_deepcopy_keep_subclass_slots() -> None:
    import copy
    import pickle

    named_io: NamedIO = NamedIO(io.StringIO(), 'spam-stream')
    named_streams: NamedStreams = NamedStreams('spam-streams')
    for name in ('stdout', 'stderr'):
        setattr(named_streams, f'original_{name}', io.StringIO())
        setattr(named_streams, name, io.StringIO())
    # a builtin pickles by reference only while it is still installed,
    # and another test may have left the shared hook wrapped
    named_streams.original_excepthook = sys.excepthook
    for restore in (copy.deepcopy, lambda o: pickle.loads(pickle.dumps(o))):
        assert restore(named_io).name == 'spam-stream'
        assert restore(named_streams).name == 'spam-streams'


def test_restored_wrappers_share_the_restored_listener_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import copy
    import pickle

    streams: utils.StreamWrapper = utils.StreamWrapper()
    for name in ('stdout', 'stderr'):
        target: io.StringIO = io.StringIO()
        setattr(streams, f'original_{name}', target)
        setattr(streams, name, target)
        monkeypatch.setattr(sys, name, target)
    streams.wrap_stdout()
    streams.wrap_stderr()
    streams.original_excepthook = sys.excepthook  # see the slots test
    try:
        for restored in (
            copy.deepcopy(streams),
            pickle.loads(pickle.dumps(streams)),
        ):
            assert isinstance(restored.stdout, utils.WrappingIO)
            assert isinstance(restored.stderr, utils.WrappingIO)
            assert restored.stdout.listeners is restored.listeners
            assert restored.stdout.lock is restored.listeners_lock
            assert restored.stderr.lock is restored.listeners_lock
            assert restored.listeners_lock is not streams.listeners_lock
    finally:
        streams.unwrap_stdout()
        streams.unwrap_stderr()


def test_wrapping_io_subclass_without_super_init_can_write() -> None:
    class NoSuper(utils.WrappingIO):
        def __init__(self, target: io.StringIO) -> None:
            self.buffer = io.StringIO()
            self.target = target
            self.capturing = True
            self.listeners = set()
            self.needs_clear = False

    wrapper: NoSuper = NoSuper(io.StringIO())
    assert wrapper.write('spam\n') == 5
    assert wrapper.needs_clear


def test_stream_class_type_hints_evaluate_on_this_python() -> None:
    import typing

    # `threading.Lock` is a factory function before 3.13, so an annotation
    # naming it directly cannot be evaluated there (regression caught by
    # the second hunt).
    typing.get_type_hints(utils.WrappingIO.__init__)
    typing.get_type_hints(utils.WrappingIO)
    typing.get_type_hints(utils.StreamWrapper.__init__)


def test_forked_child_gets_fresh_stream_locks() -> None:
    import os

    if not hasattr(os, 'fork') or not hasattr(os, 'register_at_fork'):
        pytest.skip('needs a POSIX fork')
    streams: utils.StreamWrapper = progressbar.streams
    held: threading.Event = threading.Event()
    release: threading.Event = threading.Event()

    def holder() -> None:
        with streams.lock, streams.listeners_lock:
            held.set()
            release.wait(10)

    thread: threading.Thread = threading.Thread(target=holder, daemon=True)
    thread.start()
    held.wait(5)
    pid: int = os.fork()
    if pid == 0:  # pragma: no cover - child
        status: int = 0
        if not streams.lock.acquire(timeout=2):
            status |= 1
        if not streams.listeners_lock.acquire(timeout=2):
            status |= 2
        os._exit(status)
    try:
        _, raw_status = os.waitpid(pid, 0)
    finally:
        release.set()
        thread.join()
    assert os.waitstatus_to_exitcode(raw_status) == 0


def test_wrap_excepthook_directly(monkeypatch: pytest.MonkeyPatch) -> None:
    streams: utils.StreamWrapper = utils.StreamWrapper()
    original: object = sys.excepthook
    monkeypatch.setattr(sys, 'excepthook', original)
    streams.original_excepthook = original  # type: ignore[assignment]
    streams.wrap_excepthook()
    assert sys.excepthook == streams.excepthook
    streams.wrap_excepthook()  # idempotent
    streams.unwrap_excepthook()
    assert sys.excepthook is original


# ---- third review round (Codex re-review findings 1-4) -------------------


def test_overlapping_stop_capturing_delivers_buffered_text_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paused: threading.Event = threading.Event()
    resume: threading.Event = threading.Event()

    class PausingBuffer(io.StringIO):
        # The first stop pauses between reading and clearing the
        # buffer; a second lifecycle must not drain the same text again
        def getvalue(self) -> str:
            value: str = super().getvalue()
            if threading.current_thread().name == 'first-stop':
                paused.set()
                assert resume.wait(10)
            return value

    streams: utils.StreamWrapper = utils.StreamWrapper()
    target: io.StringIO = io.StringIO()
    streams.stdout = streams.original_stdout = target
    monkeypatch.setattr(sys, 'stdout', target)
    wrapper: utils.WrappingIO = streams.wrap_stdout()
    streams.start_capturing()
    wrapper.buffer = PausingBuffer()
    wrapper.write('spam')
    first: threading.Thread = threading.Thread(
        target=streams.stop_capturing, name='first-stop'
    )
    first.start()
    assert paused.wait(10)
    second_done: threading.Event = threading.Event()

    def another_lifecycle() -> None:
        streams.start_capturing()
        streams.stop_capturing()
        second_done.set()

    second: threading.Thread = threading.Thread(target=another_lifecycle)
    second.start()
    second_done.wait(0.3)
    resume.set()
    first.join()
    second.join()
    streams.unwrap_stdout()
    assert target.getvalue() == 'spam'


def test_subclass_defining_eq_without_hash_constructs() -> None:
    class EqualStreams(utils.StreamWrapper):
        def __eq__(self, other: object) -> bool:
            return self is other

    streams: EqualStreams = EqualStreams()
    assert streams.lock is not utils.StreamWrapper.lock


class _BackReference:  # a listener that refers to its StreamWrapper
    def __init__(self, streams: utils.StreamWrapper) -> None:
        self.streams = streams

    def update(self) -> None:
        pass


def test_cyclic_graph_restores_from_any_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import copy
    import pickle

    streams: utils.StreamWrapper = utils.StreamWrapper()
    for name in ('stdout', 'stderr'):
        target: io.StringIO = io.StringIO()
        setattr(streams, f'original_{name}', target)
        setattr(streams, name, target)
        monkeypatch.setattr(sys, name, target)
    streams.original_excepthook = sys.excepthook
    listener: _BackReference = _BackReference(streams)
    wrapper: utils.WrappingIO = streams.wrap_stdout()
    streams.start_capturing(listener)  # type: ignore[arg-type]
    try:
        for root in (streams, wrapper, listener):
            for restore in (
                copy.deepcopy,
                lambda o: pickle.loads(pickle.dumps(o)),
            ):
                clone: object = restore(root)
                if isinstance(clone, utils.WrappingIO):
                    owner = next(iter(clone.listeners)).streams  # type: ignore[attr-defined]
                    assert clone.lock is owner.listeners_lock
                elif isinstance(clone, _BackReference):
                    owner = clone.streams
                else:
                    owner = clone
                assert isinstance(owner.stdout, utils.WrappingIO)
                assert owner.stdout.lock is owner.listeners_lock
                assert owner.listeners_lock is not streams.listeners_lock
    finally:
        streams.stop_capturing(listener)  # type: ignore[arg-type]
        streams.unwrap_stdout()


def _fork_and_acquire(current_lock: typing.Callable[[], typing.Any]) -> None:
    # `current_lock` is re-read in the child: the fork hook replaces the
    # lock object, so a reference taken before the fork stays locked
    import os

    if not hasattr(os, 'fork'):
        pytest.skip('needs a POSIX fork')
    held: threading.Event = threading.Event()
    release: threading.Event = threading.Event()

    def holder() -> None:
        with current_lock():
            held.set()
            release.wait(10)

    thread: threading.Thread = threading.Thread(target=holder, daemon=True)
    thread.start()
    held.wait(5)
    pid: int = os.fork()
    if pid == 0:  # pragma: no cover - child
        os._exit(0 if current_lock().acquire(timeout=2) else 1)
    try:
        _, raw_status = os.waitpid(pid, 0)
    finally:
        release.set()
        thread.join()
    assert os.waitstatus_to_exitcode(raw_status) == 0


def test_forked_child_gets_a_fresh_standalone_wrapper_lock() -> None:
    wrapper: utils.WrappingIO = utils.WrappingIO(io.StringIO())
    _fork_and_acquire(lambda: wrapper.lock)


def test_forked_child_gets_a_fresh_interval_warning_lock() -> None:
    from progressbar import bar as bar_module

    _fork_and_acquire(lambda: bar_module._bad_interval_lock.lock)


def test_shared_lock_box_reset_and_wrapper_lock_setter() -> None:
    box: utils._SharedLock = utils._SharedLock()
    old_lock: object = box.lock
    with box.lock:
        box.reset()  # what the fork hook does: a new, unlocked lock
    assert box.lock is not old_lock
    assert box.lock.acquire(blocking=False)
    box.lock.release()

    wrapper: utils.WrappingIO = utils.WrappingIO(io.StringIO())
    private: threading.Lock = threading.Lock()
    wrapper.lock = private  # the 4.6.0-era way of handing in a lock
    assert wrapper.lock is private


def test_stop_capturing_returns_with_its_own_text_delivered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Delivery is synchronous, as in 4.6.0: text written right after a
    # stop lands below the text that stop flushed, even while another
    # thread is still inside a delivery of its own
    paused: threading.Event = threading.Event()
    resume: threading.Event = threading.Event()

    class PausingTarget(io.StringIO):
        def write(self, text: str) -> int:
            written: int = super().write(text)
            if threading.current_thread().name == 'first-stop':
                paused.set()
                assert resume.wait(10)
            return written

    streams: utils.StreamWrapper = utils.StreamWrapper()
    target: PausingTarget = PausingTarget()
    streams.stdout = streams.original_stdout = target
    monkeypatch.setattr(sys, 'stdout', target)
    wrapper: utils.WrappingIO = streams.wrap_stdout()
    streams.start_capturing()
    wrapper.write('spam|')
    first: threading.Thread = threading.Thread(
        target=streams.stop_capturing, name='first-stop'
    )
    first.start()
    assert paused.wait(10)
    streams.start_capturing()
    wrapper.write('eggs|')
    streams.stop_capturing()  # delivers 'eggs|' itself, without waiting
    wrapper.write('after-stop|')  # passes straight through, capturing is off
    resume.set()
    first.join()
    streams.unwrap_stdout()
    assert target.getvalue() == 'spam|eggs|after-stop|'


def test_target_that_flushes_the_streams_while_written_does_not_deadlock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    streams: utils.StreamWrapper = utils.StreamWrapper()

    class FlushingTarget(io.StringIO):
        # A target that calls back into the streams on the same thread,
        # as a bar-aware widget or a logging handler might
        def write(self, text: str) -> int:
            written: int = super().write(text)
            streams.flush()
            return written

    target: FlushingTarget = FlushingTarget()
    streams.stdout = streams.original_stdout = target
    monkeypatch.setattr(sys, 'stdout', target)
    streams.wrap_stdout()
    streams.start_capturing()
    print('spam', end='')
    streams.stop_capturing()
    streams.unwrap_stdout()
    assert target.getvalue() == 'spam'


def test_failed_stdout_delivery_still_delivers_the_stderr_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Broken(io.StringIO):
        def write(self, text: str) -> int:
            raise OSError('gone')

    streams: utils.StreamWrapper = utils.StreamWrapper()
    out: Broken = Broken()
    err: io.StringIO = io.StringIO()
    streams.stdout = streams.original_stdout = out
    streams.stderr = streams.original_stderr = err
    monkeypatch.setattr(sys, 'stdout', out)
    monkeypatch.setattr(sys, 'stderr', err)
    streams.wrap_stdout()
    streams.wrap_stderr()
    streams.start_capturing()
    print('spam', end='')
    print('eggs', end='', file=sys.stderr)
    with pytest.raises(OSError, match='gone'):
        streams.stop_capturing()
    assert err.getvalue() == 'eggs'  # not lost to the stdout failure
    streams.unwrap_stdout()
    streams.unwrap_stderr()


class _PausingStringIO(io.StringIO):
    """A buffer whose first `truncate()` pauses until told to go on."""

    def __init__(self) -> None:
        super().__init__()
        self.paused: threading.Event = threading.Event()
        self.resume: threading.Event = threading.Event()
        self.calls: int = 0

    def truncate(self, size: int | None = None) -> int:
        self.calls += 1
        if self.calls == 1:
            self.paused.set()
            assert self.resume.wait(10)
        return super().truncate(size)


def test_write_during_a_drain_is_not_lost() -> None:
    # Codex-4b finding 7: `_take()` read the buffer, then truncated it,
    # and a `write()` that landed between the two was gone.
    wrapper = utils.WrappingIO(io.StringIO(), capturing=True)
    buffer = _PausingStringIO()
    wrapper.buffer = buffer
    wrapper.write('A|')
    taken: list[str] = []

    def take() -> None:
        taken.append(wrapper._take())

    taker = threading.Thread(target=take)
    taker.start()
    assert buffer.paused.wait(10)
    writer = threading.Thread(target=wrapper.write, args=('B|',))
    writer.start()
    writer.join(0.5)  # blocked behind the drain, or done without a lock
    buffer.resume.set()
    taker.join(10)
    writer.join(10)
    assert not taker.is_alive() and not writer.is_alive()

    taken.append(wrapper._take())
    assert ''.join(taken) == 'A|B|'


def test_buffer_flush_that_logs_through_the_wrapper_does_not_deadlock() -> (
    None
):
    # Review 5: `_take()` called `buffer.flush()` while holding the buffer
    # lock. A replacement buffer whose flush() logs through a handler
    # that writes to the wrapper then waited for the handler lock, held
    # by a thread waiting to write into the buffer: a lock-order cycle
    # 4.6.0 could not have.
    entered: threading.Event = threading.Event()
    handler_held: threading.Event = threading.Event()
    logger: logging.Logger = logging.getLogger('test-buffer-flush-logs')
    logger.propagate = False
    logger.setLevel(logging.INFO)

    class LoggingBuffer(io.StringIO):
        fired: bool = False

        def flush(self) -> None:
            if not self.fired:
                self.fired = True
                entered.set()
                logger.info('flush-log')
            super().flush()

    wrapper = utils.WrappingIO(io.StringIO(), capturing=True)
    wrapper.buffer = LoggingBuffer()
    handler: logging.StreamHandler[typing.Any] = logging.StreamHandler(wrapper)
    logger.addHandler(handler)
    try:
        wrapper.write('A|')

        def writer() -> None:
            handler.acquire()
            try:
                handler_held.set()
                assert entered.wait(10)
                wrapper.write('B|')
            finally:
                handler.release()

        def drainer() -> None:
            assert handler_held.wait(10)
            wrapper._flush()

        threads = [
            threading.Thread(target=writer, daemon=True),
            threading.Thread(target=drainer, daemon=True),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        assert not any(thread.is_alive() for thread in threads)
        wrapper._flush()
        assert wrapper.target.getvalue() == 'A|B|flush-log\n'
    finally:
        logger.removeHandler(handler)
