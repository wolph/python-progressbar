from __future__ import annotations

import os

import pytest

import progressbar
import progressbar.terminal
from progressbar import env, terminal, widgets
from progressbar.terminal import Color, Colors, apply_colors, colors

ENVIRONMENT_VARIABLES = [
    'PROGRESSBAR_ENABLE_COLORS',
    'FORCE_COLOR',
    'COLORTERM',
    'TERM',
    'JUPYTER_COLUMNS',
    'JUPYTER_LINES',
    'JPY_PARENT_PID',
]


@pytest.fixture(autouse=True)
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Clear all environment variables that might affect the tests
    for variable in ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable, raising=False)

    monkeypatch.setattr(env, 'JUPYTER', False)


@pytest.mark.parametrize(
    'variable',
    [
        'PROGRESSBAR_ENABLE_COLORS',
        'FORCE_COLOR',
    ],
)
def test_color_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
) -> None:
    if os.name == 'nt':
        # Windows has special handling so we need to disable that to make the
        # tests work properly
        monkeypatch.setattr(os, 'name', 'posix')

    monkeypatch.setattr(
        env,
        'COLOR_SUPPORT',
        env.ColorSupport.XTERM_256,
    )

    monkeypatch.setenv(variable, 'true')
    bar = progressbar.ProgressBar()
    assert not env.is_ansi_terminal(bar.fd)
    assert not bar.is_ansi_terminal
    assert bar.enable_colors

    monkeypatch.setenv(variable, 'false')
    bar = progressbar.ProgressBar()
    assert not bar.enable_colors

    monkeypatch.setenv(variable, '')
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
def test_color_support_from_env(monkeypatch, variable, value) -> None:
    if os.name == 'nt':
        # Windows has special handling so we need to disable that to make the
        # tests work properly
        monkeypatch.setattr(os, 'name', 'posix')

    monkeypatch.setenv(variable, value)
    env.ColorSupport.from_env()


@pytest.mark.parametrize(
    ('term', 'expected'),
    [
        # Bare ``xterm`` and any ``xterm-*`` variant advertise (at least) 16
        # color support, matching the documented "if they contain ``xterm``"
        # behaviour and ``is_ansi_terminal``'s ``^xterm`` prefix match.
        ('xterm', env.ColorSupport.XTERM),
        ('xterm-color', env.ColorSupport.XTERM),
        ('xterm-16color', env.ColorSupport.XTERM),
        ('xterm-kitty', env.ColorSupport.XTERM),
        ('xterm-ghostty', env.ColorSupport.XTERM),
        # A ``256`` anywhere in the value still wins over plain xterm.
        ('xterm-256color', env.ColorSupport.XTERM_256),
        ('screen-256color', env.ColorSupport.XTERM_256),
    ],
)
def test_color_support_from_env_term(monkeypatch, term, expected) -> None:
    if os.name == 'nt':
        # Windows has special handling so we need to disable that to make the
        # tests work properly
        monkeypatch.setattr(os, 'name', 'posix')

    monkeypatch.setenv('TERM', term)
    assert env.ColorSupport.from_env() == expected


@pytest.mark.parametrize(
    'variable',
    [
        'JUPYTER_COLUMNS',
        'JUPYTER_LINES',
    ],
)
def test_color_support_from_env_jupyter(monkeypatch, variable) -> None:
    monkeypatch.setattr(env, 'JUPYTER', True)
    assert env.ColorSupport.from_env() == env.ColorSupport.XTERM_TRUECOLOR

    # Sanity check
    monkeypatch.setattr(env, 'JUPYTER', False)
    if os.name == 'nt':
        assert env.ColorSupport.from_env() == env.ColorSupport.WINDOWS
    else:
        assert env.ColorSupport.from_env() == env.ColorSupport.NONE


def test_enable_colors_flags() -> None:
    bar = progressbar.ProgressBar(enable_colors=True)
    assert bar.enable_colors

    bar = progressbar.ProgressBar(enable_colors=False)
    assert not bar.enable_colors

    bar = progressbar.ProgressBar(
        enable_colors=env.ColorSupport.XTERM_TRUECOLOR,
    )
    assert bar.enable_colors

    with pytest.raises(ValueError):
        progressbar.ProgressBar(enable_colors=12345)


class _TestFixedColorSupport(progressbar.widgets.WidgetBase):
    _fixed_colors: widgets.TFixedColors = widgets.TFixedColors(
        fg_none=progressbar.widgets.colors.yellow,
        bg_none=None,
    )

    def __call__(self, *args, **kwargs) -> None:
        pass


