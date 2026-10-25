"""Color stripping, delta coalescing, and stdout/stderr redirection.

The redirection machinery (`WrappingIO`, `StreamWrapper`, and the
module-level `streams` singleton constructed at the bottom of this
module) is what lets `print()` calls and logging output appear as
normal lines above a redrawing progress bar instead of corrupting its
line. See the "Print while a bar is running" how-to for the full
picture.
"""

from __future__ import annotations

import atexit
import contextlib
import datetime
import io
import logging
import os
import re
import sys
import threading
import typing
import weakref
from collections.abc import Callable, Iterable, Iterator, Mapping
from types import TracebackType

from python_utils import types
from python_utils.converters import scale_1024
from python_utils.terminal import get_terminal_size
from python_utils.time import epoch, format_time, timedelta_to_seconds

from progressbar import base, env, terminal

# Make sure these are available for import
assert timedelta_to_seconds is not None
assert get_terminal_size is not None
assert format_time is not None
assert scale_1024 is not None
assert epoch is not None

StringT = typing.TypeVar('StringT', bound=types.StringTypes)
T = typing.TypeVar('T')

logger: logging.Logger = logging.getLogger(__name__)


class _ProgressListener(typing.Protocol):
    """Structural type for the bars the stream wrapper notifies.

    Defined locally instead of importing ``ProgressBarMixinBase`` from
    ``bar`` so ``utils`` has no dependency on ``bar``, not even a
    type-checking-only one, which CodeQL still reports as a ``bar`` <->
    ``utils`` module-level import cycle.
    """

    def update(self) -> None:
        """Redraw in response to redirected output being written."""


# Precompiled ANSI CSI escape-sequence patterns (str and bytes). Compiled once
# at import instead of per no_color() call, which runs for every widget on
# every redraw.
_ANSI_COLOR_RE: re.Pattern[str] = re.compile('\x1b\\[.*?[@-~]')
_ANSI_COLOR_RE_BYTES: re.Pattern[bytes] = re.compile(
    bytes(terminal.ESC, 'ascii') + b'\\[.*?[@-~]',
)


@typing.overload
def deltas_to_seconds(
    *deltas: datetime.timedelta | float | int | None,
    default: type[ValueError] = ...,
) -> float:
    """Coalesce to seconds, raising ``ValueError`` if no delta is valid."""


@typing.overload
def deltas_to_seconds(
    *deltas: datetime.timedelta | float | int | None,
    default: T,
) -> float | T:
    """Coalesce to seconds, returning ``default`` if no delta is valid."""


def deltas_to_seconds(
    *deltas: datetime.timedelta | float | int | None,
    default: typing.Any = ValueError,
) -> typing.Any:
    """Coalesce timedeltas and second counts to a single seconds float.

    Returns the first argument in `deltas` that isn't `None`, converted
    to seconds as a `float`. Raises (or returns `default`, if given) only
    when every argument is `None`.

    >>> deltas_to_seconds(datetime.timedelta(seconds=1, milliseconds=234))
    1.234
    >>> deltas_to_seconds(123)
    123.0
    >>> deltas_to_seconds(1.234)
    1.234
    >>> deltas_to_seconds(None, 1.234)
    1.234
    >>> deltas_to_seconds(0, 1.234)
    0.0
    >>> deltas_to_seconds()
    Traceback (most recent call last):
    ...
    ValueError: No valid deltas passed to `deltas_to_seconds`
    >>> deltas_to_seconds(None)
    Traceback (most recent call last):
    ...
    ValueError: No valid deltas passed to `deltas_to_seconds`
    >>> deltas_to_seconds(default=0.0)
    0.0
    """
    for delta in deltas:
        if delta is None:
            continue
        if isinstance(delta, datetime.timedelta):
            return timedelta_to_seconds(delta)
        elif not isinstance(delta, float):
            return float(delta)
        else:
            return delta

    if default is ValueError:
        raise ValueError('No valid deltas passed to `deltas_to_seconds`')
    else:
        return default


def no_color(value: StringT) -> StringT:
    """Return the `value` without ANSI escape codes.

    >>> no_color(b'\u001b[1234]abc')
    b'abc'
    >>> str(no_color('\u001b[1234]abc'))
    'abc'
    >>> str(no_color('\u001b[1234]abc'))
    'abc'
    >>> no_color(123)
    Traceback (most recent call last):
    ...
    TypeError: `value` must be a string or bytes, got 123
    """
    if isinstance(value, bytes):
        # Fast path: with no ESC byte there is nothing to strip, so the regex
        # would return the value unchanged anyway. Skipping it avoids a
        # substitution on the common plain-text case, which dominates the
        # per-redraw render cost (len_color is called for every widget).
        if b'\x1b' not in value:
            return value  # type: ignore
        return _ANSI_COLOR_RE_BYTES.sub(b'', value)  # type: ignore
    elif isinstance(value, str):
        if '\x1b' not in value:
            return value  # type: ignore
        return _ANSI_COLOR_RE.sub('', value)  # type: ignore
    else:
        raise TypeError(f'`value` must be a string or bytes, got {value!r}')


