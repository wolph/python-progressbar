"""``UnitProgress`` shows a count against its total with a unit label.

Reach for it when the count needs a unit -- "12 of 24 files" -- with
optional 1024-based scaling for large counts. Compare ``SimpleProgress``
for the same idea without a unit, and ``DataSize`` for a single scaled
byte value rather than a count against a total.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [progressbar.UnitProgress(unit='files')]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
