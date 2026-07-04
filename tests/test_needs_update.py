"""`_needs_update` guard behavior.

The width-threshold computation used to run inside
``contextlib.suppress(Exception)``, so any unexpected failure silently
disabled redraws. The known-legitimate incomplete states (no value drawn
yet, no terminal width, zero max value) must still return False exactly
as before, while genuinely unexpected errors now propagate.
"""

from __future__ import annotations

import io
import typing

import pytest

import progressbar
from progressbar import utils


@pytest.fixture(autouse=True)
def _deregister_started_bars() -> typing.Iterator[None]:
    # start() registers each bar as a global capture listener (so writes to
    # the wrapped stream redraw it). These tests deliberately drive bars into
    # invalid states -- e.g. a non-numeric term_width -- and never finish()
    # them. Deregister whatever this test started so a poisoned bar cannot be
    # update()d when a *later* test writes a newline to the captured stream.
    before = set(utils.streams.listeners)
    yield
    for bar in list(utils.streams.listeners - before):
        utils.streams.stop_capturing(bar)


def _bar(**kwargs: typing.Any) -> progressbar.ProgressBar:
    bar = progressbar.ProgressBar(
        fd=io.StringIO(),
        max_value=100,
        term_width=20,
        **kwargs,
    )
    bar.start()
    bar.update(50, force=True)
    # Move the rate limiters out of the way (the constructor substitutes a
    # default for poll_interval=None) so the width-threshold branch decides.
    bar.poll_interval = None
    bar._last_update_timer = -1e9
    return bar


def test_needs_update_crossing_width_threshold() -> None:
    bar = _bar()
    bar.value = 90
    assert bar._needs_update() is True


def test_needs_update_within_same_width_bucket() -> None:
    bar = _bar()
    assert bar._last_drawn_value is not None
    bar.value = bar._last_drawn_value
    assert bar._needs_update() is False


@pytest.mark.parametrize(
    'attribute, incomplete_value',
    [
        ('value', None),
        ('_last_drawn_value', None),
        ('term_width', None),
        ('term_width', 0),
        ('max_value', None),
        ('max_value', 0),
    ],
)
def test_needs_update_incomplete_state_is_false(
    attribute: str,
    incomplete_value: typing.Any,
) -> None:
    # Each of these used to raise inside the suppress() and fall through
    # to False; the explicit guards must preserve that result.
    bar = _bar()
    bar.value = 90
    setattr(bar, attribute, incomplete_value)
    assert bar._needs_update() is False


def test_needs_update_unexpected_error_propagates() -> None:
    # A genuinely wrong type is a bug and must no longer pass silently.
    bar = _bar()
    bar.value = 90
    bar.term_width = 'wide'  # type: ignore[assignment]
    with pytest.raises(TypeError):
        bar._needs_update()
