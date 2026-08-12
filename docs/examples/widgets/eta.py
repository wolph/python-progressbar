"""``ETA`` estimates time remaining from the average rate since start.

It divides the elapsed time by the work done so far and extrapolates --
the plain, whole-run average. That average reacts slowly to a rate that
changes mid-run -- see ``AdaptiveETA`` (recent window) and
``SmoothingETA`` (exponential average) for estimates that track recent
speed instead, and ``AbsoluteETA`` for a clock time instead of a
countdown. Note that ``ProgressBar``'s own default widget set uses
``SmoothingETA``, not this widget.

This example runs longer than most in this set: the ETA is only shown to
whole-second resolution, so a bar that finishes in a few milliseconds would
show a countdown stuck at ``0:00:00`` -- the estimate this widget exists to
compute would never visibly move.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        progressbar.ETA(),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.3)


if __name__ == '__main__':
    main()
