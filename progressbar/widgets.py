#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# progressbar  - Text progress bar library for Python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''Default ProgressBar widgets'''

from __future__ import division, absolute_import, with_statement

import datetime
import math
import abc


def format_updatable(updatable, progress):
    if hasattr(updatable, 'update'):
        return updatable.update(progress)
    else:
        return updatable


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
    def __init__(self, format):
        self.format = format
        super(FormatWidgetMixin, self).__init__()

    def __call__(self, progress, data):
        '''Formats the widget into a string'''
        return self.format % data


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


class Timer(FormatWidgetMixin, TimeSensitiveWidgetBase):
    '''WidgetBase which displays the elapsed seconds.'''

    def __init__(self, format='Elapsed Time: %(time_elapsed)s'):
        super(Timer, self).__init__(format=format)

    @staticmethod
    def format_time(seconds):
        '''Formats time as the string "HH:MM:SS".'''

        return str(datetime.timedelta(seconds=int(seconds)))


class ETA(Timer):
    '''WidgetBase which attempts to estimate the time of arrival.'''

    def _eta(self, progress):
        elapsed = progress.seconds_elapsed
        return elapsed * progress.maxval / progress.currval - elapsed

    def update(self, progress):
        '''Updates the widget to show the ETA or total time when finished.'''

        if progress.currval == 0:
            return 'ETA:  --:--:--'
        elif progress.finished:
            return 'Time: %s' % self.format_time(progress.seconds_elapsed)
        else:
            return 'ETA:  %s' % self.format_time(self._eta(progress))


class AdaptiveETA(ETA):
    '''WidgetBase which attempts to estimate the time of arrival.

    Uses a sampled average of the speed based on the 10 last updates.
    Very convenient for resuming the progress halfway.
    '''

    TIME_SENSITIVE = True

    def __init__(self, num_samples=10, **kwargs):
        ETA.__init__(self, **kwargs)
        self.num_samples = num_samples
        self.samples = []
        self.sample_vals = []
        self.last_sample_val = None

    def _eta(self, progress):
        samples = self.samples
        sample_vals = self.sample_vals
        if progress.currval != self.last_sample_val:
            # Update the last sample counter, we only update if currval has
            # changed
            self.last_sample_val = progress.currval

            # Add a sample but limit the size to `num_samples`
            samples.append(progress.seconds_elapsed)
            sample_vals.append(progress.currval)
            if len(samples) > self.num_samples:
                samples.pop(0)
                sample_vals.pop(0)

        if len(samples) <= 1:
            # No samples so just return the normal ETA calculation
            return ETA._eta(self, progress)

        todo = progress.maxval - progress.currval
        items = sample_vals[-1] - sample_vals[0]
        duration = float(samples[-1] - samples[0])
        per_item = duration / items
        return todo * per_item


class FileTransferSpeed(WidgetBase):

    '''WidgetBase for showing the transfer speed (useful for file transfers).'''

    format = '%6.2f %s%s/s'
    prefixes = ' kMGTPEZY'

    def __init__(self, unit='B'):
        self.unit = unit

    def _speed(self, progress):
        speed = progress.currval / progress.seconds_elapsed
        power = int(math.log(speed, 1000))
        scaled = speed / 1000. ** power
        return scaled, power

    def update(self, progress):
        '''Updates the widget with the current SI prefixed speed.'''

        if progress.seconds_elapsed < 2e-6 or progress.currval < 2e-6:  # =~ 0
            scaled = power = 0
        else:
            scaled, power = self._speed(progress)

        return self.format % (scaled, self.prefixes[power], self.unit)


class AdaptiveTransferSpeed(FileTransferSpeed):

    '''WidgetBase for showing the transfer speed, based on the last X samples'''

    def __init__(self, num_samples=10):
        FileTransferSpeed.__init__(self)
        self.num_samples = num_samples
        self.samples = []
        self.sample_vals = []
        self.last_sample_val = None

    def _speed(self, progress):
        samples = self.samples
        sample_vals = self.sample_vals
        if progress.currval != self.last_sample_val:
            # Update the last sample counter, we only update if currval has
            # changed
            self.last_sample_val = progress.currval

            # Add a sample but limit the size to `num_samples`
            samples.append(progress.seconds_elapsed)
            sample_vals.append(progress.currval)
            if len(samples) > self.num_samples:
                samples.pop(0)
                sample_vals.pop(0)

        if len(samples) <= 1:
            # No samples so just return the parent's calculation
            return FileTransferSpeed._speed(self, progress)

        items = sample_vals[-1] - sample_vals[0]
        duration = float(samples[-1] - samples[0])
        speed = items / duration
        power = int(math.log(speed, 1000))
        scaled = speed / 1000. ** power
        return scaled, power


