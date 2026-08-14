"""The `progressbar` command is a `pv` replacement for pipes and files.

Installing the package puts a `progressbar` executable on the path,
with `bar` as its pipeline shorthand (`python -m progressbar` is the
same program), a Python implementation of the classic Unix `pv`: it
copies input to output while drawing transfer progress on stderr.
This example drives it in-process, moving 4 MiB at a rate-limited
2 MiB/s with the percentage, timer, ETA, rate and byte-counter
displays turned on.
"""

import pathlib
import tempfile

from progressbar.__main__ import main as progressbar_command

SIZE = 4 * 1024 * 1024


def main() -> None:
    with tempfile.TemporaryDirectory() as workdir:
        source = pathlib.Path(workdir) / 'input.bin'
        target = pathlib.Path(workdir) / 'output.bin'
        source.write_bytes(b'\0' * SIZE)

        progressbar_command(
            [
                '--progress',
                '--timer',
                '--eta',
                '--rate',
                '--bytes',
                '--rate-limit',
                '2M',
                '--buffer-size',
                '256K',
                str(source),
                '-o',
                str(target),
            ]
        )

        assert target.stat().st_size == SIZE


if __name__ == '__main__':
    main()
