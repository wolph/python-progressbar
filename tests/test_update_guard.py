"""`ProgressBar.update()` value-guard behavior.

The value-assignment block guards on ``isinstance(value, (int, float))``.
The two leading clauses it used to also carry -- ``value is not None`` and
``value is not base.UnknownLength`` -- are subsumed by that isinstance
check (``None`` and the ``UnknownLength`` sentinel class both fail it), so
``update(None)`` (a redraw tick) and ``update(UnknownLength)`` (the sentinel)
must leave ``value``/``previous_value`` untouched exactly as before.
"""

from __future__ import annotations

import io

import progressbar
import progressbar.base

# Alias (not a `from` import) so CodeQL doesn't flag `progressbar` as
# imported with both `import` and `import from`.
base = progressbar.base


def _bar() -> progressbar.ProgressBar:
    bar = progressbar.ProgressBar(fd=io.StringIO(), max_value=100).start()
    bar.update(40)
    assert bar.value == 40
    return bar


def test_update_none_is_a_tick_and_keeps_value() -> None:
    bar = _bar()
    previous = bar.previous_value
    # A `None` value is a redraw tick, not a new value.
    bar.update(None)
    assert bar.value == 40
    assert bar.previous_value == previous
    bar.finish()


def test_update_unknown_length_sentinel_keeps_value() -> None:
    bar = _bar()
    previous = bar.previous_value
    # The `UnknownLength` sentinel is a class, not a numeric value, so the
    # guard skips assignment rather than storing or comparing it.
    bar.update(base.UnknownLength)
    assert bar.value == 40
    assert bar.previous_value == previous
    bar.finish()
