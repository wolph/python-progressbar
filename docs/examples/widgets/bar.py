"""``Bar`` draws a classic fill-style progress bar.

The default choice for a determinate task with a known total: a marker
fills the line from left to right as ``value`` approaches ``max_value``.
See ``ReverseBar`` for the mirrored direction, ``GranularBar`` for
sub-character precision, and ``BouncingBar`` for indeterminate work.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [progressbar.Percentage(), ' ', progressbar.Bar()]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
