"""Benchmark progressbar2 against other common Python progress-bar libraries.

Measures three things, fairly, with all rendered output sent to a *real* pseudo
terminal (so every library believes it is attached to a TTY and actually draws):

  A. Default iterator-wrap overhead .. the idiomatic "wrap my loop" call with
     each library's default settings (ns added per iteration). Headline number.
  B. Forced per-update render cost ... rendering forced on every single update,
     for the libraries whose API supports it (us per rendered update).
  C. Import time ...................... cold `import` cost in a fresh interpreter
     (ms), interpreter-startup baseline subtracted.

Results are written to results.json for the reporting step to consume.
"""

from __future__ import annotations

import fcntl
import gc
import json
import os
import platform
import pty
import statistics
import struct
import subprocess
import sys
import termios
import threading
import time
import typing
from importlib import metadata

# Scenario sizes / repeats -------------------------------------------------
N_ITER: int = 1_000_000  # scenario A: default-overhead loop length
ITER_REPEATS: int = 7
N_RENDER: int = 30_000  # scenario B: forced-render loop length
RENDER_REPEATS: int = 5
IMPORT_RUNS: int = 9  # scenario C: cold-import subprocess runs

TERM_COLS: int = 80
TERM_ROWS: int = 24


class PtySink:
    """A real pty whose output is continuously drained and discarded.

    Writing to a pty that nobody reads will eventually block when the kernel
    buffer fills; the background drain thread keeps it flowing so timings are
    not polluted by blocked writes.
    """

    def __init__(self, cols: int = TERM_COLS, rows: int = TERM_ROWS) -> None:
        self._master, slave = pty.openpty()
        fcntl.ioctl(
            slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0)
        )
        self.file: typing.TextIO = os.fdopen(
            slave, 'w', buffering=1, encoding='utf-8', errors='replace'
        )
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._drain, daemon=True)
        self._thread.start()

    def _drain(self) -> None:
        while not self._stop.is_set():
            try:
                if not os.read(self._master, 65536):
                    break
            except OSError:
                break

    def close(self) -> None:
        try:
            self.file.flush()
            self.file.close()
        except Exception:
            # Teardown only: the slave fd may already be gone; nothing to do.
            pass
        self._stop.set()
        try:
            os.close(self._master)
        except OSError:
            # Master already closed once the drain thread hit EOF; ignore.
            pass
        self._thread.join(timeout=1)


def time_call(fn: typing.Callable[[], None], repeats: int) -> dict[str, float]:
    """Run ``fn`` ``repeats`` times (plus one warmup); return min/median secs."""
    fn()  # warmup: pay one-time import/compile/thread-spawn costs
    samples: list[float] = []
    for _ in range(repeats):
        gc.collect()
        gc.disable()
        start = time.perf_counter()
        fn()
        elapsed = time.perf_counter() - start
        gc.enable()
        samples.append(elapsed)
    return {'min': min(samples), 'median': statistics.median(samples)}


# --- Scenario A: default iterator-wrap overhead ---------------------------


def baseline_loop(n: int) -> None:
    for _ in range(n):
        pass


def iter_progressbar2(f: typing.TextIO, n: int) -> None:
    # Plain `pip install progressbar2`: no native accelerator, so the
    # pure-Python integer gate paces the loop. The accelerator is forced
    # off for this case because the bench venv installs `speedups` for
    # the `progressbar2[fast]` case below and detection is automatic.
    import progressbar
    import progressbar.bar

    saved = progressbar.bar._FastBarIterator
    progressbar.bar._FastBarIterator = None
    try:
        for _ in progressbar.progressbar(range(n), fd=f):
            pass
    finally:
        progressbar.bar._FastBarIterator = saved


