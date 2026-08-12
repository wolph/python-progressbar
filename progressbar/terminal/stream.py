"""`typing.TextIO` wrappers that intercept or redirect stream writes.

`TextIOOutputWrapper` is a pass-through base that delegates every
`TextIO` operation to a wrapped stream unchanged. Concrete wrappers
subclass it and override only the operation(s) they need to change
(typically `write`). Two concrete wrappers:

- `LineOffsetStreamWrapper` writes a fixed number of lines above the
  current cursor position instead of at it, used by `ProgressBar`'s
  `line_offset=` argument.
- `LastLineStream` discards everything but the most recently written
  line, used by `MultiBar` to capture a bar's rendered output without
  letting it reach the terminal directly.

Every non-underscore name here is re-exported by `progressbar.terminal`
(``from .stream import *``, no ``__all__``). `LineOffsetStreamWrapper`
is also part of the top-level `progressbar` public API.
"""

from __future__ import annotations

import sys
import typing
from collections.abc import Generator, Iterable, Iterator
from types import TracebackType

from progressbar import base


class TextIOOutputWrapper(base.TextIO):  # pragma: no cover
    """Pass-through `TextIO` base that delegates to a wrapped stream.

    Every operation forwards to `self.stream` unchanged, and subclasses
    override only what they need to intercept. `write` is left
    unimplemented: this class is meant to be subclassed, not used as-is.
    """

    def __init__(self, stream: base.TextIO) -> None:
        """Store the stream to delegate to."""
        self.stream = stream

    def close(self) -> None:
        """Delegate to the wrapped stream."""
        self.stream.close()

    def fileno(self) -> int:
        """Delegate to the wrapped stream."""
        return self.stream.fileno()

    def flush(self) -> None:
        """Delegate to the wrapped stream."""
        self.stream.flush()

    def isatty(self) -> bool:
        """Delegate to the wrapped stream."""
        return self.stream.isatty()

    def read(self, __n: int = -1) -> str:
        """Delegate to the wrapped stream."""
        return self.stream.read(__n)

    def readable(self) -> bool:
        """Delegate to the wrapped stream."""
        return self.stream.readable()

    def readline(self, __limit: int = -1) -> str:
        """Delegate to the wrapped stream."""
        return self.stream.readline(__limit)

    def readlines(self, __hint: int = -1) -> list[str]:
        """Delegate to the wrapped stream."""
        return self.stream.readlines(__hint)

    def seek(self, __offset: int, __whence: int = 0) -> int:
        """Delegate to the wrapped stream."""
        return self.stream.seek(__offset, __whence)

    def seekable(self) -> bool:
        """Delegate to the wrapped stream."""
        return self.stream.seekable()

    def tell(self) -> int:
        """Delegate to the wrapped stream."""
        return self.stream.tell()

    def truncate(self, __size: int | None = None) -> int:
        """Delegate to the wrapped stream."""
        return self.stream.truncate(__size)

    def writable(self) -> bool:
        """Delegate to the wrapped stream."""
        return self.stream.writable()

    def writelines(self, __lines: Iterable[str]) -> None:
        """Delegate to the wrapped stream."""
        return self.stream.writelines(__lines)

    def __next__(self) -> str:
        """Delegate to the wrapped stream."""
        return self.stream.__next__()

    def __iter__(self) -> Iterator[str]:
        """Delegate to the wrapped stream."""
        return self.stream.__iter__()

    def __exit__(
        self,
        __t: type[BaseException] | None,
        __value: BaseException | None,
        __traceback: TracebackType | None,
    ) -> None:
        """Delegate to the wrapped stream."""
        return self.stream.__exit__(__t, __value, __traceback)

    def __enter__(self) -> base.TextIO:
        """Delegate to the wrapped stream."""
        return self.stream.__enter__()


class LineOffsetStreamWrapper(TextIOOutputWrapper):
    """Writes land a fixed number of lines above the cursor.

    Each `write` moves the cursor up `lines` rows, writes there, then
    moves back down, leaving the cursor where it started. Used by
    `ProgressBar`'s `line_offset=` argument to draw a bar above
    other terminal output instead of at the current line.
    """

    #: ANSI "cursor up one line" (CSI ``F``).
    UP = '\033[F'
    #: ANSI "cursor down one line" (CSI ``B``).
    DOWN = '\033[B'

    def __init__(
        self, lines: int = 0, stream: typing.TextIO = sys.stderr
    ) -> None:
        """Store the offset and the stream writes are redirected to.

        Args:
            lines: Number of lines above the current cursor position
                to write to.
            stream: The underlying stream to write to.
        """
        self.lines = lines
        super().__init__(stream)

    def write(self, data: str) -> int:
        """Write `data` `self.lines` rows above the cursor.

        Moves the cursor up, writes `data` with trailing newlines
        stripped (so the write itself doesn't move the cursor),
        then moves back down to restore the original position.

        Args:
            data: Text to write.

        Returns:
            The length of `data` before newline-stripping, so
            callers can detect short writes.
        """
        written = len(data)
        data = data.rstrip('\n')
        # Move the cursor up
        self.stream.write(self.UP * self.lines)
        # Print a carriage return to reset the cursor position
        self.stream.write('\r')
        # Print the data without newlines so we don't change the position
        self.stream.write(data)
        # Move the cursor down
        self.stream.write(self.DOWN * self.lines)

        self.flush()
        return written


class LastLineStream(TextIOOutputWrapper):
    """Discards everything but the most recently written line.

    `MultiBar` rebinds a bar's `fd` to one of these so the bar's own
    redraws never reach the terminal directly. The multibar instead
    reads `.line` back out and places it on that bar's row of the
    combined frame.
    """

    #: The most recently written line. Only `write`, `writelines` and
    #: `truncate` touch this. Every other inherited method still
    #: operates on the wrapped stream.
    line: str = ''

    def seekable(self) -> bool:
        """Always `False`: there is nothing to seek within."""
        return False

    def readable(self) -> bool:
        """Always `True`: `.line` can always be read back."""
        return True

    def read(self, __n: int = -1) -> str:
        """Return `.line`, or its first `__n` characters."""
        if __n < 0:
            return self.line
        else:
            return self.line[:__n]

    def readline(self, __limit: int = -1) -> str:
        """Return `.line`, or its first `__limit` characters."""
        if __limit < 0:
            return self.line
        else:
            return self.line[:__limit]

    def write(self, data: str) -> int:
        """Replace `.line` with `data`."""
        self.line = data
        return len(data)

    def truncate(self, __size: int | None = None) -> int:
        """Clear `.line`, or cut it to its first `__size` characters."""
        if __size is None:
            self.line = ''
        else:
            self.line = self.line[:__size]

        return len(self.line)

    def __iter__(self) -> Generator[str, typing.Any, typing.Any]:
        """Yield `.line` as the stream's sole line."""
        yield self.line

    def writelines(self, __lines: Iterable[str]) -> None:
        """Keep only the last of `__lines`, discarding the rest.

        Deliberate: `MultiBar` only ever wants a bar's most recent
        rendered line, not its history.
        """
        line = ''
        # Walk through the lines and take the last one
        for line in __lines:  # noqa: B007
            pass

        self.line = line
