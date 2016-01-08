from __future__ import division, absolute_import, with_statement
from __future__ import print_function

import datetime
import abc
import sys
import pprint

from . import utils
from . import six
from . import base


class FormatWidgetMixin(object):
    '''Mixin to format widgets using a formatstring

    Variables available:
     - max_value: The maximum value (can be None with iterators)
     - value: The current value
     - total_seconds_elapsed: The seconds since the bar started
     - seconds_elapsed: The seconds since the bar started modulo 60
     - minutes_elapsed: The minutes since the bar started modulo 60
     - hours_elapsed: The hours since the bar started modulo 24
     - days_elapsed: The hours since the bar started
     - time_elapsed: Shortcut for HH:MM:SS time since the bar started including
       days
     - percentage: Percentage as a float
    '''
    required_values = []

    def __init__(self, format, **kwargs):
        self.format = format

    def __call__(self, progress, data, format=None):
        '''Formats the widget into a string'''
        try:
            return (format or self.format) % data
        except (TypeError, KeyError):
            print('Error while formatting %r' % self.format, file=sys.stderr)
            pprint.pprint(data, stream=sys.stderr)
            raise


class WidthWidgetMixin(object):
    '''Mixing to make sure widgets are only visible if the screen is within a
    specified size range so the progressbar fits on both large and small
    screens..
    '''
    def __init__(self, min_width=None, max_width=None, **kwargs):
        self.min_width = min_width
        self.max_width = max_width

    def check_size(self, progress):
        if self.min_width and self.min_width > progress.term_width:
            return False
        elif self.max_width and self.max_width < progress.term_width:
            return False
        else:
            return True


class WidgetBase(object):
    __metaclass__ = abc.ABCMeta
    '''The base class for all widgets

    The ProgressBar will call the widget's update value when the widget should
    be updated. The widget's size may change between calls, but the widget may
    display incorrectly if the size changes drastically and repeatedly.

    The boolean TIME_SENSITIVE informs the ProgressBar that it should be
    updated more often because it is time sensitive.

    WARNING: Widgets can be shared between multiple progressbars so any state
    information specific to a progressbar should be stored within the
    progressbar instead of the widget.
    '''
    INTERVAL = None

    def __init__(self, **kwargs):
        pass

    @abc.abstractmethod
    def __call__(self, progress, data):
        '''Updates the widget.

        progress - a reference to the calling ProgressBar
        '''


class AutoWidthWidgetBase(WidgetBase):
    '''The base class for all variable width widgets.

    This widget is much like the \\hfill command in TeX, it will expand to
    fill the line. You can use more than one in the same line, and they will
    all have the same width, and together will fill the line.
    '''

    @abc.abstractmethod
    def __call__(self, progress, data, width):
        '''Updates the widget providing the total width the widget must fill.

        progress - a reference to the calling ProgressBar
        width - The total width the widget must fill
        '''


class TimeSensitiveWidgetBase(WidgetBase):
    '''The base class for all time sensitive widgets.

    Some widgets like timers would become out of date unless updated at least
    every `INTERVAL`
    '''
    INTERVAL = datetime.timedelta(seconds=1)


def _format_time(seconds):
    '''Formats time as the string "HH:MM:SS".'''
    return str(datetime.timedelta(seconds=int(seconds)))


class FormatLabel(FormatWidgetMixin, WidthWidgetMixin):
    '''Displays a formatted label

    >>> label = FormatLabel('%(value)s', min_width=5, max_width=10)
    >>> class Progress(object):
    ...     pass

    >>> Progress.term_width = 0
    >>> label(Progress, dict(value='test'))
    ''

    >>> Progress.term_width = 5
    >>> label(Progress, dict(value='test'))
    'test'

    >>> Progress.term_width = 10
    >>> label(Progress, dict(value='test'))
    'test'

    >>> Progress.term_width = 11
    >>> label(Progress, dict(value='test'))
    ''
    '''

    mapping = {
        'finished': ('end_time', None),
        'last_update': ('last_update_time', None),
        'max': ('max_value', None),
        'seconds': ('seconds_elapsed', None),
        'start': ('start_time', None),
        'elapsed': ('total_seconds_elapsed', _format_time),
        'value': ('value', None),
    }

    def __init__(self, format, **kwargs):
        FormatWidgetMixin.__init__(self, format=format, **kwargs)
        WidthWidgetMixin.__init__(self, **kwargs)

    def __call__(self, progress, data):
        if not self.check_size(progress):
            return ''

        for name, (key, transform) in self.mapping.items():
            try:
                if transform is None:
                    data[name] = data[key]
                else:
                    data[name] = transform(data[key])
            except:  # pragma: no cover
                pass

        return FormatWidgetMixin.__call__(self, progress, data)


