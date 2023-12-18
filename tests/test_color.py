from __future__ import annotations

import typing

import progressbar
import progressbar.env
import progressbar.terminal
import pytest
from progressbar import env, terminal, widgets
from progressbar.terminal import Colors, apply_colors, colors


@pytest.mark.parametrize(
    'variable',
    [
        'PROGRESSBAR_ENABLE_COLORS',
        'FORCE_COLOR',
    ],
)
def test_color_environment_variables(monkeypatch, variable):
    monkeypatch.setattr(
        env,
        'COLOR_SUPPORT',
        progressbar.env.ColorSupport.XTERM_256,
    )

    monkeypatch.setenv(variable, '1')
    bar = progressbar.ProgressBar()
    assert bar.enable_colors

    monkeypatch.setenv(variable, '0')
    bar = progressbar.ProgressBar()
    assert not bar.enable_colors


@pytest.mark.parametrize(
    'variable',
    [
        'FORCE_COLOR',
        'PROGRESSBAR_ENABLE_COLORS',
        'COLORTERM',
        'TERM',
    ],
)
@pytest.mark.parametrize(
    'value',
    [
        '',
        'truecolor',
        '24bit',
        '256',
        'xterm-256',
        'xterm',
    ],
)
def test_color_support_from_env(monkeypatch, variable, value):
    monkeypatch.setenv('JUPYTER_COLUMNS', '')
    monkeypatch.setenv('JUPYTER_LINES', '')

    monkeypatch.setenv(variable, value)
    progressbar.env.ColorSupport.from_env()


@pytest.mark.parametrize(
    'variable',
    [
        'JUPYTER_COLUMNS',
        'JUPYTER_LINES',
    ],
)
def test_color_support_from_env_jupyter(monkeypatch, variable):
    monkeypatch.setenv(variable, '80')
    progressbar.env.ColorSupport.from_env()


def test_enable_colors_flags():
    bar = progressbar.ProgressBar(enable_colors=True)
    assert bar.enable_colors

    bar = progressbar.ProgressBar(enable_colors=False)
    assert not bar.enable_colors

    bar = progressbar.ProgressBar(
        enable_colors=progressbar.env.ColorSupport.XTERM_TRUECOLOR,
    )
    assert bar.enable_colors

    with pytest.raises(ValueError):
        progressbar.ProgressBar(enable_colors=12345)


class _TestFixedColorSupport(progressbar.widgets.WidgetBase):
    _fixed_colors: typing.ClassVar[
        widgets.TFixedColors
    ] = widgets.TFixedColors(
        fg_none=progressbar.widgets.colors.yellow,
        bg_none=None,
    )

    def __call__(self, *args, **kwargs):
        pass


class _TestFixedGradientSupport(progressbar.widgets.WidgetBase):
    _gradient_colors: typing.ClassVar[
        widgets.TGradientColors
    ] = widgets.TGradientColors(
        fg=progressbar.widgets.colors.gradient,
        bg=None,
    )

    def __call__(self, *args, **kwargs):
        pass


@pytest.mark.parametrize(
    'widget',
    [
        progressbar.Percentage,
        progressbar.SimpleProgress,
        _TestFixedColorSupport,
        _TestFixedGradientSupport,
    ],
)
def test_color_widgets(widget):
    assert widget().uses_colors
    print(f'{widget} has colors? {widget.uses_colors}')


def test_color_gradient():
    gradient = terminal.ColorGradient(colors.red)
    assert gradient.get_color(0) == gradient.get_color(-1)
    assert gradient.get_color(1) == gradient.get_color(2)

    assert gradient.get_color(0.5) == colors.red

    gradient = terminal.ColorGradient(colors.red, colors.yellow)
    assert gradient.get_color(0) == colors.red
    assert gradient.get_color(1) == colors.yellow
    assert gradient.get_color(0.5) != colors.red
    assert gradient.get_color(0.5) != colors.yellow

    gradient = terminal.ColorGradient(
        colors.red, colors.yellow, interpolate=False,
    )
    assert gradient.get_color(0) == colors.red
    assert gradient.get_color(1) == colors.yellow
    assert gradient.get_color(0.5) == colors.red


@pytest.mark.parametrize(
    'widget',
    [
        progressbar.Counter,
    ],
)
def test_no_color_widgets(widget):
    assert not widget().uses_colors
    print(f'{widget} has colors? {widget.uses_colors}')

    assert widget(
        fixed_colors=_TestFixedColorSupport._fixed_colors,
    ).uses_colors
    assert widget(
        gradient_colors=_TestFixedGradientSupport._gradient_colors,
    ).uses_colors


def test_colors():
    for colors_ in Colors.by_rgb.values():
        for color in colors_:
            rgb = color.rgb
            assert rgb.rgb
            assert rgb.hex
            assert rgb.to_ansi_16 is not None
            assert rgb.to_ansi_256 is not None
            assert color.underline
            assert color.fg
            assert color.bg
            assert str(color)
            assert str(rgb)


