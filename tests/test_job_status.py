import io
import time

import pytest

import progressbar
from progressbar import utils


@pytest.mark.parametrize(
    'status',
    [
        True,
        False,
        None,
    ],
)
def test_status(status) -> None:
    with progressbar.ProgressBar(
        widgets=[progressbar.widgets.JobStatusBar('status')],
    ) as bar:
        for _ in range(5):
            bar.increment(status=status, force=True)
            time.sleep(0.1)


def test_job_status_bar_does_not_overflow_width() -> None:
    # Regression: B4 - accumulated job markers made the rendered output
    # wider than the allotted width.
    widget = progressbar.widgets.JobStatusBar('status')
    bar = progressbar.ProgressBar(
        widgets=[widget],
        variables={'status': None},
        max_value=100,
        fd=io.StringIO(),
        term_width=60,
    )
    bar.start()
    data = bar.data()
    data['variables'] = {'status': True}

    width = 5
    output = ''
    for _ in range(10):
        output = widget(bar, data, width=width)

    assert utils.len_color(output) <= width
    bar.finish(dirty=True)


def _make_status_bar() -> tuple:
    bar = progressbar.ProgressBar(
        widgets=[progressbar.widgets.JobStatusBar('status')],
        variables={'status': None},
        max_value=100,
        fd=io.StringIO(),
        term_width=60,
    )
    bar.start()
    data = bar.data()
    data['variables'] = {'status': True}
    return bar, data


def test_job_markers_do_not_interleave_across_bars() -> None:
    # Regression: F2 - a single JobStatusBar reused by two ProgressBars kept
    # its marker history on the widget itself, so markers from one bar bled
    # into the other. State must live in ``progress.extra`` per bar.
    widget = progressbar.widgets.JobStatusBar('status')

    bar_a, data_a = _make_status_bar()
    bar_b, data_b = _make_status_bar()

    width = 20
    for _ in range(3):
        widget(bar_a, data_a, width=width)
    widget(bar_b, data_b, width=width)

    markers_a = widget.get_job_markers(bar_a)
    markers_b = widget.get_job_markers(bar_b)

    assert len(markers_a) == 3
    assert len(markers_b) == 1
    assert markers_a is not markers_b

    bar_a.finish(dirty=True)
    bar_b.finish(dirty=True)
