"""Let `print()` calls show up above the bar instead of corrupting it.

Pass `redirect_stdout=True` and call `print()` as normal from inside the
loop -- the bar holds the line back and flushes it above the moving bar on
the next redraw, rather than the two colliding over the same carriage
return.
"""

import time

import progressbar

FILES = ['report.csv', 'errors.log', 'summary.json']
STEPS_PER_FILE = 8


def main() -> None:
    with progressbar.ProgressBar(
        max_value=len(FILES) * STEPS_PER_FILE,
        redirect_stdout=True,
    ) as bar:
        for index, filename in enumerate(FILES):
            print(f'Processing {filename}')
            for step in range(STEPS_PER_FILE):
                bar.update(index * STEPS_PER_FILE + step + 1)
                time.sleep(0.01)


if __name__ == '__main__':
    main()
