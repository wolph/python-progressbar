"""``FileTransferSpeed`` shows the transfer rate averaged over the run.

Reach for it whenever a bar tracks bytes moved rather than abstract
units -- a transfer rate, in a sensibly scaled unit, alongside the
count. For a rate that reacts to recent speed changes instead of the
whole-run average, see ``AdaptiveTransferSpeed``.
"""

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        progressbar.FileTransferSpeed(),
    ]
    max_value = 1_000_000
    with progressbar.ProgressBar(max_value=max_value, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(int(max_value * (step + 1) / STEPS))
            time.sleep(0.005)


if __name__ == '__main__':
    main()
