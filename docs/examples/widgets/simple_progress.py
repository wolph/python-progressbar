"""``SimpleProgress`` shows progress as a raw count, like "5 of 47".

Reach for it when the counts themselves are useful information, not
just their ratio -- compare ``Percentage`` for the ratio alone, and
``UnitProgress`` for the same count with a unit label attached.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [progressbar.SimpleProgress()]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