class _TestFixedGradientSupport(progressbar.widgets.WidgetBase):
    _gradient_colors: widgets.TGradientColors = widgets.TGradientColors(
        fg=progressbar.widgets.colors.gradient,
        bg=None,
    )

    def __call__(self, *args, **kwargs) -> None:
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
def test_color_widgets(widget) -> None:
    assert widget().uses_colors
    print(f'{widget} has colors? {widget.uses_colors}')


def test_color_gradient() -> None:
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
        colors.red,
        colors.yellow,
        interpolate=False,
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
def test_no_color_widgets(widget) -> None:
    assert not widget().uses_colors
    print(f'{widget} has colors? {widget.uses_colors}')

    assert widget(
        fixed_colors=_TestFixedColorSupport._fixed_colors,
    ).uses_colors
    assert widget(
        gradient_colors=_TestFixedGradientSupport._gradient_colors,
    ).uses_colors


def test_colors(monkeypatch) -> None:
    for colors_ in Colors.by_rgb.values():
        for color in colors_:
            rgb = color.rgb
            assert rgb.rgb
            assert rgb.hex
            assert rgb.to_ansi_16 is not None
            assert rgb.to_ansi_256 is not None
            assert rgb.to_windows is not None

            with monkeypatch.context() as context:
                context.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.XTERM)
                assert color.underline
                context.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.WINDOWS)
                assert color.underline

            assert color.fg
            assert color.bg
            assert str(rgb)
            assert color('test')

            color_no_name = Color(
                rgb=color.rgb,
                hls=color.hls,
                name=None,
                xterm=color.xterm,
            )
            # Test without name
            assert str(color_no_name) != str(color)


def test_color() -> None:
    color = colors.red
    if os.name != 'nt':
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
def test_rgb_to_hls(rgb, hls) -> None:
    assert terminal.HSL.from_rgb(rgb) == hls


def test_registered_color_hls_matches_rgb() -> None:
    # Regression: the hand-entered HSL column in colors.py had corrupted
    # rows (e.g. DeepSkyBlue4 #005f87 stored hue 97 instead of 198), so
    # gradients interpolated through the wrong hue. colors.py is now
    # generated by tools/generate_colors.py, which derives every HSL from
    # its RGB; this guards the two from ever drifting apart again.
    for color in Colors.by_xterm.values():
        assert color.hls == terminal.HSL.from_rgb(color.rgb)


@pytest.mark.parametrize(
    'rgb, expected',
    [
        (terminal.RGB(255, 0, 0), 1),
        (terminal.RGB(128, 0, 0), 1),
        (terminal.RGB(0, 128, 0), 2),
        (terminal.RGB(0, 0, 128), 4),
        (terminal.RGB(128, 128, 0), 3),
        (terminal.RGB(0, 0, 0), 0),
        (terminal.RGB(255, 255, 255), 7),
        (terminal.RGB(127, 127, 127), 0),
    ],
)
def test_rgb_to_ansi_16(rgb, expected) -> None:
    # Regression: ``int(c / 255)`` is 1 only when a channel is exactly 255, so
    # every mid-intensity colour (e.g. maroon 128,0,0) collapsed to black. A
    # per-channel threshold at 128 maps each channel to its own bit.
    assert rgb.to_ansi_16 == expected


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
def test_apply_colors(
    text: str,
    fg,
    bg,
    fg_none,
    bg_none,
    percentage: float | None,
    expected,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        env,
        'COLOR_SUPPORT',
        env.ColorSupport.XTERM_256,
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


def test_windows_colors(monkeypatch) -> None:
    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.WINDOWS)
    assert (
        apply_colors(
            'test',
            fg=colors.red,
            bg=colors.red,
            fg_none=colors.red,
            bg_none=colors.red,
            percentage=1,
        )
        == 'test'
    )
    colors.red.underline('test')


def test_ansi_color(monkeypatch) -> None:
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


def test_color_ansi_respects_support_level(monkeypatch) -> None:
    # A registered colour with an xterm index and a non-black RGB.
    color = terminal.Color(
        terminal.RGB(128, 0, 0),
        terminal.HSL(0, 100, 25),
        'maroon-test',
        52,
    )

    # 256-colour terminal: the registered xterm index is used verbatim.
    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.XTERM_256)
    assert color.ansi == '5;52'

    # 16-colour terminal: the 256-colour xterm index must NOT leak through;
    # derive a 16-colour code from the RGB via to_ansi_16 instead.
    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.XTERM)
    assert color.ansi == f'5;{color.rgb.to_ansi_16}'
    assert color.ansi != '5;52'


