"""Terminal primitives: colors, escape sequences and stream wrappers.

Re-exports everything from `base` and `stream`. Neither declares an
`__all__`, so every public name in them is reachable as
`progressbar.terminal.X` and is covered by the API-surface snapshot
test.
"""

from __future__ import annotations

from .base import *  # noqa F403
from .stream import *  # noqa F403
