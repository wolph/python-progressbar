"""What the bar looks like once it detects stdout isn't a terminal.

`ProgressBar` normally checks whether its output stream is a terminal and,
if not, switches from overwriting one line to printing a new line per
update -- the shape you want once output is piped to a file, `tee`, or a
log collector, so each redraw survives instead of being lost to the next
carriage return. That auto-detection can't be demonstrated here, since this
demo is captured through something that always presents itself as a
terminal; `line_breaks=True` forces the same rendering explicitly, and is
also the parameter to reach for if you want that behaviour even when
stdout genuinely is a terminal -- a build log, say, where every line should
stay on screen.
"""

import time

import progressbar

STEPS = 12


def main() -> None:
    with progressbar.ProgressBar(max_value=STEPS, line_breaks=True) as bar:
        for step in range(STEPS):
            bar.update(step + 1)
            time.sleep(0.05)


if __name__ == '__main__':
    main()
