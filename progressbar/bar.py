from __future__ import division, absolute_import, with_statement
import os
import sys
import math
import fcntl
import shutil
import termios
import array
import signal
import warnings
from datetime import datetime, timedelta
import collections

from . import widgets
from . import six
from . import utils
from . import base


class ProgressBarMixinBase(object):
    def __init__(self, **kwargs):
        pass

    def start(self):
        pass

    def update(self, value=None):
        pass

    def finish(self):  # pragma: no cover
        pass


class ProgressBarBase(collections.Iterable, ProgressBarMixinBase):
    pass


class DefaultFdMixin(ProgressBarMixinBase):
    def __init__(self, fd=sys.stderr, **kwargs):
        self.fd = fd
        super(DefaultFdMixin, self).__init__(**kwargs)

    def update(self, *args, **kwargs):
        super(DefaultFdMixin, self).update(*args, **kwargs)
        self.fd.write('\r' + self._format_line())

    def finish(self, *args, **kwargs):  # pragma: no cover
        super(DefaultFdMixin, self).finish(*args, **kwargs)
        self.fd.write('\n')


class ResizableMixin(DefaultFdMixin):
    _DEFAULT_TERMWIDTH = 80
    _DEFAULT_TERMHEIGHT = 25

    def __init__(self, term_width=_DEFAULT_TERMWIDTH, **kwargs):
        super(ResizableMixin, self).__init__(**kwargs)

        self.signal_set = False
        if term_width is not None:
            self.term_width = term_width
        else:
            try:
                self._handle_resize()
                signal.signal(signal.SIGWINCH, self._handle_resize)
                self.signal_set = True
            except (SystemExit, KeyboardInterrupt):  # pragma: no cover
                raise
            except:  # pragma: no cover
                raise
                self.term_width = self._env_size()

    def _env_size(self):
        'Tries to find the term_width from the environment.'

        return int(os.environ.get('COLUMNS', self._DEFAULT_TERMWIDTH)) - 1

    def _handle_resize(self, signum=None, frame=None):
        'Tries to catch resize signals sent from the terminal.'

        if six.PY3:  # pragma: no cover
            h, w = shutil.get_terminal_size(
                (self._DEFAULT_TERMWIDTH, self._DEFAULT_TERMHEIGHT))
        else:  # pragma: no cover
            size = fcntl.ioctl(self.fd, termios.TIOCGWINSZ, '\0' * 8)
            h, w = array.array('h', size)[:2]
        self.term_width = w

    def finish(self):  # pragma: no cover
        if self.signal_set:
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)


class StdRedirectMixin(DefaultFdMixin):
    def __init__(self, redirect_stderr=False, redirect_stdout=False, **kwargs):
        super(StdRedirectMixin, self).__init__(**kwargs)
        self.redirect_stderr = redirect_stderr
        self.redirect_stdout = redirect_stdout

        if self.redirect_stderr:
            self._stderr = sys.stderr
            sys.stderr = six.StringIO()

        if self.redirect_stdout:
            self._stdout = sys.stdout
            sys.stdout = six.StringIO()

    def update(self, value=None):
        super(StdRedirectMixin, self).update(value=value)

        if self.redirect_stderr and sys.stderr.tell():
            self.fd.write('\r' + ' ' * self.term_width + '\r')
            self._stderr.write(sys.stderr.getvalue())
            self._stderr.flush()
            sys.stderr = six.StringIO()

        if self.redirect_stdout and sys.stdout.tell():
            self.fd.write('\r' + ' ' * self.term_width + '\r')
            self._stdout.write(sys.stdout.getvalue())
            self._stdout.flush()
            sys.stdout = six.StringIO()

    def finish(self):
        super(StdRedirectMixin, self).finish()

        if self.redirect_stderr:
            self._stderr.write(sys.stderr.getvalue())
            sys.stderr = self._stderr

        if self.redirect_stdout:
            self._stdout.write(sys.stdout.getvalue())
            sys.stdout = self._stdout


