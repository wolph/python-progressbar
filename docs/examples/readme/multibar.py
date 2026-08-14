"""Two named bars progressing at different rates in one terminal."""

import sys
import time

import progressbar

STEPS = 24


def main() -> None:
    with progressbar.MultiBar(fd=sys.stdout) as multibar:
        build = multibar['build']
        test = multibar['test']
        build.max_value = STEPS
        test.max_value = STEPS
        for step in range(STEPS):
            build.update(step + 1)
            test.update(min(STEPS, max(0, round((step - 3) * 1.2))))
            # Longer than the bars' 0.05s update gate, so every step
            # lands as a visible redraw.
            time.sleep(0.1)

        # Reaching max_value doesn't finish a bar -- only finish() does.
        # A MultiBar waits for every bar to report finished() before its
        # context manager can exit, so without these calls the block
        # above would hang forever on exit.
        build.finish()
        test.finish()


if __name__ == '__main__':
    main()
