# tests/test_fastpath.py
from __future__ import annotations

import gc
import io
import itertools
import re
import sys
import typing

import pytest

import progressbar

_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')
_PERCENT = re.compile(r'(\d+)%')


def _drawn_percentages(repaints: list[str]) -> list[int]:
    """Extract the integer percentage rendered in each repaint frame.

    The ``Percentage`` widget renders e.g. ``  4%|###...`` (no space before the
    bar), so the ``%`` token is glued to the bar body; a regex is more robust
    than whitespace tokenization.
    """
    out: list[int] = []
    for frame in repaints:
        match = _PERCENT.search(_ANSI_ESCAPE.sub('', frame))
        if match:
            out.append(int(match.group(1)))
    return out


def _assert_cadence_parity(gated: list[str], ungated: list[str]) -> None:
    """Assert the gated run kept the ungated run's rate-limited cadence.

    This is the correct equivalence criterion (NOT byte-exact frames): the gate
    may legitimately differ by a frame or two: its step is sized by time,
    but it must not silently drop a large fraction of redraws the way the
    original regression did (16 gated vs. 25 ungated buckets, a ~36% drop). The
    checks below fail for such a gate while tolerating the benign +/-1 frame
    wobble of the closed loop.
    """
    g_count = len(gated)
    u_count = len(ungated)
    # 1) Rate-limited cadence parity: counts within a frame or two of each
    #    other. A ~36% drop (e.g. 21 vs 33) fails this by a wide margin.
    assert abs(g_count - u_count) <= 2, (
        f'gated redraw count {g_count} diverged from ungated {u_count} '
        f'beyond rate-limited wobble'
    )
    # Sanity: the slow loop really did redraw many distinct frames, so the
    # comparison is meaningful (not "both drew nothing").
    assert len(set(gated)) > 10

    g_pcts = _drawn_percentages(gated)
    u_pcts = _drawn_percentages(ungated)
    assert g_pcts, 'no percentage tokens found in gated frames'
    # 2) Monotonic and reaches 100% at the end.
    assert g_pcts == sorted(g_pcts), (
        f'gated percentages not monotonic: {g_pcts}'
    )
    assert g_pcts[-1] == 100, f'gated did not reach 100%: {g_pcts[-1]}'

    # 3) No large gap: ignoring the final jump to 100% (the loop only covers
    #    part of the range, then finish() snaps to 100%), no consecutive
    #    percentages is farther apart than a small multiple of the ungated
    #    per-redraw window. A gate that drops whole stretches of the bar shows
    #    up as an oversized inner gap here.
    inner_gaps = [g_pcts[i + 1] - g_pcts[i] for i in range(len(g_pcts) - 2)]
    ungated_window = max(
        (u_pcts[i + 1] - u_pcts[i] for i in range(len(u_pcts) - 2)),
        default=1,
    )
    if inner_gaps:
        assert max(inner_gaps) <= 3 * max(ungated_window, 1), (
            f'gated skipped a stretch of the bar: max inner gap '
            f'{max(inner_gaps)} > 3x ungated window {ungated_window}'
        )


class RecordingTTY(io.StringIO):
    """A fake terminal that records each repaint (\\r-delimited write)."""

    def isatty(self) -> bool:
        return True

    def repaints(self) -> list[str]:
        # Each redraw starts with '\r'; split and drop the empty head.
        return [p for p in self.getvalue().split('\r') if p]


def run_iter(n: int, **kwargs: typing.Any) -> tuple[RecordingTTY, list[int]]:
    fd = RecordingTTY()
    seen = list(progressbar.progressbar(range(n), fd=fd, **kwargs))
    return fd, seen


def test_iterates_all_items_in_order():
    _, seen = run_iter(2000)
    assert seen == list(range(2000))


def test_value_is_live_during_iteration():
    fd = RecordingTTY()
    bar = progressbar.ProgressBar(max_value=500, fd=fd)
    last = -1
    for i in bar(range(500)):
        # bar.value == i: value reflects items yielded so far (pre-increment),
        # so at the start of the body for item i, value is i (not i+1).
        assert bar.value == i, f'bar.value mismatch at i={i}: got {bar.value}'
        # previous_value stays byte-identical to the pre-gate behavior on
        # EVERY iteration (not just at redraws): the value before the current
        # one (0 for the first item, set by start()'s forced draw).
        expected_prev = i - 1 if i else 0
        assert bar.previous_value == expected_prev, (
            f'previous_value mismatch at i={i}: got {bar.previous_value}'
        )
        last = i
    assert last == 499


