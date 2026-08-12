"""``DataSize`` shows a single byte count scaled with binary prefixes.

Reach for it to show an amount of data transferred or processed so far
-- "12.5 MiB" instead of a raw byte count -- as one value scaled to a
sensible unit. Compare ``FileTransferSpeed``, which shows a *rate*
instead of a static amount.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [progressbar.DataSize(), ' ', progressbar.Bar()]
    max_value = 12_500_000
    with progressbar.ProgressBar(max_value=max_value, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(int(max_value * (step + 1) / STEPS))
            time.sleep(0.005)


if __name__ == '__main__':
    main()
