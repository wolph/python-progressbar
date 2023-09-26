from __future__ import annotations

import typing

import progressbar
import pytest
from progressbar import terminal, widgets


@pytest.mark.parametrize(
    'variable',
    [
        'PROGRESSBAR_ENABLE_COLORS',
        'FORCE_COLOR',
    ],
)
def test_color_environment_variables(monkeypatch, variable):
    monkeypatch.setattr(
        terminal,
        'color_support',
        terminal.ColorSupport.XTERM_256,
    )

    monkeypatch.setenv(variable, '1')
    bar = progressbar.ProgressBar()
    assert bar.enable_colors

    monkeypatch.setenv(variable, '0')
    bar = progressbar.ProgressBar()
    assert not bar.enable_colors


def test_enable_colors_flags():
    bar = progressbar.ProgressBar(enable_colors=True)
    assert bar.enable_colors

    bar = progressbar.ProgressBar(enable_colors=False)
    assert not bar.enable_colors

    bar = progressbar.ProgressBar(
        enable_colors=terminal.ColorSupport.XTERM_TRUECOLOR,
    )
    assert bar.enable_colors

    with pytest.raises(ValueError):
        progressbar.ProgressBar(enable_colors=12345)


class _TestFixedColorSupport(progressbar.widgets.WidgetBase):
    _fixed_colors: typing.ClassVar[widgets.TFixedColors] = widgets.TFixedColors(
        fg_none=progressbar.widgets.colors.yellow,
        bg_none=None,
    )

    def __call__(self, *args, **kwargs):
        pass


class _TestFixedGradientSupport(progressbar.widgets.WidgetBase):
    _gradient_colors: typing.ClassVar[
        widgets.TGradientColors] = widgets.TGradientColors(
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
