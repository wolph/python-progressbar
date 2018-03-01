from datetime import timedelta
from datetime import datetime
import progressbar
from progressbar import widgets


def test_numeric_samples():
    samples = widgets.SamplesMixin(samples=10)
    bar = progressbar.ProgressBar(widgets=[samples])

    # Force updates in all cases
    samples.INTERVAL = - timedelta(1)

    bar.update(0)
    assert samples(bar, None)[1] == [0, 0, 0]
    bar.update(1)
    assert samples(bar, None)[1] == [0, 0, 0, 1, 1]
    bar.update(2)
    assert samples(bar, None)[1] == [0, 0, 0, 1, 1, 2, 2]

    assert samples(bar, None, delta=True)[1] == 2


def test_timedelta_samples():
    samples = widgets.SamplesMixin(samples=timedelta(seconds=5))
    bar = progressbar.ProgressBar(widgets=[samples])

    # Force updates in all cases
    samples.INTERVAL = - timedelta(1)

    start = datetime(2000, 1, 1)

    bar.value = 1
    bar.last_update_time = start + timedelta(seconds=1)
    assert samples(bar, None, True) == (None, None)

    bar.value = 2
    bar.last_update_time = start + timedelta(seconds=2)
    assert samples(bar, None, True) == (timedelta(0, 1), 1)

    bar.value = 3
    bar.last_update_time = start + timedelta(seconds=3)
    assert samples(bar, None, True) == (timedelta(0, 2), 2)

    assert samples(bar, None)[1] == [1, 2, 3, 3]
