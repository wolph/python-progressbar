"""``MultiProgressBar`` renders many sub-jobs as stacked fill levels.

Reach for it to show the aggregate state of several jobs -- each with
its own progress toward its own total -- as one bar, rather than one
bar per job. Compare ``MultiRangeBar`` when the sub-ranges are simple
categories instead of independent job progress. Its loop runs until
every job finishes rather than a fixed ``STEPS`` count, since that is
what the widget is for.
"""

import random
import time

import progressbar

random.seed(0)

JOBS = 25


def main() -> None:
    jobs = [[0, random.randint(1, 10)] for _ in range(JOBS)]
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.MultiProgressBar('jobs'),
    ]
    max_value = sum(total for _, total in jobs)
    with progressbar.ProgressBar(max_value=max_value, widgets=widgets) as bar:
        while True:
            incomplete = [
                idx
                for idx, (progress, total) in enumerate(jobs)
                if progress < total
            ]
            if not incomplete:
                break
            which = random.choice(incomplete)
            jobs[which][0] += 1
            progress = sum(progress for progress, _ in jobs)
            bar.update(progress, jobs=jobs, force=True)
            time.sleep(0.005)


if __name__ == '__main__':
    main()
