"""Tests for ``scripts/render_race.py``, the README benchmark race.

The race SVG is not a pty capture: it is a pure function of
``benchmarks/results.json``, so the tests can assert byte-for-byte
determinism and that the animation honestly reflects the measured
ordering (the fastest measured library finishes first).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Same guard as tests/test_readme_demos.py: render_race reuses
# scripts.render_demos' SVG emitter, whose module-scope pty/fcntl imports
# do not exist on Windows.
if os.name == 'nt':
    pytest.skip(
        'POSIX-only: the SVG emitter module needs a pty',
        allow_module_level=True,
    )

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scripts.render_race as race  # noqa: E402

LIBRARIES = (
    'progressbar2[fast]',
    'progressbar2',
    'rich',
    'tqdm',
    'alive-progress',
)


def test_race_svg_is_deterministic() -> None:
    results = race.load_results()
    first = race.race_svg(results)
    second = race.race_svg(results)

    assert first == second


def test_race_names_every_racer() -> None:
    svg = race.race_svg(race.load_results())

    for library in LIBRARIES:
        assert library in svg


def test_fastest_measured_library_finishes_first() -> None:
    results = race.load_results()
    totals = {
        library: results['scenario_a_default_overhead']['libs'][library][
            'total_min_s'
        ]
        for library in LIBRARIES
    }
    fastest = min(totals, key=totals.__getitem__)
    frames = race.race_frames(results)

    def finish_frame(library: str) -> int:
        # The trailing space matters: a bare 'progressbar2' prefix would
        # also match the 'progressbar2[fast]' lane.
        prefix = '\x1b[0m' + library + ' '
        for index, frame in enumerate(frames):
            for line in frame:
                if line.startswith(prefix) and '100%' in line:
                    return index
        return len(frames)

    finishes = {library: finish_frame(library) for library in LIBRARIES}
    assert finishes[fastest] < min(
        finish for library, finish in finishes.items() if library != fastest
    )


def test_race_shows_measured_totals() -> None:
    results = race.load_results()
    svg = race.race_svg(results)
    libs = results['scenario_a_default_overhead']['libs']

    for library in LIBRARIES:
        total_ms = libs[library]['total_min_s'] * 1000
        assert f'{total_ms:.1f} ms' in svg


def test_committed_race_svg_is_current() -> None:
    committed = race.SVG_PATH.read_text(encoding='utf-8')

    assert committed == race.race_svg(race.load_results())


def test_check_mode_fails_on_stale_svg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stale = tmp_path / 'readme-race.svg'
    stale.write_text('<svg/>', encoding='utf-8')
    monkeypatch.setattr(race, 'SVG_PATH', stale)
    monkeypatch.setattr(sys, 'argv', ['render_race.py', '--check'])

    with pytest.raises(SystemExit):
        race.main()


def test_check_mode_passes_on_fresh_svg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fresh = tmp_path / 'readme-race.svg'
    monkeypatch.setattr(race, 'SVG_PATH', fresh)

    monkeypatch.setattr(sys, 'argv', ['render_race.py'])
    race.main()

    monkeypatch.setattr(sys, 'argv', ['render_race.py', '--check'])
    race.main()
