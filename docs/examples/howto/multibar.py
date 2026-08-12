"""Several named jobs, in one `MultiBar`, finishing at different times.

Reach for `MultiBar` instead of hand-rolled `line_offset` bars when the jobs
are a single logical group -- it lays them out for you, and its context
manager waits for every job to finish before letting the `with` block exit.
Add a job with a subscript (`multibar[label]`); each one here reaches its
own target and calls `finish()` independently, so you can watch them
complete one at a time. Finished bars stay on screen rather than
disappearing -- `remove_finished` defaults to an hour.
"""

from __future__ import annotations

import random
import sys
import time

import progressbar

random.seed(0)

JOBS = {
    'download': 18,
    'extract': 10,
    'build': 26,
    'test': 22,
}


def main() -> None:
    with progressbar.MultiBar(fd=sys.stdout) as multibar:
        for name, total in JOBS.items():
            multibar[name].max_value = total

        remaining = dict(JOBS)
        while remaining:
            name = random.choice(list(remaining))
            multibar[name].increment()
            if multibar[name].value >= remaining[name]:
                multibar[name].finish()
                del remaining[name]
            time.sleep(0.01)


if __name__ == '__main__':
    main()
