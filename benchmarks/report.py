"""Render results.json into chart.png + report.md."""

from __future__ import annotations

import datetime
import json
import os
import typing

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE: str = os.path.dirname(os.path.abspath(__file__))
SUBJECT: str = 'progressbar2'

# Our two variants share one brand hue so they read as siblings: the fast
# default pops at full saturation, the full (widget) mode is a muted shade.
# Every other library is a flat neutral grey.
FAST: str = 'fast'
FULL: str = 'full'
OTHER: str = 'other'
THEME: dict[str, typing.Any] = {
    'bg': '#ffffff',
    'fast': '#4f46e5',  # bold indigo  -> progressbar2 (fast), the default
    'full': '#c4b5fd',  # muted indigo -> progressbar2 (full), widgets mode
    'other': '#d8dde6',  # neutral grey -> every other library
    'text': '#1e2430',
    'subtext': '#5b6472',
    'grid': '#e7eaf0',
    'title': '#11151c',
    'bar_height': 0.6,
}


def _font() -> str:
    """Prefer a clean sans; degrade gracefully where it is not installed."""
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ('Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'):
        if name in have:
            return name
    return 'sans-serif'


def _classify(panel: str, key: str) -> str:
    """Tag a library as our accelerated spelling, our plain one, or another.

    Every panel now carries both spellings under explicit keys:
    ``progressbar2[fast]`` (A/C) and ``progressbar2-fast`` (B) are the
    accelerated/lean variants, a bare ``progressbar2`` is the plain
    install.
    """
    if key in ('progressbar2[fast]', 'progressbar2-fast'):
        return FAST
    if key == SUBJECT:
        return FULL
    return OTHER


def _relabel(panel: str, key: str) -> str:
    """Display name: the result keys are already self-describing."""
    return key


def load() -> dict[str, typing.Any]:
    with open(os.path.join(HERE, 'results.json'), encoding='utf-8') as fh:
        return json.load(fh)


def _sorted(pairs: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(pairs.items(), key=lambda kv: kv[1])


def make_chart(data: dict[str, typing.Any]) -> str:
    a = data['scenario_a_default_overhead']['libs']
    b = data['scenario_b_forced_render']['libs']
    c = data['scenario_c_import_time']['libs']

    panels: list[tuple[str, str, str, list[tuple[str, float]], bool]] = [
        (
            'A',
            'Default iterator-wrap overhead',
            'nanoseconds added per iteration',
            _sorted({k: v['overhead_ns_per_iter'] for k, v in a.items()}),
            True,
        ),
        (
            'B',
            'Forced per-update render cost',
            'microseconds per rendered update',
            _sorted({k: v['per_update_us'] for k, v in b.items()}),
            True,
        ),
        (
            'C',
            'Cold import time',
            'milliseconds (net of startup)',
            _sorted({k: v['net_ms'] for k, v in c.items()}),
            False,
        ),
    ]

    color = {FAST: THEME['fast'], FULL: THEME['full'], OTHER: THEME['other']}

    plt.rcParams['font.family'] = _font()
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.2))
    fig.patch.set_facecolor(THEME['bg'])

    for ax, (pid, ptitle, xlabel, pairs, logx) in zip(axes, panels):
        ax.set_facecolor(THEME['bg'])
        classes = [_classify(pid, k) for k, _ in pairs]
        labels = [_relabel(pid, k) for k, _ in pairs]
        values = [v for _, v in pairs]
        ypos = list(range(len(labels)))

        ax.barh(
            ypos,
            values,
            height=THEME['bar_height'],
            color=[color[cls] for cls in classes],
        )
        ax.set_yticks(ypos)
        ax.set_yticklabels(labels, color=THEME['text'], fontsize=10)
        ax.invert_yaxis()  # fastest at top
        ax.set_xlabel(xlabel, color=THEME['subtext'], fontsize=9.5)
        ax.set_title(
            f'{pid}. {ptitle}',
            loc='left',
            fontsize=11.5,
            fontweight='bold',
            color=THEME['title'],
            pad=12,
        )
        if logx:
            ax.set_xscale('log')
        ax.grid(axis='x', color=THEME['grid'], linewidth=1)
        ax.set_axisbelow(True)
        for spine in ('top', 'right', 'left'):
            ax.spines[spine].set_visible(False)
        ax.spines['bottom'].set_color(THEME['grid'])
        ax.tick_params(colors=THEME['subtext'], length=0)
        ax.margins(x=0.2)

        xmax = max(values)
        for y, val, cls in zip(ypos, values, classes):
            label = f'{val:.1f}' if val >= 1 else f'{val:.2f}'
            ax.text(
                val * 1.08 if logx else val + xmax * 0.015,
                y,
                label,
                va='center',
                ha='left',
                fontsize=9.5,
                fontweight='normal' if cls == OTHER else 'bold',
                color=THEME['text'] if cls == OTHER else color[cls],
            )

    fig.suptitle(
        'progressbar2 vs common Python progress-bar libraries',
        fontsize=15,
        fontweight='bold',
        color=THEME['title'],
        y=0.975,
    )
    fig.text(
        0.5,
        0.915,
        'lower is faster / lighter  —  fastest at top',
        ha='center',
        fontsize=9.5,
        color=THEME['subtext'],
    )
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    out = os.path.join(HERE, 'chart.png')
    fig.savefig(out, dpi=140, facecolor=THEME['bg'])
    plt.close(fig)
    return out


