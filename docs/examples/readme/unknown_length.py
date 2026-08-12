"""A bar for work whose total is not known up front."""

from __future__ import annotations

import time

import progressbar


def main() -> None:
    with progressbar.ProgressBar(
        max_value=progressbar.UnknownLength,
    ) as bar:
        for value in range(0, 120, 10):
            bar.update(value)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
