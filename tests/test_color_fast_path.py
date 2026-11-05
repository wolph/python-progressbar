"""The colour shortcuts on the redraw path render the same bytes as before.

`terminal.apply_colors` and `ColorGradient.get_color` took shortcuts for
speed: the gradient arithmetic inlines `python_utils.converters.remap`,
and a default blend renders its escape parameter without building the
interpolated `Color`. These tests pin them against the plain composition
of the public pieces (`get_color`, `Color.fg`, `Color.bg`, `remap`) for
every colour support level and a dense grid of values.
"""

from __future__ import annotations

import decimal
import importlib
import typing

import pytest
from python_utils import converters

from progressbar import base, env, terminal, utils, widgets
from progressbar.bar import ProgressBar
from progressbar.terminal import colors

# The package re-exports `progressbar.base` under the name `base`, which
# shadows the submodule for `from progressbar.terminal import base`.
terminal_base: typing.Any = importlib.import_module(
    'progressbar.terminal.base'
)

_PERCENTAGES: list[float | int | None] = [
    None,
    -5,
    0,
    0.0,
    1e-9,
    12.345,
    14.2857,
    25,
    33.333333333,
    42.857142857,
    50,
    57.142857143,
    62.5,
    71.428571429,
    85.714285714,
    99.999,
    100,
    100.0,
    150,
]
_PERCENTAGES += [index * 100 / 997 for index in range(998)]


def _reference_get_color(
    gradient: terminal.ColorGradient, value: float
) -> terminal.Color:
    """`ColorGradient.get_color` as written before the shortcut."""
    if value == base.Undefined or value == base.UnknownLength or value <= 0:
        return gradient.colors[0]
    elif value >= 1:
        return gradient.colors[-1]

    max_color_idx = len(gradient.colors) - 1
    if max_color_idx == 0:
        return gradient.colors[0]
    elif gradient.interpolate:
        if max_color_idx > 1:
            index = round(
                converters.remap(value, 0, 1, 0, max_color_idx - 1),
            )
        else:
            index = 0

        step = converters.remap(
            value,
            index / (max_color_idx),
            (index + 1) / (max_color_idx),
            0,
            1,
        )
        return gradient.interpolate(
            gradient.colors[index],
            gradient.colors[index + 1],
            float(step),
        )
    else:
        index = round(converters.remap(value, 0, 1, 0, max_color_idx))
        return gradient.colors[index]


def _reference_apply_colors(
    text: str,
    percentage: float | None,
    fg: terminal.OptionalColor,
    bg: terminal.OptionalColor,
    fg_none: terminal.Color | None,
    bg_none: terminal.Color | None,
) -> str:
    """`terminal.apply_colors` as written before the shortcut."""

    def resolve(
        color: terminal.OptionalColor, value: float
    ) -> terminal.Color | None:
        if isinstance(color, terminal.HueGradient):
            return color.get_color(value)
        if isinstance(color, terminal.ColorGradient):
            return _reference_get_color(color, value)
        return color

    if percentage is None:
        if fg_none is not None:
            text = fg_none.fg(text)
        if bg_none is not None:
            text = bg_none.bg(text)
    elif fg is not None or bg is not None:
        fg_color = resolve(fg, percentage * 0.01)
        bg_color = resolve(bg, percentage * 0.01)
        if fg_color is not None:
            text = fg_color.fg(text)
        if bg_color is not None:
            text = bg_color.bg(text)
    return text


def _snap(a: terminal.Color, b: terminal.Color, step: float) -> terminal.Color:
    """A custom blend: the nearer end, no interpolation."""
    return a if step < 0.5 else b


_GRADIENTS: dict[str, terminal.OptionalColor] = {
    'none': None,
    'fixed': colors.red,
    'fixed_unregistered': terminal.Color(
        terminal.RGB(12, 34, 56), terminal.HSL(0, 0, 0), None, None
    ),
    'dark': colors.dark_gradient,
    'light': colors.light_gradient,
    'two': terminal.ColorGradient(colors.red, colors.green),
    'three': terminal.ColorGradient(colors.red, colors.yellow, colors.green),
    'single': terminal.ColorGradient(colors.blue),
    'snap': terminal.ColorGradient(
        colors.red, colors.yellow, colors.green, interpolate=None
    ),
    'custom_blend': terminal.ColorGradient(
        colors.red, colors.yellow, colors.green, interpolate=_snap
    ),
    'hue': terminal.HueGradient(),
    'bg': colors.bg_gradient,
    'unregistered': terminal.ColorGradient(
        terminal.Color(
            terminal.RGB(10, 20, 30), terminal.HSL(0, 0, 0), None, None
        ),
        terminal.Color(
            terminal.RGB(200, 100, 50), terminal.HSL(0, 0, 0), None, None
        ),
    ),
}


