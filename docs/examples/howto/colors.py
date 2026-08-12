"""Color a bar with a fixed color or a gradient that shifts with progress.

`gradient_colors` interpolates between colors as `percentage` moves from 0
to 100 -- only meaningful once a `max_value` gives the bar something to
compute a percentage against. `fixed_colors` is for the opposite case: an
indeterminate bar, which never has a percentage, uses `fg_none`/`bg_none`
as a single unchanging color instead.
"""

from __future__ import annotations

import time

import progressbar
from progressbar.terminal import ColorGradient, colors
from progressbar.widgets import TFixedColors, TGradientColors

STEPS = 24

HEALTH_GRADIENT = ColorGradient(colors.red, colors.yellow, colors.green)


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(
            gradient_colors=TGradientColors(fg=HEALTH_GRADIENT, bg=None),
        ),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)

    spinner_widgets = [
        'Scanning: ',
        progressbar.Bar(
            marker=progressbar.AnimatedMarker(),
            fixed_colors=TFixedColors(fg_none=colors.blue, bg_none=None),
        ),
    ]
    with progressbar.ProgressBar(
        max_value=progressbar.UnknownLength, widgets=spinner_widgets
    ) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
