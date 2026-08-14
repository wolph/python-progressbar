"""Recognize `DynamicMessage` in old code as today's `Variable`.

Older code may still import `DynamicMessage` -- it is a plain subclass of
`Variable` kept for compatibility, not a different widget. Prefer
`Variable` in new code; this example updates one of each, side by side
from the same value, to show they behave identically.
"""

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
        progressbar.Variable('current'),
        ' ',
        progressbar.DynamicMessage('legacy'),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            value = random.random()
            bar.update(step + 1, current=value, legacy=value)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
