"""Security regressions for the ``bar='multi'`` parallel display."""

from __future__ import annotations

import io
import time
import typing

import pytest

import progressbar
from progressbar.utils import streams

_HOSTILE_ITEM: str = 'a\x1b]0;x\x07b\x1bcc\x9b31md\re\nf'
_FORBIDDEN: tuple[str, ...] = ('\x1b]0;x\x07', '\x1bc', '\x9b', '\r', '\n')


def _identity(item: typing.Any) -> typing.Any:
    return item


def _slow_identity(item: typing.Any) -> typing.Any:
    # Keep the task running long enough for the render thread to draw it.
    time.sleep(0.3)
    return item


@pytest.mark.no_freezegun
def test_multi_labels_strip_control_sequences() -> None:
    fd: io.StringIO = io.StringIO()
    result: list[typing.Any] = list(
        progressbar.map(
            _slow_identity,
            [_HOSTILE_ITEM],
            bar='multi',
            fd=fd,
            poll_interval=0.05,
        )
    )
    assert result == [_HOSTILE_ITEM]
    output: str = fd.getvalue()
    for sequence in ('\x1b]0;x\x07', '\x1bc', '\x9b'):
        assert sequence not in output
    assert '1: ab' in output
    # The raw label's CR and LF must not reach the output inside it.
    assert 'b\rc' not in output
    assert 'd\re' not in output
    assert 'e\nf' not in output


def test_display_label_removes_every_control() -> None:
    from progressbar._parallel import _display

    cleaned: str = _display._display_label(_HOSTILE_ITEM + '\t\x7f\x1b[31m')
    for sequence in (*_FORBIDDEN, '\t', '\x7f', '\x1b'):
        assert sequence not in cleaned


def test_multi_map_restores_stream_state() -> None:
    listeners_before: int = len(streams.listeners)
    capturing_before: int = streams.capturing
    result: list[int] = list(
        progressbar.map(_identity, range(5), bar='multi', fd=io.StringIO())
    )
    assert result == list(range(5))
    assert len(streams.listeners) == listeners_before
    assert streams.capturing == capturing_before


def test_task_started_accepts_a_non_str_label() -> None:
    from progressbar._parallel import _display

    display = _display.MultiDisplay(
        total=1, poll_interval=0.05, bar_kwargs={'fd': io.StringIO()}
    )
    display.task_started(1, 123)  # type: ignore[arg-type]
    assert display._keys[1] == '1: 123'
    display.task_finished(1, ok=True)