def len_color(value: types.StringTypes) -> int:
    """Return the length of `value` without ANSI escape codes.

    >>> len_color(b'\u001b[1234]abc')
    3
    >>> len_color('\u001b[1234]abc')
    3
    >>> len_color('\u001b[1234]abc')
    3
    """
    return len(no_color(value))


#: One installed wrapper's drained text, waiting to be written to the
#: original stream once the transition lock is released.
_Pending = tuple[str, 'WrappingIO', str]

if typing.TYPE_CHECKING:
    _Lock = threading.Lock
else:
    #: `threading.Lock` is a factory function before Python 3.13, so an
    #: annotation that names it does not evaluate there
    #: (`typing.get_type_hints` raises). The instance type does.
    _Lock = type(threading.Lock())


class _SharedLock:
    """A lock that several objects share, and that survives pickle and fork.

    `StreamWrapper` and every `WrappingIO` it installs hold the same
    box, so they agree on one lock however the graph is pickled or
    deep-copied (the box is one object, restored once, whichever object
    is the root). The lock itself is never pickled: a restored box gets
    a fresh one. Every live box is registered so a forked child can
    replace the lock it inherited, which another parent thread may
    have been holding at fork time and would otherwise stay locked
    forever in the child.
    """

    __slots__ = ('__weakref__', '_factory', 'lock')

    def __init__(
        self,
        factory: Callable[[], typing.Any] = threading.Lock,
        lock: typing.Any = None,
    ) -> None:
        self._factory: Callable[[], typing.Any] = factory
        self.lock: typing.Any = lock if lock is not None else factory()
        _lock_boxes.add(self)

    def reset(self) -> None:
        """Replace the lock with a new, unlocked one (after a fork)."""
        self.lock = self._factory()

    def __getstate__(self) -> Callable[[], typing.Any]:
        return self._factory

    def __setstate__(self, factory: Callable[[], typing.Any]) -> None:
        self._factory = factory
        self.lock = factory()
        _lock_boxes.add(self)


_lock_boxes: weakref.WeakSet[_SharedLock] = weakref.WeakSet()


def _reset_locks_after_fork() -> None:  # pragma: no cover
    for box in list(_lock_boxes):
        box.reset()


if hasattr(os, 'register_at_fork'):  # pragma: no branch
    os.register_at_fork(after_in_child=_reset_locks_after_fork)


