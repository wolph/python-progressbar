"""Render the README's benchmark race SVG from ``benchmarks/results.json``.

Unlike ``render_demos.py`` this is not a pty capture: the race is a pure
function of the committed benchmark results, dramatizing the measured
scenario-A wall-clock totals (the same 1,000,000-iteration loop, library
defaults) as five bars filling in real-time proportion. The animation
timeline maps the slowest racer's total to the full loop, so at frame
time ``t`` each library shows ``min(1, t / total)`` of its bar. Nothing
is simulated: the only inputs are the measured totals in results.json.

``click`` is measured in the benchmark but left out of the race: its
1.8 s total would compress every other lane into the first frame.

Reuses ``scripts.render_demos``'s SVG emitter so the race shares the
exact terminal chrome, fonts, and reduced-motion handling of every other
demo, and is gated the same way: ``--check`` fails when the committed
SVG differs from a fresh render of the current results.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import typing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.render_demos as render_demos  # noqa: E402

RESULTS_PATH = ROOT / 'benchmarks' / 'results.json'
SVG_PATH = ROOT / 'docs' / '_static' / 'demos' / 'readme-race.svg'

TITLE = 'The same 1,000,000-iteration loop, library defaults'
DESCRIPTION = (
    'Benchmark race: five progress bars fill in proportion to each '
    "library's measured wall-clock time for an identical one-million "
    'iteration loop. progressbar2 with the speedups accelerator finishes '
    'first. Measured by benchmarks/bench.py. click is excluded from the '
    'race because its total would flatten every other lane.'
)

#: Display order, top to bottom. Keys must exist in scenario A's results.
LANES: tuple[str, ...] = (
    'progressbar2[fast]',
    'progressbar2',
    'rich',
    'tqdm',
    'alive-progress',
)

LABEL_WIDTH = 18
BAR_WIDTH = 40
FRAME_COUNT = 36
FRAME_SECONDS = 0.25
END_HOLD_SECONDS = 3.0

RESET = '\x1b[0m'


def _sgr(red: int, green: int, blue: int) -> str:
    return f'\x1b[38;2;{red};{green};{blue}m'


def _gradient_rgb(fraction: float) -> tuple[int, int, int]:
    """Red -> yellow -> green, the library's own default gradient hues."""
    if fraction < 0.5:
        return 255, int(510 * fraction), 0
    return int(510 * (1 - fraction)), 255, 0


def _gradient_bar(filled: int) -> str:
    """A ``|##...|`` bar whose fill sweeps the red->yellow->green gradient.

    Colors are quantized to eight buckets so adjacent same-color runs
    share one SGR sequence (and so one ``<tspan>`` in the SVG) instead of
    one per character.
    """
    parts: list[str] = ['|']
    previous: str | None = None
    for column in range(filled):
        bucket = (column * 8 // BAR_WIDTH) / 7 if BAR_WIDTH > 1 else 0.0
        color = _sgr(*_gradient_rgb(min(bucket, 1.0)))
        if color != previous:
            parts.append(color)
            previous = color
        parts.append('#')
    parts.append(RESET)
    parts.append(' ' * (BAR_WIDTH - filled))
    parts.append('|')
    return ''.join(parts)


def _plain_bar(filled: int, fill_char: str, color: str | None) -> str:
    fill = fill_char * filled
    if color and filled:
        fill = f'{color}{fill}{RESET}'
    return f'|{fill}{" " * (BAR_WIDTH - filled)}|'


def _rich_bar(filled: int) -> str:
    """Mimic rich's line: magenta done-part, dim grey remainder, no pipes."""
    done = f'{_sgr(249, 38, 114)}{"━" * filled}' if filled else ''
    rest_width = BAR_WIDTH - filled
    rest = f'{_sgr(60, 66, 74)}{"━" * rest_width}' if rest_width else ''
    return f'{done}{rest}{RESET}  '


def _lane_bar(lane: str, filled: int) -> str:
    if lane == 'progressbar2[fast]':
        return _gradient_bar(filled)
    if lane == 'rich':
        return _rich_bar(filled)
    if lane == 'tqdm':
        return _plain_bar(filled, '█', None)
    if lane == 'alive-progress':
        return _plain_bar(filled, '▇', _sgr(0, 191, 255))
    return _plain_bar(filled, '#', None)


def load_results() -> dict[str, typing.Any]:
    return json.loads(RESULTS_PATH.read_text(encoding='utf-8'))


def _lane_totals(results: dict[str, typing.Any]) -> dict[str, float]:
    libs = results['scenario_a_default_overhead']['libs']
    return {lane: libs[lane]['total_min_s'] for lane in LANES}


def race_frames(results: dict[str, typing.Any]) -> list[list[str]]:
    totals = _lane_totals(results)
    t_max = max(totals.values())
    frames: list[list[str]] = []
    for index in range(FRAME_COUNT):
        t = (index + 1) / FRAME_COUNT * t_max
        lines: list[str] = []
        for lane in LANES:
            total = totals[lane]
            fraction = min(1.0, t / total)
            filled = round(fraction * BAR_WIDTH)
            pct = f'{fraction * 100:3.0f}%'
            if lane == 'progressbar2':
                # The full bar's default widgets color the percentage
                # readout with the red->green progress gradient
                # (widgets.Bar's `fg=colors.gradient` default), so the
                # plain lane wears that here too. The fill stays plain
                # '#', which is also faithful to the default look.
                pct = f'{_sgr(*_gradient_rgb(fraction))}{pct}{RESET}'
            suffix = f'  {total * 1000:.1f} ms' if fraction >= 1.0 else ''
            lines.append(
                f'{RESET}{lane:<{LABEL_WIDTH}} {pct} '
                f'{_lane_bar(lane, filled)}{suffix}'
            )
        lines.append(f'{RESET}elapsed {t * 1000:6.1f} ms')
        frames.append(lines)
    return frames


def race_svg(results: dict[str, typing.Any]) -> str:
    return render_demos.svg_document(
        TITLE,
        race_frames(results),
        DESCRIPTION,
        frame_seconds=FRAME_SECONDS,
        end_hold_seconds=END_HOLD_SECONDS,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Render the README benchmark race animation.',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='fail if the committed SVG differs from a fresh render',
    )
    args = parser.parse_args()

    svg = race_svg(load_results())
    if args.check:
        render_demos.check_svg(SVG_PATH, svg)
    else:
        SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
        SVG_PATH.write_text(svg, encoding='utf-8')


if __name__ == '__main__':
    main()