def test_final_repaint_reaches_completion():
    fd, _ = run_iter(1000)
    repaints = fd.repaints()
    assert repaints, 'expected at least one repaint'
    assert '100%' in repaints[-1]


def test_repaints_are_monotonic_in_percentage():
    fd, _ = run_iter(5000)
    pcts = []
    for p in fd.repaints():
        # Repaints contain ANSI color codes; strip before tokenizing.
        plain = _ANSI_ESCAPE.sub('', p)
        for tok in plain.split():
            if tok.endswith('%'):
                pcts.append(float(tok[:-1]))
                break
    assert pcts, 'expected at least one percentage token in repaints'
    assert pcts == sorted(pcts), 'percentage went backwards'
    assert pcts[0] >= 0 and pcts[-1] == 100.0


def test_empty_iterable_finishes_cleanly():
    fd, seen = run_iter(0)
    assert seen == []
    assert fd.getvalue() != ''  # start+finish still draw


def test_single_item():
    fd, seen = run_iter(1)
    assert seen == [0]
    assert '100%' in fd.repaints()[-1]


def test_early_break_finishes_dirty():
    fd = RecordingTTY()
    bar = progressbar.ProgressBar(max_value=1000, fd=fd)
    for i in bar(range(1000)):
        if i == 10:
            break
    del bar  # trigger GeneratorExit cleanup path (issue #212)
    gc.collect()
    # A dirty finish must NOT jump the bar to 100%.
    assert '100%' not in fd.repaints()[-1]


def test_exception_in_body_propagates_and_finishes():
    fd = RecordingTTY()
    bar = progressbar.ProgressBar(max_value=1000, fd=fd)

    class BoomError(Exception):
        pass

    with pytest.raises(BoomError):
        for i in bar(range(1000)):
            if i == 5:
                raise BoomError
    gc.collect()
    assert fd.getvalue() != ''


def fixed_clock(monkeypatch, dt: float):
    """Patch the timer used by bar.py to advance by `dt` per read."""
    bar_module = progressbar.bar

    counter = itertools.count()

    def fake_timer() -> float:
        return next(counter) * dt

    monkeypatch.setattr(bar_module.timeit, 'default_timer', fake_timer)


def test_redraw_count_is_rate_limited(monkeypatch):
    # ~1ms per timer read, 50ms min_poll_interval => far fewer redraws than N.
    fixed_clock(monkeypatch, dt=0.001)
    fd, _ = run_iter(20000)
    n_repaints = len(fd.repaints())
    assert 1 < n_repaints < 2000, n_repaints  # not one-per-iteration


def test_gate_state_initialized():
    bar = progressbar.ProgressBar(max_value=100)
    assert bar._gate_enabled is True
    assert bar._gate_step >= 1
    assert bar._next_update == 0
    assert bar._last_drawn_value is None


def _controlled_clock(monkeypatch) -> list[float]:
    """Patch bar.py's timer to read one mutable value; return that list."""
    clock = [0.0]
    monkeypatch.setattr(
        progressbar.bar.timeit, 'default_timer', lambda: clock[0]
    )
    return clock


def test_gate_calibrates_step_from_measured_rate(monkeypatch):
    # The gate calibrates _gate_step from the value/time elapsed between two
    # redraws (no separate _gate_last_* state needed). UnknownLength makes any
    # value advance redraw (rate-limited), so the measurement is deterministic.
    clock = _controlled_clock(monkeypatch)
    bar = progressbar.ProgressBar(
        max_value=progressbar.UnknownLength, fd=RecordingTTY()
    )
    bar.min_poll_interval = 0.05
    bar.start()  # forced draw at t=0; no prior sample, so step stays 1
    assert bar._gate_step == 1
    clock[0] = 0.10  # 0.10 s later
    bar.update(1000)  # redraw: 1000 iters over 0.10 s
    # step = int((1000 - 0) * min_poll_interval / interval) = 1000*0.05/0.10
    assert bar._gate_step == 500
    assert bar._next_update == 1000 + 500


def test_gate_backs_off_when_calibrated_and_no_redraw(monkeypatch):
    clock = _controlled_clock(monkeypatch)
    bar = progressbar.ProgressBar(
        max_value=progressbar.UnknownLength, fd=RecordingTTY()
    )
    bar.min_poll_interval = 0.05
    bar.start()
    clock[0] = 0.10
    bar.update(1000)  # calibrate: step=500, _next_update=1500
    step = bar._gate_step
    assert step == 500
    # Time frozen: an update past the threshold finds delta == 0 (no redraw),
    # so the gate backs off (doubles the step) instead of re-checking often.
    bar.update(1500)
    assert bar._gate_step == step * 2
    assert bar._next_update == 1500 + step * 2


