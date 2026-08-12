"""Give the bar a `max_value` so it can show a percentage and an ETA.

Without one -- as in the previous step -- `ProgressBar` has no way to know
how much work is left, so it falls back to an indeterminate spinner
instead of a percentage.
"""

from __future__ import annotations

import time

import progressbar


def main() -> None:
    with progressbar.ProgressBar(max_value=100) as bar:
        for i in range(100):
            time.sleep(0.01)
            bar.update(i + 1)


if __name__ == '__main__':
    main()
