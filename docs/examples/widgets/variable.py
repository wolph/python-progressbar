"""``Variable`` displays a live, named value with custom formatting.

Reach for it to track a value that is not the bar's own progress -- a
loss, a learning rate, a username -- updated via
``bar.update(name=value)``. Compare ``Postfix`` for several values
rendered together as one compact suffix, and ``DynamicMessage`` for the
original name of this same widget.
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
        ' ',
        progressbar.Variable('loss'),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        loss = 1.0
        for step in range(STEPS):
            loss *= 0.9 + random.random() * 0.05
            bar.update(step + 1, loss=loss)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
