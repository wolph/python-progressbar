"""``AbsoluteETA`` shows the wall-clock time the run is expected to finish.

Reach for it when the audience cares about *when* the job will finish
("done around 14:32:07") rather than a countdown duration -- every other
ETA widget in this reference reports a remaining-time span instead. This
example runs longer than most in this set: the estimate is only shown to
whole-second resolution, so a bar that finishes in a fraction of a second
never accumulates enough elapsed time for the projected finish time to
visibly move.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 30


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        progressbar.AbsoluteETA(),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.2)


if __name__ == '__main__':
    main()
