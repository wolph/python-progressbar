import contextlib
import gc
import io
import logging
import os
import signal
import sys
import time
from datetime import timedelta

import original_examples  # type: ignore
import pytest

import progressbar
from progressbar import (
    bar as bar_module,
    utils,
)

# Import hack to allow for parallel Tox
try:
    import examples
except ImportError:
    import sys

    _project_dir: str = os.path.dirname(os.path.dirname(__file__))
    sys.path.append(_project_dir)
    import examples

    sys.path.remove(_project_dir)


def test_examples(monkeypatch) -> None:
    # examples.py is now a thin runner over docs/examples (see examples.py
    # and tests/test_docs_examples.py); DEMOS/load_example is its public
    # surface, there is no longer a flat `examples.examples` callable list.
    for demo in examples.DEMOS:
        with contextlib.suppress(ValueError):
            examples.load_example(demo).main()


@pytest.mark.filterwarnings('ignore:.*maxval.*:DeprecationWarning')
@pytest.mark.parametrize('example', original_examples.examples)
def test_original_examples(example, monkeypatch) -> None:
    monkeypatch.setattr(progressbar.ProgressBar, '_MINIMUM_UPDATE_INTERVAL', 1)
    monkeypatch.setattr(time, 'sleep', lambda t: None)
    example()


@pytest.mark.parametrize('demo', examples.DEMOS, ids=lambda demo: demo.name)
def test_examples_nullbar(monkeypatch, demo) -> None:
    # Patch progressbar to use null bar instead of regular progress bar
    monkeypatch.setattr(progressbar, 'ProgressBar', progressbar.NullBar)
    assert progressbar.ProgressBar._MINIMUM_UPDATE_INTERVAL < 0.0001
    examples.load_example(demo).main()


def test_nullbar_in_multibar_context_exits() -> None:
    # MultiBar's context manager waits for every member bar to report
    # finished(). A NullBar whose finish() does not flip that flag makes
    # the exit wait spin forever -- exactly what test_examples_nullbar
    # hits for any example that assigns constructed bars into a MultiBar
    # while ProgressBar is patched to NullBar.
    with progressbar.MultiBar() as multibar:
        # A NullBar never builds its default widgets (start() is a
        # no-op), so hand it one: MultiBar's render thread labels each
        # bar and asserts on an empty widget list.
        multibar['task'] = progressbar.NullBar(
            max_value=10, widgets=[progressbar.widgets.Bar()]
        )
        multibar['task'].update(10)
        multibar['task'].finish()


def test_reuse() -> None:
    bar = progressbar.ProgressBar()
    bar.start()
    for i in range(10):
        bar.update(i)
    bar.finish()

    bar.start(init=True)
    for i in range(10):
        bar.update(i)
    bar.finish()

    bar.start(init=False)
    for i in range(10):
        bar.update(i)
    bar.finish()


def test_dirty() -> None:
    bar = progressbar.ProgressBar()
    bar.start()
    assert bar.started()
    for i in range(10):
        bar.update(i)
    bar.finish(dirty=True)
    assert bar.finished()
    assert bar.started()


def test_negative_maximum() -> None:
    with (
        pytest.raises(ValueError),
        progressbar.ProgressBar(max_value=-1) as progress,
    ):
        progress.start()


def test_progressbar_accepts_total_alias() -> None:
    bar = progressbar.ProgressBar(total=5, fd=io.StringIO())
    assert bar.max_value == 5


def test_progressbar_max_value_wins_over_total() -> None:
    bar = progressbar.ProgressBar(max_value=7, total=5, fd=io.StringIO())
    assert bar.max_value == 7


def test_progressbar_desc_maps_to_prefix() -> None:
    stream = io.StringIO()
    with progressbar.ProgressBar(
        desc='Loading',
        max_value=1,
        fd=stream,
    ) as bar:
        bar.update(1, force=True)
    assert 'Loading' in stream.getvalue()


def test_progressbar_postfix_updates_live() -> None:
    stream = io.StringIO()
    widgets = [progressbar.Postfix()]
    with progressbar.ProgressBar(
        max_value=2,
        widgets=widgets,
        postfix={'loss': 1.0},
        fd=stream,
    ) as bar:
        bar.update(1, postfix={'loss': 0.5}, force=True)
    assert 'loss=0.5' in stream.getvalue()


