"""``GranularBar`` renders sub-character progress using block glyphs.

Useful when the bar is narrow and whole-character steps would look like
the bar is stuck.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.GranularBar(),
        ' ',
        progressbar.ETA(),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
