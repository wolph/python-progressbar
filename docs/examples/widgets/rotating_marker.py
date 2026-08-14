"""``RotatingMarker`` is the original name for ``AnimatedMarker``.

Same widget, kept as an alias for code written against the old name;
prefer ``AnimatedMarker`` in new code. Shown here in its classic role:
as the marker character of a ``Bar``, rather than standing alone.
"""

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(marker=progressbar.RotatingMarker()),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
