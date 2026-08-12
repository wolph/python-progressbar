"""``AdaptiveTransferSpeed`` averages transfer speed over a short window.

Reach for it when the transfer rate itself fluctuates and a plain
``FileTransferSpeed`` -- which averages over the whole run -- reacts too
slowly to those swings. The windowed average only fills in once several
updates have landed more than a fraction of a second apart, so this
example runs longer and sleeps longer per step than most in this set;
without that, it would render '0.0 B/s' the whole way through.
"""

from __future__ import annotations

import random
import time

import progressbar

random.seed(0)

STEPS = 30


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        progressbar.AdaptiveTransferSpeed(),
    ]
    max_value = 30_000_000
    with progressbar.ProgressBar(max_value=max_value, widgets=widgets) as bar:
        transferred = 0
        for _ in range(STEPS):
            transferred += random.randint(500_000, 2_000_000)
            bar.update(min(transferred, max_value))
            time.sleep(0.02)


if __name__ == '__main__':
    main()
