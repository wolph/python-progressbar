import contextlib
import gc
import io
import os
import signal
import sys
import time
from datetime import timedelta

import original_examples  # type: ignore
import pytest

import progressbar
from progressbar import utils

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
    for example in examples.examples:
        with contextlib.suppress(ValueError):
            example()


@pytest.mark.filterwarnings('ignore:.*maxval.*:DeprecationWarning')
@pytest.mark.parametrize('example', original_examples.examples)
def test_original_examples(example, monkeypatch) -> None:
    monkeypatch.setattr(progressbar.ProgressBar, '_MINIMUM_UPDATE_INTERVAL', 1)
    monkeypatch.setattr(time, 'sleep', lambda t: None)
    example()


@pytest.mark.parametrize('example', examples.examples)
def test_examples_nullbar(monkeypatch, example) -> None:
    # Patch progressbar to use null bar instead of regular progress bar
    monkeypatch.setattr(progressbar, 'ProgressBar', progressbar.NullBar)
    assert progressbar.ProgressBar._MINIMUM_UPDATE_INTERVAL < 0.0001
    example()


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

    bar = progressbar.ProgressBar(max_value=5, fd=io.StringIO(), term_width=60)
    bar.start()
    bar.fd = ExplodingIO()
    del bar
    gc.collect()

    assert not unraisable


@pytest.mark.skipif(os.name == 'nt', reason='SIGWINCH is POSIX-only')
def test_sigwinch_restored_with_overlapping_bars() -> None:
    # Regression: A5 - with two live bars, finishing them in creation
    # order left a dangling handler installed.
    original = signal.getsignal(signal.SIGWINCH)
    try:
        bar1 = progressbar.ProgressBar(max_value=5, fd=io.StringIO())
        bar1.start()
        bar2 = progressbar.ProgressBar(max_value=5, fd=io.StringIO())
        bar2.start()

        # A resize signal is dispatched to all live bars
        signal.raise_signal(signal.SIGWINCH)
        assert isinstance(bar1.term_width, int)
        assert isinstance(bar2.term_width, int)

        bar1.update(5)
        bar1.finish()
        bar2.update(5)
        bar2.finish()

        assert signal.getsignal(signal.SIGWINCH) is original
    finally:
        signal.signal(signal.SIGWINCH, original)
