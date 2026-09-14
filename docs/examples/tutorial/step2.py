"""The explicit form: build a `ProgressBar` and `update()` it yourself.

`progressbar.progressbar()` from the previous step is a shortcut over
this. Use a `ProgressBar` as a context manager and call `update()` with the
new value wherever your own loop happens to be, instead of handing the
loop itself to a wrapper.
"""

import time

import progressbar


def main() -> None:
    with progressbar.ProgressBar() as bar:
        for i in range(100):
            time.sleep(0.01)
            bar.update(i + 1)


if __name__ == '__main__':
    main()
