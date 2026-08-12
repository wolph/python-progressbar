"""Core ``ProgressBar`` implementation: state, redraw gate, and mixins.

``ProgressBar`` is assembled from a stack of small mixins --
``DefaultFdMixin`` (writes formatted lines to a file descriptor),
``ResizableMixin`` (tracks terminal width via SIGWINCH),
``StdRedirectMixin`` (lets ``print()`` coexist with the bar) -- plus the
redraw machinery: the integer gate and ``_needs_update()`` that decide
whether a given ``update()`` call actually produces output.
"""

from __future__ import annotations

import abc
import collections.abc
import contextlib
import functools
import importlib
import itertools
import logging
import math
import os
import sys
import time
import timeit
import typing
import warnings
import weakref
from copy import deepcopy
from datetime import datetime, timedelta
from types import FrameType, TracebackType

from python_utils import converters

import progressbar.env
import progressbar.terminal
import progressbar.terminal.stream

from . import (
    base,
    utils,
)
from .terminal import os_specific

try:
    # Optional native accelerator, shipped as the ``progressbar2[fast]`` extra
    # (the separate ``speedups`` package). When importable, the iterator path
    # uses it automatically. Otherwise we fall back to the pure-Python gate.
    # Loaded via importlib so type checkers don't try to resolve the optional
    # compiled module when it is absent.
    _FastBarIterator = importlib.import_module(
        'speedups.progressbar',
    ).FastBarIterator
except Exception:  # pragma: no cover - environmental (absent / ABI mismatch)
    _FastBarIterator = None


@functools.cache
def _load_widgets() -> typing.Any:
    """Import the widgets module lazily (and once).

    The full-bar code needs ``widgets``, but the lean fast path must not pull
    it in (it drags the terminal/color tables). Imported via importlib so the
    deferred load doesn't read as a static ``bar -> widgets`` import cycle.

    Cached with ``functools.cache`` so full-bar render sites don't pay the
    ``import_module`` lookup on every call.
    """
    return importlib.import_module('progressbar.widgets')


logger = logging.getLogger(__name__)

# A `float` hint already accepts `int` under the PEP 484 numeric tower, so
# an explicit `int | float` union would be redundant noise
NumberT = float
ValueT = NumberT | type[base.UnknownLength] | None

T = typing.TypeVar('T')


class ProgressBarMixinBase(abc.ABC):
    """Shared state and cooperative no-op interface for progress-bar mixins.

    Declares the attributes every mixin/`ProgressBar` relies on and gives
    `start`/`update`/`finish`/`__init__` trivial bodies so each mixin in
    the cooperative-inheritance chain can call `super().<method>()`
    unconditionally, ending here without a `NotImplementedError`.
    """

    _started = False
    _finished = False
    _last_update_time: float | None = None

    #: The terminal width. This should be automatically detected but will
    #: fall back to 80 if auto detection is not possible.
    term_width: int = 80
    #: The widgets to render, defaults to the result of `default_widget()`
    #: (typed loosely as Any to avoid a static bar->widgets import cycle. The
    #: public ``progressbar()`` shortcut keeps the precise WidgetBase typing).
    widgets: collections.abc.MutableSequence[typing.Any]
    #: When going beyond the max_value, raise an error if True or silently
    #: ignore otherwise
    max_error: bool
    #: Prefix the progressbar with the given string
    prefix: str | None
    #: Suffix the progressbar with the given string
    suffix: str | None
    #: Justify to the left if `True` or the right if `False`
    left_justify: bool
    #: The default keyword arguments for the `default_widgets` if no widgets
    #: are configured
    widget_kwargs: dict[str, typing.Any]
    #: Custom length function for multibyte characters such as CJK. A plain
    #: ``Callable[[str], int]`` is used (rather than a bound-method signature)
    #: because mypy and pyright disagree on the more precise form.
    custom_len: collections.abc.Callable[[str], int]
    #: The time the progress bar was started
    initial_start_time: datetime | None
    #: The interval to poll for updates in seconds if there are updates
    poll_interval: float | None
    #: The minimum interval to poll for updates in seconds even if there are
    #: no updates
    min_poll_interval: float

    #: Deprecated: The number of intervals that can fit on the screen with a
    #: minimum of 100
    num_intervals: int = 0
    #: Deprecated: The `next_update` is kept for compatibility with external
    #: libs: https://github.com/WoLpH/python-progressbar/issues/207
    next_update: int = 0

    #: Current progress (min_value <= value <= max_value)
    value: NumberT
    #: Previous progress value
    previous_value: NumberT | None
    #: Value at the last actual redraw (internal, used by the update gate's
    #: pixel check, kept separate from the public `previous_value`)
    _last_drawn_value: NumberT | None
    #: The minimum/start value for the progress bar
    min_value: NumberT
    #: Maximum (and final) value. Beyond this value an error will be raised
    #: unless the `max_error` parameter is `False`.
    max_value: ValueT
    #: The time the progressbar reached `max_value` or when `finish()` was
    #: called.
    end_time: datetime | None
    #: The time `start()` was called or iteration started.
    start_time: datetime | None
    #: Seconds between `start_time` and last call to `update()`
    seconds_elapsed: float

    #: Extra data for widgets with persistent state, used by the sampling
    #: widgets for example. Keeping it here rather than on the widget lets
    #: the widget stay stateless: the state belongs to the bar, so `init()`
    #: clears it on restart and a shared widget cannot mix two bars' data.
    extra: dict[str, typing.Any]

    def get_last_update_time(self) -> datetime | None:
        """Return `last_update_time` as a `datetime`, or `None` if unset."""
        if self._last_update_time:
            return datetime.fromtimestamp(self._last_update_time)
        else:
            return None

    def set_last_update_time(self, value: datetime | None) -> None:
        """Store `value` as the `last_update_time` epoch timestamp."""
        if value:
            self._last_update_time = time.mktime(value.timetuple())
        else:
            self._last_update_time = None

    last_update_time = property(get_last_update_time, set_last_update_time)

    def __init__(self, **kwargs: typing.Any) -> None:  # noqa: B027
        """Do nothing: concrete state is set up by subclasses/mixins."""

    def start(self, **kwargs: typing.Any) -> None:
        """Mark the bar as started. Subclasses do the actual rendering."""
        self._started = True

    def update(self, value: ValueT = None) -> None:  # noqa: B027
        """Do nothing: subclasses do the actual rendering."""

    def finish(self) -> None:  # pragma: no cover
        """Mark the bar as finished. Subclasses do the actual rendering."""
        self._finished = True

    def __del__(self) -> None:
        """Best-effort `finish()` on teardown if never explicitly finished."""
        if not self._finished and self._started:  # pragma: no cover
            # We're not using contextlib.suppress here because during teardown
            # contextlib is not available anymore. Any exception can occur
            # here during interpreter shutdown (closed streams, partially
            # torn down modules), so we suppress all of them.
            try:  # noqa: SIM105
                self.finish()
            except Exception:  # noqa: BLE001, S110
                pass

    def __getstate__(self) -> collections.abc.Mapping[str, typing.Any]:
        """Return the instance `__dict__` for pickling."""
        return self.__dict__

    def data(self) -> dict[str, typing.Any]:  # pragma: no cover
        """Return the widget-facing data dict (see `ProgressBar.data`)."""
        raise NotImplementedError()

    def started(self) -> bool:
        """Return whether `start()` has (ever) been called."""
        return self._finished or self._started

    def finished(self) -> bool:
        """Return whether `finish()` has been called."""
        return self._finished


