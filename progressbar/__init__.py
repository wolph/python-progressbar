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

from .bar import ProgressBar, DataTransferBar
from .base import UnknownLength


from .__about__ import (
    __author__,
    __version__,
)

__date__ = str(date.today())
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
    'DataTransferBar',
    'format_updatable',
    'RotatingMarker',
    '__author__',
    '__version__',
]
