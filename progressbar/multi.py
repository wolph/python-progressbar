"""Render and manage multiple progress bars from a background thread.

:class:`MultiBar` is a ``dict[str, ProgressBar]``: adding a bar wires
it into a single daemon render thread that redraws every registered
bar in place, diffing each frame against the last one so only the
rows that changed are rewritten. See :class:`MultiBar` for the full
contract.
"""

from __future__ import annotations

import collections.abc
import enum
import importlib
import io
import itertools
import operator
import sys
import threading
import time
import timeit
import types
import typing
from datetime import timedelta

import python_utils

from . import bar, terminal
from .terminal import stream

# MultiBar renders full (widget) progress bars from background threads. Warm
# the widgets module now -- single-threaded, at module load, which only happens
# when MultiBar is actually used (this module is imported lazily), so the fast
# path and a bare ``import progressbar`` stay widgets-free. Pre-warming here
# means a child bar's first start() doesn't import widgets inside a render
# thread and race MultiBar._label_bar's ``assert bar.widgets``.
importlib.import_module('progressbar.widgets')

SortKeyFunc = collections.abc.Callable[[bar.ProgressBar], typing.Any]


class _Update(typing.Protocol):
    """Shape of the `update` closure `_render_bar` builds per call."""

    def __call__(self, force: bool = True, write: bool = True) -> str: ...


class SortKey(str, enum.Enum):
    """Sort keys for the MultiBar.

    This is a string enum, so you can use any
    progressbar attribute or property as a sort key.

    The multibar defaults to lazily rendering only the changed
    progressbars, so sorting by dynamic attributes such as `value` can
    trigger extra rendering with a small performance impact.
    """

    CREATED = 'index'
    LABEL = 'label'
    VALUE = 'value'
    PERCENTAGE = 'percentage'


