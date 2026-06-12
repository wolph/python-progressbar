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