class Timer(FormatLabel, TimeSensitiveWidgetBase):
    '''WidgetBase which displays the elapsed seconds.'''

    def __init__(self, format='Elapsed Time: %(elapsed)s', **kwargs):
        FormatLabel.__init__(self, format=format, **kwargs)
        TimeSensitiveWidgetBase.__init__(self, **kwargs)

    # This is exposed as a static method for backwards compatibility
    format_time = staticmethod(_format_time)


class SamplesMixin(object):
    def __init__(self, samples=10, key_prefix=None, **kwargs):
        self.samples = samples
        self.key_prefix = (self.__class__.__name__ or key_prefix) + '_'

    def get_sample_times(self, progress, data):
        return progress.extra.setdefault(self.key_prefix + 'sample_times', [])

    def get_sample_values(self, progress, data):
        return progress.extra.setdefault(self.key_prefix + 'sample_values', [])

    def __call__(self, progress, data):
        sample_times = self.get_sample_times(progress, data)
        sample_values = self.get_sample_values(progress, data)

        if progress.value != progress.previous_value:
            # Add a sample but limit the size to `num_samples`
            sample_times.append(progress.last_update_time)
            sample_values.append(progress.value)

            if len(sample_times) > self.samples:
                sample_times.pop(0)
                sample_values.pop(0)

        return sample_times, sample_values


class ETA(Timer):
    '''WidgetBase which attempts to estimate the time of arrival.'''

    def _eta(self, progress, data, value, elapsed):
        if value == progress.min_value:
            return 'ETA:  --:--:--'
        elif progress.end_time:
            return 'Time: %s' % self.format_time(
                data['total_seconds_elapsed'])
        else:
            eta = elapsed * progress.max_value / value \
                - data['total_seconds_elapsed']
            if eta > 0:
                return 'ETA:  %s' % self.format_time(eta)
            else:
                return 'ETA:  0:00:00'

    def __call__(self, progress, data):
        '''Updates the widget to show the ETA or total time when finished.'''
        return self._eta(progress, data, data['value'],
                         data['total_seconds_elapsed'])


class AbsoluteETA(Timer):
    '''Widget which attempts to estimate the absolute time of arrival.'''

    def _eta(self, progress, data, value, elapsed):
        """Update the widget to show the ETA or total time when finished."""
        if value == progress.min_value:  # pragma: no cover
            return 'Estimated finish time: ----/--/-- --:--:--'
        elif progress.end_time:
            return 'Finished at: %s' % self._format(progress.end_time)
        else:
            eta = elapsed * progress.max_value / value - elapsed
            now = datetime.datetime.now()
            eta_abs = now + datetime.timedelta(seconds=eta)
            return 'Estimated finish time: %s' % self._format(eta_abs)

    def _format(self, t):
        return t.strftime("%Y/%m/%d %H:%M:%S")

    def __call__(self, progress, data):
        '''Updates the widget to show the ETA or total time when finished.'''
        return self._eta(progress, data, data['value'],
                         data['total_seconds_elapsed'])


class AdaptiveETA(ETA, SamplesMixin):
    '''WidgetBase which attempts to estimate the time of arrival.

    Uses a sampled average of the speed based on the 10 last updates.
    Very convenient for resuming the progress halfway.
    '''

    def __init__(self, **kwargs):
        ETA.__init__(self, **kwargs)
        SamplesMixin.__init__(self, **kwargs)

    def __call__(self, progress, data):
        times, values = SamplesMixin.__call__(self, progress, data)

        if len(times) <= 1:
            # No samples so just return the normal ETA calculation
            return ETA.__call__(self, progress, data)
        else:
            return self._eta(progress, data, values[-1] - values[0],
                             utils.timedelta_to_seconds(times[-1] - times[0]))


