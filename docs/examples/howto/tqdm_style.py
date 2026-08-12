"""Keep tqdm's keyword style when you switch to progressbar.

Coming from `tqdm`, these keywords mean the same thing here: `desc` becomes
the prefix and `total` becomes `max_value` on any `ProgressBar`. `unit=`/
`unit_scale=` only show up through a widget that reads them, such as
`UnitProgress`, so this lists one explicitly alongside `Postfix` for the
live per-file status.
"""

from __future__ import annotations

import time

import progressbar

STEPS = 24


def main() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        progressbar.UnitProgress(),
        ' ',
        progressbar.Postfix(),
    ]
    with progressbar.ProgressBar(
        desc='Downloading',
        total=STEPS,
        unit='files',
        widgets=widgets,
        postfix='starting',
    ) as bar:
        for step in range(STEPS):
            bar.update(step + 1, postfix=f'file {step + 1}')
            time.sleep(0.005)


if __name__ == '__main__':
    main()
