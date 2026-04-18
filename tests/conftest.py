from __future__ import annotations

import logging
import time
import timeit
from datetime import datetime, timezone

import freezegun
import pytest

import progressbar

LOG_LEVELS: dict[str, int] = {
    '0': logging.ERROR,
    '1': logging.WARNING,
    '2': logging.INFO,
    '3': logging.DEBUG,
}


def pytest_configure(config) -> None:
    logging.basicConfig(
        level=LOG_LEVELS.get(config.option.verbose, logging.DEBUG),
    )


@pytest.fixture(autouse=True)
def small_interval(monkeypatch) -> None:
    # Remove the update limit for tests by default
    monkeypatch.setattr(
        progressbar.ProgressBar,
        '_MINIMUM_UPDATE_INTERVAL',
        1e-6,
    )
    monkeypatch.setattr(timeit, 'default_timer', time.time)


@pytest.fixture(autouse=True)
def sleep_faster(monkeypatch):
    # Compute the local UTC offset so freezegun uses the same timezone as
    # the local system. Using datetime.now(timezone.utc).astimezone() avoids
    # the deprecated datetime.utcnow() (deprecated since Python 3.12).
    local_offset = datetime.now(timezone.utc).astimezone().utcoffset()
    offset_hours = local_offset.total_seconds() / 3600

    freeze_time = freezegun.freeze_time(tz_offset=offset_hours)
    with freeze_time as fake_time:
        monkeypatch.setattr('time.sleep', fake_time.tick)
        monkeypatch.setattr('timeit.default_timer', time.time)
        yield freeze_time