def test_previous_value_tracks_last_redraw(monkeypatch):
    fixed_clock(monkeypatch, dt=0.001)
    bar = progressbar.ProgressBar(max_value=10000, fd=RecordingTTY())
    bar.start()
    drawn: list[int] = []
    real_parents = bar._update_parents

    def spy(value):
        real_parents(value)
        drawn.append(bar.value)

    bar._update_parents = spy
    for i in range(1, 10001):
        bar.update(i)
    bar.finish()
    # previous_value must equal one of the actually-drawn values, not i-1.
    assert bar.previous_value in drawn


def test_last_drawn_value_pinned_on_skipped_update(monkeypatch):
    """The gate's pixel reference advances only when a redraw happens.

    `_last_drawn_value` (the private pixel reference used by `_needs_update`)
    must stay pinned to the value at the last actual draw, even as later
    `update()` calls advance `self.value` without redrawing. The public
    `previous_value` keeps its original meaning: the value before the most
    recent `update()` call.

    After a draw at value=3 (from 0) and two rate-limited skips at 4 then 5:
        _last_drawn_value == 3  (pinned to the drawn value, for pixel check)
        previous_value     == 4  (value before the update(5) call)
    """
    bar_module = progressbar.bar

    # Freeze-then-advance clock: start at 0, jump to 1.0 so update(3) draws,
    # then keep it at 1.0 so subsequent updates are rate-limited (skipped).
    _time: list[float] = [0.0]

    def timer() -> float:
        return _time[0]

    monkeypatch.setattr(bar_module.timeit, 'default_timer', timer)

    bar = progressbar.ProgressBar(max_value=100, fd=RecordingTTY())
    bar.start()  # _last_update_timer = 0.0

    # Advance time far past min_poll_interval (0.05 s) => update(3) draws.
    _time[0] = 1.0
    bar.update(3)
    assert bar._last_drawn_value == 3  # a redraw happened at value 3

    # Time frozen at 1.0: delta == 0 => _needs_update() returns False, so the
    # next updates advance self.value but do not redraw.
    bar.update(4)
    bar.update(5)

    # Pixel reference stays at the last drawn value; public previous_value
    # tracks the value before the most recent update() call.
    assert bar._last_drawn_value == 3, (
        f'_last_drawn_value should stay at last-drawn (3), '
        f'got {bar._last_drawn_value!r}'
    )
    assert bar.value == 5  # liveness preserved on the manual path
    assert bar.previous_value == 4  # value before update(5)


def test_gate_disabled_skips_calibration():
    """When _gate_enabled is False the gate is never (re)calibrated."""
    bar = progressbar.ProgressBar(max_value=100, fd=RecordingTTY())
    bar.start()
    bar._gate_enabled = False
    initial_next = bar._next_update
    bar.update(50)
    # Neither the calibration nor the back-off branch runs: _next_update is
    # left untouched while the fast path is disabled.
    assert bar._next_update == initial_next


@pytest.mark.no_freezegun
def test_manual_update_skips_clock_when_gated(monkeypatch):
    bar_module = progressbar.bar

    reads: dict[str, int] = {'n': 0}
    real = bar_module.timeit.default_timer

    def counting() -> float:
        reads['n'] += 1
        return real()

    bar = progressbar.ProgressBar(max_value=10**7, fd=RecordingTTY())
    bar.start()
    monkeypatch.setattr(bar_module.timeit, 'default_timer', counting)
    before = reads['n']
    for i in range(1, 1_000_001):
        bar.update(i)
    reads_during = reads['n'] - before
    bar.finish()
    # Far fewer clock reads than updates (gate skips the common path).
    assert reads_during < 100_000, reads_during


def _iter_clock(monkeypatch, dt: float) -> dict[str, int]:
    """Patch the timer so its value depends on a shared loop ITERATION.

    Unlike ``fixed_clock`` (which ties time to the *number of reads*), this
    makes the clock return ``state['i'] * dt`` regardless of how many times
    it is read. The gated and ungated bars read the clock a different number
    of times, so a per-read clock would make them diverge for the wrong
    reason. Tying time to the iteration index keeps both runs seeing the
    exact same wall time at every iteration.
    """
    bar_module = progressbar.bar

    state: dict[str, int] = {'i': 0}
    monkeypatch.setattr(
        bar_module.timeit,
        'default_timer',
        lambda: state['i'] * dt,
    )
    return state


