"""Count errors while scanning log records with a Variable widget.

The bar counts inspected records. The named variable counts only the
records that contain an error, so the two readings describe different
parts of the same job.
"""

import time

import progressbar
from progressbar.widgets import WidgetBase

RECORDS: list[str] = [
    'INFO request received',
    'INFO cache hit',
    'ERROR request timed out',
    'INFO response sent',
    'INFO connection closed',
] * 20


def main() -> None:
    widgets: list[str | WidgetBase] = [
        progressbar.Variable('errors', format='Errors: {value:2.0f}'),
        ' | Scanned ',
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
    ]
    errors: int = 0
    bar: progressbar.ProgressBar
    step: int
    record: str
    with progressbar.ProgressBar(
        max_value=len(RECORDS), widgets=widgets, variables={'errors': 0}
    ) as bar:
        for step, record in enumerate(RECORDS, start=1):
            errors += record.startswith('ERROR')
            time.sleep(0.02)
            bar.update(step, errors=errors)


if __name__ == '__main__':
    main()
