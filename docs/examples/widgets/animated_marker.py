"""``AnimatedMarker`` cycles through characters to show a spinner.

Reach for it for indeterminate work where there is nothing to measure a
percentage against -- just a signal that the process is still alive.
Unlike ``Bar``, it does not grow or fill; it only replaces one character
each redraw.
"""

import time

import progressbar
from progressbar.terminal import colors

STEPS = 24


def main() -> None:
    widgets = [
        'Working: ',
        progressbar.AnimatedMarker(
            marker_wrap=colors.cyan1.fg('{}'),
            default=colors.cyan1.fg('|'),
        ),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
