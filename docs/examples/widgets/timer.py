"""``Timer`` displays the elapsed time since the bar started.

Reach for it whenever "how long has this taken so far" matters more
than an estimate of what remains -- unlike the ``ETA`` family, it needs
no ``max_value`` and works just as well for indeterminate work. Compare
``CurrentTime`` for the wall-clock time of day instead of a duration.

This example runs longer than most in this set: elapsed time is only shown
to whole-second resolution, so a bar that finishes in a few milliseconds
would read "Elapsed Time: 0:00:00" for its entire run -- the one thing this
widget exists to show would never move.
"""

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [progressbar.Timer()]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.2)


if __name__ == '__main__':
    main()
