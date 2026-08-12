"""``JobStatusBar`` marks each job as succeeded or failed on the bar.

Reach for it when a bar tracks discrete jobs rather than continuous
progress -- each ``update()`` records one job's outcome as a colored
marker; jobs not yet reported stay blank rather than showing a fill.
"""

from __future__ import annotations

import random
import time

import progressbar

random.seed(0)

STEPS = 24


def main() -> None:
    widgets = [progressbar.JobStatusBar('status')]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            roll = random.random()
            if roll > 0.66:
                status = True
            elif roll > 0.33:
                status = False
            else:
                status = None
            bar.update(step + 1, status=status)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
