"""``Counter`` displays the current value as a running count.

Reach for it when there is no meaningful total to show a percentage or
fraction against -- just the raw count so far. Compare ``SimpleProgress``
("5 of 47") when a total is known, and ``UnitProgress`` when the count
should carry a unit label.
"""

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = ['Processed: ', progressbar.Counter(), ' lines']
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
