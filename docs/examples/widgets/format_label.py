"""``FormatLabel`` renders an arbitrary %-style format string.

Reach for it to display fields from the bar's own data snapshot --
``value``, ``max``, ``elapsed`` and friends -- worded however fits, when
none of the built-in widgets already say it the way you want.
"""

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [
        progressbar.FormatLabel(
            'Processed: %(value)d lines (in: %(elapsed)s)'
        ),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
