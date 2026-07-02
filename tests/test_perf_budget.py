from __future__ import annotations

import io
import sys
import timeit

import pytest


class _TTY(io.StringIO):
    def isatty(self) -> bool:
        return True


def _overhead_ns(n: int = 200_000) -> float:
    import progressbar

    fd = _TTY()
    base = min(
        timeit.timeit(lambda: [None for _ in range(n)], number=1)
        for _ in range(3)
    )
    wrapped = min(
        timeit.timeit(
            lambda: [None for _ in progressbar.progressbar(range(n), fd=fd)],
            number=1,
        )
        for _ in range(3)
    )
    return (wrapped - base) / n * 1e9


def _clock_read_ns(n: int = 200_000) -> float:
    """Per-iteration cost of a single ``timeit.default_timer()`` read.

    Used as a machine-independent yardstick: it scales with the interpreter
    and runner speed exactly like the progress-bar wrapper does, so the ratio
    between them is stable across machines (dev, CI, different Python builds).
    """
    timer = timeit.default_timer
    base = min(
        timeit.timeit(lambda: [None for _ in range(n)], number=1)
        for _ in range(5)
    )
    read = min(
        timeit.timeit(lambda: [timer() for _ in range(n)], number=1)
        for _ in range(5)
    )
    return (read - base) / n * 1e9


def _coverage_active() -> bool:
    """Return True when a coverage tracer (sys.settrace) is installed.

    pytest-cov installs a CTracer that adds per-line overhead to every
    Python frame, distorting the measured iterator cost.  The budget
    assertion is skipped when tracing is active; the lines still *execute*
    (satisfying the 100 % coverage gate), only the assert is guarded.
    """
    return sys.gettrace() is not None


@pytest.mark.no_freezegun
def test_iterator_overhead_budget() -> None:
    # Measure both before any early return so every line runs under coverage.
    ns = _overhead_ns()
    clock_ns = _clock_read_ns()
    if _coverage_active():
        # Coverage tracing inflates per-frame cost; run the measurement (so
        # all lines are covered) but skip the assertion. The CI perf-budget
        # step runs with --no-cov, where the assertion is enforced.
        return
    # Machine-independent guard. The OLD (pre-gate) path read the clock on
    # every iteration, so its overhead was ~9x a single clock read; the gated
    # path reads no clock on the common iteration, so its overhead is ~1x.
    # A 4x ceiling sits comfortably between the two and tolerates slow/noisy
    # CI runners and different Python builds (absolute ns vary wildly; the
    # ratio does not). The point is to catch a return of the per-iteration
    # clock-read regime, not to micro-police nanoseconds.
    assert ns < 4 * clock_ns, (
        f'iterator overhead {ns:.1f} ns/iter exceeded 4x a clock read '
        f'({clock_ns:.1f} ns) - likely a regression to per-iteration '
        f'clock reads'
    )
