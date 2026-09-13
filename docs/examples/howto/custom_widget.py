"""Name each phase of a job with a custom widget.

A widget returns the text for one redraw from the bar's data snapshot.
Place the phase before the stretching bar so it stays easy to find.
"""

import time

import progressbar
from progressbar.bar import ProgressBarMixinBase
from progressbar.widgets import Data, WidgetBase

STEPS: int = 100


class Stage(WidgetBase):
    """Show the phase that corresponds to the current percentage."""

    def __call__(self, progress: ProgressBarMixinBase, data: Data) -> str:
        percentage: float = data['percentage'] or 0.0
        phase: str
        if percentage < 20:
            phase = 'preparing'
        elif percentage < 85:
            phase = 'processing'
        else:
            phase = 'finishing'
        return f'Phase: {phase:10}'


def main() -> None:
    widgets: list[str | WidgetBase] = [
        Stage(),
        ' ',
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
    ]
    bar: progressbar.ProgressBar
    step: int
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            time.sleep(0.02)
            bar.update(step + 1)


if __name__ == '__main__':
    main()
