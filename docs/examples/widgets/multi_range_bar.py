"""``MultiRangeBar`` shows several named ranges as segments of one bar.

Reach for it to visualize a whole made of distinct categories -- done,
processing, scheduled, not started -- as proportional segments of a
single bar, rather than a single fill fraction. Compare
``MultiProgressBar``, which shows independent per-job progress instead
of categories of one whole. Its loop runs until every unit reaches the
"done" range rather than a fixed ``STEPS`` count, since that is what the
widget is for.
"""

from __future__ import annotations

import random
import time

import progressbar

random.seed(0)

UNITS = 25


def main() -> None:
    markers = [
        '\x1b[38;5;2m█\x1b[39m',  # Done (green)
        '\x1b[38;5;3m#\x1b[39m',  # Processing (yellow)
        '\x1b[38;5;1m.\x1b[39m',  # Scheduled (red)
        ' ',  # Not started
    ]
    widgets = [progressbar.MultiRangeBar('amounts', markers=markers)]
    amounts = [0] * (len(markers) - 1) + [UNITS]
    with progressbar.ProgressBar(widgets=widgets) as bar:
        while True:
            incomplete = [
                idx
                for idx, amount in enumerate(amounts)
                for _ in range(amount)
                if idx != 0
            ]
            if not incomplete:
                break
            which = random.choice(incomplete)
            amounts[which] -= 1
            amounts[which - 1] += 1
            bar.update(amounts=amounts, force=True)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
