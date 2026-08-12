"""Route stdlib `logging` output above a progress bar instead of corrupting it.

`streams.wrap_stderr()` redirects raw writes the same way `redirect_stderr=
True` does; `streams.wrap_logging()` additionally retargets every
`StreamHandler` already pointed at stdout/stderr so calls to `logging.info(
...)` -- not just `print()` -- land above the bar cleanly. Construction
order does not matter: a bar defaulting to `sys.stderr` resolves that to
the unwrapped stream either way, which is what stops its own redraws
recursing through the capture. Always unwrap (and, here, remove the
handler) in a `finally`, since both mutate process-global state.
"""

from __future__ import annotations

import logging
import sys
import time

import progressbar

logger = logging.getLogger(__name__)

STEPS = 24


def main() -> None:
    handler = logging.StreamHandler()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)
    # `fd=sys.stderr` is read at call time, not bound once when this module
    # was first imported -- unlike the parameter's own default. Passing it
    # explicitly is a no-op in a real run (nothing has touched `sys.stderr`
    # yet, so it is the same object either way); it only matters to a
    # caller -- such as a test -- that has already reassigned `sys.stderr`
    # before this line runs.
    bar = progressbar.ProgressBar(max_value=STEPS, fd=sys.stderr)
    try:
        progressbar.streams.wrap_stderr()
        progressbar.streams.wrap_logging()
        try:
            with bar:
                for step in range(STEPS):
                    if step in {8, 16}:
                        logger.info('completed step %d', step)
                    bar.update(step + 1)
                    time.sleep(0.005)
        finally:
            progressbar.streams.unwrap_logging()
            progressbar.streams.unwrap_stderr()
    finally:
        logger.removeHandler(handler)


if __name__ == '__main__':
    main()
