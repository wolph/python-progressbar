"""``PercentageLabelBar`` centers the percentage inside a fill bar.

Reach for it for a compact bar that carries its own percentage label
rather than printing it beside the bar as a separate widget. A
specialization of ``FormatLabelBar`` with the format fixed to the
percentage.
"""

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [progressbar.PercentageLabelBar()]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