def _drawn_frames(
    disable_gate: bool,
    monkeypatch,
    *,
    widgets: list | None = None,
    dt: float = 0.06,
    n: int = 4000,
    maxv: int = 10_000,
) -> list[str]:
    state = _iter_clock(monkeypatch, dt)
    fd = RecordingTTY()
    if widgets is None:
        # poll_interval stays None for this widget set, which is the case
        # that exposed the uncalibrated back-off bug.
        widgets = [progressbar.Percentage(), progressbar.Bar()]
    bar = progressbar.ProgressBar(max_value=maxv, fd=fd, widgets=widgets)
    bar.start()
    if disable_gate:
        bar._gate_enabled = False
    for i in range(1, n + 1):
        state['i'] = i  # advance wall time per ITERATION
        bar.update(i)
    bar.finish()
    return fd.repaints()


def test_gated_matches_ungated_drawn_frames(monkeypatch):
    """The gate must keep the ungated rate-limited cadence (manual path).

    For a ``poll_interval is None`` bar over a slow loop (``dt`` >=
    ``min_poll_interval`` so a redraw is due at each item), a gated bar must
    redraw at the same rate-limited cadence as an identical bar with the gate
    disabled. This is the reviewer's repro of the regression where the gate
    dropped ~36% of the buckets the baseline rendered.

    The criterion is rate-limited cadence parity, NOT byte-exact frames: the
    closed-loop gate sizes its step by time, so a +/-1 frame wobble is benign
    and expected. ``_assert_cadence_parity`` tolerates that wobble while still
    failing for a gate that drops a large fraction of redraws.
    """
    with monkeypatch.context() as m:
        gated = _drawn_frames(False, m)
    with monkeypatch.context() as m:
        ungated = _drawn_frames(True, m)

    _assert_cadence_parity(gated, ungated)


def _drawn_frames_iter(
    disable_gate: bool,
    monkeypatch,
    *,
    widgets: list | None = None,
    dt: float = 0.06,
    n: int = 4000,
    maxv: int = 10_000,
) -> list[str]:
    """Drive the bar through its ITERATOR path and record drawn frames.

    Mirrors ``_drawn_frames`` but uses ``ProgressBar.__iter__`` (the iterator
    fast path) instead of manual ``update()`` calls. ``__iter__`` skips
    ``start()`` when ``start_time`` is already set, so we call ``start()``
    explicitly first (which resets the gate via ``init()``), then flip
    ``_gate_enabled`` to choose gated vs. ungated. Both runs share the same
    iteration-driven clock so they observe identical wall time per iteration.
    """
    state = _iter_clock(monkeypatch, dt)
    fd = RecordingTTY()
    if widgets is None:
        # poll_interval stays None for this widget set, which is the case
        # that exposed the uncalibrated back-off bug in the iterator path.
        widgets = [progressbar.Percentage(), progressbar.Bar()]
    bar = progressbar.ProgressBar(max_value=maxv, fd=fd, widgets=widgets)
    bar.start()  # resets _gate_enabled via init(); primes start_time
    if disable_gate:
        bar._gate_enabled = False

    class _IterClockRange:
        """An iterable that advances the shared clock once per item.

        Returning a fresh iterator each time keeps ``bar.value`` and the
        iteration index aligned regardless of how many times the clock is read.
        """

        def __len__(self) -> int:
            return n

        def __iter__(self):
            for i in range(n):
                state['i'] = i  # advance wall time per ITERATION
                yield i

    # __iter__ does not call start() again because start_time is already set.
    for _ in bar(_IterClockRange()):
        pass
    return fd.repaints()


def test_iterator_gated_matches_ungated_drawn_frames(monkeypatch):
    """The ITERATOR-path gate must keep the ungated rate-limited cadence.

    Reviewer's repro of the regression in ``__iter__``: for a
    ``poll_interval is None`` bar over a slow, iteration-driven clock
    (``dt`` >= ``min_poll_interval`` so a redraw is due at each item), the
    iterator path's inline gate skipped ``update()`` based on ``_next_update``
    with a bogus pre-measurement step, leaping over whole buckets and dropping
    redraws the ungated bar rendered.

    With the fix (``_gate_step`` starts at 1 so ``__iter__`` calls ``update()``
    every iteration until a real measurement grows it), the gated
    iterator must redraw at the same rate-limited cadence as an identical bar
    driven through the same iterator with the gate disabled. As in the manual
    path the criterion is cadence parity, not byte-exact frames.
    """
    with monkeypatch.context() as m:
        gated = _drawn_frames_iter(False, m)
    with monkeypatch.context() as m:
        ungated = _drawn_frames_iter(True, m)

    _assert_cadence_parity(gated, ungated)


