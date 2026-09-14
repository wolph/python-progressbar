"""A bar for work whose total is not known up front."""

import time

import progressbar
from progressbar.terminal import colors


def main() -> None:
    with progressbar.ProgressBar(
        max_value=progressbar.UnknownLength,
        widget_kwargs={'marker_wrap': colors.cyan1.fg('{}')},
    ) as bar:
        for value in range(0, 120, 10):
            bar.update(value)
            # Longer than the bar's 0.05s update gate, so every step
            # lands as a visible redraw.
            time.sleep(0.1)


if __name__ == '__main__':
    main()
