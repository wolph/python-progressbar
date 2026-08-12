"""The lean, widget-free renderer used by `progressbar.progressbar()`.

`FastProgressBar` reuses the full `ProgressBar` lifecycle (update gate,
native iterator, stream redirect, resizing) and replaces only the render
step with one fixed formatter, so the common "just wrap my loop" case
stays cheap. See docs/explanation/performance-and-the-fast-path.rst for
the full layer breakdown and measured costs.
"""

from __future__ import annotations

import typing
from collections.abc import Callable
from datetime import datetime, timedelta

from . import (
    bar as bar_module,
    base,
)

#: Optional native line-formatter hook. Left as ``None`` so the pure-Python
#: ``_pure_format_fast_line`` below is used by default. When set to a callable
#: it takes precedence in :py:meth:`FastProgressBar._format_line`, letting the
#: ``speedups`` package (or any caller) swap in a faster/custom formatter.
#: This is a supported extension point, exercised by
#: ``test_fast_format_line_uses_native_hook``.
_format_fast_line: Callable[[FastProgressBar], str] | None = None

#: Spinner frames cycled for unknown-length bars: bar, forward slash, dash,
#: back slash. A plain (non-raw) literal so the escape is a single ``\`` and
#: the string is exactly four characters.
_SPINNER_FRAMES: str = '|/-\\'


def _format_seconds(seconds: float) -> str:
    """Render elapsed/ETA seconds as H:MM:SS, matching the Timer widget."""
    return str(timedelta(seconds=int(seconds)))


def _pure_format_fast_line(bar: FastProgressBar) -> str:
    """Build the whole status line directly (no widgets, no data() dict).

    Two layouts: a known-length bar (percentage, count, `#`-filled bar,
    elapsed/ETA) when `max_value` is set; otherwise a spinner plus item
    count and elapsed time. Progress is clamped to `total` so a forced
    over-max render (e.g. `max_error=False` letting `value` overshoot)
    can't drive the ETA negative or overflow the bar's width.

    Args:
        bar: Bar to render, treated as read-only.

    Returns:
        The complete line, including `prefix`/`suffix`.
    """
    value = bar.value
    min_value = bar.min_value
    max_value = bar.max_value
    width = bar.term_width
    elapsed = bar._fast_elapsed()
    elapsed_text = _format_seconds(elapsed)
    prefix = bar.prefix or ''
    suffix = bar.suffix or ''

    known = max_value not in (None, base.UnknownLength)
    if known:
        total = max_value - min_value  # type: ignore[operator]
        # Clamp progress to the total so an over-shooting value (e.g. a forced
        # render past max_value with max_error=False) can't produce a negative
        # ETA or a bar that overflows its width.
        done = min(value - min_value, total)
        pct = 100.0 * done / total if total else 100.0
        count = f'({value} of {max_value})'
        if done > 0 and elapsed > 0:
            eta = _format_seconds(elapsed * (total - done) / done)
        else:
            eta = '--:--:--'
        left = f'{pct:3.0f}% {count} '
        right = f' Elapsed Time: {elapsed_text} ETA: {eta}'
        inner = max(width - len(left) - len(right) - 2, 0)
        filled = int(inner * done / total) if total else inner
        barstr = '|' + '#' * filled + ' ' * (inner - filled) + '|'
        return f'{prefix}{left}{barstr}{right}{suffix}'

    # Unknown length: spinner + count + elapsed (no bar/eta).
    spinner = _SPINNER_FRAMES[int(elapsed * 4) % len(_SPINNER_FRAMES)]
    item_count = value - min_value + 1
    return (
        f'{prefix}{spinner} {item_count} Elapsed Time: {elapsed_text}{suffix}'
    )


class FastProgressBar(bar_module.ProgressBar):
    """A lean ProgressBar whose render bypasses the widget system.

    Reuses the full ProgressBar lifecycle (the next-update gate, the native
    iterator, stream redirect, resize, start/update/finish) and overrides only
    the render with a fixed formatter, so the common case is import- and
    render-cheap. Output stays close to the default look without the gradient.
    """

    def default_widgets(self) -> list[typing.Any]:
        """Return no widgets -- `_format_line` renders everything itself."""
        return []

    def _fast_elapsed(self) -> float:
        """Seconds elapsed so far, clamped to non-negative.

        Returns:
            `0.0` before `start()` has run; otherwise elapsed since
            `start_time`, ending at `end_time` once `finish()` has run,
            or at the current time while the bar is still active.
        """
        if self.start_time is None:
            return 0.0
        end = self.end_time or self._fast_now()
        return max((end - self.start_time).total_seconds(), 0.0)

    def _fast_now(self) -> datetime:
        """Current wall-clock time, split out so tests can monkeypatch it."""
        return datetime.now()

    def _format_line(self) -> str:
        """Render via `_format_fast_line` or the pure-Python fallback."""
        formatter = _format_fast_line or _pure_format_fast_line
        return formatter(self)

    def _init_prefix(self) -> None:
        """No-op: the formatter renders `prefix` inline, not as a widget."""

    def _init_suffix(self) -> None:
        """No-op: the formatter renders `suffix` inline, not as a widget."""
