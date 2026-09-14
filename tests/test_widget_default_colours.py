"""Default widget output is coloured without custom example formatting."""

from __future__ import annotations

import io
import re

import pytest

import progressbar
from progressbar import env, utils, widgets
from progressbar.terminal import colors


@pytest.fixture(autouse=True)
def ansi_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise ANSI output independently of the runner's console support."""
    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.XTERM_256)


@pytest.mark.parametrize(
    'widget',
    [
        widgets.AnimatedMarker(),
        widgets.BouncingBar(),
        widgets.Counter(),
        widgets.FormatLabel('%(value)d items'),
        widgets.Timer(),
        widgets.UnitProgress(unit='files'),
    ],
)
@pytest.mark.parametrize('known_total', [True, False])
@pytest.mark.parametrize('enabled', [True, False])
def test_default_widget_colour_output(
    widget: widgets.WidgetBase, known_total: bool, enabled: bool
) -> None:
    output: io.StringIO = io.StringIO()
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        widgets=[widget],
        max_value=10 if known_total else progressbar.UnknownLength,
        fd=output,
        term_width=30,
        enable_colors=enabled,
    )
    with bar:
        bar.update(5, force=True)
    lines: list[str] = output.getvalue().splitlines()
    assert lines
    assert all(('\x1b[' in line) is enabled for line in lines if line)
    assert all(utils.len_color(line) <= 30 for line in lines)


@pytest.mark.parametrize('markers', ['|/-\\', '.'])
def test_spinner_cycles_colours_without_changing_its_frames(
    markers: str,
) -> None:
    widget: widgets.AnimatedMarker = widgets.AnimatedMarker(markers=markers)
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO(), max_value=progressbar.UnknownLength
    )
    frames: list[str] = [
        widget(bar, {'updates': update}) for update in range(12)
    ]
    assert [utils.no_color(frame) for frame in frames] == [
        markers[update % len(markers)] for update in range(12)
    ]
    foregrounds: set[str] = {
        code
        for frame in frames
        for code in re.findall(r'\x1b\[38;[^m]+m', frame)
    }
    assert len(foregrounds) >= 3
    wrapped: str = widget(bar, {'updates': widget.color_cycle})
    assert re.findall(r'\x1b\[38;[^m]+m', wrapped) == re.findall(
        r'\x1b\[38;[^m]+m', frames[0]
    )


def test_spinner_walks_the_rainbow_one_step_per_redraw() -> None:
    widget: widgets.AnimatedMarker = widgets.AnimatedMarker()
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO(), max_value=progressbar.UnknownLength
    )
    assert widget.color_cycle == 30
    update: int
    for update in range(31):
        expected: str = colors.rainbow.get_color(update / 30).fg(
            widget.markers[update % 4]
        )
        assert widget(bar, {'updates': update}) == expected


def test_spinner_color_cycle_override() -> None:
    widget: widgets.AnimatedMarker = widgets.AnimatedMarker(
        markers='.', color_cycle=4
    )
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO(), max_value=progressbar.UnknownLength
    )
    frames: list[str] = [
        widget(bar, {'updates': update}) for update in range(5)
    ]
    assert len(set(frames[:4])) == 4
    assert frames[4] == frames[0]


@pytest.mark.parametrize('color_cycle', [0, -1])
def test_spinner_color_cycle_must_be_positive(color_cycle: int) -> None:
    with pytest.raises(ValueError, match='color_cycle'):
        widgets.AnimatedMarker(color_cycle=color_cycle)


def test_spinner_widget_colour_opt_out() -> None:
    widget: widgets.AnimatedMarker = widgets.AnimatedMarker(
        fixed_colors={'fg_none': None, 'bg_none': None},
        gradient_colors={'fg': None, 'bg': None},
    )
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO(), max_value=progressbar.UnknownLength
    )
    assert widget(bar, {'updates': 0}) == '|'


def test_spinner_single_colour_override() -> None:
    widget: widgets.AnimatedMarker = widgets.AnimatedMarker(
        gradient_colors={'fg': colors.blue},
    )
    bar: progressbar.ProgressBar = progressbar.ProgressBar(fd=io.StringIO())
    update: int
    for update in range(12):
        frame: str = widget(bar, {'updates': update})
        assert frame == colors.blue.fg(widget.markers[update % 4])


def test_bouncing_bar_colour_opt_out_preserves_width() -> None:
    widget: widgets.BouncingBar = widgets.BouncingBar()
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO(), max_value=progressbar.UnknownLength
    )
    data: widgets.Data = {'total_seconds_elapsed': 1, 'percentage': None}
    output: str = widget(bar, data, width=10, color=False)
    assert '\x1b[' not in output
    assert len(output) == 10


def test_bouncing_bar_with_no_room_for_padding() -> None:
    widget: widgets.BouncingBar = widgets.BouncingBar(left='', right='')
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO(), max_value=progressbar.UnknownLength
    )
    output: str = widget(bar, {'percentage': None}, width=0)
    assert utils.no_color(output) == '#'
