"""``SmoothingETA`` estimates remaining time via a recency-weighted rate.

Reach for it when per-item timing is noisy but you still want a stable
estimate without the fixed sample window ``AdaptiveETA`` uses -- the
exponential moving average weights recent updates more than old ones
without discarding history outright. This example adds seeded random
jitter to each step's timing over a longer run than most examples here,
since the smoothing only becomes visible across unevenly spaced
updates -- and since the ETA is only shown to whole-second resolution,
"longer" means several seconds, not merely more than a few milliseconds.
"""

import random
import time

import progressbar

random.seed(0)

STEPS = 40


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        progressbar.SmoothingETA(),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.12 + random.random() * 0.12)


if __name__ == '__main__':
    main()
