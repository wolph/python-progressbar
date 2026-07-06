from __future__ import annotations

import atexit
import contextlib
import datetime
import io
import logging
import os
import re
import sys
import typing
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
    ``bar`` so ``utils`` has no dependency on ``bar`` — not even a
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
    *deltas: None | datetime.timedelta | float | int,
    default: type[ValueError] = ...,
) -> float:
    """Coalesce to seconds; raise ``ValueError`` if no delta is valid."""


@typing.overload
def deltas_to_seconds(
    *deltas: None | datetime.timedelta | float | int,
    default: T,
) -> float | T:
    """Coalesce to seconds; return ``default`` if no delta is valid."""


def deltas_to_seconds(
    *deltas: None | datetime.timedelta | float | int,
    default: typing.Any = ValueError,
) -> typing.Any:
    """
    Convert timedeltas and seconds as int to seconds as float while coalescing.

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
    """
    Return the `value` without ANSI escape codes.

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
    """
    Return the length of `value` without ANSI escape codes.

    >>> len_color(b'\u001b[1234]abc')
    3
    >>> len_color('\u001b[1234]abc')
    3
    >>> len_color('\u001b[1234]abc')
    3
    """
    return len(no_color(value))


class WrappingIO:
    buffer: io.StringIO
    target: base.IO
    capturing: bool
    listeners: set[_ProgressListener]
    needs_clear: bool = False

    def __init__(
        self,
        target: base.IO,
        capturing: bool = False,
        listeners: set[_ProgressListener] | None = None,
    ) -> None:
        self.buffer = io.StringIO()
        self.target = target
        self.capturing = capturing
        self.listeners = listeners or set()
        self.needs_clear = False

    def write(self, value: str) -> int:
        ret = 0
        if self.capturing:
            ret += self.buffer.write(value)
            if '\n' in value:  # pragma: no branch
                self.needs_clear = True
                for listener in self.listeners:  # pragma: no branch
                    listener.update()
        else:
            ret += self.target.write(value)
            if '\n' in value:  # pragma: no branch
                self.flush_target()

        return ret

    def flush(self) -> None:
        self.buffer.flush()

    def _flush(self) -> None:
        if value := self.buffer.getvalue():
            self.flush()
            # Clear the buffer before writing so a failed write cannot
            # cause the same data to be written again by the next flush
            self.buffer.seek(0)
            self.buffer.truncate(0)
            self.needs_clear = False
            if not self.target.closed:
                self.target.write(value)

        # when explicitly flushing, always flush the target as well
        self.flush_target()

    def flush_target(self) -> None:  # pragma: no cover
        if not self.target.closed and getattr(self.target, 'flush', None):
            self.target.flush()

    def __enter__(self) -> WrappingIO:
        return self

    def fileno(self) -> int:
        return self.target.fileno()

    def isatty(self) -> bool:
        return self.target.isatty()

    def read(self, n: int = -1) -> str:
        return self.target.read(n)

    def readable(self) -> bool:
        return self.target.readable()

    def readline(self, limit: int = -1) -> str:
        return self.target.readline(limit)

    def readlines(self, hint: int = -1) -> list[str]:
        return self.target.readlines(hint)

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        return self.target.seek(offset, whence)

    def seekable(self) -> bool:
        return self.target.seekable()

    def tell(self) -> int:
        return self.target.tell()

    def truncate(self, size: int | None = None) -> int:
        return self.target.truncate(size)

    def writable(self) -> bool:
        return self.target.writable()

    def writelines(self, lines: Iterable[str]) -> None:
        return self.target.writelines(lines)

    def close(self) -> None:
        self.flush()
        self.target.close()

    def __next__(self) -> str:
        return self.target.__next__()

    def __iter__(self) -> Iterator[str]:
        return self.target.__iter__()

    def __exit__(
        self,
        __t: type[BaseException] | None,
        __value: BaseException | None,
        __traceback: TracebackType | None,
    ) -> None:
        self.close()


