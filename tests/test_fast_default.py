from __future__ import annotations

import gc
import io
import sys

import progressbar

# Alias (not a `from` import) so CodeQL doesn't flag `progressbar` as imported
# with both `import` and `import from`.
fast_module = progressbar.fast


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


def test_fast_spinner_frames_cycle():
    """The spinner is exactly four frames and cycles through all of them.

    Regression: the raw literal ``r'|/-\\'`` is 5 chars long (the escape is not
    collapsed), so the intended four-frame cycle was fragile and length-coupled
    to a hardcoded ``% 4``.
    """
    from datetime import datetime, timedelta

    assert len(fast_module._SPINNER_FRAMES) == 4
    assert set(fast_module._SPINNER_FRAMES) == set('|/-\\')

    fd = TTY()
    bar = fast_module.FastProgressBar(
        max_value=progressbar.UnknownLength, fd=fd
    )
    bar.start_time = datetime(2020, 1, 1)
    seen = []
    for quarter in range(4):
        # Freeze elapsed at exact quarter-seconds so int(elapsed * 4) walks
        # 0, 1, 2, 3 and must surface each distinct frame.
        bar.end_time = bar.start_time + timedelta(seconds=quarter / 4)
        seen.append(bar._format_line().lstrip()[0])

    assert seen == ['|', '/', '-', '\\']


def test_fast_format_line_uses_native_hook(monkeypatch):
    """The native `_format_fast_line` hook takes precedence when set."""

    def stub(bar) -> str:
        return 'NATIVE_HOOK_OUTPUT'

    monkeypatch.setattr(fast_module, '_format_fast_line', stub)
    fd = TTY()
    bar = fast_module.FastProgressBar(max_value=100, fd=fd)
    assert bar._format_line() == 'NATIVE_HOOK_OUTPUT'


def test_fast_unknown_length_renders_count_and_elapsed():
    fd = TTY()
    bar = fast_module.FastProgressBar(
        max_value=progressbar.UnknownLength, fd=fd
    )
    out = list(bar(iter(range(40))))
    assert out == list(range(40))
    assert bar.value == 39
    last = fd.repaints()[-1]
    assert 'Elapsed Time:' in last
    assert '40' in last  # the count is shown
    assert ' of ' not in last  # no "(n of max)" when length unknown


def test_fast_prefix_suffix_in_line_not_widgets():
    fd = TTY()
    bar = fast_module.FastProgressBar(
        max_value=10, fd=fd, prefix='load ', suffix=' done'
    )
    list(bar(range(10)))
    assert bar.widgets == []  # prefix/suffix not injected as widgets
    last = fd.repaints()[-1]
    assert last.lstrip().startswith('load')
    assert 'done' in last


def test_fast_empty_iterable():
    fd = TTY()
    bar = fast_module.FastProgressBar(max_value=0, fd=fd)
    assert list(bar([])) == []
    assert bar._finished


def test_fast_break_restores_streams():
    real_out = sys.stdout
    fd = TTY()
    bar = fast_module.FastProgressBar(
        max_value=1000, fd=fd, redirect_stdout=True
    )
    for i in bar(range(1000)):
        if i == 5:
            break
    del bar
    gc.collect()
    assert sys.stdout is real_out


def test_fast_with_statement():
    fd = TTY()
    with fast_module.FastProgressBar(max_value=10, fd=fd) as bar:
        out = list(bar(range(10)))
    assert out == list(range(10))
    assert bar._finished


def test_shortcut_dispatch(monkeypatch):
    # Record which class the shortcut constructs for each input combination.
    from progressbar import shortcuts

    calls = {'fast': 0, 'full': 0}

    class FastSpy(fast_module.FastProgressBar):
        def __init__(self, *a, **k):
            calls['fast'] += 1
            super().__init__(*a, **k)

    class FullSpy(progressbar.ProgressBar):
        def __init__(self, *a, **k):
            calls['full'] += 1
            super().__init__(*a, **k)

    monkeypatch.setattr(shortcuts.fast_module, 'FastProgressBar', FastSpy)
    monkeypatch.setattr(shortcuts.bar, 'ProgressBar', FullSpy)

    # Default (no widgets, no fast flag) -> fast.
    assert list(shortcuts.progressbar(range(3), fd=TTY())) == [0, 1, 2]
    assert calls == {'fast': 1, 'full': 0}

    # Custom widgets -> full.
    list(
        shortcuts.progressbar(
            range(3), fd=TTY(), widgets=[progressbar.Percentage()]
        )
    )
    assert calls == {'fast': 1, 'full': 1}

    # fast=False -> full even with no widgets.
    list(shortcuts.progressbar(range(3), fd=TTY(), fast=False))
    assert calls == {'fast': 1, 'full': 2}

    # Env override forces full.
    monkeypatch.setenv('PROGRESSBAR_DISABLE_FASTPATH', '1')
    list(shortcuts.progressbar(range(3), fd=TTY()))
    assert calls == {'fast': 1, 'full': 3}

    # Dynamic variables force full (the fast formatter can't render them).
    monkeypatch.delenv('PROGRESSBAR_DISABLE_FASTPATH', raising=False)
    list(shortcuts.progressbar(range(3), fd=TTY(), variables={'x': 1}))
    assert calls == {'fast': 1, 'full': 4}


def test_full_bar_injects_prefix_suffix_widgets():
    # The full ProgressBar (unlike the fast bar) injects prefix/suffix as
    # FormatLabel widgets in start(); exercise that path directly.
    fd = TTY()
    bar_ = progressbar.ProgressBar(
        max_value=10, fd=fd, prefix='pre ', suffix=' suf'
    )
    list(bar_(range(10)))
    assert bar_.widgets  # widgets were built (not the fast empty list)
    last = fd.repaints()[-1]
    assert 'pre' in last
    assert 'suf' in last


def test_import_progressbar_is_lazy():
    # A fresh interpreter: `import progressbar` must not eagerly pull heavy
    # submodules; FastProgressBar still resolves lazily.
    import subprocess

    check = (
        'import sys, progressbar\n'
        'assert "progressbar.multi" not in sys.modules\n'
        'assert progressbar.FastProgressBar is not None\n'
        'print("ok")\n'
    )
    out = subprocess.run(
        [sys.executable, '-c', check], capture_output=True, text=True
    )
    assert out.returncode == 0, out.stderr
    assert 'ok' in out.stdout


def test_fast_path_does_not_import_widgets_or_colors():
    # Running the fast default end-to-end must not pull in the widgets module
    # or the terminal colour tables (the heaviest imports).
    import subprocess

    check = (
        'import sys, progressbar\n'
        'list(progressbar.progressbar(range(10)))\n'
        'assert "progressbar.widgets" not in sys.modules\n'
        'assert "progressbar.terminal.colors" not in sys.modules\n'
        'print("ok")\n'
    )
    out = subprocess.run(
        [sys.executable, '-c', check], capture_output=True, text=True
    )
    assert out.returncode == 0, out.stderr
    assert 'ok' in out.stdout