# NOTE: A default-widget bar (poll_interval is set by the Timer/animation
# widgets) intentionally does NOT get a byte-exact equivalence test. Its
# redraws are time-driven, not value-driven, so matching the ungated frame
# sequence would require the gate to read the clock on every call - which is
# precisely the read the gate exists to skip. The correctness obligation only
# binds the value-driven (poll_interval is None) case above, which is also the
# case that exposed the uncalibrated back-off bug.


def test_next_direct_exhaustion_calls_finish():
    """Direct next(bar) still finishes the bar on StopIteration."""
    fd = RecordingTTY()
    bar = progressbar.ProgressBar(max_value=2, fd=fd)
    bar(range(2))
    bar.start()
    assert next(bar) == 0
    assert next(bar) == 1
    with pytest.raises(StopIteration):
        next(bar)  # exhausts iterable, calls finish()
    assert '100%' in fd.repaints()[-1]


def test_shortcut_has_single_generator_layer():
    import types

    gen = progressbar.progressbar(range(3), fd=RecordingTTY())
    assert isinstance(gen, types.GeneratorType)
    # It is the bar's own __iter__ generator, not a wrapper: compare the
    # generator's code object to ProgressBar.__iter__ (robust across versions).
    assert gen.gi_code is progressbar.ProgressBar.__iter__.__code__


def test_env_disables_fastpath(monkeypatch):
    monkeypatch.setenv('PROGRESSBAR_DISABLE_FASTPATH', '1')
    bar = progressbar.ProgressBar(max_value=100, fd=RecordingTTY())
    bar.start()
    assert bar._gate_enabled is False


def test_zero_min_poll_interval_disables_gate():
    # Build a bar and force min_poll_interval to zero on the *instance* (not
    # the class) before calling start(), so the class version-tag is
    # untouched and CPython's adaptive specialiser for __iter__ is not
    # disturbed.
    bar = progressbar.ProgressBar(max_value=100, fd=RecordingTTY())
    bar.min_poll_interval = 0.0  # instance-level override, zero rate-limit
    bar.start()
    # With no rate limit the user wants every update considered.
    assert bar._gate_enabled is False


@pytest.mark.no_freezegun
@pytest.mark.skipif(
    sys.gettrace() is not None,
    reason='coverage tracing inflates per-iteration cost; benchmark skipped',
)
def test_iterator_overhead_is_low():
    import timeit as _t

    # Use the REAL clock (no fixed_clock): under a frozen clock (dt == 0) the
    # corrected gate never calibrates, so update() runs every iteration and the
    # measurement no longer reflects the gated fast path. A real, advancing
    # `perf_counter` lets the gate calibrate and skip as it does in production.
    fd = RecordingTTY()
    n = 200_000
    t = min(
        _t.timeit(
            lambda: [None for _ in progressbar.progressbar(range(n), fd=fd)],
            number=1,
        )
        for _ in range(3)
    )
    ns = t / n * 1e9
    # Generous smoke gate only; the authoritative per-iteration budget is
    # enforced in tests/test_perf_budget.py (Task 8).
    assert ns < 200, f'{ns:.1f} ns/iter (real clock)'


def test_no_color_fast_path_and_ansi():
    # Render-cost optimization adds a no-ESC fast path to no_color/len_color.
    # It must be identical to the regex path for both plain and ANSI input.
    utils = progressbar.utils

    # Fast path (no ESC byte): returned unchanged, str and bytes.
    assert utils.no_color('plain text') == 'plain text'
    assert utils.no_color(b'plain bytes') == b'plain bytes'
    assert utils.len_color('plain') == 5
    # Regex path (ANSI present): escape sequences stripped, str and bytes.
    assert utils.no_color('\x1b[31mred\x1b[0m') == 'red'
    assert utils.no_color(b'\x1b[31mred\x1b[0m') == b'red'
    assert utils.len_color('\x1b[1mbold\x1b[0m') == 4


def test_render_output_stable(monkeypatch):
    # Guard the default-widget render path against the render-cost
    # optimization changing appearance: the final repaint must reach 100%.
    fixed_clock(monkeypatch, dt=10.0)  # force a redraw on every forced update
    fd = RecordingTTY()
    bar = progressbar.ProgressBar(max_value=100, fd=fd)
    bar.start()
    for i in range(1, 101):
        bar.update(i, force=True)
    bar.finish()
    repaints = fd.repaints()
    assert repaints
    last = _ANSI_ESCAPE.sub('', repaints[-1])
    assert last.strip().startswith('100%')
