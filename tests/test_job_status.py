import time

import pytest

import progressbar


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
