"""`python -m progressbar`: a partial reimplementation of Unix `pv`.

Pipes data from one or more input files (or stdin) to an output file
(or stdout) while rendering a progress bar, with optional rate
limiting. See `create_argument_parser` for the supported flags.
"""

from __future__ import annotations

import argparse
import contextlib
import pathlib
import sys
import time
import typing
from pathlib import Path
from typing import IO, BinaryIO, TextIO

import progressbar


def size_to_bytes(size_str: str) -> int:
    """Convert a size string with suffixes 'k', 'm', etc., to bytes.

    A `@`-prefixed argument is treated as a file path and returns that
    file's size.

    >>> size_to_bytes('1024k')
    1048576
    >>> size_to_bytes('1024m')
    1073741824
    >>> size_to_bytes('1024g')
    1099511627776
    >>> size_to_bytes('1024')
    1024
    >>> size_to_bytes('1024p')
    1152921504606846976
    """
    suffix_exponent = {
        'k': 1,
        'm': 2,
        'g': 3,
        't': 4,
        'p': 5,
    }

    exponent = 0

    if size_str.startswith('@'):
        return pathlib.Path(size_str[1:]).stat().st_size

    if size_str[-1].lower() in suffix_exponent:
        exponent = suffix_exponent[size_str[-1].lower()]
        size_str = size_str[:-1]

    return int(size_str) * (1024**exponent)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the `progressbar` command."""
    description = """
        Monitor the progress of data through a pipe.

        A Python implementation of the original `pv` command: functional
        but not yet feature complete.
    """
    parser = argparse.ArgumentParser(description=description)

    # Display switches
    parser.add_argument(
        '-p',
        '--progress',
        action='store_true',
        help='Turn the progress bar on.',
    )
    parser.add_argument(
        '-t', '--timer', action='store_true', help='Turn the timer on.'
    )
    parser.add_argument(
        '-e', '--eta', action='store_true', help='Turn the ETA timer on.'
    )
    parser.add_argument(
        '-I',
        '--fineta',
        action='store_true',
        help='Display the ETA as local time of arrival.',
    )
    parser.add_argument(
        '-r', '--rate', action='store_true', help='Turn the rate counter on.'
    )
    parser.add_argument(
        '-a',
        '--average-rate',
        action='store_true',
        help='Turn the average rate counter on.',
    )
    parser.add_argument(
        '-b',
        '--bytes',
        action='store_true',
        help='Turn the total byte counter on.',
    )
    parser.add_argument(
        '-8',
        '--bits',
        action='store_true',
        help='Display total bits instead of bytes.',
    )
    parser.add_argument(
        '-T',
        '--buffer-percent',
        action='store_true',
        help='Turn on the transfer buffer percentage display.',
    )
    parser.add_argument(
        '-A',
        '--last-written',
        type=int,
        help='Show the last NUM bytes written.',
    )
    parser.add_argument(
        '-F',
        '--format',
        type=str,
        help='Use the format string FORMAT for output format.',
    )
    parser.add_argument(
        '-n', '--numeric', action='store_true', help='Numeric output.'
    )
    parser.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        help='No output.',
    )

    # Output modifiers
    parser.add_argument(
        '-W',
        '--wait',
        action='store_true',
        help='Wait until the first byte has been transferred.',
    )
    parser.add_argument('-D', '--delay-start', type=float, help='Delay start.')
    parser.add_argument(
        '-s', '--size', type=str, help='Assume total data size is SIZE.'
    )
    parser.add_argument(
        '-l',
        '--line-mode',
        action='store_true',
        help='Count lines instead of bytes.',
    )
    parser.add_argument(
        '-0',
        '--null',
        action='store_true',
        help='Count lines terminated with a zero byte.',
    )
    parser.add_argument(
        '-i', '--interval', type=float, help='Interval between updates.'
    )
    parser.add_argument(
        '-m',
        '--average-rate-window',
        type=int,
        help='Window for average rate calculation.',
    )
    parser.add_argument(
        '-w',
        '--width',
        type=int,
        help='Assume terminal is WIDTH characters wide.',
    )
    parser.add_argument(
        '-H', '--height', type=int, help='Assume terminal is HEIGHT rows high.'
    )
    parser.add_argument(
        '-N', '--name', type=str, help='Prefix output information with NAME.'
    )
    parser.add_argument(
        '-f', '--force', action='store_true', help='Force output.'
    )
    parser.add_argument(
        '-c',
        '--cursor',
        action='store_true',
        help='Use cursor positioning escape sequences.',
    )

    # Data transfer modifiers
    parser.add_argument(
        '-L',
        '--rate-limit',
        type=str,
        help='Limit transfer to RATE bytes per second.',
    )
    parser.add_argument(
        '-B',
        '--buffer-size',
        type=str,
        help='Use transfer buffer size of BYTES.',
    )
    parser.add_argument(
        '-C', '--no-splice', action='store_true', help='Never use splice.'
    )
    parser.add_argument(
        '-E', '--skip-errors', action='store_true', help='Ignore read errors.'
    )
    parser.add_argument(
        '-Z',
        '--error-skip-block',
        type=str,
        help='Skip block size when ignoring errors.',
    )
    parser.add_argument(
        '-S',
        '--stop-at-size',
        action='store_true',
        help='Stop transferring after SIZE bytes.',
    )
    parser.add_argument(
        '-Y',
        '--sync',
        action='store_true',
        help='Synchronise buffer caches to disk after writes.',
    )
    parser.add_argument(
        '-K',
        '--direct-io',
        action='store_true',
        help='Set O_DIRECT flag on all inputs/outputs.',
    )
    parser.add_argument(
        '-X',
        '--discard',
        action='store_true',
        help='Discard input data instead of transferring it.',
    )
    parser.add_argument(
        '-d', '--watchfd', type=str, help='Watch file descriptor of process.'
    )
    parser.add_argument(
        '-R',
        '--remote',
        type=int,
        help='Remote control another running instance of pv.',
    )

    # General options
    parser.add_argument(
        '-P', '--pidfile', type=pathlib.Path, help='Save process ID in FILE.'
    )
    parser.add_argument(
        'input',
        help='Input file path. Uses stdin if not specified.',
        default='-',
        nargs='*',
    )
    parser.add_argument(
        '-o',
        '--output',
        default='-',
        help='Output file path. Uses stdout if not specified.',
    )

    return parser


def _default_widgets(
    filesize_available: bool,
) -> list[progressbar.widgets.WidgetBase | str]:
    """Build the widget list used when no display flag was passed.

    Args:
        filesize_available: Whether a total size is known, so
            progress can be shown as a percentage/bar rather than a
            raw count.

    Returns:
        A percentage/bar/timer/speed layout if a size is known,
        otherwise a count/data-size/timer layout.
    """
    if filesize_available:
        return [
            progressbar.Percentage(),
            ' ',
            progressbar.Bar(),
            ' ',
            progressbar.Timer(),
            ' ',
            progressbar.FileTransferSpeed(),
        ]
    return [
        progressbar.SimpleProgress(),
        ' ',
        progressbar.DataSize(),
        ' ',
        progressbar.Timer(),
    ]


def _append_widget_group(
    widgets: list[progressbar.widgets.WidgetBase | str],
    group: typing.Sequence[progressbar.widgets.WidgetBase | str],
) -> None:
    """Append `group` to `widgets` in place, spacing groups apart."""
    if widgets:
        widgets.append(' ')
    widgets.extend(group)


def _build_widgets(
    args: argparse.Namespace,
    filesize_available: bool,
) -> list[progressbar.widgets.WidgetBase | str]:
    """Build the widget list from the display flags the user passed.

    Each display flag (`-p`, `-b`, `-t`, `-e`, `-I`, `-r`/`-a`) that
    was set contributes its own widget group, in a fixed order,
    space-separated. Unset flags contribute nothing. With no display
    flag at all, falls back to `_default_widgets`.

    Args:
        args: The parsed command-line arguments.
        filesize_available: Whether a total size is known, passed
            through to `_default_widgets`.

    Returns:
        The assembled widget list, or `[]` if `--quiet` was passed.
    """
    if args.quiet:
        return []

    requested_widgets = [
        (args.progress, [progressbar.Percentage(), ' ', progressbar.Bar()]),
        (args.bytes, [progressbar.DataSize()]),
        (args.timer, [progressbar.Timer()]),
        (args.eta, [progressbar.AdaptiveETA()]),
        (args.fineta, [progressbar.AbsoluteETA()]),
        (args.rate or args.average_rate, [progressbar.FileTransferSpeed()]),
    ]
    selected_widgets = [
        group for selected, group in requested_widgets if selected
    ]
    if not selected_widgets:
        return _default_widgets(filesize_available)

    widgets: list[progressbar.widgets.WidgetBase | str] = []
    for group in selected_widgets:
        _append_widget_group(widgets, group)

    return widgets


def _sleep_for_rate_limit(
    rate_limit: int | None,
    transferred: int,
    started_at: float,
    now: float | None = None,
) -> None:
    """Block until `transferred` bytes are on pace for `rate_limit`.

    Compares how long transferring `transferred` bytes at
    `rate_limit` bytes/second *should* have taken against how long it
    actually took since `started_at`, and sleeps off the difference
    when running ahead of schedule. A no-op once actual elapsed time
    has caught up or overtaken the expected pace.

    Args:
        rate_limit: Target transfer rate in bytes/second, or `None`/
            `0` to disable rate limiting entirely.
        transferred: Total bytes transferred so far.
        started_at: `time.monotonic()` reading taken when the
            transfer began.
        now: `time.monotonic()` reading to treat as "now", sampled
            internally if not given (a test seam).
    """
    if not rate_limit:
        return
    now = time.monotonic() if now is None else now
    expected_elapsed = transferred / rate_limit
    actual_elapsed = now - started_at
    delay = expected_elapsed - actual_elapsed
    if delay > 0:
        time.sleep(delay)


def main(argv: list[str] | None = None) -> None:  # noqa: C901
    """Run the `progressbar` command.

    Args:
        argv: Command-line arguments. Defaults to `sys.argv[1:]`.
    """
    parser: argparse.ArgumentParser = create_argument_parser()
    args: argparse.Namespace = parser.parse_args(argv)

    with contextlib.ExitStack() as stack:
        output_stream: typing.IO[typing.Any] = _get_output_stream(
            args.output, args.line_mode, stack
        )

        input_paths: list[BinaryIO | TextIO | Path | IO[typing.Any]] = []
        total_size: int = 0
        filesize_available: bool = True
        for filename in args.input:
            input_path: typing.IO[typing.Any] | pathlib.Path
            if filename == '-':
                if args.line_mode:
                    input_path = sys.stdin
                else:
                    input_path = sys.stdin.buffer

                filesize_available = False
            else:
                input_path = pathlib.Path(filename)
                if not input_path.exists():
                    parser.error(f'File not found: {filename}')

                if not args.size:
                    total_size += input_path.stat().st_size

            input_paths.append(input_path)

        # Determine the size for the progress bar (if provided)
        if args.size:
            total_size = size_to_bytes(args.size)
            filesize_available = True

        widgets = _build_widgets(args, filesize_available)
        progress_bar_class: type[progressbar.ProgressBar] = (
            progressbar.NullBar if args.quiet else progressbar.ProgressBar
        )

        bar = progress_bar_class(
            widgets=widgets,
            max_value=total_size if filesize_available else None,
            max_error=False,
            line_breaks=True if args.numeric else None,
        )

        buffer_size = (
            size_to_bytes(args.buffer_size) if args.buffer_size else 1024
        )
        rate_limit = (
            size_to_bytes(args.rate_limit) if args.rate_limit else None
        )
        started_at = time.monotonic()
        total_transferred = 0

        bar.start()
        with contextlib.suppress(KeyboardInterrupt, BrokenPipeError):
            for input_path in input_paths:
                if isinstance(input_path, pathlib.Path):
                    if args.line_mode:
                        # newline='' disables universal-newline
                        # translation so the byte count matches the file
                        # size for CRLF files as well
                        input_stream = stack.enter_context(
                            input_path.open('r', newline=''),
                        )
                    else:
                        input_stream = stack.enter_context(
                            input_path.open('rb'),
                        )
                else:
                    input_stream = input_path

                while True:
                    data: str | bytes
                    if args.line_mode:
                        data = input_stream.readline(buffer_size)
                    else:
                        data = input_stream.read(buffer_size)

                    if not data:
                        break

                    output_stream.write(data)
                    if isinstance(data, str):
                        # The total size is measured in bytes, so progress
                        # must be tracked in bytes as well
                        encoding = (
                            getattr(input_stream, 'encoding', None) or 'utf-8'
                        )
                        total_transferred += len(
                            data.encode(encoding, errors='replace'),
                        )
                    else:
                        total_transferred += len(data)

                    bar.update(total_transferred)
                    _sleep_for_rate_limit(
                        rate_limit,
                        total_transferred,
                        started_at,
                    )

        bar.finish(dirty=True)


def _get_output_stream(
    output: str | None,
    line_mode: bool,
    stack: contextlib.ExitStack,
) -> typing.IO[typing.Any]:
    """Open (or pick) the output stream: a file, or stdout for `-`/unset.

    Files are registered with `stack` so they close on exit. In line
    mode the stream is text with newline translation disabled,
    otherwise binary.
    """
    if output and output != '-':
        if line_mode:
            # newline='' passes the data through without newline
            # translation, mirroring the input handling
            return stack.enter_context(
                open(output, 'w', newline=''),  # noqa: SIM115
            )

        return stack.enter_context(open(output, 'wb'))  # noqa: SIM115
    elif line_mode:
        return sys.stdout
    else:
        return sys.stdout.buffer


if __name__ == '__main__':
    main()
