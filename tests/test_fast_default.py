from __future__ import annotations

import io

from progressbar import fast as fast_module


class TTY(io.StringIO):
    def isatty(self) -> bool:
        return True

    def repaints(self) -> list[str]:
        return [p for p in self.getvalue().split('\r') if p]


def test_fast_known_length_renders_and_completes():
    fd = TTY()
    bar = fast_module.FastProgressBar(max_value=1000, fd=fd)
    out = list(bar(range(1000)))
    assert out == list(range(1000))
    assert bar.value == 1000
    assert bar.percentage == 100.0
    assert bar._finished
    frames = fd.repaints()
    assert frames, 'fast bar drew nothing'
    # Close-to-default look: percentage, (n of max), a bar, Elapsed/ETA.
    last = frames[-1]
    assert '100%' in last
    assert '(1000 of 1000)' in last
    assert '|' in last  # bar delimiters
    assert 'Elapsed Time:' in last


def test_fast_elapsed_with_no_start_time():
    """Test _fast_elapsed returns 0 when start_time is None."""
    fd = TTY()
    bar = fast_module.FastProgressBar(max_value=100, fd=fd)
    assert bar._fast_elapsed() == 0.0


def test_fast_format_line_with_eta_calculation():
    """Test ETA calculation path with done > 0 and elapsed > 0."""
    from datetime import datetime, timedelta

    fd = TTY()
    bar = fast_module.FastProgressBar(max_value=100, fd=fd)
    # Manually set start_time to the past to ensure elapsed > 0
    bar.start_time = datetime.now() - timedelta(seconds=2)
    bar.value = 50  # Set done=50 to enable ETA calculation
    line = bar._format_line()
    # With done > 0 and elapsed > 0, ETA is computed instead of '--:--:--'.
    assert 'ETA:' in line
    assert 'ETA: --:--:--' not in line


def test_fast_format_line_uses_native_hook(monkeypatch):
    """The native `_format_fast_line` hook takes precedence when set."""

    def stub(bar) -> str:
        return 'NATIVE_HOOK_OUTPUT'

    monkeypatch.setattr(fast_module, '_format_fast_line', stub)
    fd = TTY()
    bar = fast_module.FastProgressBar(max_value=100, fd=fd)
    assert bar._format_line() == 'NATIVE_HOOK_OUTPUT'
