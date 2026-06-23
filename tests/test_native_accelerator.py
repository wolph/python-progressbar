# tests/test_native_accelerator.py
"""Tests for the optional native (Cython) iterator accelerator.

Two groups:

* Integration-coverage tests that exercise ``ProgressBar.__iter__`` dispatch
  and the ``_fast_*`` protocol hooks **without** needing the compiled
  ``speedups`` package (using a fake iterator / direct calls), so they run —
  and keep ``bar.py`` at 100% coverage — in CI where ``speedups`` is absent.
* End-to-end equivalence tests marked ``@requires_speedups`` that drive the
  real ``speedups.progressbar.FastBarIterator``; they run wherever it is
  installed (dev/bench env) and are skipped otherwise.

The conftest ``disable_native_accelerator`` autouse fixture forces the
pure-Python path for the rest of the suite; here we restore the real iterator
explicitly where needed.
"""

from __future__ import annotations

import gc
import io
import re
import sys

import pytest

import progressbar

# Alias (not a `from` import) so CodeQL doesn't flag `progressbar` as imported
# with both `import` and `import from`.
bar_module = progressbar.bar

# Captured at import, before the autouse fixture nulls it for each test.
_REAL_FAST = bar_module._FastBarIterator
HAS_SPEEDUPS = _REAL_FAST is not None
requires_speedups = pytest.mark.skipif(
    not HAS_SPEEDUPS,
    reason='native accelerator (speedups package) not installed',
)

_PERCENT = re.compile(r'(\d+)%')
_ANSI = re.compile(r'\x1b\[[0-9;]*m')


class TTY(io.StringIO):
    def isatty(self) -> bool:
        return True


class RecordingTTY(io.StringIO):
    def isatty(self) -> bool:
        return True

    def repaints(self) -> list[str]:
        return [p for p in self.getvalue().split('\r') if p]


def _percentages(frames: list[str]) -> list[int]:
    out: list[int] = []
    for frame in frames:
        match = _PERCENT.search(_ANSI.sub('', frame))
        if match:
            out.append(int(match.group(1)))
    return out


class _FakeFast:
    """Stand-in for FastBarIterator: records construction, yields nothing.

    Lets the native dispatch branch be covered without the compiled package.
    """

    def __init__(self, bar, iterable):
        self.bar = bar
        self.iterable = iterable

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration


# --- dispatch coverage (no compiled speedups required) --------------------


def test_iter_uses_native_when_available(monkeypatch):
    monkeypatch.setattr(bar_module, '_FastBarIterator', _FakeFast)
    bar = progressbar.ProgressBar(max_value=10, fd=TTY())
    iterable = range(10)
    it = iter(bar(iterable))
    assert isinstance(it, _FakeFast)
    assert it.bar is bar
    assert it.iterable is bar._iterable


def test_iter_falls_back_when_native_absent(monkeypatch):
    monkeypatch.setattr(bar_module, '_FastBarIterator', None)
    bar = progressbar.ProgressBar(max_value=10, fd=TTY())
    it = iter(bar(range(10)))
    assert not isinstance(it, _FakeFast)
    assert list(it) == list(range(10))


def test_iter_falls_back_without_iterable(monkeypatch):
    # Native needs an iterable; iterating a bar without one must not use it.
    monkeypatch.setattr(bar_module, '_FastBarIterator', _FakeFast)
    bar = progressbar.ProgressBar(max_value=10, fd=TTY())
    it = iter(bar)
    assert not isinstance(it, _FakeFast)


def test_iter_falls_back_when_env_disabled(monkeypatch):
    monkeypatch.setattr(bar_module, '_FastBarIterator', _FakeFast)
    monkeypatch.setenv('PROGRESSBAR_DISABLE_FASTPATH', '1')
    bar = progressbar.ProgressBar(max_value=10, fd=TTY())
    it = iter(bar(range(10)))
    assert not isinstance(it, _FakeFast)
    assert list(it) == list(range(10))


# --- protocol hook unit coverage (no compiled speedups required) ----------


def test_fast_begin_starts_once():
    bar = progressbar.ProgressBar(max_value=10, fd=TTY())
    assert bar.start_time is None
    bar._fast_begin()
    assert bar.start_time is not None
    started = bar.start_time
    bar._fast_begin()  # already started: no-op
    assert bar.start_time is started


def test_fast_tick_updates_value():
    bar = progressbar.ProgressBar(max_value=100, fd=TTY())
    bar._fast_begin()
    bar._fast_tick(50)
    assert bar.value == 50


