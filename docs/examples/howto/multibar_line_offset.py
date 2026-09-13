"""Several independently updating bars stacked by hand, without `MultiBar`.

Reach for `line_offset` on plain `ProgressBar` instances -- instead of
`MultiBar` -- when the bars are not a single managed group: each one here
only knows its own row in the stack, not the others. Print the blank lines
first to reserve the rows, since `line_offset` moves the cursor relative to
wherever it already is.
"""

import random
import time

import progressbar

random.seed(0)

BARS: int = 4
STEPS: int = 20


def main() -> None:
    print('\n' * BARS, end='')
    bars: list[progressbar.ProgressBar] = [
        progressbar.ProgressBar(
            max_value=STEPS,
            line_offset=index + 1,
            prefix=f'Job {index + 1}: ',
            widgets=[
                progressbar.Percentage(),
                ' ',
                progressbar.Bar(),
                ' (',
                progressbar.SimpleProgress(),
                ')',
            ],
            max_error=False,
        )
        for index in range(BARS)
    ]
    bar: progressbar.ProgressBar
    for bar in bars:
        bar.start()
    for _ in range(STEPS * BARS):
        random.choice(bars).increment()
        time.sleep(0.01)

    for bar in bars:
        bar.finish()
    print()


if __name__ == '__main__':
    main()
