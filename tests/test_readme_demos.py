from __future__ import annotations

import os
import re
import sys
import types
from pathlib import Path

import pytest

# `scripts.render_demos` imports fcntl, pty, select and termios at module
# scope -- it captures each demo under a real pty, which is what lets the
# example modules stay idiomatic. On Windows that import is a collection
# *error*, not a skip, which would take the whole suite down. Guard at
# module level, matching tests/test_os_specific_posix.py.
if os.name == 'nt':
    pytest.skip(
        'POSIX-only: the demo renderer needs a pty', allow_module_level=True
    )

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scripts.render_demos as demos  # noqa: E402


def _bar_widths(frames: list[list[str]]) -> list[int]:
    return [
        len(match.group('inner'))
        for frame in frames
        for line in frame
        if (match := demos.BAR_RE.search(line))
    ]


_RAW_ASSET_BASE = (
    'https://raw.githubusercontent.com/wolph/python-progressbar/develop/'
    'docs/_static'
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


def test_render_svg_preserves_basic_16_color_ansi_segments(
    tmp_path: Path,
) -> None:
    # Regression guard: ansi_sgr_style used to only decode the extended
    # SGR forms (38;2;r;g;b truecolor, 38;5;n 256-color) and silently
    # dropped the plain, no-prefix 8/16-color codes (30-37 normal, 90-97
    # bright) -- the form a contributor would type from memory (see
    # task-11-report.md: docs/examples/widgets/multi_range_bar.py
    # originally used exactly this form and rendered with no color and no
    # error). No demo or library code currently emits this form (confirmed
    # by grep), so this test is what exercises the branch.
    output = tmp_path / 'demo.svg'
    demos.render_svg(
        output,
        title='Demo',
        frames=[
            [
                (
                    '\x1b[31mred\x1b[39m \x1b[32mgreen\x1b[39m '
                    '\x1b[91mbright-red\x1b[39m'
                )
            ],
        ],
    )

    text = output.read_text(encoding='utf-8')
    assert 'style="fill: #800000">red</tspan>' in text
    assert 'style="fill: #008000">green</tspan>' in text
    assert 'style="fill: #ff0000">bright-red</tspan>' in text
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


def test_render_svg_labels_root_for_accessibility(tmp_path: Path) -> None:
    output = tmp_path / 'demo.svg'
    demos.render_svg(
        output,
        title='Demo Title',
        frames=[['a'], ['b']],
        description='A demo description.',
    )
    text = output.read_text(encoding='utf-8')

    assert 'role="img"' in text
    title_match = re.search(r'<title id="([^"]+)">Demo Title</title>', text)
    desc_match = re.search(
        r'<desc id="([^"]+)">A demo description\.</desc>', text
    )
    assert title_match is not None, text
    assert desc_match is not None, text
    assert (
        f'aria-labelledby="{title_match.group(1)} {desc_match.group(1)}"'
        in text
    )


def test_render_svg_reduced_motion_rule_freezes_on_last_frame(
    tmp_path: Path,
) -> None:
    output = tmp_path / 'demo.svg'
    demos.render_svg(output, title='Demo', frames=[['a'], ['b'], ['c']])
    text = output.read_text(encoding='utf-8')

    assert '@media (prefers-reduced-motion: reduce)' in text
    assert 'animate { display: none; }' in text
    # The override must be strong enough (!important) to beat the SMIL
    # animation, and must land on the *last* frame group, not the first --
    # confirmed live in a browser (see task-9-report.md) that a plain,
    # non-!important opacity override is silently outranked by the still-
    # running animated value every frame, and that landing on the last
    # frame (not the first) shows a finished bar rather than an empty one.
    assert 'g { display: none !important; opacity: 0 !important; }' in text
    assert (
        'g:last-of-type { display: inline !important; opacity: 1 !important; }'
    ) in text


def test_demo_description_strips_single_backtick_markup_from_real_docstring() -> (  # noqa: E501
    None
):
    # docs/examples/howto/custom_widget.py's docstring uses RST's
    # single-backtick inline-code style (`WidgetBase`) -- unlike the
    # widgets/*.py docstrings, which use double backticks (``Widget``).
    # Regression guard: an earlier version of demo_description only
    # stripped the double-backtick pattern, leaking single backticks
    # verbatim into 11 of the registry's 50 demos' <desc> text.
    demo = demos.DEMOS_BY_NAME['howto/custom-widget']

    description = demos.demo_description(demo)

    assert '`' not in description
    assert 'WidgetBase' in description


def test_demo_description_strips_double_and_single_backtick_markup(
    tmp_path: Path,
) -> None:
    # A docstring mixing both RST inline-code styles on one line, per the
    # ordering hazard called out on RST_DOUBLE_BACKTICK_RE /
    # RST_SINGLE_BACKTICK_RE: stripping must resolve every double-backtick
    # pair as a complete first pass, separately from single-backtick pairs
    # -- not as one combined alternation applied once, which could match
    # the *inner* backtick pair of a ``Widget`` run before the outer one
    # and leave the outer two backticks behind.
    source = tmp_path / 'mixed_markup_demo.py'
    source.write_text(
        '"""``Widget`` reads `config` and writes `Output` files."""\n'
    )
    demo = types.SimpleNamespace(
        name='mixed-markup-demo', title='Mixed', path=source
    )

    description = demos.demo_description(demo)

    assert '`' not in description
    assert description == 'Widget reads config and writes Output files.'


@pytest.mark.parametrize('demo', demos.DEMOS, ids=lambda demo: demo.name)
def test_every_registered_demo_module_has_a_docstring(
    demo: demos.Demo,
) -> None:
    # demo_description()'s no-docstring fallback ("Terminal recording of
    # {title}.") is the same near-useless-read-aloud placeholder the SVG
    # <desc> exists to avoid -- it is a defensive fallback for a demo
    # added without one in the future, not something any demo currently
    # needs. This guard makes that assumption explicit and checked: if it
    # ever fails, a newly added module is missing a docstring, not this
    # test being wrong.
    assert demos.load_example(demo).__doc__


def test_normalize_terminal_line_keeps_timing_text_verbatim() -> None:
    # There used to be a TIMING_FIELD_RE zeroing "Elapsed Time:"/"ETA:"/
    # "Time:" readings, because the original capture ran under a real,
    # unfrozen clock and those readings differed every run. Every demo's
    # capture now runs under the frozen, deterministically-ticking clock
    # instead (see _demo_argv), so those readings are already byte-stable
    # on their own -- proven empirically (see normalize_terminal_line's
    # docstring) -- and zeroing them destroyed the one thing widgets like
    # CurrentTime and Timer exist to show. Nothing should rewrite this text
    # anymore.
    line = 'Current Time: 13:44:08 |####| Elapsed Time: 0:00:01 ETA:   0:00:02'
    assert demos.normalize_terminal_line(line) == line


def test_normalize_terminal_line_strips_stray_cursor_control_codes() -> None:
    # A line that is nothing but cursor-repositioning noise (see
    # MULTIBAR_REPOSITION_RE / STRAY_CSI_RE) must normalize to empty, not
    # leak a raw ESC byte into SVG text -- that byte is not valid XML.
    assert demos.normalize_terminal_line('\x1b[1F') == ''
    assert demos.normalize_terminal_line('\x1b[2Fbuild 10%\x1b[2E') == (
        'build 10%'
    )


def test_parse_frames_no_longer_rewrites_timing_text() -> None:
    frames = demos.parse_frames(
        'Build:  50% Elapsed Time: 0:01:23 ETA:   9:08:07\n'
        'Build: 100% Elapsed Time: 0:00:04 Time:  2:03:04'
    )
    assert frames == [
        ['Build:  50% Elapsed Time: 0:01:23 ETA:   9:08:07'],
        ['Build: 100% Elapsed Time: 0:00:04 Time:  2:03:04'],
    ]


def test_parse_frames_splits_carriage_return_output() -> None:
    frames = demos.parse_frames('zero\rone\ntwo\rthree')
    assert frames == [['zero'], ['one'], ['two'], ['three']]


def test_limit_animation_frames_keeps_more_animation_states() -> None:
    frames = demos.parse_frames(
        '\n'.join(f'frame {index}' for index in range(30))
    )
    limited = demos.limit_animation_frames(frames, 24)

    assert len(limited) == 24
    assert limited[0] == ['frame 0']
    assert limited[-1] == ['frame 29']


def test_dedupe_consecutive_frames_collapses_repeats_only() -> None:
    # MultiBar's forced final render can re-emit a state the immediately
    # preceding, non-forced render already showed (progressbar/multi.py's
    # `run`) -- collapse only *consecutive* repeats, not repeats separated
    # by other content, since the latter are a real (if unlikely) return to
    # an earlier-seen state, not a redundant redraw.
    frames = [['a'], ['a'], ['b'], ['b'], ['b'], ['a'], ['c']]
    assert demos.dedupe_consecutive_frames(frames) == [
        ['a'],
        ['b'],
        ['a'],
        ['c'],
    ]


def test_dedupe_consecutive_frames_handles_empty_input() -> None:
    assert demos.dedupe_consecutive_frames([]) == []


def test_parse_frames_groups_multibar_redraws_by_offset() -> None:
    # MultiBar redraws one bar at a time, repositioning the cursor to that
    # bar's row and back (PREVIOUS_LINE/NEXT_LINE) instead of rewriting the
    # whole screen with a single \r like a lone ProgressBar. Splitting on \r
    # would scatter "build" and "test" across separate single-line frames
    # and never show them together, which defeats a multi-bar demo.
    output = (
        '\x1b[2Fbuild 10%\x1b[2E\x1b[1Ftest 5%\x1b[1E\x1b[2Fbuild 20%\x1b[2E'
    )
    frames = demos.parse_frames(output)
    assert frames == [
        ['build 10%'],
        ['build 10%', 'test 5%'],
        ['build 20%', 'test 5%'],
    ]


def test_readme_demos_are_registered_in_display_order() -> None:
    readme_demos = [
        demo for demo in demos.DEMOS if demo.name.startswith('readme/')
    ]
    assert [(demo.name, demo.title) for demo in readme_demos] == [
        ('readme/hero', 'Progress with clean logs'),
        ('readme/multibar', 'Multiple active jobs'),
        ('readme/unknown-length', 'Unknown length'),
    ]


@pytest.mark.parametrize('demo', demos.DEMOS, ids=lambda demo: demo.name)
def test_every_demo_animates_across_at_least_two_frames(
    demo: demos.Demo,
) -> None:
    # This is exactly what would have caught widgets/timer rendering as a
    # single static "Elapsed Time: 0:00:00" frame: its original 24-step,
    # 5ms-per-step run never accumulated a whole second of elapsed time to
    # display (format_time truncates to 1s precision), so every frame was
    # identical and dedupe_consecutive_frames correctly collapsed them to
    # one. Fixed by giving the demo a longer run (docs/examples/widgets/
    # timer.py), not by weakening this assertion -- a demo that genuinely
    # cannot produce two distinct frames needs the same visible,
    # commented-and-named opt-out as Demo.drift_check, not a silent
    # exception here.
    frames = demos.capture_demo(demo)
    assert len(frames) >= 2, (
        f'{demo.name} produced only one distinct frame -- its animation '
        'never visibly changes'
    )


# Demos whose entire purpose is a time-derived reading (an elapsed duration,
# a countdown, a projected clock time, the time of day) rather than a demo
# that merely happens to show elapsed/ETA text as part of ProgressBar's
# default widgets. widgets/bar showing a static "0:00:00" is irrelevant --
# nobody reads that page for the ETA -- so this is a named, explicit list,
# not every demo with a timing field: a future contributor adding a fifth
# ETA variant should see this pattern and extend the list, rather than an
# over-general assertion failing on unrelated demos with a legitimately
# static reading. Each regex targets only the widget's *own* in-progress
# reading -- the not-yet-started placeholder ("--:--:--", "----/--/--
# --:--:--") and the finished-state label ("Time:", "Finished at:") use
# different text and are deliberately excluded, so a demo whose countdown
# never itself changes cannot pass by counting those bookend frames as the
# "at least two values".
TIME_DERIVED_WIDGET_FIELDS = {
    'widgets/timer': re.compile(r'Elapsed Time:\s*(\d+:\d{2}:\d{2})'),
    'widgets/eta': re.compile(r'\bETA:\s*(\d+:\d{2}:\d{2})'),
    'widgets/adaptive-eta': re.compile(r'\bETA:\s*(\d+:\d{2}:\d{2})'),
    'widgets/smoothing-eta': re.compile(r'\bETA:\s*(\d+:\d{2}:\d{2})'),
    'widgets/absolute-eta': re.compile(
        r'Estimated finish time: (\d{4}-\d{2}-\d{2} \d+:\d{2}:\d{2})'
    ),
    'widgets/current-time': re.compile(r'Current Time:\s*(\d+:\d{2}:\d{2})'),
}


@pytest.mark.parametrize(
    'demo_name, field_re',
    sorted(TIME_DERIVED_WIDGET_FIELDS.items()),
)
def test_time_derived_widget_reading_visibly_changes(
    demo_name: str,
    field_re: re.Pattern[str],
) -> None:
    demo = demos.DEMOS_BY_NAME[demo_name]
    frames = demos.capture_demo(demo)
    lines = (
        demos.ANSI_SGR_RE.sub('', line) for frame in frames for line in frame
    )
    values = {
        match.group(1) for line in lines if (match := field_re.search(line))
    }

    assert len(values) >= 2, (
        f'{demo_name}: its own time-derived reading never changes -- saw '
        f'only {values!r} across {len(frames)} frames'
    )


def test_readme_uses_absolute_demo_asset_urls() -> None:
    # README.rst is rendered as the PyPI package description, which serves
    # the file with no repository around it -- relative image paths (e.g.
    # `docs/_static/...`) 404 there, so demo assets must be absolute URLs
    # back to this repo instead, pointing at the registry's committed demo
    # names under docs/_static/demos/ (see docs/examples/_registry.py's
    # Demo.svg_path), not the superseded docs/_static/progressbar-*.svg
    # assets those replaced.
    readme = (demos.ROOT / 'README.rst').read_text(encoding='utf-8')

    assert f'.. image:: {_RAW_ASSET_BASE}/demos/readme-hero.svg' in readme
    assert f'.. image:: {_RAW_ASSET_BASE}/demos/readme-multibar.svg' in readme
    assert (
        f'.. image:: {_RAW_ASSET_BASE}/demos/readme-unknown-length.svg'
        in readme
    )
    assert '.. image:: docs/_static/' not in readme
    assert 'progressbar-hero.svg' not in readme
    assert 'progressbar-multibar.svg' not in readme
    assert 'progressbar-unknown-length.svg' not in readme
    assert 'progressbar-ergonomics.svg' not in readme
    assert 'Tqdm-style ergonomic options' not in readme


def _readme_demo_block(example_name: str) -> str:
    """Return ``docs/examples/readme/{example_name}.py``, RST-indented.

    README.rst is plain RST rendered standalone on PyPI -- no Sphinx, so no
    ``literalinclude`` -- meaning each ``.. code:: python`` block is a
    literal copy of the matching example file's current contents, indented
    four spaces per RST's code-block convention. This must stay a copy
    checked by a test, not just a one-time paste: nothing else would catch
    the block silently drifting out of sync the next time someone edits the
    example but not the README.
    """
    source = (
        demos.ROOT / 'docs' / 'examples' / 'readme' / f'{example_name}.py'
    ).read_text(encoding='utf-8')
    return '\n'.join(
        f'    {line}' if line else '' for line in source.splitlines()
    )


@pytest.mark.parametrize(
    'example_name', ['hero', 'multibar', 'unknown_length']
)
def test_readme_code_blocks_match_example_sources(example_name: str) -> None:
    readme = (demos.ROOT / 'README.rst').read_text(encoding='utf-8')
    assert _readme_demo_block(example_name) in readme


def test_readme_omits_obsolete_gpg_release_verification() -> None:
    readme = (demos.ROOT / 'README.rst').read_text(encoding='utf-8')

    assert 'Release verification' not in readme
    assert 'GPG' not in readme
    assert 'pgp.mit.edu' not in readme
    assert '.tar.gz.asc' not in readme


def test_multibar_demo_captures_rendered_progressbar_output() -> None:
    demo = demos.DEMOS_BY_NAME['readme/multibar']
    frames = demos.capture_demo(demo)
    text = '\n'.join(line for frame in frames for line in frame)

    assert frames
    assert 'build' in text
    assert 'test' in text
    assert 'Elapsed Time:' in text
    assert '(24 of 24)' in text
    # The two bars are shown together at least once -- the whole point of
    # this demo -- even though how many redraws land in any single capture
    # is not deterministic (see _demo_argv's docstring on MultiBar's
    # threaded render loop).
    assert any(
        len(frame) == 2
        and any('build' in line for line in frame)
        and any('test' in line for line in frame)
        for frame in frames
    )


def test_multibar_demo_shows_both_bars_finishing() -> None:
    demo = demos.DEMOS_BY_NAME['readme/multibar']
    frames = demos.capture_demo(demo)
    last_frame = '\n'.join(frames[-1])

    assert 'build' in last_frame
    assert 'test' in last_frame
    assert last_frame.count('(24 of 24)') == 2


def test_capture_demo_reports_a_crashing_example_clearly(
    tmp_path: Path,
) -> None:
    script = tmp_path / 'broken.py'
    script.write_text("raise RuntimeError('boom')\n", encoding='utf-8')
    demo = types.SimpleNamespace(
        name='broken-test',
        path=script,
        term_width=80,
        log_lines=0,
        max_frames=24,
    )

    with pytest.raises(SystemExit) as error:
        demos.capture_demo(demo)

    # Python 3.13 colorizes tracebacks when attached to a terminal (which
    # the pty makes it), so the traceback excerpt has ANSI codes woven
    # through it -- strip them before matching the underlying text.
    message = demos.ANSI_SGR_RE.sub('', str(error.value))
    assert 'example failed: broken-test (exit code 1)' in message
    assert 'RuntimeError' in message
    assert 'boom' in message


def test_capture_demo_reports_a_hanging_example_clearly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = tmp_path / 'hangs.py'
    script.write_text(
        'import time\nwhile True:\n    time.sleep(3600)\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(demos, 'CAPTURE_TIMEOUT_SECONDS', 1.0)
    demo = types.SimpleNamespace(
        name='hang-test',
        path=script,
        term_width=80,
        log_lines=0,
        max_frames=24,
    )

    with pytest.raises(SystemExit) as error:
        demos.capture_demo(demo)

    assert str(error.value) == 'example hung: hang-test'


def test_hero_demo_keeps_recent_logs_visible_above_progress() -> None:
    demo = demos.DEMOS_BY_NAME['readme/hero']
    frames = demos.capture_demo(demo)

    assert max(len(frame) for frame in frames) >= 3
    assert any(
        any(line.startswith('log: completed step 8') for line in frame)
        and any('Build' in line for line in frame)
        for frame in frames
    )


def test_logging_integration_demo_keeps_recent_logs_visible_above_progress() -> (  # noqa: E501
    None
):
    # Regression guard: keep_recent_logs_with_progress used to classify a
    # line as "log output to retain" only by a literal "log:" prefix, which
    # happened to hold for readme/hero.py's demo but not this one --
    # logger.info(...) has no such prefix, so "completed step 8" was
    # misclassified as the bar's own (bar-less) redraw and surfaced as its
    # own isolated frame instead of staying visible above the next one. See
    # keep_recent_logs_with_progress's docstring for the BAR_RE-based fix.
    demo = demos.DEMOS_BY_NAME['howto/logging-integration']
    frames = demos.capture_demo(demo)

    assert max(len(frame) for frame in frames) >= 2
    assert any(
        any('completed step 8' in line for line in frame)
        and any(demos.BAR_RE.search(line) for line in frame)
        for frame in frames
    )


def test_redirect_stdout_demo_keeps_recent_prints_visible_above_progress() -> (
    None
):
    # Same regression as test_logging_integration_demo_... above: this
    # demo's plain print(f'Processing {filename}') calls have no "log:"
    # prefix either.
    demo = demos.DEMOS_BY_NAME['howto/redirect-stdout']
    frames = demos.capture_demo(demo)

    assert max(len(frame) for frame in frames) >= 2
    assert any(
        any('Processing errors.log' in line for line in frame)
        and any(demos.BAR_RE.search(line) for line in frame)
        for frame in frames
    )


def test_tutorial_step5_demo_keeps_recent_prints_visible_above_progress() -> (
    None
):
    # Regression guard: docs/examples/_registry.py originally registered
    # this demo with no log_lines (defaulting to 0), so
    # keep_recent_logs_with_progress never ran for it at all -- gated on
    # `if demo.log_lines:` in capture_demo -- even though the demo's own
    # docstring claims printed output "is held back and flushed above the
    # bar on its next redraw." Every print(f'Reached step {i}') instead
    # flashed by in its own isolated, bar-less frame: the animation showed
    # exactly the opposite of what the demo claims, and Task 12's tutorial
    # prose is written around this exact demo. Caught by external review
    # of this task, not by its own self-review -- see the fix report
    # appended to task-11-report.md. See
    # test_demos_that_print_or_log_retain_it_or_are_explicitly_exempt
    # below for the general guard added so this class of omission can't
    # recur silently.
    demo = demos.DEMOS_BY_NAME['tutorial/step5']
    frames = demos.capture_demo(demo)

    assert max(len(frame) for frame in frames) >= 2
    assert any(
        any('Reached step 0' in line for line in frame)
        and any(demos.BAR_RE.search(line) for line in frame)
        for frame in frames
    )


# Demos whose example module calls print(...)/logger.<level>(...) but
# deliberately do not retain that output via log_lines, because the call
# does not produce human-readable status text meant to stay visible above
# the bar. A future demo like this should extend this set with the same
# kind of comment explaining why not, rather than the guard test below
# being weakened or worked around.
DEMOS_WITH_NON_LOG_PRINTS: frozenset[str] = frozenset(
    {
        # print('\n' * BARS, end='') / print() here only reserve and then
        # release terminal rows for line_offset's stacked bars -- cursor
        # positioning, not log/status text a reader is meant to see
        # retained above a bar. See
        # docs/examples/howto/multibar_line_offset.py's docstring.
        'howto/multibar-line-offset',
    }
)

_PRINT_OR_LOGGER_CALL_RE = re.compile(r'\bprint\(|\blogger\.\w+\(')


@pytest.mark.parametrize('demo', demos.DEMOS, ids=lambda demo: demo.name)
def test_demos_that_print_or_log_retain_it_or_are_explicitly_exempt(
    demo: demos.Demo,
) -> None:
    # keep_recent_logs_with_progress only ever runs when log_lines > 0
    # (`if demo.log_lines:` in capture_demo) -- a demo whose source calls
    # print(...)/logger.<level>(...) but leaves log_lines at its default
    # of 0 silently renders with that output flashing by in its own,
    # bar-less frame, never shown together with the bar it is printed
    # "above". This is exactly the bug fixed in tutorial/step5 (see
    # test_tutorial_step5_demo_keeps_recent_prints_visible_above_progress
    # above): its registry entry had no log_lines despite the demo's own
    # docstring promising retained output, and nothing caught it short of
    # rendering all 50 demos and reading each one by eye. This guard makes
    # that whole class of omission fail a test instead.
    source = demo.path.read_text(encoding='utf-8')
    if not _PRINT_OR_LOGGER_CALL_RE.search(source):
        return

    assert demo.log_lines > 0 or demo.name in DEMOS_WITH_NON_LOG_PRINTS, (
        f'{demo.name} calls print()/logger.*() but has log_lines=0 and is '
        'not in DEMOS_WITH_NON_LOG_PRINTS -- its printed output will '
        'never appear together with the bar redraw (see '
        'keep_recent_logs_with_progress). Set log_lines>0 in '
        'docs/examples/_registry.py, or add this demo to '
        'DEMOS_WITH_NON_LOG_PRINTS with a comment explaining why its '
        'output is not meant to be retained.'
    )


def test_hero_demo_shows_wide_determinate_progress_bar() -> None:
    demo = demos.DEMOS_BY_NAME['readme/hero']
    frames = demos.capture_demo(demo)
    first_frame = '\n'.join(frames[0])
    last_frame = '\n'.join(frames[-1])
    text = '\n'.join(line for frame in frames for line in frame)

    assert '0%' in first_frame
    assert '100%' in last_frame
    assert max(_bar_widths(frames)) >= 32
    assert 'Elapsed Time:' in text


# No win32 skipif here: the module-level guard above already means this
# file never loads on Windows.
def test_readme_demos_capture_real_percentage_color_changes() -> None:
    demo = demos.DEMOS_BY_NAME['readme/hero']
    text = '\n'.join(
        line for frame in demos.capture_demo(demo) for line in frame
    )

    assert '\x1b[38;2;255;0;0m' in text
    assert '\x1b[38;2;0;255;0m' in text


def test_absolute_eta_demo_shows_a_deterministic_projected_finish_time() -> (
    None
):
    # The demo now runs long enough (see docs/examples/widgets/
    # absolute_eta.py) for the projected finish time to shift as the
    # estimate stabilizes -- it is not pinned to the exact frozen start
    # instant anymore (test_time_derived_widget_reading_visibly_changes
    # covers that it changes at all). It is still deterministic: the frozen
    # clock never advances far enough during a ~6s run to cross a day
    # boundary, so the projected date is always the frozen one.
    demo = demos.DEMOS_BY_NAME['widgets/absolute-eta']
    frames = demos.capture_demo(demo)
    text = '\n'.join(line for frame in frames for line in frame)

    frozen_date = demos.CAPTURE_CLOCK_INSTANT.split('T')[0]
    assert f'Estimated finish time: {frozen_date} ' in text
    assert 'Estimated finish time:  ----/--/-- --:--:--' in text


def test_current_time_demo_shows_a_frozen_plausible_clock_reading() -> None:
    demo = demos.DEMOS_BY_NAME['widgets/current-time']
    frames = demos.capture_demo(demo)
    text = '\n'.join(line for frame in frames for line in frame)

    clock_reading = demos.CAPTURE_CLOCK_INSTANT.split('T')[1]
    assert f'Current Time: {clock_reading}' in text
    # Regression guard for the bug that shipped a now-removed
    # TIMING_FIELD_RE: it zeroed this exact reading to "0:00:00".
    assert '0:00:00' not in text


def test_bouncing_bar_demo_respects_narrow_term_width() -> None:
    demo = demos.DEMOS_BY_NAME['widgets/bouncing-bar']
    assert demo.term_width == 30

    frames = demos.capture_demo(demo)
    widths = [len(line) for frame in frames for line in frame]

    assert widths
    assert max(widths) <= demo.term_width


def test_two_captures_of_the_same_demo_are_byte_identical() -> None:
    demo = demos.DEMOS_BY_NAME['readme/hero']
    first = demos.svg_document(demo.title, demos.capture_demo(demo))
    second = demos.svg_document(demo.title, demos.capture_demo(demo))
    assert first == second


def test_main_rejects_unknown_only_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys, 'argv', ['render_demos.py', '--only', 'no/such-demo']
    )

    with pytest.raises(SystemExit) as error:
        demos.main()

    assert 'unknown demo: no/such-demo' in str(error.value)


def test_check_mode_skips_and_reports_drift_check_false_demos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A demo opted out of the drift gate (Demo.drift_check=False -- see
    # docs/examples/_registry.py's two MultiBar entries) must not be
    # captured or compared at all under --check: there is deliberately no
    # committed asset to compare it against here, so capture_demo would be
    # the only way this test could still fail.
    demo = types.SimpleNamespace(
        name='flaky-demo',
        title='Flaky',
        svg_path=tmp_path / 'never-written.svg',
        drift_check=False,
    )

    def _must_not_be_called(_: object) -> list[list[str]]:
        raise AssertionError('drift_check=False demo must not be captured')

    monkeypatch.setattr(demos, 'DEMOS', [demo])
    monkeypatch.setattr(demos, 'DEMOS_BY_NAME', {demo.name: demo})
    monkeypatch.setattr(demos, 'capture_demo', _must_not_be_called)
    monkeypatch.setattr(sys, 'argv', ['render_demos.py', '--check'])

    demos.main()

    assert not demo.svg_path.exists()
    stderr = capsys.readouterr().err
    assert 'not gating 1 demo' in stderr
    assert demo.name in stderr
    assert 'drift_check' in stderr


def test_render_mode_still_renders_drift_check_false_demos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # drift_check only opts a demo out of the --check comparison -- a plain
    # render (e.g. to hand-verify it, per CONTRIBUTING.rst) must still work.
    output = tmp_path / 'flaky.svg'
    source = tmp_path / 'flaky_demo.py'
    source.write_text('"""A flaky demo, for test purposes only."""\n')
    demo = types.SimpleNamespace(
        name='flaky-demo',
        title='Flaky',
        svg_path=output,
        drift_check=False,
        path=source,
    )

    monkeypatch.setattr(demos, 'DEMOS_BY_NAME', {demo.name: demo})
    monkeypatch.setattr(demos, 'capture_demo', lambda _: [['rendered']])
    monkeypatch.setattr(sys, 'argv', ['render_demos.py', '--only', demo.name])

    demos.main()

    assert output.exists()


def test_check_mode_does_not_rewrite_mismatched_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / 'stale.svg'
    output.write_text('stale asset', encoding='utf-8')
    source = tmp_path / 'fake_check_demo.py'
    source.write_text('"""A fake check demo, for test purposes only."""\n')
    demo = types.SimpleNamespace(
        name='fake-check-demo',
        title='Fake',
        svg_path=output,
        drift_check=True,
        path=source,
    )

    monkeypatch.setattr(demos, 'DEMOS_BY_NAME', {demo.name: demo})
    monkeypatch.setattr(demos, 'capture_demo', lambda _: [['fresh asset']])
    monkeypatch.setattr(
        sys, 'argv', ['render_demos.py', '--check', '--only', demo.name]
    )

    with pytest.raises(SystemExit) as error:
        demos.main()

    assert 'outdated generated asset' in str(error.value)
    assert output.read_text(encoding='utf-8') == 'stale asset'
