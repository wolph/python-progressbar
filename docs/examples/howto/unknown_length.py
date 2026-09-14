"""Show progress for work whose total length isn't known in advance.

Pass `max_value=progressbar.UnknownLength` and include an `AnimatedMarker`
so there is still something visibly moving -- there is no percentage or
ETA to show without a known total to measure against.
"""

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [
        'Scanning: ',
        progressbar.AnimatedMarker(),
        ' ',
        progressbar.Counter(),
        ' files found',
    ]
    with progressbar.ProgressBar(
        max_value=progressbar.UnknownLength, widgets=widgets
    ) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
