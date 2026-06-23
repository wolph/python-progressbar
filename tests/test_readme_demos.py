import re
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scripts.render_readme_demos as demos  # noqa: E402


def _bar_widths(frames: list[list[str]]) -> list[int]:
    return [
        len(match.group('inner'))
        for frame in frames
        for line in frame
        if (match := demos.BAR_RE.search(line))
    ]


def _indented_snippet(snippet: str) -> str:
    return '\n'.join(
        f'    {line}' if line else ''
        for line in textwrap.dedent(snippet).strip().splitlines()
    )


def _readme_demo_block(demo: demos.Demo, alt: str) -> str:
    return (
        f'.. image:: docs/_static/progressbar-{demo.name}.svg\n'
        f'    :alt: {alt}\n\n'
        '.. code:: python\n\n'
        f'{_indented_snippet(demo.snippet)}'
    )


def test_render_svg_escapes_terminal_text(tmp_path: Path) -> None:
    output = tmp_path / 'demo.svg'
    demos.render_svg(
        output,
        title='Demo',
        frames=[
            ['<start>', 'progress 0%'],
            ['done & clean', 'progress 100%'],
        ],
    )
    text = output.read_text(encoding='utf-8')
    assert '&lt;start&gt;' in text
    assert 'done &amp; clean' in text
    assert '<animate' in text


def test_render_svg_colors_progress_segments(tmp_path: Path) -> None:
    output = tmp_path / 'demo.svg'
    demos.render_svg(
        output,
        title='Demo',
        frames=[
            [
                'Build:  50% (1 of 2) |##  | ETA:   0:00:00 loss=0.5',
                'log: completed step 1',
            ],
        ],
    )

    text = output.read_text(encoding='utf-8')
    assert 'class="terminal-label">Build:</tspan>' in text
    assert 'class="terminal-percent">50%</tspan>' in text
    assert 'class="terminal-bar-fill">##</tspan>' in text
    assert 'class="terminal-bar-empty">  </tspan>' in text
    assert 'class="terminal-postfix">loss=0.5</tspan>' in text
    assert 'class="terminal-log">log:</tspan>' in text


def test_render_svg_preserves_actual_ansi_truecolor_segments(
    tmp_path: Path,
) -> None:
    output = tmp_path / 'demo.svg'
    demos.render_svg(
        output,
        title='Demo',
        frames=[
            ['\x1b[38;2;255;0;0m  0%\x1b[39m \x1b[38;2;0;255;0m100%\x1b[39m'],
        ],
    )

    text = output.read_text(encoding='utf-8')
    assert 'style="fill: #ff0000">  0%</tspan>' in text
    assert 'style="fill: #00ff00">100%</tspan>' in text
    assert 'class="terminal-percent"' not in text
    assert '\x1b' not in text


def test_styled_terminal_line_keeps_spinner_pipe_outside_bar() -> None:
    styled = demos.styled_terminal_line('| |#  | 31 Elapsed Time: 0:00:00')

    assert styled.startswith(
        '| <tspan class="terminal-bar-frame">|</tspan>'
        '<tspan class="terminal-bar-fill">#</tspan>'
    )
    spinner_bar = (
        'terminal-bar-empty"> </tspan><tspan class="terminal-bar-frame">'
    )
    assert spinner_bar not in styled


def test_demo_definitions_are_ordered_and_exercise_key_features() -> None:
    assert [(demo.name, demo.title) for demo in demos.DEMOS] == [
        ('hero', 'Progress with clean logs'),
        ('multibar', 'Multiple active jobs'),
        ('unknown-length', 'Unknown length'),
    ]

    snippets = {demo.name: demo.snippet for demo in demos.DEMOS}
    assert 'redirect_stdout=True' in snippets['hero']
    assert 'progressbar.MultiBar' in snippets['multibar']
    assert 'io.StringIO()' in snippets['multibar']
    assert 'fd.getvalue()' in snippets['multibar']
    assert '.fd.line' not in snippets['multibar']
    assert 'build: {build.value}/3' not in snippets['multibar']
    assert 'progressbar.UnknownLength' in snippets['unknown-length']
    assert 'for value in range(0, 120, 10):' in snippets['unknown-length']
    assert 'for value in (' not in snippets['unknown-length']


