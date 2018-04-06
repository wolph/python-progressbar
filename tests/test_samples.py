import time
from datetime import timedelta
from datetime import datetime
import progressbar
from progressbar import widgets


def test_numeric_samples():
    samples = 5
    samples_widget = widgets.SamplesMixin(samples=samples)
    bar = progressbar.ProgressBar(widgets=[samples_widget])

    # Force updates in all cases
    samples_widget.INTERVAL = timedelta(0)

    start = datetime(2000, 1, 1)

    bar.value = 1
    bar.last_update_time = start + timedelta(seconds=bar.value)
    assert samples_widget(bar, None, True) == (None, None)

    for i in range(2, 6):
        bar.value = i
        bar.last_update_time = start + timedelta(seconds=i)
        assert samples_widget(bar, None, True) == (timedelta(0, i - 1), i - 1)

    bar.value = 8
    bar.last_update_time = start + timedelta(seconds=bar.value)
    assert samples_widget(bar, None, True) == (timedelta(0, 6), 6)

    bar.value = 10
    bar.last_update_time = start + timedelta(seconds=bar.value)
    assert samples_widget(bar, None, True) == (timedelta(0, 7), 7)

    bar.value = 20
    bar.last_update_time = start + timedelta(seconds=bar.value)
    assert samples_widget(bar, None, True) == (timedelta(0, 16), 16)

    assert samples_widget(bar, None)[1] == [4, 5, 8, 10, 20]


def test_timedelta_samples():
    samples = timedelta(seconds=5)
    samples_widget = widgets.SamplesMixin(samples=samples)
    bar = progressbar.ProgressBar(widgets=[samples_widget])

    # Force updates in all cases
    samples_widget.INTERVAL = timedelta(0)

    start = datetime(2000, 1, 1)

    bar.value = 1
    bar.last_update_time = start + timedelta(seconds=bar.value)
    assert samples_widget(bar, None, True) == (None, None)

    for i in range(2, 6):
        time.sleep(1)
        bar.value = i
        bar.last_update_time = start + timedelta(seconds=i)
        assert samples_widget(bar, None, True) == (timedelta(0, i - 1), i - 1)

    bar.value = 8
    bar.last_update_time = start + timedelta(seconds=bar.value)
    assert samples_widget(bar, None, True) == (timedelta(0, 6), 6)

    bar.last_update_time = start + timedelta(seconds=bar.value)
    bar.value = 8
    assert samples_widget(bar, None, True) == (timedelta(0, 6), 6)

    bar.value = 10
    bar.last_update_time = start + timedelta(seconds=bar.value)
    assert samples_widget(bar, None, True) == (timedelta(0, 6), 6)

    bar.value = 20
    bar.last_update_time = start + timedelta(seconds=bar.value)
    assert samples_widget(bar, None, True) == (timedelta(0, 10), 10)

    assert samples_widget(bar, None)[1] == [10, 20]


def test_timedelta_no_update():
    samples = timedelta(seconds=0.1)
    samples_widget = widgets.SamplesMixin(samples=samples)
    bar = progressbar.ProgressBar(widgets=[samples_widget])
    bar.update()

    assert samples_widget(bar, None, True) == (None, None)
    assert samples_widget(bar, None, False)[1] == [0]
    assert samples_widget(bar, None, True) == (None, None)
    assert samples_widget(bar, None, False)[1] == [0]

    time.sleep(1)
    assert samples_widget(bar, None, True) == (None, None)
    assert samples_widget(bar, None, False)[1] == [0]

    bar.update(1)
    assert samples_widget(bar, None, True) == (timedelta(0, 1), 1)
    assert samples_widget(bar, None, False)[1] == [0, 1]

    time.sleep(1)
    bar.update(2)
    assert samples_widget(bar, None, True) == (timedelta(0, 1), 1)
    assert samples_widget(bar, None, False)[1] == [1, 2]

    time.sleep(0.01)
    bar.update(3)
    assert samples_widget(bar, None, True) == (timedelta(0, 1), 1)
    assert samples_widget(bar, None, False)[1] == [1, 2]