class WrappingIO:
    """`sys.stdout`/`sys.stderr` replacement installed while capturing.

    Buffers writes in memory instead of passing them straight through
    while `capturing` is on, so a bar can erase its own line, flush the
    buffer above it, and redraw. See `StreamWrapper.wrap_stdout`/
    `wrap_stderr` for how one gets installed.
    """

    buffer: io.StringIO
    target: base.IO
    capturing: bool
    listeners: set[_ProgressListener]
    #: Holds the lock that guards `listeners` only. The class-level
    #: default keeps a subclass that skips `super().__init__()` working,
    #: as for `StreamWrapper`.
    _lock_box: _SharedLock = _SharedLock()
    needs_clear: bool = False

    @property
    def lock(self) -> _Lock:
        """The lock guarding `listeners`, shared with the installer."""
        return self._lock_box.lock

    @lock.setter
    def lock(self, lock: _Lock) -> None:
        self._lock_box = _SharedLock(threading.Lock, lock)

    def __init__(
        self,
        target: base.IO,
        capturing: bool = False,
        listeners: set[_ProgressListener] | None = None,
        lock: _Lock | _SharedLock | None = None,
    ) -> None:
        """Wrap `target` so writes can be buffered while `capturing`.

        Args:
            target: The real stream writes are buffered for, and
                eventually flushed through to.
            capturing: Start in buffering mode immediately instead of
                passing writes straight through.
            listeners: Bars to notify (`update()`) whenever a buffered
                write completes a line. Typically shared with
                `StreamWrapper.listeners` by the caller, so every
                wrapped stream notifies the same bars.
            lock: The lock that guards the `listeners` set and nothing
                else. `StreamWrapper` passes its `listeners_lock`, so
                the snapshot taken in `write()` cannot race with
                `start_capturing()` and `stop_capturing()` on another
                thread (a real race on free-threaded builds). It is
                never held while calling out, so it cannot take part
                in a lock-order cycle with a logging handler or a
                locking target stream. Defaults to a private lock.
        """
        self.buffer = io.StringIO()
        self.target = target
        self.capturing = capturing
        self.listeners = listeners if listeners is not None else set()
        if isinstance(lock, _SharedLock):
            self._lock_box = lock
        else:
            self._lock_box = _SharedLock(threading.Lock, lock)
        self.needs_clear = False

    def write(self, value: str) -> int:
        """Write `value`, buffering it in memory while `capturing`.

        While `capturing` is on, `value` is appended to `buffer` instead
        of reaching `target`. If the buffered text now contains a
        newline, `needs_clear` is set and every listener's `update()` is
        called, so a capturing bar redraws promptly instead of waiting
        for its next scheduled update. While not `capturing`, `value` is
        written straight through to `target` and `target` is flushed on
        every newline, so unbuffered output still appears live.

        Returns:
            The number of characters written (buffered or passed
            through), mirroring the return value of a normal file
            `write()`.
        """
        ret = 0
        if self.capturing:
            ret += self.buffer.write(value)
            if '\n' in value:  # pragma: no branch
                self.needs_clear = True
                # Iterate a snapshot taken under the lock: a listener's
                # update() may finish its bar, which removes it from this
                # shared set, and another thread may be mutating it
                with self.lock:
                    listeners = tuple(self.listeners)
                for listener in listeners:  # pragma: no branch
                    listener.update()
        else:
            ret += self.target.write(value)
            if '\n' in value:  # pragma: no branch
                self.flush_target()

        return ret

    def flush(self) -> None:
        """Flush the in-memory buffer, a no-op for `io.StringIO`.

        Only satisfies the file-like `flush()` protocol. It does not
        write buffered text through to `target`. Use `_flush()` (or
        `StreamWrapper.flush()`, which calls it) for that.
        """
        self.buffer.flush()

    def _flush(self) -> None:
        """Write buffered output through to `target`, then flush it.

        The buffer is drained (`seek`/`truncate`) *before*
        `target.write()` is called, not after, so if that write
        raises, the already-buffered text isn't written a second time
        by the next call. `target` is flushed unconditionally at the
        end, even when the buffer was empty, since this runs on every
        bar redraw, not just when there's something to flush.
        """
        self._deliver(self._take())

    def _take(self) -> str:
        """Drain and return the buffered text without touching `target`.

        `StreamWrapper` calls this under its transition lock, so two
        overlapping flushes cannot both pick up the same text, and
        delivers the result after releasing it.
        """
        value: str = self.buffer.getvalue()
        if value:
            self.flush()
            # Clear the buffer before writing so a failed write cannot
            # cause the same data to be written again by the next flush
            self.buffer.seek(0)
            self.buffer.truncate(0)
            self.needs_clear = False
        return value

    def _deliver(self, value: str) -> None:
        """Write text taken by `_take()` to `target`, then flush it."""
        if value and not self.target.closed:
            self.target.write(value)
        # when explicitly flushing, always flush the target as well
        self.flush_target()

    def flush_target(self) -> None:  # pragma: no cover
        """Flush `target` itself, if it's open and flushable."""
        if not self.target.closed and getattr(self.target, 'flush', None):
            self.target.flush()

    def __enter__(self) -> WrappingIO:
        """Return `self` for use as a context manager."""
        return self

    def fileno(self) -> int:
        """Return `target`'s file descriptor."""
        return self.target.fileno()

    def isatty(self) -> bool:
        """Return whether `target` is a tty."""
        return self.target.isatty()

    def read(self, n: int = -1) -> str:
        """Read up to `n` characters from `target`."""
        return self.target.read(n)

    def readable(self) -> bool:
        """Return whether `target` supports reading."""
        return self.target.readable()

    def readline(self, limit: int = -1) -> str:
        """Read a single line (up to `limit` characters) from `target`."""
        return self.target.readline(limit)

    def readlines(self, hint: int = -1) -> list[str]:
        """Read all lines from `target`."""
        return self.target.readlines(hint)

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        """Seek `target` to `offset`, relative to `whence`."""
        return self.target.seek(offset, whence)

    def seekable(self) -> bool:
        """Return whether `target` supports seeking."""
        return self.target.seekable()

    def tell(self) -> int:
        """Return `target`'s current stream position."""
        return self.target.tell()

    def truncate(self, size: int | None = None) -> int:
        """Truncate `target` to `size`."""
        return self.target.truncate(size)

    def writable(self) -> bool:
        """Return whether `target` supports writing."""
        return self.target.writable()

    def writelines(self, lines: Iterable[str]) -> None:
        """Write `lines` to `target`."""
        return self.target.writelines(lines)

    def close(self) -> None:
        """Flush the buffer and close `target`."""
        self.flush()
        self.target.close()

    def __next__(self) -> str:
        """Return the next line read from `target`."""
        return self.target.__next__()

    def __iter__(self) -> Iterator[str]:
        """Return an iterator over `target`'s lines."""
        return self.target.__iter__()

    def __exit__(
        self,
        __t: type[BaseException] | None,
        __value: BaseException | None,
        __traceback: TracebackType | None,
    ) -> None:
        """Close on context-manager exit, regardless of `__t`."""
        self.close()


