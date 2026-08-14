"""``ReverseBar`` draws a fill bar whose marker grows right to left.

Reach for it to visually contrast with a normal ``Bar`` -- for example a
pair of gauges that meet in the middle -- or any layout that reads
right-to-left. Everything else about it matches ``Bar``.
"""

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [progressbar.Percentage(), ' ', progressbar.ReverseBar()]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
