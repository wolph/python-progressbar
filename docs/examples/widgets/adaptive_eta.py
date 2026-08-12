"""``AdaptiveETA`` estimates time remaining from the last few seconds.

Reach for it when the processing rate can change mid-run -- resuming a
paused job, or one that starts slow and speeds up -- so the estimate
should track the *current* pace rather than the whole-run average that
plain ``ETA`` uses. This example runs slower at first and speeds up
partway through so the adaptive estimate visibly reacts; a uniform run
like most examples in this set would look identical to ``ETA``.

It also runs longer than most in this set: the ETA is only shown to
whole-second resolution, so too short a run shows only a tick or two rather
than a real countdown reacting to the pace change.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 40


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        progressbar.AdaptiveETA(),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.32 if step < STEPS // 2 else 0.04)


if __name__ == '__main__':
    main()
