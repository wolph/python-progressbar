"""Track a data transfer's size and speed together on one bar.

`DataSize` shows how much has moved so far, `FileTransferSpeed` averages the
rate over the whole transfer, and `AdaptiveTransferSpeed` reacts to only the
last few updates instead -- put all three on one bar to compare them
directly. The windowed average only fills in once several updates have
landed more than a fraction of a second apart, so this sleeps longer per
step than most examples in this set.
"""

import random
import time

import progressbar

random.seed(0)

STEPS = 30


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        progressbar.DataSize(),
        ' ',
        progressbar.FileTransferSpeed(),
        ' ',
        progressbar.AdaptiveTransferSpeed(),
    ]
    max_value = 30_000_000
    with progressbar.ProgressBar(max_value=max_value, widgets=widgets) as bar:
        transferred = 0
        for _ in range(STEPS):
            transferred += random.randint(500_000, 2_000_000)
            bar.update(min(transferred, max_value))
            time.sleep(0.02)


if __name__ == '__main__':
    main()