def test_color_ansi_black_xterm_zero(monkeypatch) -> None:
    # Regression: ``if self.xterm:`` is falsy for index 0 (Black), so Black
    # fell through to the RGB fallback instead of using its xterm index.
    black = terminal.Color(
        terminal.RGB(0, 0, 0),
        terminal.HSL(0, 0, 0),
        'black-test',
        0,
    )
    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.XTERM_256)
    assert black.ansi == '5;0'


def test_sgr_call() -> None:
    assert progressbar.terminal.encircled('test') == '\x1b[52mtest\x1b[54m'


def test_hsl_interpolate_preserves_components() -> None:
    # Regression: C1 - interpolate() swapped the saturation and lightness
    # arguments, corrupting every HSL gradient blend.
    start_color = terminal.HSL(0, 100, 25)
    end_color = terminal.HSL(0, 100, 75)

    assert start_color.interpolate(end_color, 0.5) == terminal.HSL(0, 100, 50)


@pytest.mark.parametrize('value', ['1', 'true', 'on'])
def test_color_support_force_color_flag(monkeypatch, value) -> None:
    # Regression: C8 - the conventional FORCE_COLOR=1 left color support
    # at NONE because only depth-style values were recognised.
    if os.name == 'nt':
        monkeypatch.setattr(os, 'name', 'posix')

    monkeypatch.setenv('FORCE_COLOR', value)
    assert env.ColorSupport.from_env() == env.ColorSupport.XTERM_TRUECOLOR


class _PerInstanceColorWidget(progressbar.widgets.WidgetBase):
    def __call__(self, *args, **kwargs) -> None:  # pragma: no cover
        pass


def test_fixed_colors_override_is_per_instance() -> None:
    # Regression: F1 - passing ``fixed_colors`` to one instance mutated the
    # shared class-level dict, rewriting colors for every other instance and
    # subclass. The override must be copy-on-write.
    class_default = dict(_PerInstanceColorWidget._fixed_colors)
    override = widgets.TFixedColors(fg_none=colors.yellow, bg_none=None)

    a = _PerInstanceColorWidget(fixed_colors=override)
    b = _PerInstanceColorWidget()

    assert _PerInstanceColorWidget._fixed_colors == class_default
    assert a._fixed_colors['fg_none'] == colors.yellow
    assert b._fixed_colors == class_default
    assert a._fixed_colors is not override


def test_gradient_colors_override_is_per_instance() -> None:
    # Regression: F1 - same copy-on-write requirement for ``gradient_colors``.
    class_default = dict(_PerInstanceColorWidget._gradient_colors)
    override = widgets.TGradientColors(fg=colors.gradient, bg=None)

    a = _PerInstanceColorWidget(gradient_colors=override)
    b = _PerInstanceColorWidget()

    assert _PerInstanceColorWidget._gradient_colors == class_default
    assert a._gradient_colors['fg'] == colors.gradient
    assert b._gradient_colors == class_default
    assert a._gradient_colors is not override


def test_sgr_color_without_ansi_leaves_text_unstyled(monkeypatch) -> None:
    # Regression: when Color.ansi is None (no registered xterm index and no
    # support level to derive a code from), SGRColor rendered a malformed
    # '\x1b[38;Nonem' escape whose tail leaked into visible output as
    # 'onem'. Without a usable color representation the text must pass
    # through completely unstyled.
    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.NONE)
    unregistered = terminal.Color(
        terminal.RGB(1, 2, 3),
        terminal.HSL(0, 0, 1),
        None,
        None,
    )
    assert unregistered.ansi is None
    assert unregistered.fg('X') == 'X'
    assert unregistered.bg('X') == 'X'
    assert unregistered.underline('X') == 'X'


def test_registered_color_renders_when_forced_without_support(
    monkeypatch,
) -> None:
    # Callers can force colors (enable_colors=True) on terminals whose
    # support detection reports NONE; a registered color must still render
    # its xterm index there instead of silently dropping the styling.
    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.NONE)
    green = colors.green
    assert green.ansi == '5;2'
    assert green.fg('X') == '\x1b[38;5;2mX\x1b[39m'
