from __future__ import division, absolute_import, with_statement
import os
import sys
import math
import time
import fcntl
import termios
import array
import signal
from datetime import datetime
import collections
from . import widgets
from . import six


class UnknownLength(object):
    pass


class ProgressBarMixinBase(object):
    def __init__(self, **kwargs):
        super(ProgressBarMixinBase, self).__init__(**kwargs)

    def start(self):
        pass

    def update(self, value=None):
        pass

    def finish(self):
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

    def finish(self, *args, **kwargs):
        super(DefaultFdMixin, self).finish(*args, **kwargs)
        self.fd.write('\n')


class ResizableMixin(DefaultFdMixin):
    _DEFAULT_TERMSIZE = 80

    def __init__(self, term_width=_DEFAULT_TERMSIZE, **kwargs):
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

        return int(os.environ.get('COLUMNS', self._DEFAULT_TERMSIZE)) - 1

    def _handle_resize(self, signum=None, frame=None):
        'Tries to catch resize signals sent from the terminal.'

        size = fcntl.ioctl(self.fd, termios.TIOCGWINSZ, '\0' * 8)
        h, w = array.array('h', size)[:2]
        self.term_width = w

    def finish(self):
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
     - value: current progress (0 <= value <= max_value)
     - max_value: maximum (and final) value
     - finished: True if the bar has finished (reached 100%)
     - start_time: the time when start() method of ProgressBar was called
     - seconds_elapsed: seconds elapsed since start_time and last call to
                        update
     - percentage(): progress in percent [0..100]
    '''

    _DEFAULT_MAXVAL = 100

    def __init__(self, max_value=None, widgets=None, poll=0.1,
                 left_justify=True, **kwargs):
        '''Initializes a progress bar with sane defaults'''
        super(ProgressBar, self).__init__(**kwargs)

        if widgets is None:
            # Don't share widgets with any other progress bars
            widgets = self.default_widgets()

        self.max_value = max_value
        self.widgets = widgets
        self.left_justify = left_justify

        self.__iterable = None
        self._update_widgets()
        self.value = 0
        self.finished = False
        self.last_update_time = None
        self.poll = poll
        self.seconds_elapsed = 0
        self.start_time = None
        self.update_interval = 1

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
        elapsed = datetime.now() - self.start_time
        # For Python 2.7 and higher we have _`timedelta.total_seconds`, but we
        # want to support older versions as well
        total_seconds_elapsed = (elapsed.microseconds
                                 + (elapsed.seconds + elapsed.days * 24 * 3600)
                                 * 10**6
                                 / 10**6)

        if self.max_value is None:
            percentage = None
        elif self.max_value:
            percentage = self.value / self.max_value
        else:
            percentage = 1

        return dict(
            # The maximum value (can be None with iterators)
            max_value = self.max_value,
            # The current value
            value = self.value,
            # The seconds since the bar started
            total_seconds_elapsed = total_seconds_elapsed,
            # The seconds since the bar started modulo 60
            seconds_elapsed = (elapsed.seconds % 60) + elapsed.microseconds,
            # The minutes since the bar started modulo 60
            minutes_elapsed = (elapsed.seconds / 60) % 60,
            # The hours since the bar started modulo 24
            hours_elapsed = (elapsed.seconds / (60 * 60)) % 24,
            # The hours since the bar started
            days_elapsed = (elapsed.seconds / (60 * 60 * 24)),
            # The raw elapsed `datetime.timedelta` object
            time_elapsed = elapsed,
            # Percentage as a float or `None` if no max_value is available
            percentage = percentage,
        )

    def default_widgets(self):
        return [
            widgets.Percentage(),
            ' (', widgets.SimpleProgress(), ')',
            ' ', widgets.Bar(),
            ' ', widgets.Timer(),
            ' ', widgets.AdaptiveETA(),
        ]

    def __call__(self, iterable, max_value=None):
        'Use a ProgressBar to iterate through an iterable'
        if max_value is None:
            try:
                self.max_value = len(iterable)
            except:
                if self.max_value is None:
                    self.max_value = UnknownLength
        else:
            self.max_value = max_value

        self.__iterable = iter(iterable)
        return self

    def __iter__(self):
        return self

    def __next__(self):
        try:
            value = next(self.__iterable)
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

    def percentage(self):
        'Returns the progress as a percentage.'
        assert self.max_value is not UnknownLength, \
            'Need a max_value for a percentage'

        return self.value * 100.0 / (self.max_value or 1)

    percent = property(percentage)

    def _format_widgets(self):
        result = []
        expanding = []
        width = self.term_width
        data = self.data()

        for index, widget in enumerate(self.widgets):
            if isinstance(widget, widgets.AutoWidthWidgetBase):
                result.append(widget)
                expanding.insert(0, index)
            elif isinstance(widget, basestring):
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

    def _need_update(self):
        'Returns whether the ProgressBar should redraw the line.'
        if self.value >= self.next_update or self.finished:
            return True

        delta = time.time() - self.last_update_time
        return self._time_sensitive and delta > self.poll

    def _update_widgets(self):
        'Checks all widgets for the time sensitive bit'

        self._time_sensitive = any(getattr(w, 'TIME_SENSITIVE', False)
                                   for w in self.widgets)

    def update(self, value=None):
        'Updates the ProgressBar to a new value.'

        if value is not None and value is not UnknownLength:
            if (self.max_value is not UnknownLength
                    and not 0 <= value <= self.max_value
                    and not value < self.value):

                raise ValueError('Value out of range')

            self.value = value

        if self.start_time is None:
            self.start()
            self.update(value)
        if not self._need_update():
            return

        now = datetime.now()
        self.seconds_elapsed = now - self.start_time
        self.next_update = self.value + self.update_interval
        self.last_update_time = now
        super(ProgressBar, self).update(value=value)

    def start(self):
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

        if self.max_value is None:
            self.max_value = self._DEFAULT_MAXVAL

        self.num_intervals = max(100, self.term_width)
        self.next_update = 0

        if self.max_value is not UnknownLength:
            if self.max_value < 0:
                raise ValueError('Value out of range')
            self.update_interval = self.max_value / self.num_intervals

        self.start_time = self.last_update_time = datetime.now()
        self.update(0)

        return self

    def finish(self):
        'Puts the ProgressBar bar in the finished state.'

        self.finished = True
        self.update(self.max_value)

        super(ProgressBar, self).finish()