def iter_progressbar2_fast(f: typing.TextIO, n: int) -> None:
    # `pip install 'progressbar2[fast]'`: the speedups C iterator counts
    # natively and calls back into Python only at redraw crossings.
    import progressbar
    import progressbar.bar

    if progressbar.bar._FastBarIterator is None:
        raise SystemExit(
            'the progressbar2[fast] case needs the speedups package '
            '(pip install -r benchmarks/requirements.txt)'
        )
    for _ in progressbar.progressbar(range(n), fd=f):
        pass


def iter_tqdm(f: typing.TextIO, n: int) -> None:
    from tqdm import tqdm

    for _ in tqdm(range(n), file=f):
        pass


def iter_rich(f: typing.TextIO, n: int) -> None:
    from rich.console import Console
    from rich.progress import track

    console = Console(file=f, force_terminal=True, width=TERM_COLS)
    for _ in track(range(n), console=console):
        pass


def iter_alive(f: typing.TextIO, n: int) -> None:
    from alive_progress import alive_bar

    with alive_bar(n, file=f, force_tty=True) as bar:
        for _ in range(n):
            bar()


def iter_click(f: typing.TextIO, n: int) -> None:
    import click

    with click.progressbar(range(n), file=f) as bar:
        for _ in bar:
            pass


# --- Scenario B: forced per-update render ---------------------------------


def render_progressbar2(f: typing.TextIO, n: int) -> None:
    import progressbar

    # force=True bypasses the time-based redraw throttle (whose floor is
    # _MINIMUM_UPDATE_INTERVAL=0.050s), so every update actually renders.
    with progressbar.ProgressBar(max_value=n, fd=f) as bar:
        for i in range(n):
            bar.update(i + 1, force=True)


def render_progressbar2_fast(f: typing.TextIO, n: int) -> None:
    import progressbar

    # The fast default path: fixed formatter, no widget machinery.
    with progressbar.FastProgressBar(max_value=n, fd=f) as bar:
        for i in range(n):
            bar.update(i + 1, force=True)


def render_tqdm(f: typing.TextIO, n: int) -> None:
    from tqdm import tqdm

    for _ in tqdm(range(n), file=f, mininterval=0, miniters=1):
        pass


def render_rich(f: typing.TextIO, n: int) -> None:
    from rich.console import Console
    from rich.progress import Progress

    console = Console(file=f, force_terminal=True, width=TERM_COLS)
    with Progress(console=console, auto_refresh=False) as progress:
        task = progress.add_task('bench', total=n)
        for _ in range(n):
            progress.advance(task)
            progress.refresh()


# --- Scenario C: cold import time -----------------------------------------

IMPORT_STMTS: dict[str, str] = {
    # Blocking `speedups` in sys.modules makes the accelerator probe fail
    # exactly as it does on a plain install, without needing a second venv.
    'progressbar2': (
        'import sys; sys.modules["speedups"] = None; import progressbar'
    ),
    'progressbar2[fast]': 'import progressbar',
    'tqdm': 'from tqdm import tqdm',
    'rich': 'from rich.progress import track',
    'alive-progress': 'from alive_progress import alive_bar',
    'click': 'import click',
}


