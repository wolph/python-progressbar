import pytest
from datetime import timedelta

import progressbar


@pytest.mark.parametrize('poll_interval,expected', [
    (1, 1),
    (timedelta(seconds=1), 1),
    (0.001, 0.001),
    (timedelta(microseconds=1000), 0.001),
])
@pytest.mark.parametrize('parameter', [
    'poll_interval',
    'min_poll_interval',
])
def test_poll_interval(parameter, poll_interval, expected):
    # Test int, float and timedelta intervals
    bar = progressbar.ProgressBar(**{parameter: poll_interval})
    assert getattr(bar, parameter) == expected


@pytest.mark.parametrize('interval', [
    1,
    timedelta(seconds=1),
])
def test_intervals(monkeypatch, interval):
    monkeypatch.setattr(progressbar.ProgressBar, '_MINIMUM_UPDATE_INTERVAL',
                        interval)
    bar = progressbar.ProgressBar(max_value=100)

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

