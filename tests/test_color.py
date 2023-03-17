import pytest

import progressbar
from progressbar import terminal


@pytest.mark.parametrize(
    'variable', [
        'PROGRESSBAR_ENABLE_COLORS',
        'FORCE_COLOR',
    ]
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
        enable_colors=terminal.ColorSupport.XTERM_TRUECOLOR
    )
    assert bar.enable_colors

    with pytest.raises(ValueError):
        progressbar.ProgressBar(enable_colors=12345)