class DataSize(FormatWidgetMixin):
    '''
    Widget for showing an amount of data transferred/processed.

    Automatically formats the value (assumed to be a count of bytes) with an
    appropriate sized unit, based on the IEC binary prefixes (powers of 1024).
    '''
    def __init__(
            self, variable='value',
            format='%(scaled)5.1f %(prefix)s%(unit)s', unit='B',
            prefixes=('', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
            **kwargs):
        self.variable = variable
        self.unit = unit
        self.prefixes = prefixes
        FormatWidgetMixin.__init__(self, format=format, **kwargs)

    def __call__(self, progress, data):
        value = data[self.variable]
        if value is not None:
            scaled, power = utils.scale_1024(value, len(self.prefixes))
        else:
            scaled = power = 0

        data['scaled'] = scaled
        data['prefix'] = self.prefixes[power]
        data['unit'] = self.unit

        return FormatWidgetMixin.__call__(self, progress, data)


class FileTransferSpeed(FormatWidgetMixin, TimeSensitiveWidgetBase):
    '''
    WidgetBase for showing the transfer speed (useful for file transfers).
    '''

    def __init__(
            self, format='%(scaled)5.1f %(prefix)s%(unit)-s/s',
            inverse_format='%(scaled)5.1f s/%(prefix)s%(unit)-s', unit='B',
            prefixes=('', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
            **kwargs):
        self.unit = unit
        self.prefixes = prefixes
        self.inverse_format = inverse_format
        FormatWidgetMixin.__init__(self, format=format, **kwargs)
        TimeSensitiveWidgetBase.__init__(self, **kwargs)

    def _speed(self, value, elapsed):
        speed = float(value) / elapsed
        return utils.scale_1024(speed, len(self.prefixes))

    def __call__(self, progress, data, value=None, total_seconds_elapsed=None):
        '''Updates the widget with the current SI prefixed speed.'''
        value = data['value'] or value
        elapsed = data['total_seconds_elapsed'] or total_seconds_elapsed

        if value is not None and elapsed is not None \
                and elapsed > 2e-6 and value > 2e-6:  # =~ 0
            scaled, power = self._speed(value, elapsed)
        else:
            scaled = power = 0

        data['unit'] = self.unit
        if power == 0 and scaled < 0.1:
            if scaled > 0:
                scaled = 1 / scaled
            data['scaled'] = scaled
            data['prefix'] = self.prefixes[0]
            return FormatWidgetMixin.__call__(self, progress, data,
                                              self.inverse_format)
        else:
            data['scaled'] = scaled
            data['prefix'] = self.prefixes[power]
            return FormatWidgetMixin.__call__(self, progress, data)


class AdaptiveTransferSpeed(FileTransferSpeed, SamplesMixin):
    '''WidgetBase for showing the transfer speed, based on the last X samples
    '''

    def __init__(self, **kwargs):
        FileTransferSpeed.__init__(self, **kwargs)
        SamplesMixin.__init__(self, **kwargs)

    def __call__(self, progress, data):
        times, values = SamplesMixin.__call__(self, progress, data)
        if len(times) <= 1:
            # No samples so just return the normal transfer speed calculation
            value = None
            elapsed = None
        else:
            value = values[-1] - values[0]
            elapsed = utils.timedelta_to_seconds(times[-1] - times[0])

        return FileTransferSpeed.__call__(self, progress, data, value, elapsed)


class AnimatedMarker(WidgetBase):
    '''An animated marker for the progress bar which defaults to appear as if
    it were rotating.
    '''

    def __init__(self, markers='|/-\\', default=None, **kwargs):
        self.markers = markers
        self.default = default or markers[0]
        WidgetBase.__init__(self, **kwargs)

    def __call__(self, progress, data, width=None):
        '''Updates the widget to show the next marker or the first marker when
        finished'''

        if progress.end_time:
            return self.default

        return self.markers[data['updates'] % len(self.markers)]

# Alias for backwards compatibility
RotatingMarker = AnimatedMarker


class Counter(FormatWidgetMixin, WidgetBase):
    '''Displays the current count'''

    def __init__(self, format='%(value)d', **kwargs):
        FormatWidgetMixin.__init__(self, format=format, **kwargs)
        WidgetBase.__init__(self, format=format, **kwargs)


class Percentage(FormatWidgetMixin, WidgetBase):
    '''Displays the current percentage as a number with a percent sign.'''

    def __init__(self, format='%(percentage)3d%%', **kwargs):
        FormatWidgetMixin.__init__(self, format=format, **kwargs)
        WidgetBase.__init__(self, format=format, **kwargs)


class SimpleProgress(FormatWidgetMixin, WidgetBase):
    '''Returns progress as a count of the total (e.g.: "5 of 47")'''

    def __init__(self, format='%(value)d of %(max_value)d', max_width=None,
                 **kwargs):
        self.max_width = dict(default=max_width)
        FormatWidgetMixin.__init__(self, format=format, **kwargs)
        WidgetBase.__init__(self, format=format, **kwargs)

    def __call__(self, progress, data, format=None):
        formatted = FormatWidgetMixin.__call__(self, progress, data,
                                               format=format)

        # Guess the maximum width from the min and max value
        key = progress.min_value, progress.max_value
        max_width = self.max_width.get(key, self.max_width['default'])
        if not max_width:
            temporary_data = data.copy()
            for value in key:
                if value is None:  # pragma: no cover
                    continue

                temporary_data['value'] = value
                width = len(FormatWidgetMixin.__call__(
                    self, progress, temporary_data, format=format))
                if width:  # pragma: no branch
                    max_width = max(max_width or 0, width)

            self.max_width[key] = max_width

        # Adjust the output to have a consistent size in all cases
        if max_width:  # pragma: no branch
            formatted = formatted.rjust(max_width)
        return formatted


class Bar(AutoWidthWidgetBase):

    '''A progress bar which stretches to fill the line.'''
    def __init__(self, marker='#', left='|', right='|', fill=' ',
                 fill_left=True, **kwargs):
        '''Creates a customizable progress bar.

        The callable takes the same parameters as the `__call__` method

        marker - string or callable object to use as a marker
        left - string or callable object to use as a left border
        right - string or callable object to use as a right border
        fill - character to use for the empty part of the progress bar
        fill_left - whether to fill from the left or the right
        '''
        def string_or_lambda(input_):
            if isinstance(input_, six.basestring):
                def render_input(progress, data, width):
                    return input_ % data

                return render_input
            else:
                return input_

        def _marker(marker):
            def __marker(progress, data, width):
                if progress.max_value is not base.UnknownLength \
                        and progress.max_value > 0:
                    length = int(progress.value / progress.max_value * width)
                    return (marker * length)
                else:
                    return ''

            if isinstance(marker, six.basestring):
                assert len(marker) == 1, 'Markers are required to be 1 char'
                return __marker
            else:
                return marker

        self.marker = _marker(marker)
        self.left = string_or_lambda(left)
        self.right = string_or_lambda(right)
        self.fill = string_or_lambda(fill)
        self.fill_left = fill_left

        AutoWidthWidgetBase.__init__(self, **kwargs)

    def __call__(self, progress, data, width):
        '''Updates the progress bar and its subcomponents'''

        left = self.left(progress, data, width)
        right = self.right(progress, data, width)
        width -= len(left) + len(right)
        marker = self.marker(progress, data, width)
        fill = self.fill(progress, data, width)

        if self.fill_left:
            marker = marker.ljust(width, fill)
        else:
            marker = marker.rjust(width, fill)

        return left + marker + right


class ReverseBar(Bar):

    '''A bar which has a marker which bounces from side to side.'''

    def __init__(self, marker='#', left='|', right='|', fill=' ',
                 fill_left=False, **kwargs):
        '''Creates a customizable progress bar.

        marker - string or updatable object to use as a marker
        left - string or updatable object to use as a left border
        right - string or updatable object to use as a right border
        fill - character to use for the empty part of the progress bar
        fill_left - whether to fill from the left or the right
        '''
        Bar.__init__(self, marker=marker, left=left, right=right, fill=fill,
                     fill_left=fill_left, **kwargs)


class BouncingBar(Bar):

    def update(self, progress, width):  # pragma: no cover
        '''Updates the progress bar and its subcomponents'''

        left, marker, right = (i for i in (self.left, self.marker, self.right))

        width -= len(left) + len(right)

        if progress.finished:
            return '%s%s%s' % (left, width * marker, right)

        position = int(progress.value % (width * 2 - 1))
        if position > width:
            position = width * 2 - position
        lpad = self.fill * (position - 1)
        rpad = self.fill * (width - len(marker) - len(lpad))

        # Swap if we want to bounce the other way
        if not self.fill_left:
            rpad, lpad = lpad, rpad

        return '%s%s%s%s%s' % (left, lpad, marker, rpad, right)
