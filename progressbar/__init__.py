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
    # The redundant `name as name` aliases mark the namespace-only
    # exports (kept out of ``__all__``, see ``_NAMESPACE_ONLY``) as
    # deliberate re-exports for type checkers and linters.
    from ._parallel import (
        AsyncPool,
        ParallelFunction,
        Pool,
        aimap as aimap,
        aimap_unordered as aimap_unordered,
        amap as amap,
        as_completed as as_completed,
        current_task_bar,
        gather as gather,
        imap as imap,
        imap_unordered as imap_unordered,
        map as map,  # noqa: A004 - namespaced use only, not in __all__
        parallel,
        process_map,
        run as run,
        starmap,
        thread_map,
    )
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
    'AsyncPool': '_parallel',
    'ParallelFunction': '_parallel',
    'Pool': '_parallel',
    'current_task_bar': '_parallel',
    'parallel': '_parallel',
    'process_map': '_parallel',
    'starmap': '_parallel',
    'thread_map': '_parallel',
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

#: Exported name -> submodule, for names resolvable as
#: ``progressbar.<name>`` (and by explicit import) but deliberately
#: kept out of ``__all__``: they would shadow builtins or stdlib names
#: under ``from progressbar import *`` (``map``, ``as_completed``, ...).
_NAMESPACE_ONLY: dict[str, str] = {
    'aimap': '_parallel',
    'aimap_unordered': '_parallel',
    'amap': '_parallel',
    'as_completed': '_parallel',
    'gather': '_parallel',
    'imap': '_parallel',
    'imap_unordered': '_parallel',
    'map': '_parallel',
    'run': '_parallel',
}


def __getattr__(name: str) -> typing.Any:
    """Lazily import submodules and exported names on first access."""
    if name in _SUBMODULES:
        module = importlib.import_module(f'.{name}', __name__)
        globals()[name] = module  # cache so __getattr__ runs only once
        return module

    module_name = _NAME_TO_MODULE.get(name) or _NAMESPACE_ONLY.get(name)
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
    'AsyncPool',
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
    'ParallelFunction',
    'Percentage',
    'PercentageLabelBar',
    'Pool',
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
    'current_task_bar',
    'len_color',
    'parallel',
    'process_map',
    'progressbar',
    'starmap',
    'streams',
    'thread_map',
]
