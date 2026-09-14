"""Choose a progress gradient and a solid colour for an animated spinner.

The bar follows its percentage. The spinner normally cycles through
colours with its frames. Passing one colour instead of a gradient
keeps it blue throughout the animation.
"""

import time

import progressbar
from progressbar.terminal import ColorGradient, colors
from progressbar.widgets import TGradientColors

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
        progressbar.AnimatedMarker(
            gradient_colors=TGradientColors(fg=colors.blue, bg=None),
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