@pytest.fixture(params=list(env.ColorSupport))
def color_support(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> env.ColorSupport:
    support: env.ColorSupport = request.param
    monkeypatch.setattr(env, 'COLOR_SUPPORT', support)
    return support


@pytest.mark.parametrize('fg_name', list(_GRADIENTS))
@pytest.mark.parametrize('bg_name', ['none', 'bg', 'fixed', 'two'])
def test_apply_colors_matches_reference(
    color_support: env.ColorSupport, fg_name: str, bg_name: str
) -> None:
    fg: terminal.OptionalColor = _GRADIENTS[fg_name]
    bg: terminal.OptionalColor = _GRADIENTS[bg_name]
    for percentage in _PERCENTAGES:
        expected: str = _reference_apply_colors(
            'spam', percentage, fg, bg, colors.yellow, colors.black
        )
        actual: str = terminal.apply_colors(
            'spam',
            percentage,
            fg=fg,
            bg=bg,
            fg_none=colors.yellow,
            bg_none=colors.black,
        )
        assert actual == expected, (percentage, color_support)


@pytest.mark.parametrize('name', list(_GRADIENTS))
def test_gradient_get_color_matches_reference(
    color_support: env.ColorSupport, name: str
) -> None:
    gradient: terminal.OptionalColor = _GRADIENTS[name]
    if not isinstance(gradient, terminal.ColorGradient) or isinstance(
        gradient, terminal.HueGradient
    ):
        pytest.skip('not a plain gradient')
    values: list[typing.Any] = [
        base.Undefined,
        base.UnknownLength,
        0,
        1,
        -1,
        2,
        decimal.Decimal('0.4'),
        decimal.Decimal('0.75'),
    ]
    values += [percentage * 0.01 for percentage in _PERCENTAGES[1:]]
    for value in values:
        assert gradient.get_color(value) == _reference_get_color(
            gradient, value
        ), (value, color_support)
        assert gradient(value) == gradient.get_color(value)


def test_gradient_shortcut_covers_every_branch(
    color_support: env.ColorSupport,
) -> None:
    gradient: terminal.ColorGradient = _GRADIENTS['three']  # type: ignore
    single: terminal.ColorGradient = _GRADIENTS['single']  # type: ignore
    two: terminal.ColorGradient = _GRADIENTS['two']  # type: ignore
    for grad in (gradient, single, two):
        for value in (-0.5, 0.0, 0.3, 0.5, 0.7, 1.0, 1.5):
            assert (
                terminal_base._gradient_ansi_at(grad, value)
                == grad.get_color(value).ansi
            ), (grad, value)


def test_color_subclass_keeps_its_own_styling(
    color_support: env.ColorSupport,
) -> None:
    class Loud(terminal.Color):
        @property
        def fg(self) -> typing.Any:
            return lambda text: f'<{text}>'

        @property
        def bg(self) -> typing.Any:
            return lambda text: f'[{text}]'

    loud: Loud = Loud(*colors.red)
    assert terminal.apply_colors('x', None, fg_none=loud) == '<x>'
    assert terminal.apply_colors('x', 50, fg=loud, bg=loud) == '[<x>]'


def test_coloured_str_subclass_keeps_its_type(
    color_support: env.ColorSupport,
) -> None:
    from markupsafe import Markup

    text: Markup = Markup('&lt;tag&gt;')
    for percentage, kwargs in (
        (None, {'fg_none': colors.yellow, 'bg_none': colors.black}),
        (50.0, {'fg': colors.gradient}),
        (50.0, {'fg': colors.red, 'bg': colors.gradient}),
        (50.0, {'fg': _GRADIENTS['custom_blend']}),
    ):
        result: str = terminal.apply_colors(text, percentage, **kwargs)
        assert isinstance(result, Markup), (percentage, kwargs, color_support)
        assert result == _reference_apply_colors(
            text,
            percentage,
            kwargs.get('fg'),
            kwargs.get('bg'),
            kwargs.get('fg_none'),
            kwargs.get('bg_none'),
        )


def test_gradient_cache_follows_colors_blend_and_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.XTERM_TRUECOLOR)
    gradient: terminal.ColorGradient = terminal.ColorGradient(
        colors.red, colors.green
    )
    first: str = terminal.apply_colors('x', 50, fg=gradient)
    assert terminal.apply_colors('x', 50, fg=gradient) == first
    assert first == gradient.get_color(0.5).fg('x')

    gradient.colors = (colors.blue, colors.yellow)
    swapped: str = terminal.apply_colors('x', 50, fg=gradient)
    assert swapped != first
    assert swapped == gradient.get_color(0.5).fg('x')

    gradient.interpolate = None
    snapped: str = terminal.apply_colors('x', 50, fg=gradient)
    assert snapped == gradient.get_color(0.5).fg('x')
    assert snapped != swapped

    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.XTERM_256)
    assert terminal.apply_colors('x', 50, fg=gradient) == gradient.get_color(
        0.5
    ).fg('x')
    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.NONE)
    assert terminal.apply_colors('x', 50, fg=gradient) == gradient.get_color(
        0.5
    ).fg('x')
    # A registered colour keeps its xterm index without colour support,
    # as `Color.ansi` always did, an unregistered one renders nothing.
    assert terminal.apply_colors('x', None, fg_none=colors.red) == (
        colors.red.fg('x')
    )
    plain: terminal.Color = terminal.Color(
        terminal.RGB(1, 2, 3), terminal.HSL(0, 0, 0), None, None
    )
    assert terminal.apply_colors('x', None, fg_none=plain) == 'x'
    assert (
        terminal.apply_colors('x', 50, fg=terminal.ColorGradient(plain, plain))
        == 'x'
    )