def test_color():
    color = colors.red
    assert color('x') == color.fg('x') != 'x'
    assert color.fg('x') != color.bg('x') != 'x'
    assert color.fg('x') != color.underline('x') != 'x'
    # Color hashes are based on the RGB value
    assert hash(color) == hash(terminal.Color(color.rgb, None, None, None))
    Colors.register(color.rgb)


@pytest.mark.parametrize(
    'rgb,hls',
    [
        (terminal.RGB(0, 0, 0), terminal.HSL(0, 0, 0)),
        (terminal.RGB(255, 255, 255), terminal.HSL(0, 0, 100)),
        (terminal.RGB(255, 0, 0), terminal.HSL(0, 100, 50)),
        (terminal.RGB(0, 255, 0), terminal.HSL(120, 100, 50)),
        (terminal.RGB(0, 0, 255), terminal.HSL(240, 100, 50)),
        (terminal.RGB(255, 255, 0), terminal.HSL(60, 100, 50)),
        (terminal.RGB(0, 255, 255), terminal.HSL(180, 100, 50)),
        (terminal.RGB(255, 0, 255), terminal.HSL(300, 100, 50)),
        (terminal.RGB(128, 128, 128), terminal.HSL(0, 0, 50)),
        (terminal.RGB(128, 0, 0), terminal.HSL(0, 100, 25)),
        (terminal.RGB(128, 128, 0), terminal.HSL(60, 100, 25)),
        (terminal.RGB(0, 128, 0), terminal.HSL(120, 100, 25)),
        (terminal.RGB(128, 0, 128), terminal.HSL(300, 100, 25)),
        (terminal.RGB(0, 128, 128), terminal.HSL(180, 100, 25)),
        (terminal.RGB(0, 0, 128), terminal.HSL(240, 100, 25)),
        (terminal.RGB(192, 192, 192), terminal.HSL(0, 0, 75)),
    ],
)
def test_rgb_to_hls(rgb, hls):
    assert terminal.HSL.from_rgb(rgb) == hls


@pytest.mark.parametrize(
    'text, fg, bg, fg_none, bg_none, percentage, expected',
    [
        ('test', None, None, None, None, None, 'test'),
        ('test', None, None, None, None, 1, 'test'),
        (
                'test',
                None,
                None,
                None,
                colors.red,
                None,
                '\x1b[48;5;9mtest\x1b[49m',
        ),
        (
                'test',
                None,
                colors.green,
                None,
                colors.red,
                None,
                '\x1b[48;5;9mtest\x1b[49m',
        ),
        ('test', None, colors.red, None, None, 1, '\x1b[48;5;9mtest\x1b[49m'),
        ('test', None, colors.red, None, None, None, 'test'),
        (
                'test',
                colors.green,
                None,
                colors.red,
                None,
                None,
                '\x1b[38;5;9mtest\x1b[39m',
        ),
        (
                'test',
                colors.green,
                colors.red,
                None,
                None,
                1,
                '\x1b[48;5;9m\x1b[38;5;2mtest\x1b[39m\x1b[49m',
        ),
        ('test', colors.red, None, None, None, 1, '\x1b[38;5;9mtest\x1b[39m'),
        ('test', colors.red, None, None, None, None, 'test'),
        ('test', colors.red, colors.red, None, None, None, 'test'),
        (
                'test',
                colors.red,
                colors.yellow,
                None,
                None,
                1,
                '\x1b[48;5;11m\x1b[38;5;9mtest\x1b[39m\x1b[49m',
        ),
        (
                'test',
                colors.red,
                colors.yellow,
                None,
                None,
                1,
                '\x1b[48;5;11m\x1b[38;5;9mtest\x1b[39m\x1b[49m',
        ),
    ],
)
def test_apply_colors(text, fg, bg, fg_none, bg_none, percentage, expected,
                      monkeypatch):
    monkeypatch.setattr(
        env,
        'COLOR_SUPPORT',
        progressbar.env.ColorSupport.XTERM_256,
    )
    assert (
            apply_colors(
                text,
                fg=fg,
                bg=bg,
                fg_none=fg_none,
                bg_none=bg_none,
                percentage=percentage,
            )
            == expected
    )


def test_ansi_color(monkeypatch):
    color = progressbar.terminal.Color(
        colors.red.rgb,
        colors.red.hls,
        'red-ansi',
        None,
    )

    for color_support in {
        env.ColorSupport.NONE,
        env.ColorSupport.XTERM,
        env.ColorSupport.XTERM_256,
        env.ColorSupport.XTERM_TRUECOLOR,
    }:
        monkeypatch.setattr(
            env,
            'COLOR_SUPPORT',
            color_support,
        )
        assert color.ansi is not None or color_support == env.ColorSupport.NONE


def test_sgr_call():
    assert progressbar.terminal.encircled('test') == '\x1b[52mtest\x1b[54m'
