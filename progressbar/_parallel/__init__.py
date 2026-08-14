"""Parallel execution with progress bars.

Private implementation package behind the public ``progressbar.map`` /
``imap`` / ``amap`` / ``run`` / ``Pool`` family. The package is private
(underscored) because the public surface includes a ``parallel``
*decorator* exported as ``progressbar.parallel`` -- a public
``progressbar/parallel.py`` module would clobber that attribute on
``import progressbar.parallel``.

Public names are re-exported lazily from ``progressbar/__init__.py``;
star-import-unsafe ones (``map``, ``imap``, ``gather``, ...) resolve
through the namespace only and stay out of ``progressbar.__all__``.
"""

from ._async import (
    AsyncPool,
    aimap,
    aimap_unordered,
    amap,
    gather,
)
from ._common import current_task_bar
from ._decorator import (
    ParallelFunction,
    parallel,
)
from ._shell import run
from ._sync import (
    Pool,
    as_completed,
    imap,
    imap_unordered,
    map,  # noqa: A004 - intentional builtin name, namespaced use only
    process_map,
    starmap,
    thread_map,
)

__all__ = [
    'AsyncPool',
    'ParallelFunction',
    'Pool',
    'aimap',
    'aimap_unordered',
    'amap',
    'as_completed',
    'current_task_bar',
    'gather',
    'imap',
    'imap_unordered',
    'map',
    'parallel',
    'process_map',
    'run',
    'starmap',
    'thread_map',
]