def _rel(value: float, ref: float) -> str:
    if ref == 0:
        return 'n/a'
    factor = value / ref
    if abs(factor - 1) < 0.005:
        return 'baseline'
    return f'{factor:.2f}x'


def make_report(data: dict[str, typing.Any], chart_name: str) -> str:
    meta = data['meta']
    a = data['scenario_a_default_overhead']
    b = data['scenario_b_forced_render']
    c = data['scenario_c_import_time']
    n_iter = meta['n_iter']
    n_render = meta['n_render']
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    pb_a = a['libs'][SUBJECT]['overhead_ns_per_iter']
    pb_b = b['libs'][SUBJECT]['per_update_us']

    lines: list[str] = []
    w = lines.append

    w('# Python progress-bar library benchmark')
    w('')
    w(
        f'_Generated {now}. Subject: **{SUBJECT}** '
        f'(version {meta["versions"]["progressbar2"]})._'
    )
    w('')
    w(
        'Compares `progressbar2` against the most common alternatives across '
        'three independent dimensions. All rendered output is written to a real '
        'pseudo-terminal (pty) that is continuously drained, so every library '
        'believes it is attached to a TTY and actually draws — the comparison is '
        'apples-to-apples, not "is output suppressed when piped".'
    )
    w('')
    w(f'![benchmark chart]({chart_name})')
    w('')

    # Environment ------------------------------------------------------
    w('## Environment')
    w('')
    w('| | |')
    w('|---|---|')
    w(f'| Python | {meta["implementation"]} {meta["python"]} |')
    w(f'| Platform | {meta["platform"]} |')
    w(f'| Processor | {meta["processor"]} ({meta["cpu_count"]} cores) |')
    w(f'| Terminal | {meta["term"]} (pty) |')
    w('')
    w('| Library | Version |')
    w('|---|---|')
    for name, ver in meta['versions'].items():
        w(f'| {name} | {ver} |')
    w('')

    # Scenario A -------------------------------------------------------
    w('## A. Default iterator-wrap overhead (headline)')
    w('')
    w(
        f'Idiomatic "wrap my loop" call with each library\'s **default** '
        f'settings, over **{n_iter:,}** iterations with a trivial body. This is '
        f'the real-world cost of dropping a progress bar around a fast loop. '
        f'Overhead = (wrapped time − bare-loop time) / iterations. '
        f'Lower is faster.'
    )
    w('')
    w(
        f'Bare loop baseline: **{a["baseline_min_s"] * 1e3:.2f} ms** '
        f'for {n_iter:,} iterations.'
    )
    w('')
    w('| Library | Total time | Overhead/iter | vs progressbar2 |')
    w('|---|--:|--:|--:|')
    for name, v in _sorted(
        {k: vv['overhead_ns_per_iter'] for k, vv in a['libs'].items()}
    ):
        vv = a['libs'][name]
        bold = '**' if name.startswith('progressbar2') else ''
        w(
            f'| {bold}{name}{bold} | {vv["total_min_s"] * 1e3:.1f} ms '
            f'| {vv["overhead_ns_per_iter"]:.1f} ns '
            f'| {_rel(vv["overhead_ns_per_iter"], pb_a)} |'
        )
    w('')

    # Scenario B -------------------------------------------------------
    w('## B. Forced per-update render cost')
    w('')
    w(
        f'Rendering **forced on every single update** over **{n_render:,}** '
        f'updates — i.e. the cost of one full bar redraw, throttling disabled. '
        f'Lower is faster.'
    )
    w('')
    w('| Library | Total time | Per rendered update | vs progressbar2 |')
    w('|---|--:|--:|--:|')
    for name, v in _sorted(
        {k: vv['per_update_us'] for k, vv in b['libs'].items()}
    ):
        vv = b['libs'][name]
        bold = '**' if name.startswith('progressbar2') else ''
        w(
            f'| {bold}{name}{bold} | {vv["total_min_s"] * 1e3:.1f} ms '
            f'| {vv["per_update_us"]:.2f} us '
            f'| {_rel(vv["per_update_us"], pb_b)} |'
        )
    w('')
    w('Excluded from this panel (no per-update force-render API):')
    for name, why in b['excluded'].items():
        w(f'- **{name}** — {why}')
    w('')

    # Scenario C -------------------------------------------------------
    w('## C. Cold import time')
    w('')
    w(
        f'Wall-clock cost of importing the library in a fresh interpreter '
        f'(minimum of {meta["import_runs"]} runs), with bare-interpreter startup '
        f'({c["interpreter_baseline_s"] * 1e3:.0f} ms) subtracted. Matters for '
        f'short-lived CLIs. Lower is lighter.'
    )
    w('')
    w('| Library | Import time (net) |')
    w('|---|--:|')
    for name, v in _sorted({k: vv['net_ms'] for k, vv in c['libs'].items()}):
        vv = c['libs'][name]
        bold = '**' if name.startswith('progressbar2') else ''
        w(f'| {bold}{name}{bold} | {vv["net_ms"]:.1f} ms |')
    w('')

    # Takeaways --------------------------------------------------------
    a_rank = _sorted(
        {k: vv['overhead_ns_per_iter'] for k, vv in a['libs'].items()}
    )
    b_rank = _sorted({k: vv['per_update_us'] for k, vv in b['libs'].items()})
    pb_a_pos = [k for k, _ in a_rank].index(SUBJECT) + 1
    fastest_a = a_rank[0][0]
    slowest_a = a_rank[-1][0]
    w('## Takeaways')
    w('')
    w(
        f'- **Default per-iteration overhead:** `{SUBJECT}` is '
        f'{pb_a:.0f} ns/iter, ranking #{pb_a_pos} of '
        f'{len(a_rank)}. `{fastest_a}` is the lightest per iteration '
        f'({a_rank[0][1]:.0f} ns), `{slowest_a}` the heaviest '
        f'({a_rank[-1][1]:.0f} ns).'
    )
    w(
        f'  - `progressbar2[fast]` wins because the `speedups` C iterator '
        f'counts natively and only calls back into Python at redraw '
        f'crossings; a plain `{SUBJECT}` install pays the pure-Python '
        f'integer gate instead.'
    )
    w(
        f'- **Render cost:** when a redraw actually happens, `{SUBJECT}` draws '
        f'one update in {b_rank[[k for k, _ in b_rank].index(SUBJECT)][1]:.1f} us '
        f'— {_rel(pb_b, b_rank[0][1])} the cheapest (`{b_rank[0][0]}`) but '
        f"{b['libs']['rich']['per_update_us'] / pb_b:.1f}x cheaper than rich's "
        f'full-display re-render.'
    )
    w(
        f'- **Why both numbers matter:** `{SUBJECT}` caps redraws at ~20/sec by '
        f'default (50 ms floor), so in practice the cheap render in B fires '
        f'rarely and the per-iteration cost in A dominates real workloads.'
    )
    c_rank = _sorted({k: vv['net_ms'] for k, vv in c['libs'].items()})
    w(
        f'- **Import weight:** `{c_rank[0][0]}` is the lightest to import '
        f'({c_rank[0][1]:.1f} ms), `{c_rank[-1][0]}` the heaviest '
        f'({c_rank[-1][1]:.1f} ms).'
    )
    w('')

    # Methodology ------------------------------------------------------
    w('## Methodology & caveats')
    w('')
    w(
        f'- Timing: `time.perf_counter`, GC disabled during measurement, one '
        f'untimed warmup per case, **minimum** of N repeats reported '
        f'(A: {meta["iter_repeats"]}, B: {meta["render_repeats"]}). Minimum is '
        f'used to reduce scheduler/JIT noise.'
    )
    w(
        '- Output goes to a real pty sized '
        f'{meta["term"]}, drained by a background thread so writes never block.'
    )
    w(
        '- "Overhead/iter" subtracts the bare-loop baseline, isolating the '
        "library's own cost."
    )
    w(
        '- Default settings reflect out-of-the-box behaviour; tuning '
        '(`mininterval`, `poll_interval`, etc.) shifts these numbers. Results '
        'are specific to the environment above and will vary by machine.'
    )
    w(
        '- This measures CPU/throughput overhead only — not feature set, output '
        'quality, nesting, or multi-bar support.'
    )
    w('')
    w('Reproduce: `python benchmarks/bench.py && python benchmarks/report.py`')
    w('')

    report = '\n'.join(lines)
    out = os.path.join(HERE, 'report.md')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(report)
    return out


def main() -> None:
    data = load()
    chart = make_chart(data)
    report = make_report(data, os.path.basename(chart))
    print('wrote', chart)
    print('wrote', report)


if __name__ == '__main__':
    main()