def test_progressbar_postfix_preserves_default_widgets() -> None:
    stream = io.StringIO()
    with progressbar.ProgressBar(
        max_value=2,
        postfix='ok',
        fd=stream,
    ) as bar:
        bar.update(2, force=True)
    rendered = stream.getvalue()
    assert 'ok' in rendered
    assert '100%' in rendered or '(2 of 2)' in rendered


def test_progressbar_empty_desc_maps_to_prefix() -> None:
    stream = io.StringIO()
    with progressbar.ProgressBar(desc='', max_value=1, fd=stream) as bar:
        bar.update(1, force=True)
    assert stream.getvalue().startswith(': ')


def test_shortcut_passes_total_desc_and_postfix() -> None:
    stream = io.StringIO()
    values = list(
        progressbar.progressbar(
            range(2),
            total=2,
            desc='Items',
            postfix='ok',
            fd=stream,
        )
    )
    assert values == [0, 1]
    rendered = stream.getvalue()
    assert 'Items' in rendered
    assert 'ok' in rendered


def test_elapsed_data_spans_days() -> None:
    # Regression: A1 - days_elapsed was computed from timedelta.seconds,
    # which only contains the sub-day component.
    bar = progressbar.ProgressBar(
        max_value=10, fd=io.StringIO(), term_width=60
    )
    bar.start()
    bar.start_time -= timedelta(days=2, hours=3, minutes=4)
    data = bar.data()

    expected_days = 2 + (3 * 3600 + 4 * 60) / 86400
    assert data['days_elapsed'] == pytest.approx(expected_days, abs=0.01)


@pytest.mark.no_freezegun
def test_data_is_a_pure_snapshot(monkeypatch) -> None:
    # `data()` must be a pure read of the current state: calling it must not
    # mutate the timing fields (`_last_update_time` / `_last_update_timer`).
    # The redraw path refreshes those via `_mark_update()`, not the getter.
    #
    # A strictly-increasing clock makes any hidden mutation observable: on the
    # old code each data() call re-stamped the fields with a fresh (larger)
    # value, so two calls would disagree.
    import timeit as _timeit

    import progressbar.bar as bar_module

    ticks = iter(range(1_700_000_000, 1_700_001_000))

    def fake_clock() -> float:
        return float(next(ticks))

    bar = progressbar.ProgressBar(
        max_value=10, fd=io.StringIO(), term_width=60
    )
    bar.start()

    monkeypatch.setattr(bar_module.time, 'time', fake_clock)
    monkeypatch.setattr(_timeit, 'default_timer', fake_clock)

    time_before = bar._last_update_time
    timer_before = bar._last_update_timer

    first = bar.data()
    second = bar.data()

    # Neither the wall-clock nor the perf-counter timing state may change.
    assert bar._last_update_time == time_before
    assert bar._last_update_timer == timer_before
    # And the two snapshots agree on the timing-derived fields.
    assert first['last_update_time'] == second['last_update_time']
    assert first['total_seconds_elapsed'] == second['total_seconds_elapsed']
    assert first['time_elapsed'] == second['time_elapsed']


def test_restart_after_finish_writes_final_newline() -> None:
    # Regression: A2 - init() did not reset _finished, so a reused bar
    # never wrote its final newline (and never flushed) again.
    bar = progressbar.ProgressBar(
        max_value=5, fd=io.StringIO(), term_width=60, line_breaks=False
    )
    bar.start()
    bar.update(5)
    bar.finish()
    assert bar.fd.getvalue().endswith('\n')

    bar.fd = io.StringIO()
    bar.start()
    assert not bar._finished
    bar.update(5)
    bar.finish()
    assert bar.fd.getvalue().endswith('\n')


def test_repeated_finish_keeps_capturing_balanced() -> None:
    # Regression: A2 - every finish() call decremented the global
    # capturing counter, even when the bar was already finished.
    baseline = utils.streams.capturing
    try:
        bar = progressbar.ProgressBar(
            max_value=5, fd=io.StringIO(), term_width=60
        )
        bar.start()
        bar.update(5)
        bar.finish()
        bar.finish()
        assert utils.streams.capturing == baseline
    finally:
        utils.streams.capturing = baseline