def test_readme_uses_branch_relative_demo_assets() -> None:
    readme = (demos.ROOT / 'README.rst').read_text(encoding='utf-8')

    assert (
        'raw.githubusercontent.com/WoLpH/python-progressbar/develop'
        not in readme
    )
    assert '.. image:: docs/_static/progressbar-hero.svg' in readme
    assert '.. image:: docs/_static/progressbar-multibar.svg' in readme
    assert '.. image:: docs/_static/progressbar-unknown-length.svg' in readme
    assert 'progressbar-ergonomics.svg' not in readme
    assert 'Tqdm-style ergonomic options' not in readme


def test_readme_omits_obsolete_gpg_release_verification() -> None:
    readme = (demos.ROOT / 'README.rst').read_text(encoding='utf-8')

    assert 'Release verification' not in readme
    assert 'GPG' not in readme
    assert 'pgp.mit.edu' not in readme
    assert '.tar.gz.asc' not in readme


def test_readme_places_exact_demo_code_after_each_animation() -> None:
    readme = (demos.ROOT / 'README.rst').read_text(encoding='utf-8')
    alt_by_name = {
        'hero': 'progressbar2 showing clean progress output with logs',
        'multibar': 'multiple progress bars updating together',
        'unknown-length': 'unknown length progress with an animated marker',
    }

    for demo in demos.DEMOS:
        assert _readme_demo_block(demo, alt_by_name[demo.name]) in readme


def test_render_svg_first_frame_is_visible_without_animation(
    tmp_path: Path,
) -> None:
    output = tmp_path / 'demo.svg'
    demos.render_svg(
        output,
        title='Demo',
        frames=[
            ['first'],
            ['second'],
        ],
    )

    text = output.read_text(encoding='utf-8')
    assert text.count('<g opacity="1">') == 1
    assert text.count('<g opacity="0">') == 1
    assert '<g opacity="1"><animate' in text


def test_render_svg_uses_fast_readme_animation_pacing(
    tmp_path: Path,
) -> None:
    output = tmp_path / 'demo.svg'
    demos.render_svg(output, title='Demo', frames=[['a'], ['b'], ['c']])

    text = output.read_text(encoding='utf-8')
    assert 'dur="0.24s"' in text
    assert 'dur="3.6s"' not in text
    assert '3.599999999' not in text


def test_render_svg_uses_wide_canvas_for_readable_bars(
    tmp_path: Path,
) -> None:
    output = tmp_path / 'demo.svg'
    demos.render_svg(output, title='Demo', frames=[['a']])

    text = output.read_text(encoding='utf-8')
    assert 'width="1080"' in text
    assert 'viewBox="0 0 1080 96"' in text


def test_multibar_demo_captures_rendered_progressbar_output() -> None:
    demo = next(demo for demo in demos.DEMOS if demo.name == 'multibar')
    frames = demos.capture_demo(demo)
    text = '\n'.join(line for frame in frames for line in frame)

    assert frames
    assert all(len(frame) == 2 for frame in frames)
    assert 'build: 1/3 | test: 1/3' not in text
    assert 'build' in text
    assert 'test' in text
    assert 'Elapsed Time:' in text
    assert 'ETA:' in text
    assert '(0 of 24)' in text
    assert '(1 of 24)' in text or '(2 of 24)' in text
    assert '(24 of 24)' in text


def test_multibar_demo_shows_independent_progress_values() -> None:
    demo = next(demo for demo in demos.DEMOS if demo.name == 'multibar')
    frames = demos.capture_demo(demo)

    mismatched_values = []
    for frame in frames:
        values = [
            int(match.group(1))
            for line in frame
            if (match := re.search(r'\((\d+) of 24\)', line))
        ]
        if len(values) == 2 and values[0] != values[1]:
            mismatched_values.append(values)

    assert mismatched_values


