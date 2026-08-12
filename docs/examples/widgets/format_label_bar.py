"""``FormatLabelBar`` centers a formatted label inside a fill bar.

Reach for it to combine ``Bar`` and ``FormatLabel`` in one widget -- the
label sits centered over the fill instead of beside it. See
``PercentageLabelBar`` for the common case of centering the percentage
specifically.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [progressbar.FormatLabelBar('%(value)d of %(max_value)d')]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