def test_del_suppresses_finish_errors(monkeypatch) -> None:
    # Regression: A4 - __del__ only suppressed AttributeError; any other
    # exception from finish() leaked out of the finalizer (reported via
    # sys.unraisablehook during garbage collection).
    class ExplodingIO(io.StringIO):
        def write(self, value: str) -> int:
            raise ValueError('I/O operation on closed file')

    unraisable: list[object] = []
    monkeypatch.setattr(sys, 'unraisablehook', unraisable.append)
    baseline_capturing = utils.streams.capturing

    bar = progressbar.ProgressBar(max_value=5, fd=io.StringIO(), term_width=60)
    bar.start()
    bar_id = id(bar)
    # The listener registry deliberately owns running bars. Remove this
    # test's artificial reference so the finalizer path is exercised.
    utils.streams.listeners.discard(bar)
    bar.fd = ExplodingIO()
    del bar
    gc.collect()

    assert not unraisable
    assert all(id(listener) != bar_id for listener in utils.streams.listeners)
    assert utils.streams.capturing == baseline_capturing


def test_finish_cleans_stream_listener_when_render_fails() -> None:
    class ExplodingIO(io.StringIO):
        def write(self, value: str) -> int:
            raise ValueError('I/O operation on closed file')

    bar = progressbar.ProgressBar(max_value=5, fd=io.StringIO(), term_width=60)
    bar.start()
    assert bar in utils.streams.listeners

    bar.fd = ExplodingIO()
    with pytest.raises(ValueError, match='I/O operation on closed file'):
        bar.finish()

    assert bar not in utils.streams.listeners


def test_start_cleans_stream_listener_when_validation_fails() -> None:
    bar = progressbar.ProgressBar(
        min_value=-2,
        max_value=-1,
        fd=io.StringIO(),
    )

    with pytest.raises(ValueError, match='max_value out of range'):
        bar.update(-1)

    assert bar not in utils.streams.listeners


def test_start_preserves_original_error_when_base_cleanup_fails(
    monkeypatch,
) -> None:
    def fail_start(self, max_value=None):
        raise ValueError('resize start failed')

    def fail_finish(self):
        raise RuntimeError('base cleanup failed')

    monkeypatch.setattr(bar_module.ResizableMixin, 'start', fail_start)
    monkeypatch.setattr(bar_module.ProgressBarBase, 'finish', fail_finish)

    bar = progressbar.ProgressBar(max_value=5, fd=io.StringIO())
    with pytest.raises(ValueError, match='resize start failed'):
        bar.start()


@pytest.mark.skipif(os.name == 'nt', reason='SIGWINCH is POSIX-only')
def test_sigwinch_restored_with_overlapping_bars(
    isolated_resize_registry,
) -> None:
    # Regression: A5 - with two live bars, finishing them in creation
    # order left a dangling handler installed. The fixture starts from
    # SIG_IGN, so "still installed" and "restored" can be told apart.
    bar1 = progressbar.ProgressBar(max_value=5, fd=io.StringIO())
    bar1.start()
    bar2 = progressbar.ProgressBar(max_value=5, fd=io.StringIO())
    bar2.start()

    # The first bar installs the shared handler
    assert signal.getsignal(signal.SIGWINCH) is not signal.SIG_IGN

    # A resize signal is dispatched to all live bars
    signal.raise_signal(signal.SIGWINCH)
    assert isinstance(bar1.term_width, int)
    assert isinstance(bar2.term_width, int)

    bar1.update(5)
    bar1.finish()
    # The handler must stay installed while bar2 is still live
    assert signal.getsignal(signal.SIGWINCH) is not signal.SIG_IGN

    bar2.update(5)
    bar2.finish()
    # The last bar to finish restores the previous handler
    assert signal.getsignal(signal.SIGWINCH) is signal.SIG_IGN