class ProgressBarBase(collections.abc.Iterable[NumberT], ProgressBarMixinBase):
    """Adds the `Iterable` protocol and a process-unique `index`/`label`.

    `index` identifies a bar among others (e.g. for `MultiBar`, which uses
    it to order/label child bars). `label` is a human-readable name for the
    same purpose.
    """

    _index_counter = itertools.count()
    index: int = -1
    label: str = ''

    def __init__(self, **kwargs: typing.Any) -> None:
        """Assign a process-unique `index` on first construction."""
        # Guard against the cooperative chain (or an old-style subclass
        # making several explicit parent __init__ calls) reaching this
        # method more than once per instance: `index` keeps its class
        # default of -1 until the first construction, so each bar
        # consumes exactly one counter value.
        if self.index == -1:
            self.index = next(self._index_counter)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """Return e.g. ``<ProgressBar#3: my label>``."""
        label = f': {self.label}' if self.label else ''
        return f'<{self.__class__.__name__}#{self.index}{label}>'


class DefaultFdMixin(ProgressBarMixinBase):
    """Formats and writes the bar's rendered line to a file descriptor.

    Owns ANSI/terminal/color detection for `fd` (defaults to
    `sys.stderr`) and the widget layout pass (`_format_widgets`) that turns
    `self.widgets` into one printable line.
    """

    # The file descriptor to write to. Defaults to `sys.stderr`
    fd: base.TextIO = sys.stderr
    #: Set the terminal to be ANSI compatible. If a terminal is ANSI
    #: compatible we will automatically enable `colors` and disable
    #: `line_breaks`.
    is_ansi_terminal: bool | None = False
    #: Whether the file descriptor is a terminal or not. This is used to
    #: determine whether to use ANSI escape codes or not.
    is_terminal: bool | None
    #: Whether to print line breaks. This is useful for logging the
    #: progressbar. When disabled the current line is overwritten.
    line_breaks: bool | None = True
    #: Specify the type and number of colors to support. Defaults to auto
    #: detection based on the file descriptor type (i.e. interactive terminal)
    #: environment variables such as `COLORTERM` and `TERM`. Color output can
    #: be forced in non-interactive terminals using the
    #: `PROGRESSBAR_ENABLE_COLORS` environment variable which can also be used
    #: to force a specific number of colors by specifying `24bit`, `256` or
    #: `16`.
    #: For true (24 bit/16M) color support you can use `COLORTERM=truecolor`.
    #: For 256 color support you can use `TERM=xterm-256color`.
    #: For 16 colorsupport you can use `TERM=xterm`.
    enable_colors: progressbar.env.ColorSupport = progressbar.env.COLOR_SUPPORT

    def __init__(
        self,
        fd: base.TextIO = sys.stderr,
        is_terminal: bool | None = None,
        line_breaks: bool | None = None,
        enable_colors: progressbar.env.ColorSupport | None = None,
        line_offset: int = 0,
        **kwargs: typing.Any,
    ) -> None:
        """Resolve `fd`/ANSI/color state for this bar.

        Args:
            fd: Where to write the bar. `sys.stdout`/`sys.stderr` are
                swapped for the *original*, unwrapped streams so a bar
                writing to one doesn't redirect through its own
                `StdRedirectMixin` capture.
            is_terminal: Force terminal detection. `None` autodetects.
            line_breaks: Print each redraw on a new line instead of
                overwriting via a carriage return. `None` autodetects from
                `is_terminal` (and the `PROGRESSBAR_LINE_BREAKS`
                environment variable).
            enable_colors: Color support override. `None` autodetects.
            line_offset: Number of lines to offset the bar from the current
                line, via a `LineOffsetStreamWrapper` around `fd`.
            **kwargs: Forwarded to `super().__init__()`.
        """
        if fd is sys.stdout:
            fd = utils.streams.original_stdout
        elif fd is sys.stderr:
            fd = utils.streams.original_stderr

        fd = self._apply_line_offset(fd, line_offset)
        self.fd = fd
        self.is_ansi_terminal = progressbar.env.is_ansi_terminal(fd)
        self.is_terminal = progressbar.env.is_terminal(fd, is_terminal)
        self.line_breaks = self._determine_line_breaks(line_breaks)
        self.enable_colors = self._determine_enable_colors(enable_colors)

        super().__init__(**kwargs)

    def _apply_line_offset(
        self,
        fd: base.TextIO,
        line_offset: int,
    ) -> base.TextIO:
        """Wrap `fd` in a `LineOffsetStreamWrapper` if `line_offset` is set."""
        if line_offset:
            return progressbar.terminal.stream.LineOffsetStreamWrapper(
                line_offset,
                fd,
            )
        else:
            return fd

    def _determine_line_breaks(self, line_breaks: bool | None) -> bool | None:
        """Resolve `line_breaks`, autodetecting from `is_terminal` if unset."""
        if line_breaks is None:
            return progressbar.env.env_flag(
                'PROGRESSBAR_LINE_BREAKS',
                not self.is_terminal,
            )
        else:
            return line_breaks

    def _determine_enable_colors(
        self,
        enable_colors: progressbar.env.ColorSupport | None,
    ) -> progressbar.env.ColorSupport:
        """Resolve the effective color support for this bar.

        Args:
            enable_colors: `None` autodetects from the
                `PROGRESSBAR_ENABLE_COLORS`/`FORCE_COLOR` environment
                variables and ANSI-terminal detection, in that order.
                `True` forces `XTERM_256`, `False` forces `NONE`. Any other
                value must already be a `ColorSupport` instance, used as-is.

        Returns:
            The resolved color support.

        Raises:
            ValueError: `enable_colors` is not `None`, `True`, `False`, or a
                `ColorSupport` instance.
        """
        color_support: progressbar.env.ColorSupport
        if enable_colors is None:
            colors = (
                progressbar.env.env_flag('PROGRESSBAR_ENABLE_COLORS'),
                progressbar.env.env_flag('FORCE_COLOR'),
                self.is_ansi_terminal,
            )

            for color_enabled in colors:
                if color_enabled is not None:
                    if color_enabled:
                        color_support = progressbar.env.COLOR_SUPPORT
                    else:
                        color_support = progressbar.env.ColorSupport.NONE
                    break
            else:
                color_support = progressbar.env.ColorSupport.NONE

        elif enable_colors is True:
            color_support = progressbar.env.ColorSupport.XTERM_256
        elif enable_colors is False:
            color_support = progressbar.env.ColorSupport.NONE
        elif isinstance(enable_colors, progressbar.env.ColorSupport):
            color_support = enable_colors
        else:
            raise ValueError(f'Invalid color support value: {enable_colors}')

        return color_support

    def print(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        """Print to `self.fd` instead of `sys.stdout`."""
        print(*args, file=self.fd, **kwargs)

    def start(self, **kwargs: typing.Any) -> None:
        """Put the terminal in the console mode the bar needs, then chain."""
        os_specific.set_console_mode()
        super().start(**kwargs)

    def update(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        """Format the current widgets into one line and write it to `fd`."""
        super().update(*args, **kwargs)

        line: str = converters.to_unicode(self._format_line())
        if not self.enable_colors:
            line = utils.no_color(line)

        line = line.rstrip() + '\n' if self.line_breaks else '\r' + line

        try:  # pragma: no cover
            self.fd.write(line)
        except UnicodeEncodeError:  # pragma: no cover
            # ``fd`` is a text stream, so write an ASCII-safe *str*: encode
            # with 'replace' to drop un-encodable characters, then decode
            # back. Writing the raw bytes here would raise ``TypeError``.
            self.fd.write(line.encode('ascii', 'replace').decode('ascii'))

    def finish(
        self,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:  # pragma: no cover
        """Restore the console mode and write the final `end` string."""
        os_specific.reset_console_mode()

        if self._finished:
            return

        end = kwargs.pop('end', '\n')
        super().finish(*args, **kwargs)

        if end and not self.line_breaks:
            self.fd.write(end)

        self.fd.flush()

    def _format_line(self) -> str:
        """Join the formatted widgets and justify to `term_width`."""
        widgets = ''.join(self._to_unicode(self._format_widgets()))

        if self.left_justify:
            return widgets.ljust(self.term_width)
        else:
            return widgets.rjust(self.term_width)

    def _format_widgets(self) -> list[str]:
        """Render `self.widgets` to strings, splitting width in two passes.

        Pass 1 walks `self.widgets` in order. A widget failing
        `check_size` is skipped entirely (no width, no output). A plain
        `str` has its length subtracted from the shared `width` budget
        immediately. An `AutoWidthWidgetBase` is deferred (its index is
        pushed onto `expanding`, so that list ends up in *reverse* index
        order) rather than rendered yet. Anything else (a fixed-width
        widget) is rendered right away and its length subtracted from
        `width`.

        Pass 2 divides whatever `width` remains among the deferred
        auto-width widgets. `expanding` holds them in reverse index
        order and `pop()` takes from the end, so they are processed
        front-to-back: the earliest auto-width widget in the bar is
        sized first. Each gets `ceil(remaining_width /
        remaining_count)`, floored at 0, so an uneven split gives the
        larger share to the earlier widgets. Its rendered length is
        then subtracted from `width` before the next widget's share is
        computed, so a widget rendering shorter or longer than its
        allocation shifts the rest.
        """
        widgets = _load_widgets()

        result = []
        expanding = []
        width = self.term_width
        data = self.data()

        for index, widget in enumerate(self.widgets):
            if isinstance(
                widget,
                widgets.WidgetBase,
            ) and not widget.check_size(self):
                continue
            elif isinstance(widget, widgets.AutoWidthWidgetBase):
                result.append(widget)
                expanding.insert(0, index)
            elif isinstance(widget, str):
                result.append(widget)
                width -= self.custom_len(widget)  # type: ignore
            else:
                widget_output = converters.to_unicode(widget(self, data))
                result.append(widget_output)
                width -= self.custom_len(widget_output)  # type: ignore

        count = len(expanding)
        while expanding:
            portion = max(math.ceil(width / count), 0)
            index = expanding.pop()
            widget = result[index]
            count -= 1

            widget_output = widget(self, data, portion)
            width -= self.custom_len(widget_output)  # type: ignore
            result[index] = widget_output

        return result

    @classmethod
    def _to_unicode(
        cls, args: collections.abc.Iterable[typing.Any]
    ) -> collections.abc.Iterator[str]:
        """Convert each item in `args` to `str` via `converters.to_unicode`."""
        for arg in args:
            yield converters.to_unicode(arg)


class _ResizeRegistry:
    """Shared SIGWINCH handling for all resizable progressbars.

    A single signal handler dispatches to every live bar. The original
    handler is saved when the first bar registers and restored when the
    last one unregisters, so overlapping bars can finish in any order
    without leaving a dangling handler installed.
    """

    bars: typing.ClassVar[weakref.WeakSet[ResizableMixin]] = weakref.WeakSet()
    previous_handler: typing.ClassVar[typing.Any] = None

    @classmethod
    def install(cls, bar: ResizableMixin) -> None:
        """Register `bar` for resize dispatch, installing the handler once.

        The process-global `SIGWINCH` handler is only installed (saving
        whatever handler was previously set) on the first registration. A
        second, third, etc. overlapping bar just joins the `WeakSet`.
        """
        import signal

        if not hasattr(signal, 'SIGWINCH'):  # pragma: no cover
            # Not available on Windows
            return

        if not cls.bars:
            cls.previous_handler = signal.getsignal(
                signal.SIGWINCH  # type: ignore[attr-defined]
            )
            signal.signal(
                signal.SIGWINCH,  # type: ignore[attr-defined]
                cls.handle_resize,
            )

        cls.bars.add(bar)

    @classmethod
    def uninstall(cls, bar: ResizableMixin) -> None:
        """Unregister `bar`, restoring the original handler once empty.

        Only the *last* bar to unregister actually restores
        `previous_handler` -- other still-live bars (in the `WeakSet`)
        keep the shared handler installed regardless of registration
        order.
        """
        import signal

        if not hasattr(signal, 'SIGWINCH'):  # pragma: no cover
            # Not available on Windows
            return

        cls.bars.discard(bar)
        if not cls.bars:
            signal.signal(
                signal.SIGWINCH,  # type: ignore[attr-defined]
                cls.previous_handler,
            )
            cls.previous_handler = None

    @classmethod
    def handle_resize(
        cls, signum: int | None = None, frame: FrameType | None = None
    ) -> None:
        """Dispatch a `SIGWINCH` to every currently-registered bar."""
        for bar in list(cls.bars):
            bar._handle_resize(signum, frame)


class ResizableMixin(ProgressBarMixinBase):
    """Keeps `term_width` current via a shared `SIGWINCH` handler.

    With an explicit `term_width`, that value is fixed and no signal
    handler is installed. Otherwise, autodetection and
    `_ResizeRegistry.install` are attempted and any failure (e.g. no
    controlling terminal, no `SIGWINCH` on this platform) is silently
    swallowed, leaving `term_width` at its class default.
    """

    def __init__(
        self, term_width: int | None = None, **kwargs: typing.Any
    ) -> None:
        """Fix `term_width`, or autodetect it and track further resizes."""
        super().__init__(**kwargs)

        self.signal_set = False
        if term_width:
            self.term_width = term_width
        else:  # pragma: no cover
            with contextlib.suppress(Exception):
                self._handle_resize()
                _ResizeRegistry.install(self)
                self.signal_set = True

    def _handle_resize(
        self, signum: int | None = None, frame: FrameType | None = None
    ) -> None:
        """Try to catch resize signals sent from the terminal."""
        w, _h = utils.get_terminal_size()
        self.term_width = w

    def finish(self) -> None:  # pragma: no cover
        """Unregister from `_ResizeRegistry` if this bar was registered."""
        super().finish()
        if self.signal_set:
            with contextlib.suppress(Exception):
                _ResizeRegistry.uninstall(self)
                self.signal_set = False


class StdRedirectMixin(DefaultFdMixin):
    """Redirect ``stdout``/``stderr`` so prints appear above the bar.

    Args:
        redirect_stderr (bool): Capture ``sys.stderr`` and print it above the
            bar instead of letting it corrupt the bar.
        redirect_stdout (bool): Capture ``sys.stdout`` and print it above the
            bar instead of letting it corrupt the bar.
        redirect_blank_line (bool): When redirecting, keep a blank line
            between the redirected output and the bar. Defaults to ``False``.
    """

    redirect_stderr: bool = False
    redirect_stdout: bool = False
    redirect_blank_line: bool = False
    stdout: utils.WrappingIO | base.IO[typing.Any]
    stderr: utils.WrappingIO | base.IO[typing.Any]
    _stdout: base.IO[typing.Any]
    _stderr: base.IO[typing.Any]

    def __init__(
        self,
        redirect_stderr: bool = False,
        redirect_stdout: bool = False,
        redirect_blank_line: bool = False,
        **kwargs: typing.Any,
    ) -> None:
        """Store the redirect flags. Actual wrapping happens in `start()`."""
        super().__init__(**kwargs)
        self.redirect_stderr = redirect_stderr
        self.redirect_stdout = redirect_stdout
        # Separate redirected output from the bar with a blank line
        self.redirect_blank_line = redirect_blank_line
        self._stdout = self.stdout = sys.stdout
        self._stderr = self.stderr = sys.stderr

    def start(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        """Wrap `stdout`/`stderr` (if requested) and register as a listener.

        `utils.streams.wrap_stdout`/`wrap_stderr` refcount the wrap, so
        nested/concurrent bars share one `WrappingIO` and only the last to
        finish restores the real stream.
        """
        if self.redirect_stdout:
            utils.streams.wrap_stdout()

        if self.redirect_stderr:
            utils.streams.wrap_stderr()

        self._stdout = utils.streams.original_stdout
        self._stderr = utils.streams.original_stderr

        self.stdout = utils.streams.stdout
        self.stderr = utils.streams.stderr

        utils.streams.start_capturing(self)
        super().start(*args, **kwargs)

    def update(self, value: NumberT | None = None) -> None:
        """Let buffered prints land above the bar, then redraw.

        If a captured `print()` happened since the last redraw
        (`needs_clear()`), the ordering that makes prints appear as normal
        scrollback above a still-live bar is: erase this bar's current
        line, flush the buffered print text through to the real terminal
        (it becomes a permanent line where the bar used to be), then
        redraw the bar fresh on the blank line below it.
        """
        cleared = not self.line_breaks and utils.streams.needs_clear()
        if cleared:
            self.fd.write('\r' + ' ' * self.term_width + '\r')

        utils.streams.flush()
        if cleared and self.redirect_blank_line:
            # Keep a blank line between the redirected output and the bar
            self.fd.write('\n')
        super().update(value=value)

    def finish(self, end: str = '\n') -> None:
        """Finish, then always release the global stream-wrapping state.

        The unwrap runs in a `finally` even when the final render raises,
        since a leaked listener would corrupt every later progressbar in
        the process.
        """
        try:
            super().finish(end=end)
        finally:
            utils.streams.stop_capturing(self)
            if self.redirect_stdout:
                utils.streams.unwrap_stdout()

            if self.redirect_stderr:
                utils.streams.unwrap_stderr()


class ProgressBar(
    StdRedirectMixin,
    ResizableMixin,
    ProgressBarBase,
):
    """Updates and prints a progress bar for a task of known or unknown length.

    Args:
        min_value: The minimum/start value for the progress bar.
        max_value: The maximum/end value for the progress bar. Defaults to
            `_DEFAULT_MAXVAL` (`UnknownLength`) if neither this nor `total`
            is given.
        widgets: The widgets to render, defaults to the result of
            `default_widgets()`.
        left_justify: Justify to the left if `True` or the right if
            `False`.
        initial_value: The value to start with.
        poll_interval: The maximum time between redraws, forcing one even
            if `value` hasn't changed -- useful for widgets that show
            elapsed time or an animation and should keep visibly moving.
            `None` (the default) never forces a redraw on time alone.
            Redraws from value changes can still happen sooner, but never
            faster than `min_poll_interval`.
        min_poll_interval: The minimum time between redraws -- a rate
            limit. The bar is not redrawn faster than this regardless of
            how fast `value` changes, unless `force=True`. Clamped to at
            least `_MINIMUM_UPDATE_INTERVAL`, and can be raised further
            (never lowered) by the `PROGRESSBAR_MINIMUM_UPDATE_INTERVAL`
            environment variable.
        widget_kwargs: Default keyword arguments passed to each widget
            built by `default_widgets()`.
        custom_len: Overrides how a rendered widget's width is measured.
            The default also strips ANSI color codes before measuring;
            override this if you use e.g. wide/CJK characters whose
            on-screen width doesn't match `len()`.
        max_error: Raise a `ValueError` if `value` goes beyond `max_value`.
            If `False`, `value` is clamped to `max_value` instead.
        prefix: Prefix the progressbar with the given string.
        suffix: Suffix the progressbar with the given string.
        variables: User-defined variables that can be used from a label
            using `format='{variables.my_var}'`. These values can be
            updated using `bar.update(my_var='newValue')`. This can also
            be used to set initial values for variables' widgets.
        line_offset: The number of lines to offset the progressbar from
            your current line. This is useful if you have other output or
            multiple progressbars.
        desc: tqdm-style alias for `prefix` (rendered as `f'{desc}: '`).
            Ignored if `prefix` is also given.
        total: tqdm-style alias for `max_value`. Ignored if `max_value` is
            also given.
        unit: The unit label used by unit-aware widgets. Defaults to
            `'it'`.
        unit_scale: Whether unit-aware widgets should scale the unit (e.g.
            show `1.2K` instead of `1200`).
        postfix: tqdm-style initial value for the `postfix` variable.
            With the default widgets, also appends a `Postfix` widget
            automatically.

    A common way of using it is like:

    >>> progress = ProgressBar().start()
    >>> for i in range(100):
    ...     progress.update(i + 1)
    ...     # do something
    >>> progress.finish()

    You can also use a ProgressBar as an iterator:

    >>> progress = ProgressBar()
    >>> some_iterable = range(100)
    >>> for i in progress(some_iterable):
    ...     # do something
    ...     pass

    Since the progress bar is incredibly customizable you can specify
    different widgets of any type in any order. You can even write your own
    widgets! However, since there are already a good number of widgets you
    should probably play around with them before moving on to create your own
    widgets.

    The term_width parameter represents the current terminal width. If the
    parameter is set to an integer then the progress bar will use that,
    otherwise it will attempt to determine the terminal width falling back to
    80 columns if the width cannot be determined.

    When implementing a widget's update method you are passed a reference to
    the current progress bar. As a result, you have access to the
    ProgressBar's methods and attributes. Although there is nothing preventing
    you from changing the ProgressBar you should treat it as read only.
    """

    _iterable: collections.abc.Iterator | None

    _DEFAULT_MAXVAL: type[base.UnknownLength] = base.UnknownLength
    # update every 50 milliseconds (up to a 20 times per second)
    _MINIMUM_UPDATE_INTERVAL: float = 0.050
    _last_update_time: float | None = None
    paused: bool = False

    def __init__(
        self,
        min_value: NumberT = 0,
        max_value: ValueT = None,
        widgets: collections.abc.Sequence[typing.Any] | None = None,
        left_justify: bool = True,
        initial_value: NumberT = 0,
        poll_interval: timedelta | float | None = None,
        widget_kwargs: dict[str, typing.Any] | None = None,
        custom_len: collections.abc.Callable[[str], int] = utils.len_color,
        max_error: bool = True,
        prefix: str | None = None,
        suffix: str | None = None,
        variables: dict[str, typing.Any] | None = None,
        min_poll_interval: timedelta | float | None = None,
        desc: str | None = None,
        total: ValueT = None,
        unit: str = 'it',
        unit_scale: bool = False,
        postfix: typing.Any = None,
        **kwargs: typing.Any,
    ) -> None:
        """Initializes a progress bar with sane defaults."""
        super().__init__(**kwargs)

        max_value, poll_interval = self._apply_deprecated_aliases(
            max_value, poll_interval, kwargs
        )

        if max_value is None and total is not None:
            # tqdm-style alias for `max_value`
            max_value = total
        if prefix is None and desc is not None:
            # tqdm-style alias for `prefix`
            prefix = f'{desc}: '

        if max_value and min_value > typing.cast(NumberT, max_value):
            raise ValueError(
                'Max value needs to be bigger than the min value',
            )
        self.min_value = min_value
        # Legacy issue, `max_value` can be `None` before execution. After
        # that it either has a value or is `UnknownLength`
        self.max_value = max_value  # type: ignore
        self.max_error = max_error

        self.widgets = self._copy_widgets(widgets)

        self.unit = unit
        self.unit_scale = unit_scale
        # Auto-append a Postfix widget in start() when `postfix` is used
        # with the default widgets. Explicit widget lists are left alone.
        self._auto_postfix = widgets is None and postfix is not None
        self._auto_postfix_added = False

        self.prefix = prefix
        self.suffix = suffix
        self.widget_kwargs = widget_kwargs or {}
        self.left_justify = left_justify
        self.value = initial_value
        self._iterable = None
        self.custom_len = custom_len  # type: ignore
        self.initial_start_time = kwargs.get('start_time')
        self.init()

        self._setup_poll_intervals(poll_interval, min_poll_interval)
        self._seed_variables(variables)
        if postfix is not None:
            self.variables['postfix'] = postfix

    def _apply_deprecated_aliases(
        self,
        max_value: ValueT,
        poll_interval: timedelta | float | None,
        kwargs: dict[str, typing.Any],
    ) -> tuple[ValueT, timedelta | float | None]:
        """Resolve the deprecated ``maxval``/``poll`` keyword aliases.

        Emits a :py:class:`DeprecationWarning` for each legacy name that is
        used without its modern counterpart and returns the (possibly updated)
        ``(max_value, poll_interval)`` pair.
        """
        if not max_value and kwargs.get('maxval') is not None:
            warnings.warn(
                'The usage of `maxval` is deprecated, please use '
                '`max_value` instead',
                DeprecationWarning,
                stacklevel=1,
            )
            max_value = kwargs.get('maxval')

        if not poll_interval and kwargs.get('poll'):
            warnings.warn(
                'The usage of `poll` is deprecated, please use '
                '`poll_interval` instead',
                DeprecationWarning,
                stacklevel=1,
            )
            poll_interval = kwargs.get('poll')

        return max_value, poll_interval

    def _copy_widgets(
        self, widgets: collections.abc.Sequence[typing.Any] | None
    ) -> list[typing.Any]:
        """Return a fresh widget list, deep-copying the copy-safe widgets.

        Only copy a widget if it's safe to copy. Most widgets are, so that is
        assumed to be true unless a widget opts out with ``copy = False``.
        """
        result: list[typing.Any] = []
        for widget in widgets or []:
            if getattr(widget, 'copy', True):
                widget = deepcopy(widget)
            result.append(widget)
        return result

    def _setup_poll_intervals(
        self,
        poll_interval: timedelta | float | None,
        min_poll_interval: timedelta | float | None,
    ) -> None:
        """Convert the poll intervals to seconds and clamp the minimum.

        Convert a given timedelta to a floating point number as the internal
        interval. We're not using timedelta's internally for two reasons:
        1. Backwards compatibility (most important one)
        2. Performance. Even though the amount of time it takes to compare a
        timedelta with a float versus a float directly is negligible, this
        comparison is run for _every_ update. With billions of updates
        (downloading a 1GiB file for example) this adds up.
        """
        poll_interval = utils.deltas_to_seconds(poll_interval, default=None)
        min_poll_interval = utils.deltas_to_seconds(
            min_poll_interval,
            default=None,
        )
        self._MINIMUM_UPDATE_INTERVAL = (
            utils.deltas_to_seconds(self._MINIMUM_UPDATE_INTERVAL)
            or self._MINIMUM_UPDATE_INTERVAL
        )

        # _MINIMUM_UPDATE_INTERVAL floors low values below.
        self.poll_interval = poll_interval
        self.min_poll_interval = max(
            min_poll_interval or self._MINIMUM_UPDATE_INTERVAL,
            self._MINIMUM_UPDATE_INTERVAL,
            float(os.environ.get('PROGRESSBAR_MINIMUM_UPDATE_INTERVAL', 0)),
        )  # type: ignore

    def _seed_variables(self, variables: dict[str, typing.Any] | None) -> None:
        """Seed the user-defined variables dict and scan widgets for names.

        Builds the ``variables`` mapping read by ``Variable`` and by
        ``FormatWidgetMixin`` subclasses, and registers a ``None``
        placeholder for every ``VariableMixin`` widget whose name isn't
        already supplied.
        """
        self.variables = utils.AttributeDict(variables or {})
        if self.widgets:
            widgets_module = _load_widgets()

            for widget in self.widgets:
                if (
                    isinstance(widget, widgets_module.VariableMixin)
                    and widget.name not in self.variables
                ):
                    self.variables[widget.name] = None

    @property
    def dynamic_messages(self) -> typing.Any:  # pragma: no cover
        """Deprecated alias for `variables`, kept for old callers."""
        return self.variables

    @dynamic_messages.setter
    def dynamic_messages(self, value: typing.Any) -> None:  # pragma: no cover
        self.variables = value

    def init(self) -> None:
        """Reset per-run state so the bar can be started (again).

        Called from `__init__` and re-run by `start(init=True)`.
        """
        self.previous_value = None
        # Value at the last actual redraw, used internally by the update
        # gate's pixel check (distinct from the public `previous_value`).
        self._last_drawn_value = None
        self.last_update_time = None
        self.start_time = None
        self.updates = 0
        self.end_time = None
        self.extra = dict()
        self._last_update_timer = timeit.default_timer()
        # Fast-path "next update" gate. The common iteration only re-enters
        # the redraw machinery when value reaches `_next_update`. `_gate_step`
        # is a closed-loop estimate of iterations per `min_poll_interval`,
        # calibrated in `update()` from the value/time elapsed between redraws
        # (tracked by `_last_drawn_value`/`_last_update_timer`). It starts at 1
        # so the gate forces an `update()` every iteration until a real timing
        # measurement (or the back-off doubling) grows the step, so slow
        # iterators (where time advances between calls) are never skipped
        # before that.
        self._next_update = 0
        self._gate_step = 1
        self._gate_enabled = True
        self._started = False
        self._finished = False

    @property
    def percentage(self) -> float | None:
        """Return current percentage, returns None if no max_value is given.

        >>> progress = ProgressBar()
        >>> progress.max_value = 10
        >>> progress.min_value = 0
        >>> progress.value = 0
        >>> progress.percentage
        0.0
        >>>
        >>> progress.value = 1
        >>> progress.percentage
        10.0
        >>> progress.value = 10
        >>> progress.percentage
        100.0
        >>> progress.min_value = -10
        >>> progress.percentage
        100.0
        >>> progress.value = 0
        >>> progress.percentage
        50.0
        >>> progress.value = 5
        >>> progress.percentage
        75.0
        >>> progress.value = -5
        >>> progress.percentage
        25.0
        >>> progress.max_value = None
        >>> progress.percentage
        """
        if self.max_value is None or self.max_value is base.UnknownLength:
            return None
        elif self.max_value:
            todo = self.value - self.min_value
            total = self.max_value - self.min_value  # type: ignore
            percentage = 100.0 * todo / total
        else:
            percentage = 100.0

        return percentage

    def data(self) -> dict[str, typing.Any]:
        """Return the snapshot dict passed to every widget's `__call__`.

        Returns:
            dict:
                - `max_value`: The configured maximum. `None` before
                  `start()`, `UnknownLength` when the bar has no known
                  length.
                - `start_time`: When `start()` ran.
                - `last_update_time`: Wall-clock time of the most recent
                  redraw.
                - `end_time`: Set by `finish()`, `None` until then.
                - `value`: The current value.
                - `previous_value`: The value before the current
                  `update()` call.
                - `updates`: Count of redraws performed so far.
                - `total_seconds_elapsed`: Seconds since `start_time`,
                  uninterrupted.
                - `seconds_elapsed`: `total_seconds_elapsed` modulo 60.
                - `minutes_elapsed`: Elapsed minutes modulo 60.
                - `hours_elapsed`: Elapsed hours modulo 24.
                - `days_elapsed`: Elapsed time in whole days (not modulo).
                - `time_elapsed`: The raw elapsed `datetime.timedelta`.
                - `percentage`: 0-100, or `None` when `max_value` is
                  `None`/`UnknownLength` (can exceed 100 if `max_error` is
                  `False` and `value` overshoots).
                - `unit`: The configured unit label (default `'it'`).
                - `unit_scale`: Whether widgets should scale the unit
                  (e.g. `1.2K` instead of `1200`).
                - `variables`: User-defined variables set via the
                  `variables=` constructor arg or `bar.update(name=value)`;
                  read by `Variable` and by `FormatWidgetMixin`
                  subclasses via `str.format()` substitution.
                - `dynamic_messages`: Deprecated alias for `variables` --
                  the same object, kept for old widgets that read this
                  key.

        This is a pure snapshot of the current state: it performs no timing
        side effects. The redraw path stamps the update timestamps via
        `_mark_update` before the widgets read them.
        """
        elapsed = self.last_update_time - self.start_time  # type: ignore
        total_seconds_elapsed = utils.deltas_to_seconds(elapsed)
        return dict(
            max_value=self.max_value,
            start_time=self.start_time,
            last_update_time=self.last_update_time,
            end_time=self.end_time,
            value=self.value,
            previous_value=self.previous_value,
            updates=self.updates,
            total_seconds_elapsed=total_seconds_elapsed,
            seconds_elapsed=(elapsed.seconds % 60)
            + (elapsed.microseconds / 1000000.0),
            minutes_elapsed=(elapsed.seconds / 60) % 60,
            hours_elapsed=(elapsed.seconds / (60 * 60)) % 24,
            days_elapsed=(elapsed.total_seconds() / (60 * 60 * 24)),
            time_elapsed=elapsed,
            percentage=self.percentage,
            unit=self.unit,
            unit_scale=self.unit_scale,
            variables=self.variables,
            # Deprecated alias for `variables`, deliberately the same object.
            dynamic_messages=self.variables,
        )

    def default_widgets(self) -> list[typing.Any]:
        """Build the widgets used when no explicit `widgets=` is given.

        Percentage/ETA-style widgets when `max_value` is known, otherwise
        an indeterminate animation (no percentage/ETA is computable
        without a known length).
        """
        widgets = _load_widgets()

        if self.max_value:
            return [
                widgets.Percentage(**self.widget_kwargs),
                ' ',
                widgets.SimpleProgress(
                    format=f'({widgets.SimpleProgress.DEFAULT_FORMAT})',
                    **self.widget_kwargs,
                ),
                ' ',
                widgets.Bar(**self.widget_kwargs),
                ' ',
                widgets.Timer(**self.widget_kwargs),
                ' ',
                widgets.SmoothingETA(**self.widget_kwargs),
            ]
        else:
            return [
                widgets.AnimatedMarker(**self.widget_kwargs),
                ' ',
                widgets.BouncingBar(**self.widget_kwargs),
                ' ',
                widgets.Counter(**self.widget_kwargs),
                ' ',
                widgets.Timer(**self.widget_kwargs),
            ]

    def __call__(
        self,
        iterable: collections.abc.Iterable[typing.Any],
        max_value: ValueT = None,
    ) -> ProgressBar:
        """Wrap `iterable` for use as `for item in bar(iterable):`.

        If `max_value` isn't given (here or already set), it's inferred
        from `len(iterable)`. An iterable without a `__len__` (e.g. a
        generator) falls back to `UnknownLength`.
        """
        if max_value is not None:
            self.max_value = max_value
        elif self.max_value is None:
            try:
                self.max_value = len(iterable)  # type: ignore[arg-type]
            except TypeError:  # pragma: no cover
                self.max_value = base.UnknownLength

        self._iterable = iter(iterable)
        return self

    def __iter__(self) -> collections.abc.Iterator[typing.Any]:
        """Dispatch to the native iterator if available, else the Python one.

        The native path counts in C and syncs `value`/`previous_value`
        only at redraw crossings (so they lag mid-loop, like `tqdm.n`),
        beating the per-iteration attribute writes the pure-Python path
        pays to keep them live every iteration.
        """
        if (
            _FastBarIterator is not None
            and self._iterable is not None
            and not os.environ.get('PROGRESSBAR_DISABLE_FASTPATH')
        ):
            return _FastBarIterator(self, self._iterable)
        return self._iter_python()

    def _iter_python(self) -> collections.abc.Iterator[typing.Any]:
        """Pure-Python iterator, used when the native accelerator can't run.

        A single generator (see issue #212): a `break`/exception in the
        loop body raises `GeneratorExit` here, caught below to `finish()`
        the bar (and restore any redirected streams) on early exit too.

        Value semantics must match the pre-gate behavior: `start()`
        draws 0% and the first item is yielded at `value == min_value`
        (no increment), so during the loop body for item `i` (0-indexed),
        `bar.value == i`, not `i + 1`. Only later items increment. The
        peek-first structure below (yield the first item, then loop the
        rest) reproduces that without a per-iteration branch for the
        first item.

        `gate_enabled` is read from `self._gate_enabled` into a local
        once: it's fixed by `start()` for the whole iteration, so
        hoisting it drops a per-iteration attribute load from the hot
        path.
        """
        iterable = self._iterable if self._iterable is not None else iter(())
        try:
            if self.start_time is None:
                self.start()
            iterator = iter(iterable)
            try:
                item = next(iterator)
            except StopIteration:
                self.finish()
                return
            yield item  # first item at value == min_value (matches old code)
            value = self.value
            next_update = value
            update = self.update
            gate_enabled = self._gate_enabled
            for item in iterator:
                value += 1
                # When the gate is disabled, call `update()` every iteration so
                # behavior is byte-identical to the ungated bar. When enabled,
                # only re-enter `update()` once value reaches the threshold.
                # The step starts at 1, so until a real measurement grows it
                # this still calls `update()` every iteration and lets
                # `_needs_update()` make the real redraw decision. Calling
                # `update()` (rather than pre-setting `self.value`) lets it
                # record the prior value in the public `previous_value`,
                # preserving its original semantics.
                if not gate_enabled or value >= next_update:
                    update(value)
                    next_update = self._next_update
                else:
                    # Gated out: advance bar.value AND previous_value (exactly
                    # as update() would) without entering the redraw machinery,
                    # so reads of bar.previous_value mid-loop stay identical to
                    # the original every-iteration semantics. The gate's pixel
                    # reference is the separate `_last_drawn_value`.
                    self.previous_value = self.value
                    self.value = value
                yield item
            self.finish()
        except GeneratorExit:
            self.finish(dirty=True)
            raise

    # --- Native accelerator protocol (used by speedups.FastBarIterator) ------
    # The C iterator counts items itself and calls back here only at gate
    # crossings, reusing the existing gate/redraw/calibration machinery so the
    # redraw cadence is identical to `_iter_python`.

    def _fast_begin(self) -> None:
        """Start the bar (draws 0%, sets `_next_update`/`_gate_enabled`)."""
        if self.start_time is None:
            self.start()

    def _fast_tick(self, value: int) -> None:
        """Handle a redraw crossing: redraw-if-due and recompute the gate."""
        self.update(value)

    def _fast_end(self) -> None:
        """Finish normally (draws 100%, restores streams) on exhaustion."""
        self.finish()

    def _fast_end_dirty(self) -> None:
        """Finish dirty on early break/exception (restores streams)."""
        self.finish(dirty=True)

    def __next__(self) -> typing.Any:
        """Draw 0% on the first call, else `update()` and return the item."""
        value: typing.Any
        try:
            if self._iterable is None:  # pragma: no cover
                value = self.value
            else:
                value = next(self._iterable)

            if self.start_time is None:
                self.start()
            else:
                self.update(self.value + 1)

        except StopIteration:
            self.finish()
            raise
        else:
            return value

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Finish the bar, marking it dirty if the with-block raised.

        `dirty=True` leaves `value` alone rather than jumping to 100%, so
        exiting via an exception doesn't falsely report completion.
        """
        self.finish(dirty=bool(exc_type))

    def __enter__(self) -> ProgressBar:
        """Return self, so the bar can be used as its own context manager."""
        return self

    # Create an alias so that Python 2.x won't complain about not being
    # an iterator.
    next = __next__

    def __iadd__(self, value: NumberT) -> ProgressBar:
        """Update the ProgressBar by adding a new value."""
        return self.increment(value)

    def increment(
        self, value: NumberT = 1, *args: typing.Any, **kwargs: typing.Any
    ) -> ProgressBar:
        """Advance `value` by `value` (default 1), then `update()`."""
        self.update(self.value + value, *args, **kwargs)
        return self

    def _needs_update(self) -> bool:
        """Return whether the ProgressBar should redraw the line."""
        if self.paused:
            return False
        delta = timeit.default_timer() - self._last_update_timer
        if delta < self.min_poll_interval:
            # Prevent updating too often
            return False
        elif self.poll_interval and delta > self.poll_interval:
            # Needs to redraw timers and animations
            return True
        elif self.max_value is base.UnknownLength:
            # There's no terminal-width threshold to compute for an unknown
            # length, so redraw whenever the value advanced (still rate
            # limited by the min_poll_interval check above)
            return self.value != self._last_drawn_value

        # Update if the value increment is large enough to add more bars
        # to the progressbar (according to the current terminal width).
        # While the state is incomplete -- nothing drawn yet, no usable
        # terminal width, no (nonzero) max value -- there is no width
        # threshold to compute and no redraw is due. Those guards mirror
        # what a `suppress(Exception)` used to swallow here. Anything else
        # failing in this math is a real bug and should propagate instead
        # of silently stopping redraws.
        if (
            self.value is not None
            and self._last_drawn_value is not None
            and self.term_width
            and self.max_value
        ):
            divisor: float = self.max_value / self.term_width  # type: ignore
            value_divisor = self.value // divisor
            pvalue_divisor = self._last_drawn_value // divisor
            if value_divisor != pvalue_divisor:
                return True
        # No need to redraw yet
        return False

    def _gate_skips(
        self, value: ValueT, force: bool, variables_changed: bool
    ) -> bool:
        """Whether the fast-path gate should skip this update() call entirely.

        Only skips while enabled, never for forced draws, variable changes,
        or a `None` (tick) value, and only while the value is still below the
        `_next_update` threshold.
        """
        return (
            self._gate_enabled
            and not force
            and not variables_changed
            and value is not None
            and self.value < self._next_update
        )

    def _draw_and_recalibrate(
        self, value: ValueT, variables_changed: bool, force: bool
    ) -> None:
        """Redraw if due, then resize the gate's next-update threshold.

        On a redraw, `_gate_step` is calibrated to ~one `min_poll_interval`
        window of iterations, measured from the value/time elapsed since the
        previous redraw (snapshotted here before the draw overwrites
        `_last_drawn_value`/`_last_update_timer`, so the gate needs no extra
        copies of those quantities). If we passed the threshold but no redraw
        was due (the loop sped up), back off by doubling the step.
        """
        if self._needs_update() or variables_changed or force:
            prev_value = self._last_drawn_value
            prev_timer = self._last_update_timer
            try:
                self._update_parents(value)  # _mark_update refreshes timer
            finally:
                # `_last_drawn_value` is the value at the last *redraw* (the
                # pixel reference for `_needs_update`). Set in finally so it
                # advances even if a draw raised.
                self._last_drawn_value = self.value
            if self._gate_enabled:
                interval = self._last_update_timer - prev_timer
                if (
                    prev_value is not None
                    and interval > 0
                    and self.value > prev_value
                ):
                    self._gate_step = max(
                        1,
                        int(
                            (self.value - prev_value)
                            * self.min_poll_interval
                            / interval
                        ),
                    )
                self._next_update = self.value + self._gate_step
        elif self._gate_enabled and value is not None:
            self._gate_step = max(1, self._gate_step * 2)
            self._next_update = self.value + self._gate_step

    def update(
        self, value: ValueT = None, force: bool = False, **kwargs: typing.Any
    ) -> None:
        """Update the bar to `value` and redraw if the gate allows it.

        The redraw is skipped unless `force` is set, a `variables=`
        value changed, or `_needs_update()` decides enough
        time/progress has passed (see
        :doc:`/explanation/rendering-and-the-update-gate`). Widget
        variables can be updated by keyword:
        `bar.update(my_var='value')`.

        Args:
            value: The new progress value. `None` leaves it unchanged.
            force: Redraw regardless of the update gate.
            **kwargs: Widget variable updates, applied to
                `self.variables`.
        """
        if self.start_time is None:
            self.start()

        # `isinstance(value, (int, float))` already excludes both `None` and
        # the `UnknownLength` sentinel (a class, not a numeric instance), so
        # the earlier explicit `is not None`/`is not UnknownLength` clauses
        # were redundant.
        if isinstance(value, (int, float)):
            if self.max_value is base.UnknownLength:
                # Can't compare against unknown lengths so just update
                pass
            elif self.min_value > value:  # type: ignore
                raise ValueError(
                    f'Value {value} is too small. Should be '
                    f'between {self.min_value} and {self.max_value}',
                )
            elif self.max_value < value:  # type: ignore
                if self.max_error:
                    raise ValueError(
                        f'Value {value} is too large. Should be between '
                        f'{self.min_value} and {self.max_value}',
                    )
                else:
                    value = typing.cast(NumberT, self.max_value)

            # `previous_value` keeps its original public meaning: the value
            # before this update() call. The gate uses a separate private
            # `_last_drawn_value` (set on redraw) for its pixel check.
            self.previous_value = self.value
            self.value = value

        # Save the updated values for dynamic messages (skip the call and the
        # empty-dict iteration on the common no-kwargs path).
        variables_changed = self._update_variables(kwargs) if kwargs else False

        if self._gate_skips(value, force, variables_changed):
            return

        self._draw_and_recalibrate(value, variables_changed, force)

    def _update_variables(self, kwargs: dict[str, typing.Any]) -> bool:
        """Apply changed `kwargs` to `self.variables`, returning if changed.

        Raises:
            TypeError: `kwargs` contains a name not already present in
                `self.variables`.
        """
        variables_changed = False
        for key, value_ in kwargs.items():
            if key not in self.variables:
                raise TypeError(
                    'update() got an unexpected variable name as argument '
                    f'{key!r}',
                )
            elif self.variables[key] != value_:
                self.variables[key] = kwargs[key]
                variables_changed = True
        return variables_changed

    def _mark_update(self) -> None:
        """Stamp the wall-clock and perf-counter time of the current redraw.

        ``_last_update_timer`` feeds the poll-interval gate and cadence
        calibration, ``_last_update_time`` backs the public
        ``last_update_time`` read by timer/ETA widgets. Kept out of
        :py:meth:`data` so that method stays a pure snapshot.
        """
        self._last_update_time = time.time()
        self._last_update_timer = timeit.default_timer()

    def _update_parents(self, value: ValueT) -> None:
        """Stamp the redraw time and dispatch the cooperative `update()`.

        Stamps before formatting widgets so `data()`/`last_update_time`
        reflect this redraw and `_draw_and_recalibrate`'s interval
        calculation (which snapshots `_last_update_timer` before this call
        and reads it again afterwards) measures up to this draw.
        """
        self.updates += 1
        self._mark_update()
        # Cooperative dispatch through the MRO
        # (StdRedirectMixin -> DefaultFdMixin -> ProgressBarMixinBase). The
        # `value` is passed by keyword so the intermediate `*args, **kwargs`
        # and `value=None` signatures interoperate.
        super().update(value=value)  # type: ignore

        # Only flush if something was actually written
        self.fd.flush()

    def start(
        self,
        max_value: NumberT | None = None,
        init: bool = True,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> ProgressBar:
        """Start measuring time, print the bar at 0%, and return `self`.

        Returning `self` allows chaining, as in the example below.

        Args:
            max_value: The maximum value of the progressbar.
            init: (Re)Initialize the progressbar, this is useful if you
                wish to reuse the same progressbar but can be disabled if
                data needs to be persisted between runs.
            *args: Accepted for signature compatibility with subclasses
                that override `start()` and forward via
                `super().start(*args, **kwargs)`. Not used here.
            **kwargs: Same as `*args` -- accepted but not used here.

        >>> pbar = ProgressBar().start()
        >>> for i in range(100):
        ...     # do something
        ...     pbar.update(i + 1)
        >>> pbar.finish()
        """
        if init:
            self.init()

        # Prevent multiple starts
        if self.start_time is not None:  # pragma: no cover
            return self

        if max_value is not None:
            self.max_value = max_value

        if self.max_value is None:
            self.max_value = self._DEFAULT_MAXVAL

        # Constructing the default widgets is only done when we know
        # max_value
        if not self.widgets:
            self.widgets = self.default_widgets()
        if self._auto_postfix and not self._auto_postfix_added:
            self.widgets.append(_load_widgets().Postfix())
            self._auto_postfix_added = True

        self._init_prefix()
        self._init_suffix()
        self._calculate_poll_interval()
        if (
            os.environ.get('PROGRESSBAR_DISABLE_FASTPATH')
            or not self.min_poll_interval
        ):
            self._gate_enabled = False

        try:
            self._verify_max_value()

            # Timing state must be populated before `_started` becomes
            # observable: a concurrent reader (MultiBar's render thread) that
            # sees `started()` True calls `update(force=True)`, and `update()`
            # re-enters `start()` whenever `start_time` is still None --
            # running the stream-capturing path twice.
            now = datetime.now()
            self.start_time = self.initial_start_time or now
            self.last_update_time = now
            self._last_update_timer = timeit.default_timer()

            # Cooperative dispatch through the MRO
            # (StdRedirectMixin -> DefaultFdMixin -> ProgressBarMixinBase);
            # ResizableMixin/ProgressBarBase define no `start` and are
            # skipped. This runs *after* all widget/state setup so that
            # `_started` (set by ProgressBarMixinBase.start) only becomes
            # observable once `widgets` is fully populated. Otherwise a
            # concurrent reader (e.g. MultiBar's render thread) could see
            # `started()` True with an empty widget list and crash in
            # `_label_bar`'s `assert bar.widgets`. The 0% draw below still
            # happens at the same point, after stream/console setup.
            super().start(max_value=max_value)

            self.update(self.min_value, force=True)
        except Exception:
            # A failed start must not leak global stream-wrapping state
            # (registered listeners, redirected stdout/stderr): run the
            # finish chain suppressed and re-raise the original error.
            with contextlib.suppress(Exception):
                super().finish(end='')
            raise

        return self

    def _init_suffix(self) -> None:
        """Append `suffix` as a widget once, then clear it.

        Clearing after applying means a later `start(init=False)` on the
        same bar won't re-append it.
        """
        if self.suffix:
            widgets = _load_widgets()

            self.widgets.append(
                widgets.FormatLabel(self.suffix, new_style=True),
            )
            self.suffix = None

    def _init_prefix(self) -> None:
        """Insert `prefix` as a widget once, then clear it.

        Clearing after applying means a later `start(init=False)` on the
        same bar won't re-insert it.
        """
        if self.prefix:
            widgets = _load_widgets()

            self.widgets.insert(
                0,
                widgets.FormatLabel(self.prefix, new_style=True),
            )
            self.prefix = None

    def _verify_max_value(self) -> None:
        """Raise if `max_value` is a negative number."""
        if (
            self.max_value is not base.UnknownLength
            and self.max_value is not None
            and self.max_value < 0  # type: ignore
        ):
            raise ValueError(f'max_value out of range, got {self.max_value!r}')

    def _calculate_poll_interval(self) -> None:
        """Derive `poll_interval` from any widget's `INTERVAL` attribute.

        Timer-like widgets (e.g. an animation) declare `INTERVAL`. The
        smallest one seen wins, so the bar redraws often enough to keep
        every such widget visibly moving.
        """
        self.num_intervals = max(100, self.term_width)
        for widget in self.widgets:
            interval: int | float | None = utils.deltas_to_seconds(
                getattr(widget, 'INTERVAL', None),
                default=None,
            )
            if interval is not None:
                self.poll_interval = min(
                    self.poll_interval or interval,
                    interval,
                )

    def finish(self, end: str = '\n', dirty: bool = False) -> None:
        """Put the ProgressBar in the finished state.

        Also flushes and disables output buffering if this was the last
        progressbar running.

        Args:
            end: The string to end the progressbar with, defaults to a
                newline.
            dirty: When True the progressbar kept the current state and
                won't be set to 100 percent.
        """
        if self._finished:
            # Finishing twice would corrupt the global stream-wrapping
            # state, so extra calls are no-ops
            return

        try:
            if not dirty:
                self.end_time = datetime.now()
                self.update(self.max_value, force=True)
        finally:
            # Run the finish chain even when the final render raises, so a
            # failing widget cannot leak the global stream-wrapping state.
            # Cooperative dispatch through the MRO
            # (StdRedirectMixin -> DefaultFdMixin -> ResizableMixin ->
            # ProgressBarMixinBase). Ordering note: the SIGWINCH uninstall in
            # ResizableMixin.finish now runs *before* the stream unwrap in
            # StdRedirectMixin.finish (previously it ran after). The two
            # subsystems are independent, so the observable result is
            # unchanged.
            super().finish(end=end)

    @property
    def currval(self) -> NumberT:
        """Legacy alias for `value`, kept progressbar-2 compatible."""
        warnings.warn(
            'The usage of `currval` is deprecated, please use `value` instead',
            DeprecationWarning,
            stacklevel=1,
        )
        return self.value


class DataTransferBar(ProgressBar):
    """A progress bar with sensible defaults for downloads etc.

    This assumes that the values its given are numbers of bytes.
    """

    def default_widgets(self) -> list[typing.Any]:
        """Build byte-oriented widgets: `DataSize` instead of ETA text."""
        widgets = _load_widgets()

        if self.max_value:
            return [
                widgets.Percentage(),
                ' of ',
                widgets.DataSize('max_value'),
                ' ',
                widgets.Bar(),
                ' ',
                widgets.Timer(),
                ' ',
                widgets.SmoothingETA(),
            ]
        else:
            return [
                widgets.AnimatedMarker(),
                ' ',
                widgets.DataSize(),
                ' ',
                widgets.Timer(),
            ]


class NullBar(ProgressBar):
    """Progress bar that does absolutely nothing.

    Useful for single verbosity flags, where the same call sites can
    unconditionally drive a bar whether or not it should render.
    """

    def start(self, *args: typing.Any, **kwargs: typing.Any) -> ProgressBar:
        """Do nothing and return self."""
        return self

    def update(self, *args: typing.Any, **kwargs: typing.Any) -> ProgressBar:
        """Do nothing and return self."""
        return self

    def finish(self, *args: typing.Any, **kwargs: typing.Any) -> ProgressBar:
        """Do nothing and return self."""
        return self
