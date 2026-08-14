"""One call fans work out to threads and renders every bar for you.

`progressbar.map` runs `crunch` over the batch on a thread pool and
drives one overall bar plus a live bar per running task. The everyday
spelling is `bar='multi'`. Handing it a `MultiBar` instance instead, as
here, lets the finished overall bar stay on screen when the run ends.
Inside a task, `progressbar.current_task_bar()` hands back that task's
own bar so it can report sub-progress too.
"""

import sys
import time

import progressbar

FILES = [
    'alpha.dat',
    'bravo.dat',
    'charlie.dat',
    'delta.dat',
    'echo.dat',
    'foxtrot.dat',
    'golf.dat',
    'hotel.dat',
]


def crunch(path: str) -> str:
    # Deterministic, per-file amount of work: later files take longer,
    # so the bars visibly finish one after another.
    bar = progressbar.current_task_bar()
    for block in range(4 + FILES.index(path)):
        if bar is not None:
            bar.update(block + 1)
        time.sleep(0.05)
    return path


def main() -> None:
    multibar = progressbar.MultiBar(fd=sys.stdout, sort_reverse=False)
    results = progressbar.map(crunch, FILES, workers=8, bar=multibar)
    assert results == FILES
    # One more beat before the interpreter exits, so the finished
    # overall bar's final redraw reaches the terminal.
    time.sleep(0.1)


if __name__ == '__main__':
    main()
