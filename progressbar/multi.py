from __future__ import annotations

import enum
import io
import itertools
import operator
import sys
import threading
import time
import timeit
import typing
from datetime import timedelta

import python_utils

from . import bar, terminal
from .terminal import stream

SortKeyFunc = typing.Callable[[bar.ProgressBar], typing.Any]


class SortKey(str, enum.Enum):
    '''
    Sort keys for the MultiBar

    This is a string enum, so you can use any
    progressbar attribute or property as a sort key.

    Note that the multibar defaults to lazily rendering only the changed
    progressbars. This means that sorting by dynamic attributes such as
    `value` might result in more rendering which can have a small performance
    impact.
    '''

    CREATED = 'index'
    LABEL = 'label'
    VALUE = 'value'
    PERCENTAGE = 'percentage'


class MultiBar(dict[str, bar.ProgressBar]):
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

    #: The kwargs passed to the progressbar constructor
    progressbar_kwargs: typing.Dict[str, typing.Any]

    #: The progressbar sorting key function
    sort_keyfunc: SortKeyFunc

    _previous_output: list[str]
    _finished_at: dict[bar.ProgressBar, float]
    _labeled: set[bar.ProgressBar]
    _print_lock: threading.RLock = threading.RLock()
    _thread: threading.Thread | None = None
    _thread_finished: threading.Event = threading.Event()
    _thread_closed: threading.Event = threading.Event()

    def __init__(
        self,
        bars: typing.Iterable[tuple[str, bar.ProgressBar]] | None = None,
        fd=sys.stderr,
        prepend_label: bool = True,
        append_label: bool = False,
        label_format='{label:20.20} ',
        initial_format: str | None = '{label:20.20} Not yet started',
        finished_format: str | None = None,
        update_interval: float = 1 / 60.0,  # 60fps
        show_initial: bool = True,
        show_finished: bool = True,
        remove_finished: timedelta | float = timedelta(seconds=3600),
        sort_key: str | SortKey = SortKey.CREATED,
        sort_reverse: bool = True,
        sort_keyfunc: SortKeyFunc | None = None,
        **progressbar_kwargs,
    ):
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
            remove_finished
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

        super().__init__(bars or {})

    def __setitem__(self, key: str, value: bar.ProgressBar):
        '''Add a progressbar to the multibar'''
        if value.label != key:  # pragma: no branch
            value.label = key
            value.fd = stream.LastLineStream(self.fd)
            value.paused = True
            value.print = self.print

        # Just in case someone is using a progressbar with a custom
        # constructor and forgot to call the super constructor
        if value.index == -1:
            value.index = next(value._index_counter)

        super().__setitem__(key, value)

    def __delitem__(self, key):
        '''Remove a progressbar from the multibar'''
        super().__delitem__(key)
        self._finished_at.pop(key, None)
        self._labeled.discard(key)

    def __getitem__(self, item):
        '''Get (and create if needed) a progressbar from the multibar'''
        try:
            return super().__getitem__(item)
        except KeyError:
            progress = bar.ProgressBar(**self.progressbar_kwargs)
            self[item] = progress
            return progress

    def _label_bar(self, bar: bar.ProgressBar):
        if bar in self._labeled:  # pragma: no branch
            return

        assert bar.widgets, 'Cannot prepend label to empty progressbar'
        self._labeled.add(bar)

        if self.prepend_label:  # pragma: no branch
            bar.widgets.insert(0, self.label_format.format(label=bar.label))

        if self.append_label and bar not in self._labeled:  # pragma: no branch
            bar.widgets.append(self.label_format.format(label=bar.label))

    def render(self, flush: bool = True, force: bool = False):
        '''Render the multibar to the given stream'''
        now = timeit.default_timer()
        expired = now - self.remove_finished if self.remove_finished else None
        output = []
        for bar_ in self.get_sorted_bars():
            if not bar_.started() and not self.show_initial:
                continue

            def update(force=True, write=True):
                self._label_bar(bar_)
                bar_.update(force=force)
                if write:
                    output.append(bar_.fd.line)

            if bar_.finished():
                if bar_ not in self._finished_at:
                    self._finished_at[bar_] = now
                    # Force update to get the finished format
                    update(write=False)

                if self.remove_finished:
                    if expired >= self._finished_at[bar_]:
                        del self[bar_.label]
                        continue

                if not self.show_finished:
                    continue

            if bar_.finished():
                if self.finished_format is None:
                    update(force=False)
                else:
                    output.append(
                        self.finished_format.format(
                            label=bar_.label
                        )
                    )
            elif bar_.started():
                update()
            else:
                if self.initial_format is None:
                    bar_.start()
                    update()
                else:
                    output.append(self.initial_format.format(label=bar_.label))

        with self._print_lock:
            # Clear the previous output if progressbars have been removed
            for i in range(len(output), len(self._previous_output)):
                self._buffer.write(terminal.clear_line(i + 1))

            # Add empty lines to the end of the output if progressbars have
            # been added
            for i in range(len(self._previous_output), len(output)):
                # Adding a new line so we don't overwrite previous output
                self._buffer.write('\n')

            for i, (previous, current) in enumerate(
                itertools.zip_longest(
                    self._previous_output, output, fillvalue=''
                )
            ):
                if previous != current or force:
                    self.print(
                        '\r' + current.strip(),
                        offset=i + 1,
                        end='',
                        clear=False,
                        flush=False,
                    )

            self._previous_output = output

            if flush:
                self.flush()

    def print(
        self, *args, end='\n', offset=None, flush=True, clear=True, **kwargs
    ):
        '''
        Print to the progressbar stream without overwriting the progressbars

        Args:
            end: The string to append to the end of the output
            offset: The number of lines to offset the output by. If None, the
                output will be printed above the progressbars
            flush: Whether to flush the output to the stream
            clear: If True, the line will be cleared before printing.
            **kwargs: Additional keyword arguments to pass to print
        '''
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

    def flush(self):
        self.fd.write(self._buffer.getvalue())
        self._buffer.truncate(0)
        self.fd.flush()

    def run(self, join=True):
        '''
        Start the multibar render loop and run the progressbars until they
        have force _thread_finished
        '''
        while not self._thread_finished.is_set():
            self.render()
            time.sleep(self.update_interval)

            if join or self._thread_closed.is_set():
                # If the thread is closed, we need to check if force
                # progressbars
                # have finished. If they have, we can exit the loop
                for bar_ in self.values():
                    if not bar_.finished():
                        break
                else:
                    # Render one last time to make sure the progressbars are
                    # correctly finished
                    self.render(force=True)
                    return

    def start(self):
        assert not self._thread, 'Multibar already started'
        self._thread_closed.set()
        self._thread = threading.Thread(target=self.run, args=(False,))
        self._thread.start()

    def join(self, timeout=None):
        if self._thread is not None:
            self._thread_closed.set()
            self._thread.join(timeout=timeout)
            self._thread = None

    def stop(self, timeout: float | None = None):
        self._thread_finished.set()
        self.join(timeout=timeout)

    def get_sorted_bars(self):
        return sorted(
            self.values(),
            key=self.sort_keyfunc,
            reverse=self.sort_reverse,
        )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.join()