class MultiBar(dict[str, bar.ProgressBar]):
    """Render and manage multiple progressbars from background threads.

    Adding a bar (`multibar[key] = progress`, see `__setitem__`) hands
    its rendering over to a single daemon thread started by
    `start`/`__enter__`. That thread redraws every bar in place by
    diffing each frame against the previous one (`render`) and moving
    the cursor between lines, rather than reprinting the whole block
    every time.

    On a clean context-manager exit the multibar waits for its render
    thread via :meth:`join`. By default (``join_timeout=None``) that wait
    is unbounded, so a bar that never finishes blocks the program forever.
    Pass ``join_timeout`` (seconds, or a :class:`datetime.timedelta`) to
    bound that wait: once it elapses any still-unfinished bars are
    abandoned and the render thread (a daemon) is left running so the
    program can exit. The default preserves the historical wait-forever
    behavior.

    Note:
        `fd` is resolved once, from the parameter default, at the time
        this module is first imported. Unlike a plain `ProgressBar`,
        `MultiBar` is a bare `dict` subclass with none of
        `DefaultFdMixin`'s construction-time `sys.stdout`/`sys.stderr`
        remapping, so replacing `sys.stderr` after import does not
        change where an already- or later-constructed `MultiBar`
        writes.

    Note:
        The render thread needs real OS threads. Under Pyodide,
        `Thread.start()` raises ``RuntimeError``, so `with
        MultiBar(...):` (which calls `start` from `__enter__`) fails
        before anything is rendered. Call `.render()` directly instead
        of using `.start()`/the context manager there.

    Args:
        bars: Initial bars to add, keyed the same way `multibar[key] =
            progress` would add them one at a time.
        fd: The stream to render to. See the frozen-default note above.
        prepend_label: Insert a label widget at the start of each bar's
            `widgets` the first time it's rendered.
        append_label: Like `prepend_label`, but appended at the end.
        label_format: The `str.format` template for that label widget,
            formatted with `label` as a keyword argument.
        initial_format: The template used for a bar that hasn't been
            started yet, formatted with `label`. If `None`, the
            multibar starts the bar itself and renders it normally
            instead of using a placeholder line.
        finished_format: The template used once a bar has finished,
            formatted with `label`. If `None`, the bar's own finished
            rendering is used instead.
        update_interval: Seconds the render thread sleeps between
            frames.
        show_initial: Whether a not-yet-started bar is rendered at all.
        show_finished: Whether a finished bar stays visible instead of
            being hidden (it is still tracked for `remove_finished`
            either way).
        remove_finished: How long a finished bar stays visible before
            being dropped from the multibar entirely.
        sort_key: A `ProgressBar` attribute or property name used to
            order rendered bars, unless `sort_keyfunc` is given.
        sort_reverse: Whether the sort order from `sort_key`/
            `sort_keyfunc` is reversed.
        sort_keyfunc: A custom key function overriding `sort_key`.
        join_timeout: See above.
        **progressbar_kwargs: Passed to `ProgressBar()` when a missing
            key is looked up and a bar is auto-created for it (see
            `__getitem__`).
    """

    fd: typing.TextIO
    _buffer: io.StringIO

    #: The format for the label to append/prepend to the progressbar
    label_format: str
    #: Automatically prepend the label to the progressbars
    prepend_label: bool
    #: Automatically append the label to the progressbars
    append_label: bool
    #: If `initial_format` is `None`, the progressbar rendering is used
    # which will *start* the progressbar. That means the progressbar will
    # have no knowledge of your data and will run as an infinite progressbar.
    initial_format: str | None
    #: If `finished_format` is `None`, the progressbar rendering is used.
    finished_format: str | None

    #: The multibar updates at a fixed interval regardless of the progressbar
    # updates
    update_interval: float
    remove_finished: float | None
    #: Seconds to wait for the render thread on a clean context-manager
    # exit before abandoning unfinished bars. `None` waits forever.
    join_timeout: float | None

    #: The kwargs passed to the progressbar constructor
    progressbar_kwargs: dict[str, typing.Any]

    #: The progressbar sorting key function
    sort_keyfunc: SortKeyFunc

    _previous_output: list[str]
    _finished_at: dict[bar.ProgressBar, float]
    _labeled: set[bar.ProgressBar]
    _print_lock: threading.RLock
    _thread: threading.Thread | None
    _thread_finished: threading.Event
    _thread_closed: threading.Event

    def __init__(
        self,
        bars: (
            collections.abc.Mapping[str, bar.ProgressBar]
            | collections.abc.Iterable[tuple[str, bar.ProgressBar]]
            | None
        ) = None,
        fd: typing.TextIO = sys.stderr,
        prepend_label: bool = True,
        append_label: bool = False,
        label_format: str = '{label:20.20} ',
        initial_format: str | None = '{label:20.20} Not yet started',
        finished_format: str | None = None,
        update_interval: float = 1 / 60.0,  # 60fps
        show_initial: bool = True,
        show_finished: bool = True,
        remove_finished: timedelta | float = timedelta(seconds=3600),
        sort_key: str | SortKey = SortKey.CREATED,
        sort_reverse: bool = True,
        sort_keyfunc: SortKeyFunc | None = None,
        *,
        join_timeout: timedelta | float | None = None,
        **progressbar_kwargs: typing.Any,
    ) -> None:
        """Initialize the multibar and add any initial `bars`."""
        self.fd = fd

        self.prepend_label = prepend_label
        self.append_label = append_label
        self.label_format = label_format
        self.initial_format = initial_format
        self.finished_format = finished_format

        self.update_interval = update_interval

        self.show_initial = show_initial
        self.show_finished = show_finished
        self.remove_finished = python_utils.delta_to_seconds_or_none(
            remove_finished,
        )
        self.join_timeout = python_utils.delta_to_seconds_or_none(
            join_timeout,
        )

        self.progressbar_kwargs = progressbar_kwargs

        if sort_keyfunc is None:
            sort_keyfunc = operator.attrgetter(sort_key)

        self.sort_keyfunc = sort_keyfunc
        self.sort_reverse = sort_reverse

        self._labeled = set()
        self._finished_at = {}
        self._previous_output = []
        self._buffer = io.StringIO()
        self._print_lock = threading.RLock()
        self._thread = None
        self._thread_finished = threading.Event()
        self._thread_closed = threading.Event()

        super().__init__()

        bar_items: typing.Iterable[tuple[str, bar.ProgressBar]]
        if bars is None:
            bar_items = ()
        elif isinstance(bars, collections.abc.Mapping):
            bar_items = typing.cast(
                typing.Iterable[tuple[str, bar.ProgressBar]],
                bars.items(),
            )
        else:
            bar_items = bars

        for key, progress in bar_items:
            self[key] = progress

    def __setitem__(self, key: str, bar: bar.ProgressBar) -> None:
        """Add `bar` to the multibar, rebinding it to draw through us.

        This is the whole integration contract between a standalone
        `ProgressBar` and the multibar -- everything below is mutating
        `bar` in place so its own draw path stops touching the
        terminal directly:

        - `bar.label` is forced to `key`, so lookups/sorting by label
          stay consistent with the dict key.
        - `bar.fd` is rebound to a `LastLineStream` writing through
          `self.fd` (unless it already is one for this multibar), so a
          redraw the bar triggers on its own is captured into that
          stream's `.line` instead of reaching the terminal -- the
          multibar's own `render` reads `.line` and places it.
        - `bar.print = self.print`, so a `print()` made through the bar
          routes through the multibar's cursor-aware printing instead
          of corrupting whichever line the bar or another bar is on.
        - `bar.paused` is set `True`: the render thread, not the bar,
          now decides when this bar redraws.
        - if `bar` was constructed directly and never went through
          `ProgressBar.__init__`'s indexing, `bar.index` is pulled
          from `bar._index_counter` here so it still sorts correctly
          by creation order under `SortKey.CREATED`.

        Args:
            key: The label and dict key to add/update `bar` under.
            bar: The progressbar to add, mutated as described above.
        """
        if bar.label != key or not key:  # pragma: no branch
            bar.label = key

        if not (
            isinstance(bar.fd, stream.LastLineStream)
            and bar.fd.stream is self.fd
        ):
            bar.fd = stream.LastLineStream(self.fd)

        bar.paused = True
        # `mypy` rejects assigning to a method, hence the ignore.
        bar.print = self.print  # type: ignore

        # Just in case someone is using a progressbar with a custom
        # constructor and forgot to call the super constructor
        if bar.index == -1:
            bar.index = next(
                bar._index_counter  # pyright: ignore[reportPrivateUsage]
            )

        super().__setitem__(key, bar)

    def __delitem__(self, key: str) -> None:
        """Remove a progressbar from the multibar."""
        bar_: bar.ProgressBar = self.pop(key)
        self._finished_at.pop(bar_, None)
        self._labeled.discard(bar_)

    def __getitem__(self, key: str) -> bar.ProgressBar:
        """Get (and create if needed) a progressbar from the multibar."""
        try:
            return super().__getitem__(key)
        except KeyError:
            progress = bar.ProgressBar(**self.progressbar_kwargs)
            self[key] = progress
            return progress

    def _label_bar(self, bar: bar.ProgressBar) -> None:
        """Insert the label widget(s) into `bar.widgets`, once per bar."""
        if bar in self._labeled:  # pragma: no branch
            return

        assert bar.widgets, 'Cannot prepend label to empty progressbar'

        if self.prepend_label:  # pragma: no branch
            self._labeled.add(bar)
            bar.widgets.insert(0, self.label_format.format(label=bar.label))

        if self.append_label:  # pragma: no branch
            self._labeled.add(bar)
            bar.widgets.append(self.label_format.format(label=bar.label))

    def render(self, flush: bool = True, force: bool = False) -> None:
        """Redraw every bar, only touching lines that actually changed.

        Builds one output line per visible bar (`_render_bar`) and
        diffs it against `_previous_output` -- the frame built by the
        previous call: lines whose text is unchanged are left alone,
        lines that changed are reprinted in place through
        `print(clear=False)` at their fixed offset, lines for bars
        that vanished since the last frame are cleared, and a blank
        line is appended to the buffer for each bar that's new since
        the last frame so it doesn't overwrite existing output.

        Args:
            flush: Whether to flush the buffered escape sequences to
                `fd` immediately after building this frame.
            force: Reprint every line even if its text is unchanged --
                used for the final render before the render thread
                stops, so a just-finished bar's finished-format is
                guaranteed to reach the screen.
        """
        now: float = timeit.default_timer()
        expired: float | None = (
            now - self.remove_finished if self.remove_finished else None
        )

        # sourcery skip: list-comprehension
        output: list[str] = []
        for bar_ in self.get_sorted_bars():
            if not bar_.started() and not self.show_initial:
                continue

            output.extend(
                iter(self._render_bar(bar_, expired=expired, now=now)),
            )

        with self._print_lock:
            # Clear the previous output if progressbars have been removed
            for i in range(len(output), len(self._previous_output)):
                self._buffer.write(
                    terminal.clear_line(i + 1),
                )  # pragma: no cover

            # Add empty lines to the end of the output if progressbars have
            # been added
            for _ in range(len(self._previous_output), len(output)):
                # Adding a new line so we don't overwrite previous output
                self._buffer.write('\n')

            for i, (previous, current) in enumerate(
                itertools.zip_longest(
                    self._previous_output,
                    output,
                    fillvalue='',
                ),
            ):
                if previous != current or force:  # pragma: no branch
                    self.print(
                        '\r' + current.strip(),
                        offset=i + 1,
                        end='',
                        clear=False,
                        flush=False,
                    )

            self._previous_output = output

            if flush:  # pragma: no branch
                self.flush()

    def _render_bar(
        self,
        bar_: bar.ProgressBar,
        now: float,
        expired: float | None,
    ) -> collections.abc.Iterable[str]:
        """Yield the rendered line(s) for one bar, by lifecycle state.

        Finished bars delegate to `_render_finished_bar` (0 or 1
        lines). A started bar is force-updated and yields its current
        line. A not-yet-started bar either yields `initial_format`
        as-is, or, if `initial_format` is `None`, is started and
        rendered immediately instead of showing a placeholder.

        Returns:
            The line(s) to place on this bar's row(s) of the frame.
        """

        def update(
            force: bool = True, write: bool = True
        ) -> str:  # pragma: no cover
            self._label_bar(bar_)
            bar_.update(force=force)
            if write:
                return typing.cast(stream.LastLineStream, bar_.fd).line
            else:
                return ''

        if bar_.finished():
            yield from self._render_finished_bar(bar_, now, expired, update)

        elif bar_.started():
            yield update()
        else:
            if self.initial_format is None:
                bar_.start()
                yield update()
            else:
                yield self.initial_format.format(label=bar_.label)

    def _render_finished_bar(
        self,
        bar_: bar.ProgressBar,
        now: float,
        expired: float | None,
        update: _Update,
    ) -> collections.abc.Iterable[str]:
        """Render a finished bar once, then expire or hide it as configured.

        The first time a bar is seen finished, `_finished_at` is
        stamped and the bar is force-updated once (without writing a
        line) so its widgets pick up the finished format. After that,
        a bar older than `remove_finished` is dropped from the
        multibar entirely, and a bar hidden by `show_finished=False`
        yields nothing.

        Returns:
            Zero lines (dropped or hidden) or one rendered line.
        """
        if bar_ not in self._finished_at:
            self._finished_at[bar_] = now
            # Force update to get the finished format
            update(write=False)

        if (
            self.remove_finished
            and expired is not None
            and expired >= self._finished_at[bar_]
        ):
            del self[bar_.label]
            return

        if not self.show_finished:
            return

        if bar_.finished():  # pragma: no branch
            if self.finished_format is None:
                yield update(force=False)
            else:  # pragma: no cover
                yield self.finished_format.format(label=bar_.label)

    def print(
        self,
        *args: typing.Any,
        end: str = '\n',
        offset: int | None = None,
        flush: bool = True,
        clear: bool = True,
        **kwargs: typing.Any,
    ) -> None:
        """Print above (or redraw one line within) the progressbar block.

        Moves the cursor up `offset` lines and writes `args` through
        the builtin `print`, then restores the cursor -- but does so
        two different ways depending on `clear`:

        - `clear=True` (the default: a genuine `print()` call made
          while bars are active): clears the target line first, then,
          because the new line permanently occupies a row and pushes
          everything below it down, clears to the end of the screen
          and re-emits the whole previous bar frame underneath, so the
          bars end up back on the lines below the new output.
        - `clear=False` (used internally by `render` to redraw a
          single bar's row in place): skips both clears and just moves
          the cursor to the next line after writing, since the caller
          already overwrote the existing line itself (by prefixing it
          with a carriage return) instead of inserting a new one, so
          nothing below it needs to move.

        Args:
            *args: Values to print, passed straight through to the
                builtin `print`.
            end: The string to append to the end of the output.
            offset: How many lines above the cursor's current position
                to move before writing. If `None`, defaults to the
                number of lines in the last rendered frame, i.e. print
                above all currently visible bars.
            flush: Whether to flush the buffered escape sequences to
                `fd` immediately.
            clear: Whether this is a genuine new line of output rather
                than an in-place bar redraw (see above).
            **kwargs: Additional keyword arguments passed to the
                builtin `print`.
        """
        with self._print_lock:
            if offset is None:
                offset = len(self._previous_output)

            if not clear:
                self._buffer.write(terminal.PREVIOUS_LINE(offset))

            if clear:
                self._buffer.write(terminal.PREVIOUS_LINE(offset))
                self._buffer.write(terminal.CLEAR_LINE_ALL())

            print(*args, **kwargs, file=self._buffer, end=end)

            if clear:
                self._buffer.write(terminal.CLEAR_SCREEN_TILL_END())
                for line in self._previous_output:
                    self._buffer.write(line.strip())
                    self._buffer.write('\n')

            else:
                self._buffer.write(terminal.NEXT_LINE(offset))

            if flush:
                self.flush()

    def flush(self) -> None:
        """Write the buffered escape sequences and text to `fd`.

        Runs under `_print_lock`, like `print`/`render`, so the fd
        write happens under the lock as well and concurrent
        `print()`/`render()` calls cannot interleave their output.
        """
        with self._print_lock:
            value = self._buffer.getvalue()
            self._buffer.seek(0)
            self._buffer.truncate(0)
            self.fd.write(value)
            self.fd.flush()

    def run(self, join: bool = True) -> None:
        """Render in a loop until stopped or every bar has finished.

        This is the render thread's target when started via `start`
        (which passes `join=False`). It can also be called directly to
        block the calling thread instead of backgrounding the loop.
        Each pass renders once and sleeps `update_interval`. Then, but
        only if `join` is true or `_thread_closed` has been set (i.e.
        `join`/`stop` was called), every current bar is checked in a
        `for`/`else`: finding an unfinished bar just breaks out and the
        loop continues, but running the `for` to completion means every
        bar is finished, so one last forced render is issued, to make
        sure the just-finished bars' finished-format actually reaches
        the screen, and the method returns. `stop` bypasses all of
        this by setting `_thread_finished` directly, which ends the
        loop on its next `while` check regardless of bar state.

        Args:
            join: Whether to return as soon as every current bar has
                finished, rather than only after `_thread_closed` is
                set. `start()` passes `False` so the background render
                thread keeps looping, picking up bars added after it
                started, until `join`/`stop` asks it to close.
        """
        while not self._thread_finished.is_set():  # pragma: no branch
            self.render()
            time.sleep(self.update_interval)

            if join or self._thread_closed.is_set():
                # If the thread is closed, we need to check if the progressbars
                # have finished. If they have, we can exit the loop
                for bar_ in list(self.values()):  # pragma: no cover
                    if not bar_.finished():
                        break
                else:
                    # Render one last time to make sure the progressbars are
                    # correctly finished
                    self.render(force=True)
                    return

    def start(self) -> None:
        """Start the daemon thread that renders this multibar.

        The thread runs `run(join=False)` (see there for the loop's
        exit conditions) and is a daemon so it never blocks interpreter
        exit on its own -- `__exit__`/`join`/`stop` are what make a
        clean shutdown actually wait for it.

        Not available under Pyodide, which has no real threads (see
        the class docstring).
        """
        assert not self._thread, 'Multibar already started'
        self._thread_finished.clear()
        self._thread_closed.clear()
        self._thread = threading.Thread(
            target=self.run,
            args=(False,),
            daemon=True,
        )
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        """Ask the render thread to close, then wait for it to exit.

        Sets `_thread_closed` so `run`'s loop starts checking whether
        every bar has finished, then blocks on `Thread.join`. Unlike
        `stop`, this does not force the loop to exit early -- if bars
        never finish, `timeout` (or forever, if `None`) is the only
        bound on the wait.

        Args:
            timeout: Seconds to wait for the thread, passed straight
                through to `threading.Thread.join`. `None` waits
                forever.
        """
        if self._thread is not None:
            self._thread_closed.set()
            self._thread.join(timeout=timeout)
            if not self._thread.is_alive():
                self._thread = None

    def stop(self, timeout: float | None = None) -> None:
        """Force the render thread to exit, then wait for it.

        Sets `_thread_finished`, which ends `run`'s loop on its next
        `while` check regardless of whether any bar has finished --
        unlike a plain `join()`, unfinished bars don't block this.

        Args:
            timeout: Seconds to wait for the thread, forwarded to
                `join`.
        """
        self._thread_finished.set()
        self.join(timeout=timeout)

    def get_sorted_bars(self) -> list[bar.ProgressBar]:
        """Return the current bars, ordered per `sort_keyfunc`.

        Returns:
            The bars sorted by `sort_keyfunc`, reversed if
            `sort_reverse`. The values are copied into a list first so
            a concurrent `__setitem__`/`__delitem__` from another
            thread (the multibar is a plain `dict`, not a thread-safe
            one) can't mutate it out from under the sort.
        """
        bars = list(self.values())
        return sorted(bars, key=self.sort_keyfunc, reverse=self.sort_reverse)

    def __enter__(self) -> MultiBar:
        """Start the render thread and return this multibar."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> bool | None:
        """Wind down the render thread on context-manager exit.

        On a clean exit (`exc_type is None`), waits for the render
        thread via `join(timeout=join_timeout)`. `join_timeout=None`
        (the default) waits forever, matching the historical behavior.
        If the timeout elapses with the thread still alive, `stop()`
        is called to explicitly signal it to shut down -- the thread is
        a daemon and would eventually die with the interpreter anyway,
        but leaving it running would mean it keeps re-rendering (and
        writing to `fd`) for as long as the process stays alive after
        the `with` block exits, rather than actually honoring the
        timeout the caller asked for.

        When an exception is propagating instead, waiting for
        unfinished bars would block forever for no benefit, so the
        thread is stopped immediately without waiting on
        `join_timeout`.
        """
        if exc_type is None:
            # Bound the wait so a never-finishing bar cannot hang a clean
            # exit. `join_timeout=None` keeps the historical forever-wait.
            self.join(timeout=self.join_timeout)
            if self._thread is not None:
                # The timeout elapsed with bars unfinished: signal the
                # render thread to shut down instead of leaving the daemon
                # looping (and writing) until interpreter exit.
                self.stop(timeout=self.update_interval)
        else:
            # Don't wait for unfinished progressbars when an exception is
            # propagating: that would block forever.
            self.stop()
