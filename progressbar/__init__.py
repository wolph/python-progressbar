#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# progressbar  - Text progress bar library for Python.
# Copyright (c) 2005 Nilton Volpato
# Copyright (c) 2012 Rick van Hattem
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


'''Text progress bar library for Python.

A text progress bar is typically used to display the progress of a long
running operation, providing a visual cue that processing is underway.

The ProgressBar class manages the current progress, and the format of the line
is given by a number of widgets. A widget is an object that may display
differently depending on the state of the progress bar. There are three types
of widgets:

 - a string, which always shows itself

 - a ProgressBarWidget, which may return a different value every time its
   update method is called

 - a ProgressBarWidgetHFill, which is like ProgressBarWidget, except it
   expands to fill the remaining width of the line.

The progressbar module is very easy to use, yet very powerful. It will also
automatically enable features like auto-resizing when the system supports it.
'''
from datetime import date

from progressbar.widgets import (
    Timer,
    ETA,
    AdaptiveETA,
    AbsoluteETA,
    DataSize,
    FileTransferSpeed,
    AdaptiveTransferSpeed,
    AnimatedMarker,
    Counter,
    Percentage,
    FormatLabel,
    SimpleProgress,
    Bar,
    ReverseBar,
    BouncingBar,
    RotatingMarker,
)

from .bar import ProgressBar
from .base import UnknownLength


__author__ = 'Rick van Hattem'
__author_email__ = 'Rick.van.Hattem@Fawo.nl'
__date__ = str(date.today())
__version__ = '2.7.3'
__all__ = [
    'AbstractWidget',
    'Widget',
    'WidgetHFill',
    'Timer',
    'ETA',
    'AdaptiveETA',
    'AbsoluteETA',
    'DataSize',
    'FileTransferSpeed',
    'AdaptiveTransferSpeed',
    'AnimatedMarker',
    'Counter',
    'Percentage',
    'FormatLabel',
    'SimpleProgress',
    'Bar',
    'ReverseBar',
    'BouncingBar',
    'UnknownLength',
    'ProgressBar',
    'format_updatable',
    'RotatingMarker',
]