class ProgressBar(StdRedirectMixin, ResizableMixin, ProgressBarBase):

    '''The ProgressBar class which updates and prints the bar.

    A common way of using it is like:

    >>> progress = ProgressBar().start()
    >>> for i in range(100):
    ...     progress.update(i+1)
    ...     # do something
    ...
    >>> progress.finish()

    You can also use a ProgressBar as an iterator:

    >>> progress = ProgressBar()
    >>> some_iterable = range(100)
    >>> for i in progress(some_iterable):
    ...     # do something
    ...     pass
    ...

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

    Useful methods and attributes include (Public API):
     - value: current progress (min_value <= value <= max_value)
     - max_value: maximum (and final) value
     - finished: True if the bar has finished (reached 100%)
     - start_time: the time when start() method of ProgressBar was called
     - seconds_elapsed: seconds elapsed since start_time and last call to
                        update
    '''

    _DEFAULT_MAXVAL = 100

    def __init__(self, min_value=0, max_value=None, widgets=None,
                 left_justify=True, initial_value=0, poll_interval=None,
                 **kwargs):
        '''Initializes a progress bar with sane defaults'''
        super(ProgressBar, self).__init__(**kwargs)
        if not max_value and kwargs.get('maxval'):
            warnings.warn('The usage of `maxval` is deprecated, please use '
                          '`max_value` instead', DeprecationWarning)
            max_value = kwargs.get('maxval')

        if not poll_interval and kwargs.get('poll'):
            warnings.warn('The usage of `poll` is deprecated, please use '
                          '`poll_interval` instead', DeprecationWarning)
            poll_interval = kwargs.get('poll')

        if max_value:
            if min_value > max_value:
                raise ValueError('Max value needs to be bigger than the min '
                                 'value')
        self.min_value = min_value
        self.max_value = max_value
        self.widgets = widgets or self.default_widgets()
        self.left_justify = left_justify

        self._iterable = None
        self.previous_value = None
        self.value = initial_value
        self.last_update_time = None
        self.start_time = None
        self.updates = 0
        self.end_time = None
        self.extra = dict()

        if poll_interval and isinstance(poll_interval, (int, float)):
            poll_interval = timedelta(seconds=poll_interval)

        self.poll_interval = poll_interval
        for widget in self.widgets:
            interval = getattr(widget, 'INTERVAL', None)
            if interval is not None:
                self.poll_interval = min(
                    self.poll_interval or interval,
                    interval,
                )

    @property
    def percentage(self):
        '''Return current percentage, returns None if no max_value is given

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
        '''
        if self.max_value is None or self.max_value is base.UnknownLength:
            return None
        elif self.max_value:
            todo = self.value - self.min_value
            total = self.max_value - self.min_value
            percentage = todo / total
        else:
            percentage = 1

        return percentage * 100

    def data(self):
        '''
        Variables available:
        - max_value: The maximum value (can be None with iterators)
        - value: The current value
        - total_seconds_elapsed: The seconds since the bar started
        - seconds_elapsed: The seconds since the bar started modulo 60
        - minutes_elapsed: The minutes since the bar started modulo 60
        - hours_elapsed: The hours since the bar started modulo 24
        - days_elapsed: The hours since the bar started
        - time_elapsed: Shortcut for HH:MM:SS time since the bar started
        including days
        - percentage: Percentage as a float
        '''
        self.last_update_time = datetime.now()
        elapsed = self.last_update_time - self.start_time
        # For Python 2.7 and higher we have _`timedelta.total_seconds`, but we
        # want to support older versions as well
        total_seconds_elapsed = utils.timedelta_to_seconds(elapsed)
        return dict(
            # The maximum value (can be None with iterators)
            max_value=self.max_value,
            # Start time of the widget
            start_time=self.start_time,
            # Last update time of the widget
            last_update_time=self.last_update_time,
            # End time of the widget
            end_time=self.end_time,
            # The current value
            value=self.value,
            # The previous value
            previous_value=self.previous_value,
            # The total update count
            updates=self.updates,
            # The seconds since the bar started
            total_seconds_elapsed=total_seconds_elapsed,
            # The seconds since the bar started modulo 60
            seconds_elapsed=(elapsed.seconds % 60) + elapsed.microseconds,
            # The minutes since the bar started modulo 60
            minutes_elapsed=(elapsed.seconds / 60) % 60,
            # The hours since the bar started modulo 24
            hours_elapsed=(elapsed.seconds / (60 * 60)) % 24,
            # The hours since the bar started
            days_elapsed=(elapsed.seconds / (60 * 60 * 24)),
            # The raw elapsed `datetime.timedelta` object
            time_elapsed=elapsed,
            # Percentage as a float or `None` if no max_value is available
            percentage=self.percentage,
        )

    def default_widgets(self):
        if self.max_value:
            return [
                widgets.Percentage(),
                ' (', widgets.SimpleProgress(), ')',
                ' ', widgets.Bar(),
                ' ', widgets.Timer(),
                ' ', widgets.AdaptiveETA(),
            ]
        else:
            return [
                widgets.Percentage(),
                ' (', widgets.SimpleProgress(), ')',
                ' ', widgets.Bar(),
                ' ', widgets.Timer(),
            ]

    def __call__(self, iterable, max_value=None):
        'Use a ProgressBar to iterate through an iterable'
        if max_value is None:
            try:
                self.max_value = len(iterable)
            except TypeError:
                if self.max_value is None:
                    self.max_value = base.UnknownLength
        else:
            self.max_value = max_value

        self._iterable = iter(iterable)
        return self

    def __iter__(self):
        return self

    def __next__(self):
        try:
            value = next(self._iterable)
            if self.start_time is None:
                self.start()
            else:
                self.update(self.value + 1)
            return value
        except StopIteration:
            self.finish()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        self.finish()

    def __enter__(self):
        return self.start()

    # Create an alias so that Python 2.x won't complain about not being
    # an iterator.
    next = __next__

    def __iadd__(self, value):
        'Updates the ProgressBar by adding a new value.'
        self.update(self.value + value)
        return self

    def _format_widgets(self):
        result = []
        expanding = []
        width = self.term_width
        data = self.data()

        for index, widget in enumerate(self.widgets):
            if isinstance(widget, widgets.AutoWidthWidgetBase):
                result.append(widget)
                expanding.insert(0, index)
            elif isinstance(widget, six.basestring):
                result.append(widget)
                width -= len(widget)
            else:
                widget_output = widget(self, data)
                result.append(widget_output)
                width -= len(widget_output)

        count = len(expanding)
        while expanding:
            portion = max(int(math.ceil(width * 1. / count)), 0)
            index = expanding.pop()
            widget = result[index]
            count -= 1

            widget_output = widget(self, data, portion)
            width -= len(widget_output)
            result[index] = widget_output

        return result

    def _format_line(self):
        'Joins the widgets and justifies the line'

        widgets = ''.join(self._format_widgets())

        if self.left_justify:
            return widgets.ljust(self.term_width)
        else:
            return widgets.rjust(self.term_width)

    def _needs_update(self):
        'Returns whether the ProgressBar should redraw the line.'
        if self.value > self.next_update or self.end_time:
            return True

        elif self.poll_interval:
            delta = datetime.now() - self.last_update_time
            return delta > self.poll_interval

    def update(self, value=None):
        'Updates the ProgressBar to a new value.'
        if self.start_time is None:
            self.start()
            return self.update(value)

        if value is not None and value is not base.UnknownLength:
            if self.max_value is base.UnknownLength:
                # Can't compare against unknown lengths so just update
                pass
            elif self.min_value <= value <= self.max_value:
                # Correct value, let's accept
                pass
            else:
                raise ValueError(
                    'Value out of range, should be between %s and %s'
                    % (self.min_value, self.max_value))

            self.previous_value = self.value
            self.value = value

        if not self._needs_update():
            return

        self.updates += 1
        super(ProgressBar, self).update(value=value)

    def start(self, max_value=None):
        '''Starts measuring time, and prints the bar at 0%.

        It returns self so you can use it like this:

        >>> pbar = ProgressBar().start()
        >>> for i in range(100):
        ...    # do something
        ...    pbar.update(i+1)
        ...
        >>> pbar.finish()
        '''
        super(ProgressBar, self).start()

        self.max_value = max_value or self.max_value
        if self.max_value is None:
            self.max_value = self._DEFAULT_MAXVAL

        self.num_intervals = max(100, self.term_width)
        self.next_update = 0

        if self.max_value is not base.UnknownLength:
            if self.max_value < 0:
                raise ValueError('Value out of range')
            self.update_interval = self.max_value / self.num_intervals

        self.start_time = self.last_update_time = datetime.now()
        self.update(0)

        return self

    def finish(self):
        'Puts the ProgressBar bar in the finished state.'

        self.end_time = datetime.now()
        self.update(self.max_value)

        super(ProgressBar, self).finish()

