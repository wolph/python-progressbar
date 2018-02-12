from datetime import timedelta

import progressbar


def test_poll_interval():
    # Test int, float and timedelta intervals
    bar = progressbar.ProgressBar(poll_interval=1)
    assert bar.poll_interval.seconds == 1
    assert bar.poll_interval.microseconds == 0

    bar = progressbar.ProgressBar(poll_interval=.001)
    assert bar.poll_interval.seconds == 0
    assert bar.poll_interval.microseconds < 1001

    bar = progressbar.ProgressBar(poll_interval=timedelta(seconds=1))
    assert bar.poll_interval.seconds == 1
    assert bar.poll_interval.microseconds == 0

    bar = progressbar.ProgressBar(poll_interval=timedelta(microseconds=1000))
    assert bar.poll_interval.seconds == 0
    assert bar.poll_interval.microseconds < 1001


def test_intervals():
    bar = progressbar.ProgressBar(max_value=100)
    bar._MINIMUM_UPDATE_INTERVAL = 1

    # Initially there should be no last_update_time
    assert bar.last_update_time is None

    # After updating there should be a last_update_time
    bar.update(1)
    assert bar.last_update_time

    # We should not need an update if the time is nearly the same as before
    last_update_time = bar.last_update_time
    bar.update(2)
    assert bar.last_update_time == last_update_time

    # We should need an update if we're beyond the poll_interval
    bar._last_update_time -= 2
    bar.update(3)
    assert bar.last_update_time != last_update_time

