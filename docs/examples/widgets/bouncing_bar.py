"""``BouncingBar`` slides a marker back and forth instead of filling.

Reach for it for indeterminate work -- there is no total to measure
progress against, so instead of a percentage it shows a bouncing marker
to signal that the process is still running, similar in spirit to
``AnimatedMarker`` but shaped like a full-width bar. The marker moves on
a wall-clock timer, not per ``update()`` call, so this example runs
longer than most in this set -- otherwise it barely twitches before the
run ends.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 40


def main() -> None:
    widgets = ['Working: ', progressbar.BouncingBar()]
    with progressbar.ProgressBar(
        max_value=progressbar.UnknownLength,
        widgets=widgets,
    ) as bar:
        for step in range(STEPS):
            bar.update(step)
            time.sleep(0.05)


if __name__ == '__main__':
    main()
