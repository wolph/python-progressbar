"""Tests for the parallel display layer (plain/null/instance modes)."""

from __future__ import annotations

import io
import time
import typing

import pytest

import progressbar
from progressbar._parallel import _display


def _make(
    mode: typing.Any,
    total: typing.Any = 3,
    poll_interval: float = 0.1,
    **bar_kwargs: typing.Any,
) -> _display.Display:
    return _display.make_display(
        mode, total=total, poll_interval=poll_interval, bar_kwargs=bar_kwargs
    )


class TestPlainDisplay:
    def test_advances_to_completion(self) -> None:
        stream = io.StringIO()
        display: _display.Display = _make('plain', fd=stream)
        display.start(3)
        display.advance()
        display.advance(2)
        display.finish()
        assert '3' in stream.getvalue()
        assert stream.getvalue().endswith('\n')

    def test_tick_redraws_without_progress(self) -> None:
        # Keep-alive: with zero completions, a tick after poll_interval
        # must produce a new render (pins the rev-2 spec blocker).
        stream = io.StringIO()
        display = _make('plain', fd=stream)
        display.start(3)
        before: int = len(stream.getvalue())
        time.sleep(0.5)  # advances the frozen clock via autouse fixture
        display.tick()
        assert len(stream.getvalue()) > before
        display.finish()

    def test_task_hooks_are_noops(self) -> None:
        display = _make('plain', fd=io.StringIO())
        display.start(1)
        assert display.task_started(1, 'label') is None
        display.task_finished(1, ok=True)
        display.finish()

    def test_failure_finish_does_not_force_max(self) -> None:
        stream = io.StringIO()
        display = _make('plain', fd=stream)
        display.start(3)
        time.sleep(0.01)  # let the frozen clock pass the update gate
        display.advance()
        display.finish(success=False)
        # A dirty finish keeps the value at 1 instead of jumping to 3.
        last_line: str = stream.getvalue().rstrip('\n').rsplit('\r', 1)[-1]
        assert '1 of 3' in last_line
        assert stream.getvalue().endswith('\n')


class TestNullDisplay:
    def test_everything_is_a_noop(self) -> None:
        display = _make(False)
        display.start(1)
        display.advance()
        display.tick()
        assert display.task_started(1, 'x') is None
        display.task_finished(1, ok=False)
        display.finish(success=False)


class TestInstanceDisplay:
    def test_wraps_and_drives_unstarted_bar(self) -> None:
        stream = io.StringIO()
        bar: progressbar.ProgressBar = progressbar.ProgressBar(
            max_value=2, fd=stream, poll_interval=0.1
        )
        display = _make(bar)
        display.start(2)
        display.advance(2)
        display.finish()
        assert bar.finished()

    def test_prestarted_bar_is_not_finished_by_us(self) -> None:
        stream = io.StringIO()
        bar = progressbar.ProgressBar(max_value=2, fd=stream)
        bar.start()
        display = _make(bar)
        display.start(2)
        display.advance()
        display.finish()
        assert not bar.finished()


class TestMultiDisplay:
    def _multi(self, total: int = 3) -> _display.MultiDisplay:
        display = _display.make_display(
            'multi',
            total=total,
            poll_interval=0.05,
            bar_kwargs={'fd': io.StringIO()},
        )
        assert isinstance(display, _display.MultiDisplay)
        return display

    def test_satisfies_protocol(self) -> None:
        display = self._multi()
        assert isinstance(display, _display.Display)
        display.finish()

    def test_per_task_bars_appear_and_disappear(self) -> None:
        display = self._multi()
        display.start(3)
        task_bar = display.task_started(1, 'item-a')
        assert task_bar is not None
        assert '1: item-a' in display.multibar
        display.task_finished(1, ok=True)
        assert '1: item-a' not in display.multibar
        display.finish()

    def test_duplicate_labels_get_distinct_keys(self) -> None:
        display = self._multi()
        display.start(3)
        display.task_started(1, 'same')
        display.task_started(2, 'same')
        assert '1: same' in display.multibar
        assert '2: same' in display.multibar
        display.task_finished(1, ok=True)
        display.task_finished(2, ok=False)
        display.finish()

    def test_overall_bar_counts_completions(self) -> None:
        display = self._multi()
        display.start(3)
        display.advance()
        display.advance(2)
        assert display.multibar['Total'].value == 3
        display.finish()

    def test_render_thread_stopped_after_finish(self) -> None:
        display = self._multi()
        display.start(3)
        display.advance(3)
        display.finish()
        assert display.multibar._thread is None  # noqa: SLF001

    def test_task_finished_with_unknown_seq_is_a_noop(self) -> None:
        display = self._multi()
        display.start(1)
        display.task_finished(99, ok=True)
        display.finish()

    def test_finish_removes_live_task_bars(self) -> None:
        display = self._multi()
        display.start(3)
        display.task_started(1, 'still-running')
        display.task_started(2, 'also-running')
        display.finish(success=False)
        assert '1: still-running' not in display.multibar
        assert '2: also-running' not in display.multibar

    def test_adopts_existing_multibar_without_stopping_it(self) -> None:
        multibar = progressbar.MultiBar(fd=io.StringIO())
        multibar.start()
        display = _display.make_display(
            multibar, total=2, poll_interval=0.05, bar_kwargs={}
        )
        display.start(2)
        display.advance(2)
        display.finish()
        assert multibar._thread is not None  # noqa: SLF001
        multibar.stop(timeout=5)


class TestMakeDisplay:
    def test_unknown_mode_raises(self) -> None:
        with pytest.raises(TypeError, match='bogus'):
            _make('bogus')

    def test_bar_kwargs_reach_the_bar(self) -> None:
        stream = io.StringIO()
        display = _make('plain', fd=stream, prefix='PFX ')
        display.start(3)
        display.advance()
        display.finish()
        assert 'PFX' in stream.getvalue()
