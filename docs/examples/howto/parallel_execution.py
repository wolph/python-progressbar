"""Report a hundred small steps from each of three concurrent workers.

The overall bar counts finished files. Each worker supplies its own
known block count through current_task_bar(), so its row shows a
percentage while the other files are still being processed.
"""

import sys
import time

import progressbar

FILES: list[str] = ['users.csv', 'sales.csv', 'stock.csv']
BLOCKS: int = 100


def process_file(filename: str) -> str:
    task_bar: progressbar.ProgressBar | None = progressbar.current_task_bar()
    if task_bar is not None:
        task_bar.max_value = BLOCKS
        task_bar.widgets = [
            f'{filename:10} ',
            progressbar.Percentage(),
            ' ',
            progressbar.Bar(),
        ]
    delay: float = 0.02 + FILES.index(filename) * 0.004
    block: int
    for block in range(BLOCKS):
        time.sleep(delay)
        if task_bar is not None:
            task_bar.update(block + 1)
    return filename


def main() -> None:
    multibar: progressbar.MultiBar = progressbar.MultiBar(
        fd=sys.stdout, sort_reverse=False, prepend_label=False
    )
    results: list[str] = progressbar.map(
        process_file,
        FILES,
        workers=3,
        bar=multibar,
        poll_interval=0.02,
        widgets=[
            'Total      ',
            progressbar.SimpleProgress(),
            ' files ',
            progressbar.Bar(),
        ],
    )
    assert results == FILES


if __name__ == '__main__':
    main()
