import time
import timeit
import pytest
import logging
import freezegun
import progressbar


LOG_LEVELS = {
    '0': logging.ERROR,
    '1': logging.WARNING,
    '2': logging.INFO,
    '3': logging.DEBUG,
}


def pytest_configure(config):
    logging.basicConfig(
        level=LOG_LEVELS.get(config.option.verbose, logging.DEBUG))


@pytest.fixture(autouse=True)
def small_interval(monkeypatch):
    # Remove the update limit for tests by default
    monkeypatch.setattr(
        progressbar.ProgressBar, '_MINIMUM_UPDATE_INTERVAL', 1e-6)
    monkeypatch.setattr(timeit, 'default_timer', time.time)


@pytest.fixture(autouse=True)
def sleep_faster(monkeypatch):
    with freezegun.freeze_time() as fake_time:
        monkeypatch.setattr('time.sleep', fake_time.tick)
        monkeypatch.setattr('timeit.default_timer', time.time)
        yield