def test_fast_end_finishes_at_100():
    bar = progressbar.ProgressBar(max_value=10, fd=TTY())
    bar._fast_begin()
    bar._fast_end()
    assert bar._finished
    assert bar.value == bar.max_value


def test_fast_end_dirty_keeps_partial_value():
    bar = progressbar.ProgressBar(max_value=10, fd=TTY())
    bar._fast_begin()
    bar._fast_tick(3)
    bar._fast_end_dirty()
    assert bar._finished
    assert bar.value == 3  # not snapped to max_value


# --- end-to-end with the real compiled accelerator ------------------------


@pytest.fixture
def native(monkeypatch):
    """Restore the real FastBarIterator for a single test."""
    monkeypatch.setattr(bar_module, '_FastBarIterator', _REAL_FAST)
    return _REAL_FAST


@requires_speedups
def test_native_iterator_type(native):
    bar = progressbar.ProgressBar(max_value=10, fd=TTY())
    it = iter(bar(range(10)))
    assert type(it) is _REAL_FAST


@requires_speedups
def test_native_yields_all_items_and_final_value(native):
    bar = progressbar.ProgressBar(max_value=100, fd=RecordingTTY())
    out = list(bar(range(100)))
    assert out == list(range(100))
    assert bar.value == 100
    assert bar.percentage == 100.0
    assert bar._finished


@requires_speedups
def test_native_renders_and_finishes_at_100(native):
    fd = RecordingTTY()
    list(progressbar.progressbar(range(500), fd=fd))
    frames = fd.repaints()
    assert frames, 'native path drew nothing'
    pcts = _percentages(frames)
    assert pcts == sorted(pcts), f'percentages not monotonic: {pcts}'
    assert pcts[-1] == 100


@requires_speedups
def test_native_matches_fallback_items(native, monkeypatch):
    # Native run.
    native_items = list(progressbar.progressbar(range(250), fd=RecordingTTY()))
    # Fallback run (force pure-Python).
    monkeypatch.setattr(bar_module, '_FastBarIterator', None)
    fallback_items = list(
        progressbar.progressbar(range(250), fd=RecordingTTY())
    )
    assert native_items == fallback_items == list(range(250))


@requires_speedups
def test_native_generator_input(native):
    def gen():
        yield from range(30)

    bar = progressbar.ProgressBar(max_value=30, fd=RecordingTTY())
    assert list(bar(gen())) == list(range(30))
    assert bar.value == 30


@requires_speedups
def test_native_unknown_length(native):
    bar = progressbar.ProgressBar(
        max_value=progressbar.UnknownLength, fd=RecordingTTY()
    )
    out = list(bar(iter(range(40))))
    assert out == list(range(40))
    assert bar.value == 39
    assert bar._finished


@requires_speedups
def test_native_empty_iterable(native):
    bar = progressbar.ProgressBar(max_value=0, fd=RecordingTTY())
    assert list(bar([])) == []
    assert bar._finished


@requires_speedups
def test_native_with_statement(native):
    fd = RecordingTTY()
    with progressbar.ProgressBar(max_value=10, fd=fd) as bar:
        out = list(bar(range(10)))
    assert out == list(range(10))
    assert bar._finished


@requires_speedups
def test_native_overshoot_clamps(native):
    # max_error=False: iterating past max_value clamps instead of raising.
    bar = progressbar.ProgressBar(
        max_value=5, fd=RecordingTTY(), max_error=False
    )
    out = list(bar(range(20)))
    assert out == list(range(20))  # every item still yielded
    assert bar.value == 5  # clamped to max at finish


@requires_speedups
def test_native_break_restores_streams(native):
    # Issue #212: breaking out of the loop must restore redirected streams,
    # which the cdef iterator does via __dealloc__ (no GeneratorExit hook).
    real_out, real_err = sys.stdout, sys.stderr
    fd = RecordingTTY()
    bar = progressbar.ProgressBar(max_value=1000, fd=fd, redirect_stdout=True)
    for i in bar(range(1000)):
        assert sys.stdout is not real_out  # redirected while iterating
        if i == 5:
            break
    del bar
    gc.collect()
    assert sys.stdout is real_out
    assert sys.stderr is real_err


@requires_speedups
def test_native_exception_restores_streams(native):
    real_out = sys.stdout
    fd = RecordingTTY()
    bar = progressbar.ProgressBar(max_value=1000, fd=fd, redirect_stdout=True)
    with pytest.raises(ValueError):
        for i in bar(range(1000)):
            if i == 5:
                raise ValueError('boom')
    del bar
    gc.collect()
    assert sys.stdout is real_out
