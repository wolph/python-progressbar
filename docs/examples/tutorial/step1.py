"""The first progress bar: wrap a `range` with `progressbar.progressbar`.

`progressbar.progressbar(iterable)` turns any `for` loop into a progress
bar with no other change to the loop -- start, update and finish all
happen for you.
"""

from __future__ import annotations

import time

import progressbar


def main() -> None:
    for _ in progressbar.progressbar(range(100)):
        time.sleep(0.01)


if __name__ == '__main__':
    main()