class StreamWrapper:
    """Wrap stdout and stderr globally."""

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
    wrapped_excepthook: int = 0
    logging_handlers: list[tuple[logging.StreamHandler[base.IO], base.IO]]
    capturing: int = 0
    listeners: set[_ProgressListener]

    def __init__(self) -> None:
        self.stdout = self.original_stdout = sys.stdout
        self.stderr = self.original_stderr = sys.stderr
        self.original_excepthook = sys.excepthook
        self.wrapped_stdout = 0
        self.wrapped_stderr = 0
        self.wrapped_logging = 0
        self.wrapped_excepthook = 0
        self.logging_handlers = []
        self.capturing = 0
        self.listeners = set()

        if env.env_flag('WRAP_STDOUT', default=False):  # pragma: no cover
            self.wrap_stdout()

        if env.env_flag('WRAP_STDERR', default=False):  # pragma: no cover
            self.wrap_stderr()

    def start_capturing(self, bar: _ProgressListener | None = None) -> None:
        if bar:  # pragma: no branch
            self.listeners.add(bar)

        self.capturing += 1
        self.update_capturing()

    def stop_capturing(self, bar: _ProgressListener | None = None) -> None:
        if bar:  # pragma: no branch
            with contextlib.suppress(KeyError):
                self.listeners.remove(bar)

        self.capturing -= 1
        self.update_capturing()

    def update_capturing(self) -> None:  # pragma: no cover
        if isinstance(self.stdout, WrappingIO):
            self.stdout.capturing = self.capturing > 0

        if isinstance(self.stderr, WrappingIO):
            self.stderr.capturing = self.capturing > 0

        if self.capturing <= 0:
            self.flush()

    def wrap(self, stdout: bool = False, stderr: bool = False) -> None:
        if stdout:
            self.wrap_stdout()

        if stderr:
            self.wrap_stderr()

    def wrap_stdout(self) -> WrappingIO:
        self.wrap_excepthook()

        if not self.wrapped_stdout:
            self.stdout = sys.stdout = WrappingIO(  # type: ignore
                self.original_stdout,
                listeners=self.listeners,
            )
        self.wrapped_stdout += 1

        return sys.stdout  # type: ignore

    def wrap_stderr(self) -> WrappingIO:
        self.wrap_excepthook()

        if not self.wrapped_stderr:
            self.stderr = sys.stderr = WrappingIO(  # type: ignore
                self.original_stderr,
                listeners=self.listeners,
            )
        self.wrapped_stderr += 1

        return sys.stderr  # type: ignore

    def wrap_logging(self) -> None:
        """Retarget stdout/stderr logging handlers to wrapped streams."""
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
        stream = handler.stream
        replacement = wrapped_streams.get(stream)
        if replacement is not None and replacement is not stream:
            if self._set_handler_stream(handler, replacement):
                self.logging_handlers.append((handler, stream))
        elif (restore_stream := restore_streams.get(stream)) is not None:
            self.logging_handlers.append((handler, restore_stream))

    def unwrap_logging(self) -> None:
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
        with contextlib.suppress(AttributeError, ValueError):
            handler.setStream(stream)
            return True
        return False

    def _iter_loggers(self) -> types.Iterator[logging.Logger]:
        yield logging.getLogger()
        for logger_ in tuple(logging.Logger.manager.loggerDict.values()):
            if isinstance(logger_, logging.Logger):
                yield logger_

    def unwrap_excepthook(self) -> None:
        if self.wrapped_excepthook:
            self.wrapped_excepthook -= 1
            sys.excepthook = self.original_excepthook

    def wrap_excepthook(self) -> None:
        if not self.wrapped_excepthook:
            logger.debug('wrapping excepthook')
            self.wrapped_excepthook += 1
            sys.excepthook = self.excepthook

    def unwrap(self, stdout: bool = False, stderr: bool = False) -> None:
        if stdout:
            self.unwrap_stdout()

        if stderr:
            self.unwrap_stderr()

    def unwrap_stdout(self) -> None:
        if self.wrapped_stdout > 1:
            self.wrapped_stdout -= 1
        else:
            # Also reset our own reference so needs_clear() and
            # update_capturing() don't act on a stale wrapper
            self.stdout = sys.stdout = self.original_stdout
            self.wrapped_stdout = 0
            if not self.wrapped_stderr:
                self.unwrap_excepthook()

    def unwrap_stderr(self) -> None:
        if self.wrapped_stderr > 1:
            self.wrapped_stderr -= 1
        else:
            # Also reset our own reference so needs_clear() and
            # update_capturing() don't act on a stale wrapper
            self.stderr = sys.stderr = self.original_stderr
            self.wrapped_stderr = 0
            if not self.wrapped_stdout:
                self.unwrap_excepthook()

    def needs_clear(self) -> bool:  # pragma: no cover
        stdout_needs_clear = getattr(self.stdout, 'needs_clear', False)
        stderr_needs_clear = getattr(self.stderr, 'needs_clear', False)
        return stderr_needs_clear or stdout_needs_clear

    def flush(self) -> None:
        if self.wrapped_stdout and isinstance(self.stdout, WrappingIO):
            try:
                self.stdout._flush()
            except io.UnsupportedOperation:
                self.wrapped_stdout = 0
                logger.warning(
                    'Disabling stdout redirection, %r is not seekable',
                    sys.stdout,
                )

        if self.wrapped_stderr and isinstance(self.stderr, WrappingIO):
            try:
                self.stderr._flush()
            except io.UnsupportedOperation:  # pragma: no cover
                self.wrapped_stderr = 0
                logger.warning(
                    'Disabling stderr redirection, %r is not seekable',
                    sys.stderr,
                )

    def excepthook(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        self.original_excepthook(exc_type, exc_value, exc_traceback)
        self.flush()


class AttributeDict(dict):
    """
    A dict that can be accessed with .attribute.

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

    def __getattr__(self, name: str) -> typing.Any:
        if name in self:
            return self[name]
        else:
            raise AttributeError(f'No such attribute: {name}')

    def __setattr__(self, name: str, value: typing.Any) -> None:
        self[name] = value

    def __delattr__(self, name: str) -> None:
        if name in self:
            del self[name]
        else:
            raise AttributeError(f'No such attribute: {name}')


streams = StreamWrapper()
atexit.register(streams.flush)