def test_colour_caches_stay_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(env, 'COLOR_SUPPORT', env.ColorSupport.XTERM_TRUECOLOR)
    gradient: terminal.ColorGradient = terminal.ColorGradient(
        colors.red, colors.green
    )
    for step in range(1100):
        terminal.apply_colors('x', step / 11, fg=gradient, bg=gradient)
    entry = terminal_base._GRADIENT_SGR[gradient]
    assert len(entry[1]) <= 1024
    for _step in range(70):
        terminal.apply_colors(
            'x', 50, fg=terminal.ColorGradient(colors.red, colors.green)
        )
    assert len(terminal_base._GRADIENT_SGR) <= 64
    for red in range(1100):
        terminal.apply_colors(
            'x',
            None,
            fg_none=terminal.Color(
                terminal.RGB(red % 256, red // 256, 0),
                terminal.HSL(0, 0, 0),
                None,
                None,
            ),
        )
    assert len(terminal_base._COLOR_SGR) <= 1024


def test_gradient_with_reassigned_blend_is_not_shortcut(
    color_support: env.ColorSupport,
) -> None:
    gradient: terminal.ColorGradient = terminal.ColorGradient(
        colors.red, colors.yellow, colors.green
    )
    gradient.interpolate = _snap
    for percentage in _PERCENTAGES:
        assert terminal.apply_colors(
            'x', percentage, fg=gradient
        ) == _reference_apply_colors(
            'x', percentage, gradient, None, None, None
        )


def test_get_color_resolves_gradients_and_passes_colors_through(
    color_support: env.ColorSupport,
) -> None:
    gradient: terminal.ColorGradient = _GRADIENTS['three']  # type: ignore
    assert terminal.get_color(0.5, gradient) == gradient.get_color(0.5)
    assert terminal.get_color(0.5, colors.red) is colors.red
    assert terminal.get_color(0.5, None) is None


def test_rgb_ansi_helpers_match_properties() -> None:
    for red, green, blue in ((0, 0, 0), (127, 128, 255), (200, 10, 90)):
        rgb: terminal.RGB = terminal.RGB(red, green, blue)
        assert rgb.to_ansi_16 == terminal_base._to_ansi_16(red, green, blue)
        assert rgb.to_ansi_256 == terminal_base._to_ansi_256(red, green, blue)


def test_len_color_counts_visible_characters_only() -> None:
    assert utils.len_color('plain') == 5
    assert utils.len_color('\x1b[38;5;196mred\x1b[39m') == 3
    assert utils.len_color(b'\x1b[1mbold\x1b[22m') == 4


def test_format_widgets_converts_non_str_output() -> None:
    class Number(widgets.WidgetBase):
        def __call__(
            self, progress: typing.Any, data: typing.Any
        ) -> typing.Any:
            return 42

    class Auto(widgets.AutoWidthWidgetBase):
        def __call__(
            self, progress: typing.Any, data: typing.Any, width: int = 0
        ) -> typing.Any:
            return b'auto'

    def plain(progress: typing.Any, data: typing.Any) -> bytes:
        return b'bytes'

    class Separator(str):
        pass

    bar: ProgressBar = ProgressBar(
        widgets=[Number(), '|', Auto(), Separator('|'), plain],
        max_value=10,
        term_width=20,
        fd=utils.StreamWrapper().original_stdout,
    )
    bar.start()
    assert bar._format_line().strip() == '42|auto|bytes'
    assert list(bar._to_unicode([b'a', 'b', 3])) == ['a', 'b', '3']
    bar.finish()


def test_format_label_alias_transform_failure_is_ignored() -> None:
    label: widgets.FormatLabel = widgets.FormatLabel(
        '%(value)s', fixed_colors={'fg_none': None}
    )
    data: dict[str, typing.Any] = {
        'value': 3,
        'total_seconds_elapsed': 'not a number',
    }
    assert label(None, data) == '3'  # type: ignore[arg-type]
    assert 'elapsed' not in data
