from __future__ import annotations

import typing
from datetime import datetime, timedelta

from . import (
    bar as bar_module,
)

#: Optional native line formatter, provided by the `speedups` package. When
#: present it replaces the pure-Python formatter below. Wired in a later task.
_format_fast_line: typing.Callable[[FastProgressBar], str] | None = None


def _format_seconds(seconds: float) -> str:
    """Render elapsed/ETA seconds as H:MM:SS, matching the Timer widget."""
    return str(timedelta(seconds=int(seconds)))


def _pure_format_fast_line(bar: FastProgressBar) -> str:
    """Build the whole status line directly (no widgets, no data() dict)."""
    value = bar.value
    min_value = bar.min_value
    max_value = bar.max_value
    width = bar.term_width

    elapsed = bar._fast_elapsed()
    done = value - min_value
    total = (max_value - min_value) if max_value else 0  # type: ignore[operator]

    pct = 100.0 * done / total if total else 100.0
    count = f'({value} of {max_value})'
    if done > 0 and elapsed > 0:
        eta = _format_seconds(elapsed * (total - done) / done)
    else:
        eta = '--:--:--'
    elapsed_text = _format_seconds(elapsed)

    left = f'{pct:3.0f}% {count} '
    right = f' Elapsed Time: {elapsed_text} ETA: {eta}'
    inner = max(width - len(left) - len(right) - 2, 0)
    filled = int(inner * done / total) if total else inner
    barstr = '|' + '#' * filled + ' ' * (inner - filled) + '|'

    prefix = bar.prefix or ''
    suffix = bar.suffix or ''
    return f'{prefix}{left}{barstr}{right}{suffix}'


class FastProgressBar(bar_module.ProgressBar):
    """A lean ProgressBar whose render bypasses the widget system.

    Reuses the full ProgressBar lifecycle (the next-update gate, the native
    iterator, stream redirect, resize, start/update/finish) and overrides only
    the render with a fixed formatter, so the common case is import- and
    render-cheap. Output stays close to the default look without the gradient.
    """

    def default_widgets(self) -> list:
        # No widgets: the fixed formatter renders everything.
        return []

    def _fast_elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        end = self.end_time or self._fast_now()
        return max((end - self.start_time).total_seconds(), 0.0)

    def _fast_now(self) -> datetime:
        return datetime.now()

    def _format_line(self) -> str:
        formatter = _format_fast_line or _pure_format_fast_line
        return formatter(self)
