"""Write your own widget by subclassing `WidgetBase`.

A widget is a callable: `__call__(self, progress, data)` returns the text
to render for one redraw. `progress` is the bar itself (read from it, don't
mutate it); `data` is the same snapshot dict the built-in widgets read --
`data['value']`, `data['percentage']`, and so on. This one names the
current phase instead of showing a percentage.
"""

import time

import progressbar
from progressbar.bar import ProgressBarMixinBase
from progressbar.widgets import Data, WidgetBase

STEPS = 24


class Stage(WidgetBase):
    """Names the current phase of the job instead of a percentage."""

    def __call__(self, progress: ProgressBarMixinBase, data: Data) -> str:
        percentage = data['percentage'] or 0.0
        if percentage < 20:
            return 'starting'
        elif percentage < 90:
            return 'working'
        else:
            return 'finishing'


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        Stage(),
    ]
    with progressbar.ProgressBar(max_value=STEPS, widgets=widgets) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