def test_capture_demo_timeout_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> object:
        raise demos.subprocess.TimeoutExpired(cmd=['python'], timeout=5)

    demo = demos.Demo('sample', 'Sample', '')
    monkeypatch.setattr(demos.subprocess, 'run', raise_timeout)

    with pytest.raises(SystemExit) as error:
        demos.capture_demo(demo)

    assert str(error.value) == 'timed out capturing demo: sample'


def test_capture_frames_splits_carriage_return_output() -> None:
    frames = demos.frames_from_output('zero\rone\ntwo\rthree')
    assert frames == [['zero'], ['one'], ['two'], ['three']]


def test_capture_frames_keeps_more_animation_states() -> None:
    frames = demos.frames_from_output(
        '\n'.join(f'frame {index}' for index in range(30))
    )

    assert len(frames) == 24
    assert frames[0] == ['frame 0']
    assert frames[-1] == ['frame 29']


def test_readme_demos_emit_enough_frames_to_look_responsive() -> None:
    frame_counts = {
        demo.name: len(demos.capture_demo(demo)) for demo in demos.DEMOS
    }

    assert frame_counts['hero'] == 24
    assert frame_counts['multibar'] == 24
    assert frame_counts['unknown-length'] >= 8


def test_readme_demos_show_wide_determinate_progress_bars() -> None:
    frames_by_name = {
        demo.name: demos.capture_demo(demo) for demo in demos.DEMOS
    }

    for name in ('hero', 'multibar'):
        text = '\n'.join(
            line for frame in frames_by_name[name] for line in frame
        )
        first_frame = '\n'.join(frames_by_name[name][0])
        last_frame = '\n'.join(frames_by_name[name][-1])
        assert '0%' in first_frame
        assert '100%' in last_frame
        assert '0%' in text
        assert '100%' in text
        assert max(_bar_widths(frames_by_name[name])) >= 32


def test_readme_demos_capture_real_percentage_color_changes() -> None:
    demo = next(demo for demo in demos.DEMOS if demo.name == 'hero')
    text = '\n'.join(
        line for frame in demos.capture_demo(demo) for line in frame
    )

    assert '\x1b[38;2;255;0;0m' in text
    assert '\x1b[38;2;0;255;0m' in text


def test_hero_demo_keeps_recent_logs_visible_above_progress() -> None:
    demo = next(demo for demo in demos.DEMOS if demo.name == 'hero')
    frames = demos.capture_demo(demo)

    assert max(len(frame) for frame in frames) >= 3
    assert any(
        any(line.startswith('log: completed step 8') for line in frame)
        and any('Build:' in line for line in frame)
        for frame in frames
    )


def test_capture_frames_normalizes_variable_timing_text() -> None:
    frames = demos.frames_from_output(
        'Build:  50% Elapsed Time: 0:01:23 ETA:   9:08:07\n'
        'Build: 100% Elapsed Time: 0:00:04 Time:  2:03:04'
    )
    assert frames == [
        ['Build:  50% Elapsed Time: 0:00:00 ETA:   0:00:00'],
        ['Build: 100% Elapsed Time: 0:00:00 Time:  0:00:00'],
    ]


def test_check_mode_does_not_rewrite_mismatched_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = demos.Demo('sample', 'Sample', '')
    output = tmp_path / 'progressbar-sample.svg'
    output.write_text('stale asset', encoding='utf-8')

    monkeypatch.setattr(demos, 'DEMOS', [demo])
    monkeypatch.setattr(demos, 'STATIC_DIR', tmp_path)
    monkeypatch.setattr(demos, 'capture_demo', lambda demo: [['fresh asset']])
    monkeypatch.setattr(sys, 'argv', ['render_readme_demos.py', '--check'])

    with pytest.raises(SystemExit) as error:
        demos.main()

    assert 'outdated generated asset' in str(error.value)
    assert output.read_text(encoding='utf-8') == 'stale asset'
