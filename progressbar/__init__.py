"""progressbar2 public API.

Imports are lazy (PEP 562): ``import progressbar`` loads almost nothing; each
submodule and exported name is imported on first access. This keeps the import
light (in particular the widgets and the terminal/color tables are only loaded
when actually used) while preserving the full public API.
"""

import importlib
import typing

# Re-exported as a static module attribute (kept out of ``__all__`` for
# backwards compatibility). ``__date__`` used to be recomputed at import time
# via ``date.today()``; it now mirrors the release date from ``__about__``.
from .__about__ import (
    __author__,
    __date__ as __date__,
    __version__,
)

if typing.TYPE_CHECKING:
    # Eager imports for type checkers only, loaded lazily at runtime by
    # __getattr__ below. Names appear in __all__ so they read as re-exports.
    from .algorithms import (
        DoubleExponentialMovingAverage,
        ExponentialMovingAverage,
        SmoothingAlgorithm,
    )
    from .bar import DataTransferBar, NullBar, ProgressBar
    from .base import UnknownLength
    from .fast import FastProgressBar
    from .multi import MultiBar, SortKey
    from .shortcuts import progressbar
    from .terminal.stream import LineOffsetStreamWrapper
    from .utils import len_color, streams
    from .widgets import (
        ETA,
        AbsoluteETA,
        AdaptiveETA,
        AdaptiveTransferSpeed,
        AnimatedMarker,
        Bar,
        BouncingBar,
        Counter,
        CurrentTime,
        DataSize,
        DynamicMessage,
        FileTransferSpeed,
        FormatCustomText,
        FormatLabel,
        FormatLabelBar,
        GranularBar,
        JobStatusBar,
        MultiProgressBar,
        MultiRangeBar,
        Percentage,
        PercentageLabelBar,
        Postfix,
        ReverseBar,
        RotatingMarker,
        SimpleProgress,
        SmoothingETA,
        Timer,
        UnitProgress,
        Variable,
        VariableMixin,
    )

#: Submodules accessible as ``progressbar.<name>``.
_SUBMODULES: frozenset[str] = frozenset(
    {
        'algorithms',
        'bar',
        'base',
        'env',
        'fast',
        'multi',
        'shortcuts',
        'terminal',
        'utils',
        'widgets',
    }
)

#: Exported name -> submodule it lives in.
_NAME_TO_MODULE: dict[str, str] = {
    'DoubleExponentialMovingAverage': 'algorithms',
    'ExponentialMovingAverage': 'algorithms',
    'SmoothingAlgorithm': 'algorithms',
    'DataTransferBar': 'bar',
    'NullBar': 'bar',
    'ProgressBar': 'bar',
    'FastProgressBar': 'fast',
    'UnknownLength': 'base',
    'MultiBar': 'multi',
    'SortKey': 'multi',
    'progressbar': 'shortcuts',
    'LineOffsetStreamWrapper': 'terminal.stream',
    'len_color': 'utils',
    'streams': 'utils',
    'ETA': 'widgets',
    'AbsoluteETA': 'widgets',
    'AdaptiveETA': 'widgets',
    'AdaptiveTransferSpeed': 'widgets',
    'AnimatedMarker': 'widgets',
    'Bar': 'widgets',
    'BouncingBar': 'widgets',
    'Counter': 'widgets',
    'CurrentTime': 'widgets',
    'DataSize': 'widgets',
    'DynamicMessage': 'widgets',
    'FileTransferSpeed': 'widgets',
    'FormatCustomText': 'widgets',
    'FormatLabel': 'widgets',
    'FormatLabelBar': 'widgets',
    'GranularBar': 'widgets',
    'JobStatusBar': 'widgets',
    'MultiProgressBar': 'widgets',
    'MultiRangeBar': 'widgets',
    'Percentage': 'widgets',
    'Postfix': 'widgets',
    'PercentageLabelBar': 'widgets',
    'ReverseBar': 'widgets',
    'RotatingMarker': 'widgets',
    'SimpleProgress': 'widgets',
    'SmoothingETA': 'widgets',
    'Timer': 'widgets',
    'UnitProgress': 'widgets',
    'Variable': 'widgets',
    'VariableMixin': 'widgets',
}


def __getattr__(name: str) -> typing.Any:
    """Lazily import submodules and exported names on first access."""
    if name in _SUBMODULES:
        module = importlib.import_module(f'.{name}', __name__)
        globals()[name] = module  # cache so __getattr__ runs only once
        return module

    module_name = _NAME_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
    value = getattr(importlib.import_module(f'.{module_name}', __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """List lazily loaded exports and submodules along with globals."""
    return sorted(set(globals()) | set(__all__) | _SUBMODULES)


#: Canonical export list, kept equal to ``sorted(_NAME_TO_MODULE)`` (the single
#: source of truth for lazily re-exported names) plus the eagerly imported
#: dunders. Held as a static literal so type checkers can see the re-exports.
#: ``tests/test_init_exports.py`` asserts it stays in sync with the mapping.
__all__ = [
    'ETA',
    'AbsoluteETA',
    'AdaptiveETA',
    'AdaptiveTransferSpeed',
    'AnimatedMarker',
    'Bar',
    'BouncingBar',
    'Counter',
    'CurrentTime',
    'DataSize',
    'DataTransferBar',
    'DoubleExponentialMovingAverage',
    'DynamicMessage',
    'ExponentialMovingAverage',
    'FastProgressBar',
    'FileTransferSpeed',
    'FormatCustomText',
    'FormatLabel',
    'FormatLabelBar',
    'GranularBar',
    'JobStatusBar',
    'LineOffsetStreamWrapper',
    'MultiBar',
    'MultiProgressBar',
    'MultiRangeBar',
    'NullBar',
    'Percentage',
    'PercentageLabelBar',
    'Postfix',
    'ProgressBar',
    'ReverseBar',
    'RotatingMarker',
    'SimpleProgress',
    'SmoothingAlgorithm',
    'SmoothingETA',
    'SortKey',
    'Timer',
    'UnitProgress',
    'UnknownLength',
    'Variable',
    'VariableMixin',
    '__author__',
    '__version__',
    'len_color',
    'progressbar',
    'streams',
]
