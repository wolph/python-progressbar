"""Three styled bars at once: two color gradients and a fixed-color spinner.

`gradient_colors` shifts a bar's fill color as its percentage grows, so
the download bar sweeps red through gold to green and the render bar
sweeps sky blue into fuchsia. The scan spinner normally cycles through
colours with its frames. Passing a single cyan colour keeps its colour
unchanged while the marker spins.
"""

import sys
import time

import progressbar
from progressbar.terminal import ColorGradient, colors
from progressbar.widgets import TGradientColors

STEPS = 24

HEALTH = ColorGradient(colors.red, colors.gold1, colors.green)
NEON = ColorGradient(colors.deep_sky_blue1, colors.fuchsia)


def main() -> None:
    with progressbar.MultiBar(fd=sys.stdout) as multibar:
        multibar['download'] = progressbar.ProgressBar(
            max_value=STEPS,
            widgets=[
                progressbar.Percentage(),
                ' ',
                progressbar.Bar(
                    gradient_colors=TGradientColors(fg=HEALTH, bg=None),
                ),
            ],
        )
        multibar['render'] = progressbar.ProgressBar(
            max_value=STEPS,
            widgets=[
                progressbar.Percentage(),
                ' ',
                progressbar.Bar(
                    gradient_colors=TGradientColors(fg=NEON, bg=None),
                ),
            ],
        )
        multibar['scan'] = progressbar.ProgressBar(
            max_value=progressbar.UnknownLength,
            widgets=[
                progressbar.AnimatedMarker(
                    gradient_colors=TGradientColors(fg=colors.cyan1, bg=None),
                ),
            ],
        )

        for step in range(STEPS):
            multibar['download'].update(step + 1)
            multibar['render'].update(max(0, step - 4))
            multibar['scan'].update(step + 1)
            # Longer than the bars' 0.05s update gate, so every step
            # lands as a visible redraw.
            time.sleep(0.1)

        multibar['render'].update(STEPS)
        for bar in multibar.values():
            bar.finish()


if __name__ == '__main__':
    main()
