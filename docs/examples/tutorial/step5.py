"""Add `redirect_stdout=True` so a stray `print()` doesn't corrupt the bar.

Anything printed from inside the loop is held back and flushed above the
bar on its next redraw, instead of colliding with the bar's own carriage
return.
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
    with progressbar.ProgressBar(
        max_value=100, widgets=widgets, redirect_stdout=True
    ) as bar:
        for i in range(100):
            time.sleep(0.01)
            if i % 25 == 0:
                print(f'Reached step {i}')
            bar.update(i + 1)


if __name__ == '__main__':
    main()
