"""``FormatCustomText`` renders its own text, independent of the bar.

Reach for it to show auxiliary information that is not part of the
bar's progress or ``variables`` -- it keeps its own mapping, updated
directly with ``update_mapping()`` rather than through ``bar.update()``.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    status = progressbar.FormatCustomText(
        'Spam: %(spam).1f kg, eggs: %(eggs)d',
        {'spam': 0.25, 'eggs': 0},
    )
    widgets = [status, ' :: ', progressbar.Percentage()]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            status.update_mapping(eggs=step)
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
