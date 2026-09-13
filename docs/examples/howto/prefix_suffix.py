"""Show the current file and processed blocks in prefix/suffix templates.

Each file takes twenty small steps. Both templates read the same live
bar data on every redraw, including the filename supplied to update().
"""

import time

import progressbar

FILES: list[str] = ['users.csv', 'sales.csv', 'stock.csv', 'costs.csv', 'audit.csv']
BLOCKS_PER_FILE: int = 20


def main() -> None:
    completed: int = 0
    bar: progressbar.ProgressBar
    file_number: int
    filename: str
    block: int
    with progressbar.ProgressBar(
        max_value=len(FILES) * BLOCKS_PER_FILE,
        prefix='{variables.filename} {variables.file_number}/5 ',
        suffix=' {value:3}/{max_value} blocks',
        variables={'filename': FILES[0], 'file_number': 1},
        widgets=[progressbar.Percentage(), ' ', progressbar.Bar()],
    ) as bar:
        for file_number, filename in enumerate(FILES, start=1):
            for block in range(BLOCKS_PER_FILE):
                time.sleep(0.02)
                completed += 1
                bar.update(
                    completed, filename=filename, file_number=file_number
                )


if __name__ == '__main__':
    main()
