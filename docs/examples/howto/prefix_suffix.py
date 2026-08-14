"""Template `prefix=`/`suffix=` with the bar's own values, not a fixed string.

Both accept a `str.format()` template evaluated against the bar's data on
every redraw -- `{value}`, `{max_value}`, or a custom entry seeded through
`variables=` and updated by name through `bar.update()`. Compare a plain
string, which is what most other examples in this set use for their
prefix.
"""

import time

import progressbar

FILES = ['a.txt', 'b.csv', 'c.json', 'd.log', 'e.txt', 'f.csv']


def main() -> None:
    with progressbar.ProgressBar(
        max_value=len(FILES),
        prefix='{variables.filename} ',
        suffix=' ({value} of {max_value})',
        variables={'filename': '--'},
    ) as bar:
        for step, filename in enumerate(FILES):
            bar.update(step + 1, filename=filename)
            time.sleep(0.1)


if __name__ == '__main__':
    main()
