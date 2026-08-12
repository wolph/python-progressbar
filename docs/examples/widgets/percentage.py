"""``Percentage`` displays the current progress as ``N%``.

Reach for it as the simplest possible progress readout -- just the
percentage, with no bar. Compare ``SimpleProgress`` ("5 of 47") when
the raw counts matter more than the ratio, and ``PercentageLabelBar``
to overlay the same percentage on a fill bar instead of beside it.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [progressbar.Percentage()]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
