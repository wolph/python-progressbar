"""Wrap any iterable directly, without managing start/update/finish yourself.

`progressbar.progressbar(iterable)` is the shortcut for a `for` loop over a
fresh bar. Call an existing `ProgressBar` instance the same way --
`bar(iterable)` -- when you already built one for its own widgets or
prefix and want to reuse it as a wrapper.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    for _ in progressbar.progressbar(range(STEPS)):
        time.sleep(0.005)

    bar = progressbar.ProgressBar(prefix='Second pass: ')
    for _ in bar(range(STEPS)):
        time.sleep(0.005)


if __name__ == '__main__':
    main()
