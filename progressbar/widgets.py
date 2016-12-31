from __future__ import division, absolute_import, with_statement
from __future__ import print_function

import abc
import datetime
import pprint
import sys

from python_utils import converters

from . import base
from . import six
from . import utils

MAX_DATE = datetime.date(year=datetime.MAXYEAR, month=12, day=31)
MAX_TIME = datetime.time(23, 59, 59)
MAX_DATETIME = datetime.datetime.combine(MAX_DATE, MAX_TIME)


def string_or_lambda(input_):
    if isinstance(input_, six.basestring):
        def render_input(progress, data, width):
            return input_ % data

        return render_input
    else:
        return input_


def create_marker(marker):
    def _marker(progress, data, width):
        if progress.max_value is not base.UnknownLength \
                and progress.max_value > 0:
            length = int(progress.value / progress.max_value * width)
            return (marker * length)
        else:
            return marker

    if isinstance(marker, six.basestring):
        assert len(marker) == 1, 'Markers are required to be 1 char'
        return _marker
    else:
        return marker


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

    The boolean INTERVAL informs the ProgressBar that it should be
    updated more often because it is time sensitive.

    WARNING: Widgets can be shared between multiple progressbars so any state
    information specific to a progressbar should be stored within the
    progressbar instead of the widget.
    '''

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
    INTERVAL = datetime.timedelta(milliseconds=100)


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
        'elapsed': ('total_seconds_elapsed', utils.format_time),
        'value': ('value', None),
    }

    def __init__(self, format, **kwargs):
        FormatWidgetMixin.__init__(self, format=format, **kwargs)
        WidthWidgetMixin.__init__(self, **kwargs)

    def __call__(self, progress, data, **kwargs):
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

        return FormatWidgetMixin.__call__(self, progress, data, **kwargs)


class Timer(FormatLabel, TimeSensitiveWidgetBase):
    '''WidgetBase which displays the elapsed seconds.'''

    def __init__(self, format='Elapsed Time: %(elapsed)s', **kwargs):
        FormatLabel.__init__(self, format=format, **kwargs)
        TimeSensitiveWidgetBase.__init__(self, **kwargs)

    # This is exposed as a static method for backwards compatibility
    format_time = staticmethod(utils.format_time)


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

        if sample_times:
            sample_time = sample_times[-1]
        else:
            sample_time = datetime.datetime.min

        if progress.last_update_time - sample_time > self.INTERVAL:
            # Add a sample but limit the size to `num_samples`
            sample_times.append(progress.last_update_time)
            sample_values.append(progress.value)

            if len(sample_times) > self.samples:
                sample_times.pop(0)
                sample_values.pop(0)

        return sample_times, sample_values


class ETA(Timer):
    '''WidgetBase which attempts to estimate the time of arrival.'''

    def __init__(
            self,
            format_not_started='ETA:  --:--:--',
            format_finished='Time: %(elapsed)s',
            format='ETA: %(eta)s',
            format_zero='ETA:  0:00:00',
            format_NA='ETA: N/A',
            **kwargs):

        Timer.__init__(self, **kwargs)
        self.format_not_started = format_not_started
        self.format_finished = format_finished
        self.format = format
        self.format_zero = format_zero
        self.format_NA = format_NA

    def _calculate_eta(self, progress, data, value, elapsed):
        '''Updates the widget to show the ETA or total time when finished.'''
        if elapsed:
            # The max() prevents zero division errors
            per_item = elapsed / max(value, 0.0000000001)
            remaining = progress.max_value - data['value']
            eta_seconds = remaining * per_item
        else:
            eta_seconds = 0

        return eta_seconds

    def __call__(self, progress, data, value=None, elapsed=None):
        '''Updates the widget to show the ETA or total time when finished.'''

        if value is None:
            value = data['value']

        if elapsed is None:
            elapsed = data['total_seconds_elapsed']

        ETA_NA = False
        try:
            data['eta_seconds'] = self._calculate_eta(
                progress, data, value=value, elapsed=elapsed)
        except TypeError:
            data['eta_seconds'] = None
            ETA_NA = True

        if data['eta_seconds']:
            data['eta'] = utils.format_time(data['eta_seconds'])
        else:
            data['eta'] = None

        if data['value'] == progress.min_value:
            format = self.format_not_started
        elif progress.end_time:
            format = self.format_finished
        elif data['eta']:
            format = self.format
        elif ETA_NA:
            format = self.format_NA
        else:
            format = self.format_zero

        return Timer.__call__(self, progress, data, format=format)


class AbsoluteETA(ETA):
    '''Widget which attempts to estimate the absolute time of arrival.'''

    def _calculate_eta(self, progress, data, value, elapsed):
        eta_seconds = ETA._calculate_eta(self, progress, data, value, elapsed)
        now = datetime.datetime.now()
        try:
            return now + datetime.timedelta(seconds=eta_seconds)
        except OverflowError:  # pragma: no cover
            return datetime.datetime.max

    def __init__(
            self,
            format_not_started='Estimated finish time:  ----/--/-- --:--:--',
            format_finished='Finished at: %(elapsed)s',
            format='Estimated finish time: %(eta)s',
            **kwargs):
        Timer.__init__(self, **kwargs)
        self.format_not_started = format_not_started
        self.format_finished = format_finished
        self.format = format


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
            value = None
            elapsed = 0
        else:
            value = values[-1] - values[0]
            elapsed = utils.timedelta_to_seconds(times[-1] - times[0])

        return ETA.__call__(self, progress, data, value=value, elapsed=elapsed)


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

    def __call__(self, progress, data, format=None):
        # If percentage is not available, display N/A%
        if 'percentage' in data and not data['percentage']:
            return FormatWidgetMixin.__call__(self, progress, data,
                                              format='N/A%%')

        return FormatWidgetMixin.__call__(self, progress, data)


class SimpleProgress(FormatWidgetMixin, WidgetBase):
    '''Returns progress as a count of the total (e.g.: "5 of 47")'''

    DEFAULT_FORMAT = '%(value_s)s of %(max_value_s)s'

    def __init__(self, format=DEFAULT_FORMAT, max_width=None, **kwargs):
        self.max_width = dict(default=max_width)
        FormatWidgetMixin.__init__(self, format=format, **kwargs)
        WidgetBase.__init__(self, format=format, **kwargs)

    def __call__(self, progress, data, format=None):
        # If max_value is not available, display N/A
        if data.get('max_value'):
            data['max_value_s'] = data.get('max_value')
        else:
            data['max_value_s'] = 'N/A'

        # if value is not available it's the zeroth iteration
        if data.get('value'):
            data['value_s'] = data['value']
        else:
            data['value_s'] = 0

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

        self.marker = create_marker(marker)
        self.left = string_or_lambda(left)
        self.right = string_or_lambda(right)
        self.fill = string_or_lambda(fill)
        self.fill_left = fill_left

        AutoWidthWidgetBase.__init__(self, **kwargs)

    def __call__(self, progress, data, width):
        '''Updates the progress bar and its subcomponents'''

        left = converters.to_unicode(self.left(progress, data, width))
        right = converters.to_unicode(self.right(progress, data, width))
        width -= len(left) + len(right)
        marker = converters.to_unicode(self.marker(progress, data, width))
        fill = converters.to_unicode(self.fill(progress, data, width))

        if self.fill_left:
            marker = marker.ljust(width, fill)
        else:
            marker = marker.rjust(width, fill)

        return left + marker + right


class ReverseBar(Bar):
    '''A bar which has a marker that goes from right to left'''

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


class BouncingBar(Bar, TimeSensitiveWidgetBase):
    '''A bar which has a marker which bounces from side to side.'''

    INTERVAL = datetime.timedelta(milliseconds=100)

    def __call__(self, progress, data, width):
        '''Updates the progress bar and its subcomponents'''

        left = converters.to_unicode(self.left(progress, data, width))
        right = converters.to_unicode(self.right(progress, data, width))
        width -= len(left) + len(right)
        marker = converters.to_unicode(self.marker(progress, data, width))

        fill = converters.to_unicode(self.fill(progress, data, width))

        if width:  # pragma: no branch
            value = int(
                data['total_seconds_elapsed'] / self.INTERVAL.total_seconds())

            a = value % width
            b = width - a - 1
            if value % (width * 2) >= width:
                a, b = b, a

            if self.fill_left:
                marker = a * fill + marker + b * fill
            else:
                marker = b * fill + marker + a * fill

        return left + marker + right


class FormatCustomText(FormatWidgetMixin, WidthWidgetMixin):
    mapping = {}

    def __init__(self, format, mapping=mapping, **kwargs):
        self.format = format
        self.mapping = mapping
        FormatWidgetMixin.__init__(self, format=format, **kwargs)
        WidthWidgetMixin.__init__(self, **kwargs)

    def update_mapping(self, **mapping):
        self.mapping.update(mapping)

    def __call__(self, progress, data):
        return FormatWidgetMixin.__call__(self, progress, self.mapping,
                                          self.format)


class DynamicMessage(FormatWidgetMixin, WidgetBase):
    '''Displays a custom variable.'''

    def __init__(self, name):
        '''Creates a DynamicMessage associated with the given name.'''
        if not isinstance(name, str):
            raise TypeError('DynamicMessage(): argument must be a string')
        if len(name.split()) > 1:
            raise ValueError(
                'DynamicMessage(): argument must be single word')

        self.name = name

    def __call__(self, progress, data):
        val = data['dynamic_messages'][self.name]
        if val:
            return self.name + ': ' + '{:6.3g}'.format(val)
        else:
            return self.name + ': ' + 6 * '-'