class AnimatedMarker(WidgetBase):

    '''An animated marker for the progress bar which defaults to appear as if
    it were rotating.
    '''

    def __init__(self, markers='|/-\\'):
        self.markers = markers
        self.curmark = -1

    def update(self, progress):
        '''Updates the widget to show the next marker or the first marker when
        finished'''

        if progress.finished:
            return self.markers[0]

        self.curmark = (self.curmark + 1) % len(self.markers)
        return self.markers[self.curmark]

# Alias for backwards compatibility
RotatingMarker = AnimatedMarker


class Counter(WidgetBase):

    '''Displays the current count'''

    def __init__(self, format='%d'):
        self.format = format

    def update(self, progress):
        return self.format % progress.currval


class Percentage(FormatWidgetMixin, WidgetBase):
    '''Displays the current percentage as a number with a percent sign.'''

    def __init__(self, format='%(percentage)3d%%'):
        super(Percentage, self).__init__(format=format)


class FormatLabel(Timer):

    '''Displays a formatted label'''

    mapping = {
        'elapsed': ('seconds_elapsed', Timer.format_time),
        'finished': ('finished', None),
        'last_update': ('last_update_time', None),
        'max': ('maxval', None),
        'seconds': ('seconds_elapsed', None),
        'start': ('start_time', None),
        'value': ('currval', None)
    }

    def __init__(self, format):
        self.format = format

    def update(self, progress):
        context = {}
        for name, (key, transform) in self.mapping.items():
            try:
                value = getattr(progress, key)

                if transform is None:
                    context[name] = value
                else:
                    context[name] = transform(value)
            except:  # pragma: no cover
                pass

        return self.format % context


class SimpleProgress(FormatWidgetMixin, WidgetBase):

    '''Returns progress as a count of the total (e.g.: "5 of 47")'''

    def __init__(self, format='%(value)d of %(max_value)d'):
        super(SimpleProgress, self).__init__(format=format)


class Bar(AutoWidthWidgetBase):

    '''A progress bar which stretches to fill the line.'''

    def __init__(self, marker='#', left='|', right='|', fill=' ',
                 fill_left=True):
        '''Creates a customizable progress bar.

        The callable takes the same parameters as the `__call__` method

        marker - string or callable object to use as a marker
        left - string or callable object to use as a left border
        right - string or callable object to use as a right border
        fill - character to use for the empty part of the progress bar
        fill_left - whether to fill from the left or the right
        '''
        def string_or_lambda(input_):
            if isinstance(input_, basestring):
                return lambda progress, data, width: input_ % data
            else:
                return input_

        def _marker(marker):
            def __marker(progress, data, width):
                if progress.max_value > 0:
                    length = int(progress.value / progress.max_value * width)
                    return (marker * length)
                else:
                    return ''

            if isinstance(marker, basestring):
                assert len(marker) == 1, 'Markers are required to be 1 char'
                return __marker
            else:
                return marker

        self.marker = _marker(marker)
        self.left = string_or_lambda(left)
        self.right = string_or_lambda(right)
        self.fill = string_or_lambda(fill)
        self.fill_left = fill_left

        super(Bar, self).__init__()


    def __call__(self, progress, data, width):
        '''Updates the progress bar and its subcomponents'''

        left = self.left(progress, data, width)
        right = self.right(progress, data, width)
        width -= len(left) + len(right)
        marker = self.marker(progress, data, width)
        fill = self.fill(progress, data, width)

        if self.fill_left:
            try:
                marker = marker.ljust(width, fill)
            except Exception, e:
                raise IOError((marker, width, fill, e))
        else:
            marker = marker.rjust(width, fill)

        return left + marker + right


class ReverseBar(Bar):

    '''A bar which has a marker which bounces from side to side.'''

    def __init__(self, marker='#', left='|', right='|', fill=' ',
                 fill_left=False):
        '''Creates a customizable progress bar.

        marker - string or updatable object to use as a marker
        left - string or updatable object to use as a left border
        right - string or updatable object to use as a right border
        fill - character to use for the empty part of the progress bar
        fill_left - whether to fill from the left or the right
        '''
        super(ReverseBar, self).___init__(marker=marker, left=left, right=right,
                                          fill=fill, fill_left=fill_left)


class BouncingBar(Bar):

    def update(self, progress, width):
        '''Updates the progress bar and its subcomponents'''

        left, marker, right = (format_updatable(i, progress) for i in
                               (self.left, self.marker, self.right))

        width -= len(left) + len(right)

        if progress.finished:
            return '%s%s%s' % (left, width * marker, right)

        position = int(progress.currval % (width * 2 - 1))
        if position > width:
            position = width * 2 - position
        lpad = self.fill * (position - 1)
        rpad = self.fill * (width - len(marker) - len(lpad))

        # Swap if we want to bounce the other way
        if not self.fill_left:
            rpad, lpad = lpad, rpad

        return '%s%s%s%s%s' % (left, lpad, marker, rpad, right)