def time_import(stmt: str, runs: int) -> float:
    """Return the minimum wall-clock seconds to run ``stmt`` in a fresh py."""
    samples: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        subprocess.run(
            [sys.executable, '-c', stmt],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        samples.append(time.perf_counter() - start)
    return min(samples)


ITER_LIBS: dict[str, typing.Callable[[typing.TextIO, int], None]] = {
    'progressbar2[fast]': iter_progressbar2_fast,
    'progressbar2': iter_progressbar2,
    'tqdm': iter_tqdm,
    'rich': iter_rich,
    'alive-progress': iter_alive,
    'click': iter_click,
}

RENDER_LIBS: dict[str, typing.Callable[[typing.TextIO, int], None]] = {
    'progressbar2': render_progressbar2,
    'progressbar2-fast': render_progressbar2_fast,
    'tqdm': render_tqdm,
    'rich': render_rich,
}


def main() -> None:
    sink = PtySink()
    results: dict[str, typing.Any] = {
        'meta': {
            'python': platform.python_version(),
            'implementation': platform.python_implementation(),
            'platform': platform.platform(),
            'processor': platform.processor() or platform.machine(),
            'cpu_count': os.cpu_count(),
            'versions': {
                name: metadata.version(dist)
                for name, dist in {
                    'progressbar2': 'progressbar2',
                    'speedups': 'speedups',
                    'tqdm': 'tqdm',
                    'rich': 'rich',
                    'alive-progress': 'alive-progress',
                    'click': 'click',
                }.items()
            },
            'n_iter': N_ITER,
            'iter_repeats': ITER_REPEATS,
            'n_render': N_RENDER,
            'render_repeats': RENDER_REPEATS,
            'import_runs': IMPORT_RUNS,
            'term': f'{TERM_COLS}x{TERM_ROWS}',
        },
    }

    try:
        # Scenario A ----------------------------------------------------
        print('[A] default iterator-wrap overhead', file=sys.stderr)
        base = time_call(lambda: baseline_loop(N_ITER), ITER_REPEATS)
        print(
            f'    baseline           {base["min"] * 1e3:8.2f} ms',
            file=sys.stderr,
        )
        iter_results: dict[str, typing.Any] = {}
        for name, fn in ITER_LIBS.items():
            res = time_call(lambda f=fn: f(sink.file, N_ITER), ITER_REPEATS)
            overhead_ns = (res['min'] - base['min']) / N_ITER * 1e9
            iter_results[name] = {
                'total_min_s': res['min'],
                'total_median_s': res['median'],
                'overhead_ns_per_iter': overhead_ns,
            }
            print(
                f'    {name:16} {res["min"] * 1e3:8.2f} ms  '
                f'({overhead_ns:8.1f} ns/iter)',
                file=sys.stderr,
            )
        results['scenario_a_default_overhead'] = {
            'baseline_min_s': base['min'],
            'baseline_median_s': base['median'],
            'libs': iter_results,
        }

        # Scenario B ----------------------------------------------------
        print('[B] forced per-update render', file=sys.stderr)
        baseR = time_call(lambda: baseline_loop(N_RENDER), RENDER_REPEATS)
        render_results: dict[str, typing.Any] = {}
        for name, fn in RENDER_LIBS.items():
            res = time_call(
                lambda f=fn: f(sink.file, N_RENDER), RENDER_REPEATS
            )
            per_update_us = (res['min'] - baseR['min']) / N_RENDER * 1e6
            render_results[name] = {
                'total_min_s': res['min'],
                'total_median_s': res['median'],
                'per_update_us': per_update_us,
            }
            print(
                f'    {name:16} {res["min"] * 1e3:8.2f} ms  '
                f'({per_update_us:7.2f} us/update)',
                file=sys.stderr,
            )
        results['scenario_b_forced_render'] = {
            'baseline_min_s': baseR['min'],
            'libs': render_results,
            'excluded': {
                'alive-progress': 'renders on a background timer thread; no '
                'per-update render API',
                'click': 'self-throttles writes (renders only when the drawn '
                'line changes); no force-every-update API',
            },
        }
    finally:
        sink.close()

    # Scenario C --------------------------------------------------------
    print('[C] cold import time', file=sys.stderr)
    base_import = time_import('pass', IMPORT_RUNS)
    import_results: dict[str, typing.Any] = {}
    for name, stmt in IMPORT_STMTS.items():
        t = time_import(stmt, IMPORT_RUNS)
        net_ms = (t - base_import) * 1e3
        import_results[name] = {
            'total_min_s': t,
            'net_ms': net_ms,
        }
        print(f'    {name:16} {net_ms:8.1f} ms (net)', file=sys.stderr)
    results['scenario_c_import_time'] = {
        'interpreter_baseline_s': base_import,
        'libs': import_results,
    }

    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'results.json'
    )
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(results, fh, indent=2)
    print(f'\nwrote {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