@pytest.fixture
def isolated_resize_registry():
    """Give a test an empty `_ResizeRegistry` and the handler it found.

    The registry is process-global, so bars left registered by other
    tests (and a handler they left installed) would otherwise leak into
    the assertions. Everything is put back afterwards.
    """
    import progressbar.bar as bar_module

    registry = bar_module._ResizeRegistry
    saved_handler = signal.getsignal(signal.SIGWINCH)
    saved_bars = list(registry.bars)
    saved_prev = registry.previous_handler
    registry.bars.clear()
    registry.previous_handler = None
    signal.signal(signal.SIGWINCH, signal.SIG_IGN)
    try:
        yield registry
    finally:
        registry.bars.clear()
        for restored_bar in saved_bars:
            registry.bars.add(restored_bar)
        registry.previous_handler = saved_prev
        signal.signal(signal.SIGWINCH, saved_handler)


@pytest.mark.skipif(os.name == 'nt', reason='SIGWINCH is POSIX-only')
def test_sigwinch_dispatch_survives_a_raising_bar(
    isolated_resize_registry, caplog
) -> None:
    # A35: one bar's failing `_handle_resize` skipped every later bar
    # and raised out of the signal handler into whatever the main
    # thread was doing.
    class Broken(progressbar.ProgressBar):
        def _handle_resize(self, signum=None, frame=None) -> None:
            if signum is not None:
                raise RuntimeError('spam')
            super()._handle_resize(signum, frame)

    broken = Broken(max_value=5, fd=io.StringIO())
    broken.start()
    other = progressbar.ProgressBar(max_value=5, fd=io.StringIO())
    other.start()
    other.term_width = 1
    try:
        with caplog.at_level(logging.WARNING, logger='progressbar.bar'):
            signal.raise_signal(signal.SIGWINCH)
        assert other.term_width != 1
        assert any(
            record.levelno == logging.WARNING and record.exc_info
            for record in caplog.records
        )
    finally:
        broken.finish()
        other.finish()


@pytest.mark.skipif(os.name == 'nt', reason='SIGWINCH is POSIX-only')
def test_sigwinch_restored_after_a_leaked_bar(
    isolated_resize_registry,
) -> None:
    # A35: a bar that was never finished dropped out of the WeakSet,
    # and nobody restored the handler it had installed. Registration
    # happens at construction, so a bar that is built and dropped
    # without start() is the shape that gets collected (a started bar
    # is kept alive by `streams.listeners` until it finishes).
    bar = progressbar.ProgressBar(max_value=5, fd=io.StringIO())
    assert signal.getsignal(signal.SIGWINCH) is not signal.SIG_IGN
    bar._finished = True  # keep __del__ from finishing it for us
    del bar
    gc.collect()
    assert signal.getsignal(signal.SIGWINCH) is signal.SIG_IGN


@pytest.mark.skipif(os.name == 'nt', reason='SIGWINCH is POSIX-only')
def test_sigwinch_previous_handler_survives_an_off_thread_finish(
    isolated_resize_registry,
) -> None:
    # A35: `signal.signal` raises ValueError off the main thread, the
    # bar was already unregistered, and the next bar then saved the
    # registry's own handler as the "previous" one, losing SIG_IGN.
    import threading

    first = progressbar.ProgressBar(max_value=5, fd=io.StringIO())
    first.start()
    thread = threading.Thread(target=first.finish)
    thread.start()
    thread.join(10)
    assert not thread.is_alive()

    second = progressbar.ProgressBar(max_value=5, fd=io.StringIO())
    second.start()
    second.finish()
    assert signal.getsignal(signal.SIGWINCH) is signal.SIG_IGN


@pytest.mark.skipif(os.name == 'nt', reason='SIGWINCH is POSIX-only')
def test_sigwinch_restores_the_default_when_no_python_handler_was_set(
    isolated_resize_registry,
) -> None:
    # A35: `signal.getsignal` returns None for a handler installed from
    # C, and `signal.signal(SIGWINCH, None)` is a TypeError, so the
    # registry's handler stayed installed for good.
    registry = isolated_resize_registry
    bar = progressbar.ProgressBar(max_value=5, fd=io.StringIO())
    bar.start()
    registry.previous_handler = None
    bar.finish()
    assert signal.getsignal(signal.SIGWINCH) is signal.SIG_DFL
