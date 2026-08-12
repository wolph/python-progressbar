"""``DynamicMessage`` is the original name for ``Variable``.

Same widget, kept as an alias for code written against the old name;
prefer ``Variable`` in new code. Shown here in its classic role: a live
training metric climbing toward its target, reported next to the bar.
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
        progressbar.DynamicMessage('accuracy'),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        accuracy = 0.5
        for step in range(STEPS):
            accuracy += (1 - accuracy) * (0.05 + random.random() * 0.05)
            bar.update(step + 1, accuracy=accuracy)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
