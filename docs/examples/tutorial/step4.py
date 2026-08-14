"""Replace the default widget set with your own list.

`widgets=[...]` overrides everything `ProgressBar` would otherwise have
picked based on `max_value` -- the previous step's percentage, bar and ETA
are gone unless you list them again yourself.
"""

import time

import progressbar


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        progressbar.ETA(),
    ]
    with progressbar.ProgressBar(max_value=100, widgets=widgets) as bar:
        for i in range(100):
            time.sleep(0.01)
            bar.update(i + 1)


if __name__ == '__main__':
    main()