class StreamWrapper:
    """Wrap `sys.stdout`/`sys.stderr` for output, logging, and a bar to share.

    Almost always used via the module-level `streams` singleton
    (constructed once at the bottom of this module) rather than
    instantiated directly. Each `wrap_*`/`unwrap_*` pair is refcounted,
    so nested or concurrent bars that both request redirection share one
    wrapper and it's only undone once the last one finishes.
    """

    stdout: base.TextIO | WrappingIO
    stderr: base.TextIO | WrappingIO
    original_excepthook: Callable[
        [
            type[BaseException],
            BaseException,
            TracebackType | None,
        ],
        None,
    ]
    wrapped_stdout: int = 0
    wrapped_stderr: int = 0
    wrapped_logging: int = 0
    wrapped_excepthook: bool = False
    logging_handlers: list[tuple[logging.StreamHandler[base.IO], base.IO]]
    capturing: int = 0
    listeners: set[_ProgressListener]
    #: Holds the lock guarding every wrap/unwrap/capture transition.
    #: Reentrant, because wrap_stdout() calls wrap_excepthook() while
    #: holding it. Nothing is logged and no original stream is written
    #: while it is held, so it cannot take part in a lock-order cycle
    #: with a logging handler or a locking target stream. The
    #: class-level default keeps a subclass that skips
    #: `super().__init__()` working, as every counter above.
    _lock_box: _SharedLock = _SharedLock(threading.RLock)
    #: Holds the lock guarding `listeners` only. Shared with every
    #: `WrappingIO` this wrapper installs, and never held while calling
    #: out.
    _listeners_box: _SharedLock = _SharedLock()

    @property
    def lock(self) -> threading.RLock:
        """The reentrant lock guarding wrap/unwrap/capture transitions."""
        return self._lock_box.lock

    @property
    def listeners_lock(self) -> _Lock:
        """The lock guarding `listeners`, shared with the wrappers."""
        return self._listeners_box.lock

    def __init__(self) -> None:
        """Capture the *current* `sys.stdout`/`sys.stderr` as "real".

        Note:
            This runs once, at construction, and `streams` (below) is
            constructed at import time. Anything that reassigns
            `sys.stdout`/`sys.stderr` after `progressbar.utils` is first
            imported will not be picked up: `original_stdout`/
            `original_stderr` keep pointing at whatever was installed at
            that moment, not whatever is live later. This has been a
            repeat source of bugs.
        """
        self.stdout = self.original_stdout = sys.stdout
        self.stderr = self.original_stderr = sys.stderr
        self.original_excepthook = sys.excepthook
        self.wrapped_stdout = 0
        self.wrapped_stderr = 0
        self.wrapped_logging = 0
        self.wrapped_excepthook = False
        self.logging_handlers = []
        self.capturing = 0
        self.listeners = set()
        self._lock_box = _SharedLock(threading.RLock)
        self._listeners_box = _SharedLock()

        if env.env_flag('WRAP_STDOUT', default=False):  # pragma: no cover
            self.wrap_stdout()

        if env.env_flag('WRAP_STDERR', default=False):  # pragma: no cover
            self.wrap_stderr()

    def start_capturing(self, bar: _ProgressListener | None = None) -> None:
        """Turn capturing on for `bar` and bump the shared refcount.

        Args:
            bar: Registered as a listener so it's notified (`update()`)
                when captured output completes a line. Omit to just
                bump the refcount without listening.
        """
        with self.lock:
            if bar:  # pragma: no branch
                with self.listeners_lock:
                    self.listeners.add(bar)

            self.capturing += 1
            # Never flushes here: the count just went above zero
            self._apply_capturing()

    def stop_capturing(self, bar: _ProgressListener | None = None) -> None:
        """Unregister `bar` and drop the shared capturing refcount.

        Args:
            bar: The listener to remove, if it was registered via
                `start_capturing`.
        """
        with self.lock:
            if bar:  # pragma: no branch
                with self.listeners_lock, contextlib.suppress(KeyError):
                    self.listeners.remove(bar)

            # Never go negative: an unmatched stop would otherwise make
            # the next start_capturing() a no-op
            self.capturing = max(self.capturing - 1, 0)
            pending: list[_Pending] = self._apply_capturing()
        self._deliver(pending)

    def update_capturing(self) -> None:  # pragma: no cover
        """Propagate the capturing refcount to the wrapped streams.

        Flushes immediately once the refcount drops to zero or below,
        so whatever's left in the buffer reaches the terminal as soon
        as the last bar stops capturing, rather than sitting there
        until something else happens to trigger a flush.
        """
        with self.lock:
            pending: list[_Pending] = self._apply_capturing()
        self._deliver(pending)

    def _apply_capturing(self) -> list[_Pending]:
        """Push the capture state onto the wrappers, under `lock`.

        Returns the buffered text taken from each installed wrapper
        when the refcount reached zero, for the caller to deliver after
        releasing `lock`: a delivery writes into the original streams,
        and one of those may be a logging handler or a widget that
        takes a lock of its own on another thread. Taking the text
        under the lock means two overlapping flushes never deliver the
        same text twice, and an unwrap cannot swap the wrapper out
        between the type check and the drain.
        """
        if isinstance(self.stdout, WrappingIO):
            self.stdout.capturing = self.capturing > 0

        if isinstance(self.stderr, WrappingIO):
            self.stderr.capturing = self.capturing > 0

        if self.capturing > 0:
            return []
        return self._take()

    def _take(self) -> list[_Pending]:
        """Drain both installed wrappers' buffers, under `lock`."""
        pending: list[_Pending] = []
        if self.wrapped_stdout and isinstance(self.stdout, WrappingIO):
            pending.append(('stdout', self.stdout, self.stdout._take()))
        if self.wrapped_stderr and isinstance(self.stderr, WrappingIO):
            pending.append(('stderr', self.stderr, self.stderr._take()))
        return pending

    def _deliver(self, pending: list[_Pending]) -> None:
        """Write taken text to the original streams, outside `lock`.

        If writing to a stream's target raises `io.UnsupportedOperation`
        (as happens for some non-seekable streams), that stream's
        redirection disables itself: `wrapped_stdout`/`wrapped_stderr`
        is reset to 0 so no further flush attempts are made, and a
        warning is logged. `sys.stdout`/`sys.stderr` are left installed
        as-is: only further flush attempts are skipped, not the wrapping
        itself.
        """
        for name, wrapper, text in pending:
            self._deliver_one(name, wrapper, text)

    def _deliver_one(self, name: str, wrapper: WrappingIO, text: str) -> None:
        """Deliver one wrapper's text, disabling its redirection on failure."""
        try:
            wrapper._deliver(text)
        except io.UnsupportedOperation:
            setattr(self, f'wrapped_{name}', 0)
            logger.warning(
                'Disabling %s redirection, %r is not seekable',
                name,
                getattr(sys, name),
            )

    def wrap(self, stdout: bool = False, stderr: bool = False) -> None:
        """Wrap `stdout` and/or `stderr`, per the given flags."""
        if stdout:
            self.wrap_stdout()

        if stderr:
            self.wrap_stderr()

    def wrap_stdout(self) -> WrappingIO:
        """Install a `WrappingIO` over `sys.stdout`, or share it.

        Refcounted: only the first call actually replaces `sys.stdout`;
        later calls just bump `wrapped_stdout` so nested/concurrent bars
        share one wrapper, and it takes a matching number of
        `unwrap_stdout()` calls to restore the original stream. Also
        wraps `sys.excepthook`, since a traceback printed while
        capturing would otherwise bypass the buffer.

        Returns:
            The installed `WrappingIO`, the same instance on every
            call until it's fully unwrapped.
        """
        with self.lock:
            hooked: bool = self._wrap_excepthook_locked()

            if not self.wrapped_stdout:
                self.stdout = sys.stdout = WrappingIO(  # type: ignore
                    self.original_stdout,
                    listeners=self.listeners,
                    lock=self._listeners_box,
                )
            self.wrapped_stdout += 1
            wrapper: WrappingIO = sys.stdout  # type: ignore
        if hooked:
            self._log_excepthook_wrapped()
        return wrapper

    def wrap_stderr(self) -> WrappingIO:
        """Install a `WrappingIO` over `sys.stderr`, or share it.

        See `wrap_stdout` for the refcounting behavior, mirrored here
        for `sys.stderr`.

        Returns:
            The installed `WrappingIO`, the same instance on every
            call until it's fully unwrapped.
        """
        with self.lock:
            hooked: bool = self._wrap_excepthook_locked()

            if not self.wrapped_stderr:
                self.stderr = sys.stderr = WrappingIO(  # type: ignore
                    self.original_stderr,
                    listeners=self.listeners,
                    lock=self._listeners_box,
                )
            self.wrapped_stderr += 1
            wrapper: WrappingIO = sys.stderr  # type: ignore
        if hooked:
            self._log_excepthook_wrapped()
        return wrapper

    def wrap_logging(self) -> None:
        """Retarget every `StreamHandler` in the logger tree to the wrapper.

        Refcounted like `wrap_stdout`/`wrap_stderr`: only the first call
        actually walks the logger tree and rewrites handlers, so
        nested/concurrent redirection doesn't fight over the same
        handlers or lose track of what to restore. Each handler is
        visited once (deduplicated by `id()`, via `_wrap_logging_handler`)
        because the same handler object can be attached to more than one
        logger in the tree, and each retargeted handler is recorded in
        `logging_handlers` so `unwrap_logging` can put it back later.
        """
        self.wrapped_logging += 1
        if self.wrapped_logging > 1:
            return

        wrapped_streams = {
            self.original_stdout: self.stdout,
            self.original_stderr: self.stderr,
            sys.stdout: self.stdout,
            sys.stderr: self.stderr,
        }
        restore_streams: dict[object, base.IO] = {}
        if isinstance(self.stdout, WrappingIO):
            restore_streams[self.stdout] = self.original_stdout
        if isinstance(self.stderr, WrappingIO):
            restore_streams[self.stderr] = self.original_stderr

        seen: set[int] = set()
        for logger_ in self._iter_loggers():
            for handler in tuple(logger_.handlers):
                if id(handler) in seen:
                    continue
                seen.add(id(handler))
                if not isinstance(handler, logging.StreamHandler):
                    continue
                self._wrap_logging_handler(
                    handler,
                    wrapped_streams,
                    restore_streams,
                )

    def _wrap_logging_handler(
        self,
        handler: logging.StreamHandler[base.IO],
        wrapped_streams: Mapping[types.Any, types.Any],
        restore_streams: Mapping[types.Any, base.IO],
    ) -> None:
        """Retarget one handler's stream, or note it for restoration.

        `wrapped_streams` maps the real/current stdout and stderr
        objects to their wrapper. If `handler.stream` is one of those,
        it's repointed at the wrapper (`_set_handler_stream`) and the
        stream it used to point at is saved in `logging_handlers` so
        `unwrap_logging` can restore it.

        Otherwise, if `handler.stream` is itself already a wrapper (per
        `restore_streams`, e.g. `wrap_stdout`/`wrap_stderr` ran before
        `wrap_logging`, so the handler already points at the wrapper),
        it's left untouched but still recorded for restoration, so
        `unwrap_logging` still puts it back once this session ends.
        """
        stream = handler.stream
        replacement = wrapped_streams.get(stream)
        if replacement is not None and replacement is not stream:
            if self._set_handler_stream(handler, replacement):
                self.logging_handlers.append((handler, stream))
        elif (restore_stream := restore_streams.get(stream)) is not None:
            self.logging_handlers.append((handler, restore_stream))

    def unwrap_logging(self) -> None:
        """Undo one `wrap_logging()` call, restoring at refcount zero.

        Only the call that brings `wrapped_logging` to zero actually
        restores anything: it pops every entry `wrap_logging` recorded
        in `logging_handlers` and puts each handler's original stream
        back.
        """
        if self.wrapped_logging > 1:
            self.wrapped_logging -= 1
            return
        if not self.wrapped_logging:
            return

        while self.logging_handlers:
            handler, stream = self.logging_handlers.pop()
            self._set_handler_stream(handler, stream)
        self.wrapped_logging = 0

    def _set_handler_stream(
        self,
        handler: logging.StreamHandler[base.IO],
        stream: types.Any,
    ) -> bool:
        """Point `handler` at `stream`, tolerating a closed old stream.

        `StreamHandler.setStream()` flushes the handler's *current*
        stream as part of switching, which raises `ValueError` if that
        stream is already closed. `AttributeError` guards against
        `handler` not actually exposing `setStream` (defensive, given
        the type hint promises it does). Either way, the handler is left
        untouched rather than raising.

        Returns:
            Whether `handler.stream` was actually changed.
        """
        with contextlib.suppress(AttributeError, ValueError):
            handler.setStream(stream)
            return True
        return False

    def _iter_loggers(self) -> types.Iterator[logging.Logger]:
        """Yield the root logger, then every other registered logger.

        Snapshots `logging.Logger.manager.loggerDict` with `tuple()`
        first, since new loggers can be created while a caller is still
        draining this generator. Entries that are placeholders for a
        not-yet-created parent logger (not real `Logger` instances) are
        skipped.
        """
        yield logging.getLogger()
        for logger_ in tuple(logging.Logger.manager.loggerDict.values()):
            if isinstance(logger_, logging.Logger):
                yield logger_

    def unwrap_excepthook(self) -> None:
        """Restore the original `sys.excepthook`, if currently wrapped."""
        with self.lock:
            if self.wrapped_excepthook:
                self.wrapped_excepthook = False
                sys.excepthook = self.original_excepthook

    def wrap_excepthook(self) -> None:
        """Install the shared excepthook that flushes buffered output.

        A no-op if already wrapped: `wrap_stdout()` and `wrap_stderr()`
        both call this unconditionally, and either one may already have
        wrapped it.
        """
        with self.lock:
            hooked: bool = self._wrap_excepthook_locked()
        if hooked:
            self._log_excepthook_wrapped()

    def _wrap_excepthook_locked(self) -> bool:
        """Install the excepthook under `lock`; True when newly installed."""
        if self.wrapped_excepthook:
            return False
        self.wrapped_excepthook = True
        sys.excepthook = self.excepthook
        return True

    @staticmethod
    def _log_excepthook_wrapped() -> None:
        """Log the hook installation, after `lock` has been released.

        Logging while holding `lock` could wait for a handler lock held
        by a thread that is writing into a wrapper and waiting for
        `lock` in turn.
        """
        logger.debug('wrapping excepthook')

    def unwrap(self, stdout: bool = False, stderr: bool = False) -> None:
        """Unwrap `stdout` and/or `stderr`, per the given flags."""
        if stdout:
            self.unwrap_stdout()

        if stderr:
            self.unwrap_stderr()

    @staticmethod
    def _drop(dropped: object) -> tuple[WrappingIO, str] | None:
        """Stop buffering in a dropped wrapper and take what it holds.

        Runs under `lock`; the text goes to `_deliver_dropped` after
        the lock is released. Returns None for a plain stream.
        """
        if not isinstance(dropped, WrappingIO):
            return None
        dropped.capturing = False
        return dropped, dropped._take()

    @staticmethod
    def _deliver_dropped(taken: tuple[WrappingIO, str] | None) -> None:
        """Deliver the text `_drop` took, outside `lock`.

        A stale reference to the wrapper must not swallow output. The
        delivery touches the original stream, so a stream that cannot
        take it (no `flush()`, closed, a broken pipe, a GUI widget that
        is gone) is logged and otherwise ignored: unwrapping never
        raises for it, as it did not before the flush was added.
        """
        if taken is None:
            return
        dropped, text = taken
        try:
            dropped._deliver(text)
        except Exception:
            logger.debug(
                'Could not deliver buffered output on unwrap',
                exc_info=True,
            )

    def unwrap_stdout(self) -> None:
        """Undo one `wrap_stdout()` call, restoring at refcount zero.

        Only the call that brings `wrapped_stdout` to zero actually
        restores `sys.stdout`, and `self.stdout` alongside it, so
        `needs_clear()` and `update_capturing()` don't keep reading a
        wrapper that's no longer installed. Also unwraps the shared
        excepthook once `stderr` is back to its original too, since
        it's shared between the two.
        """
        with self.lock:
            if self.wrapped_stdout > 1:
                self.wrapped_stdout -= 1
                return

            taken = self._drop(self.stdout)
            # Also reset our own reference so needs_clear() and
            # update_capturing() don't act on a stale wrapper
            self.stdout = sys.stdout = self.original_stdout
            self.wrapped_stdout = 0
            if not self.wrapped_stderr:
                self.unwrap_excepthook()
        # Deliver after releasing `lock`: this writes into the original
        # stream and may log, see `_apply_capturing`
        self._deliver_dropped(taken)

    def unwrap_stderr(self) -> None:
        """Undo one `wrap_stderr()` call, restoring at refcount zero.

        Mirrors `unwrap_stdout()`: only the call that brings
        `wrapped_stderr` to zero restores `sys.stderr`, and the shared
        excepthook is unwrapped once `stdout` is back to its original
        too.
        """
        with self.lock:
            if self.wrapped_stderr > 1:
                self.wrapped_stderr -= 1
                return

            taken = self._drop(self.stderr)
            # Also reset our own reference so needs_clear() and
            # update_capturing() don't act on a stale wrapper
            self.stderr = sys.stderr = self.original_stderr
            self.wrapped_stderr = 0
            if not self.wrapped_stdout:
                self.unwrap_excepthook()
        # Deliver after releasing `lock`, see `unwrap_stdout`
        self._deliver_dropped(taken)

    def needs_clear(self) -> bool:  # pragma: no cover
        """Return whether either wrapped stream has buffered output.

        Uses `getattr` with a `False` default so this is safe to call
        whether or not `stdout`/`stderr` are currently wrapped, since a
        plain, unwrapped stream has no `needs_clear` attribute.

        Returns:
            Whether a bar's next redraw should erase its line first, so
            buffered `print()`/logging output can be flushed above it.
        """
        stdout_needs_clear = getattr(self.stdout, 'needs_clear', False)
        stderr_needs_clear = getattr(self.stderr, 'needs_clear', False)
        return stderr_needs_clear or stdout_needs_clear

    def flush(self) -> None:
        """Flush buffered captured output on both wrapped streams.

        The buffers are drained under `lock` and written to the
        original streams after releasing it, see `_deliver` for what
        happens when a stream cannot take the text.
        """
        with self.lock:
            pending: list[_Pending] = self._take()
        self._deliver(pending)

    def excepthook(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        """Run the original excepthook, then flush buffered output.

        Installed as `sys.excepthook` while stdout or stderr is wrapped
        (see `wrap_excepthook`), so an uncaught exception's traceback,
        written via the original hook, is followed by whatever output
        was still buffered, instead of that text getting lost or
        appearing in the wrong order relative to the traceback.
        """
        self.original_excepthook(exc_type, exc_value, exc_traceback)
        self.flush()


class AttributeDict(dict[str, T], typing.Generic[T]):
    """A dict that can be accessed with .attribute.

    Note:
        Double-underscore names (e.g. ``__orig_class__``, set by
        ``typing.Generic`` on subscripted instances) are routed to real
        instance attributes instead of dict entries, keeping runtime
        metadata like that out of the mapping's contents. See
        ``__setattr__``/``__delattr__``.

    >>> attrs = AttributeDict(spam=123)

    # Reading

    >>> attrs['spam']
    123
    >>> attrs.spam
    123

    # Read after update using attribute

    >>> attrs.spam = 456
    >>> attrs['spam']
    456
    >>> attrs.spam
    456

    # Read after update using dict access

    >>> attrs['spam'] = 123
    >>> attrs['spam']
    123
    >>> attrs.spam
    123

    # Read after update using dict access

    >>> del attrs.spam
    >>> attrs['spam']
    Traceback (most recent call last):
    ...
    KeyError: 'spam'
    >>> attrs.spam
    Traceback (most recent call last):
    ...
    AttributeError: No such attribute: spam
    >>> del attrs.spam
    Traceback (most recent call last):
    ...
    AttributeError: No such attribute: spam
    """

    def __getattr__(self, name: str) -> T:
        """Return `self[name]`, so dict keys are readable as attributes.

        Raises:
            AttributeError: `name` is not a key in this dict.
        """
        if name in self:
            return self[name]
        else:
            raise AttributeError(f'No such attribute: {name}')

    def __setattr__(self, name: str, value: T) -> None:
        """Store `name`/`value` as a dict entry, unless `name` is a dunder.

        Dunder names are set as a real instance attribute instead (via
        `object.__setattr__`), per the class `Note:` above.
        """
        if name.startswith('__') and name.endswith('__'):
            object.__setattr__(self, name, value)
            return
        self[name] = value

    def __delattr__(self, name: str) -> None:
        """Delete the `name` dict entry, unless `name` is a dunder.

        Mirrors `__setattr__`: dunder names are deleted via
        `object.__delattr__` instead of as dict entries.

        Raises:
            AttributeError: `name` is neither a dunder nor an existing
                key.
        """
        if name.startswith('__') and name.endswith('__'):
            object.__delattr__(self, name)
            return
        if name in self:
            del self[name]
        else:
            raise AttributeError(f'No such attribute: {name}')


#: Process-global, constructed once at import. The only place that knows
#: the *real* ``sys.stdout``/``sys.stderr`` versus whatever is currently
#: installed in their place. Every bar that redirects goes through this
#: one shared instance rather than each keeping its own. Mutating it
#: (wrapping/unwrapping) affects every bar and every plain ``print()``
#: in the process. ``bar.py``'s ``StdRedirectMixin`` is its only real
#: consumer.
streams = StreamWrapper()
atexit.register(streams.flush)
