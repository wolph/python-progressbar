from __future__ import annotations

import collections.abc
import logging
import time
import timeit
import typing
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


def pytest_configure(config: pytest.Config) -> None:
    logging.basicConfig(
        level=LOG_LEVELS.get(config.option.verbose, logging.DEBUG),
    )


@pytest.fixture(autouse=True)
def disable_native_accelerator(monkeypatch: pytest.MonkeyPatch) -> None:
    # The optional native accelerator (speedups.FastBarIterator) is exercised
    # explicitly in test_native_accelerator.py. Every other test targets the
    # pure-Python iterator (`_iter_python`), so force that path by default when
    # the compiled `speedups` package happens to be installed in the dev/bench
    # environment. Native tests restore it via their own monkeypatch.
    import progressbar.bar as bar_module

    monkeypatch.setattr(bar_module, '_FastBarIterator', None)


@pytest.fixture(autouse=True)
def small_interval(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    # Tests marked `no_freezegun` need real timing conditions (e.g. the perf
    # budget test), so preserve the default _MINIMUM_UPDATE_INTERVAL so the
    # fast-path gate can calibrate and activate correctly.
    if request.node.get_closest_marker('no_freezegun'):
        return
    # Remove the update limit for tests by default
    monkeypatch.setattr(
        progressbar.ProgressBar,
        '_MINIMUM_UPDATE_INTERVAL',
        1e-6,
    )
    monkeypatch.setattr(timeit, 'default_timer', time.time)


@pytest.fixture(autouse=True)
def sleep_faster(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> collections.abc.Iterator[typing.Any]:
    # Tests marked `no_freezegun` need a real, advancing clock (e.g. the
    # gate's perf test, which only activates after a real timing measurement).
    # For those, skip the freezegun wrapping entirely.
    if request.node.get_closest_marker('no_freezegun'):
        yield None
        return

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
