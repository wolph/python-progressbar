"""``Postfix`` renders a live key-value mapping (or string) after the bar.

Reach for it to show a snapshot of several live values at once -- like
tqdm's postfix -- as one compact ``key=value, key=value`` suffix,
sourced from a bar variable. Compare ``Variable`` for a single formatted
value and ``FormatCustomText`` for text that is not tied to the bar's
variables at all.
"""

from __future__ import annotations

import random
import time

import progressbar

random.seed(0)

STEPS = 24


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        progressbar.Postfix('stats'),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            stats = {
                'loss': round(random.random(), 3),
                'batch': step + 1,
            }
            bar.update(step + 1, stats=stats)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
