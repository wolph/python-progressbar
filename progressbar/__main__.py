"""`python -m progressbar`: a partial reimplementation of Unix `pv`.

Pipes data from one or more input files (or stdin) to an output file
(or stdout) while rendering a progress bar, with optional rate
limiting. See `create_argument_parser` for the supported flags.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import pathlib
import sys
import time
import typing
from pathlib import Path
from typing import IO

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


#: Exit status after an interrupted transfer (128 + SIGINT, as shells do).
EXIT_INTERRUPTED: int = 130


def _parse_size_option(
    parser: argparse.ArgumentParser,
    option: str,
    value: str,
    minimum: int,
) -> int:
    """Parse a size option, exiting through `parser.error` when invalid.

    Args:
        parser: The parser used to report the error (exit status 2).
        option: The flag name, used in the error message.
        value: The raw option value.
        minimum: The smallest accepted value in bytes.

    Returns:
        The size in bytes.
    """
    try:
        size: int = size_to_bytes(value)
    except (ValueError, IndexError, OSError) as exception:
        parser.error(f'invalid {option} value {value!r}: {exception}')
    if size < minimum:
        parser.error(f'{option} must be at least {minimum}, got {value!r}')
    return size


def _collect_inputs(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> tuple[list[IO[typing.Any] | Path], int, bool]:
    """Validate the input arguments without opening any file.

    Returns:
        The inputs (stdin streams or paths), the summed file size and
        whether a total size is known.
    """
    inputs: list[IO[typing.Any] | Path] = []
    total_size: int = 0
    filesize_available: bool = True
    for filename in args.input:
        if filename == '-':
            inputs.append(sys.stdin if args.line_mode else sys.stdin.buffer)
            filesize_available = False
            continue

        input_path: Path = pathlib.Path(filename)
        if not input_path.exists():
            parser.error(f'File not found: {filename}')
        if input_path.is_dir():
            parser.error(f'Is a directory: {filename}')
        total_size += input_path.stat().st_size
        inputs.append(input_path)
    return inputs, total_size, filesize_available


def _check_output_path(
    parser: argparse.ArgumentParser,
    output: str | None,
    inputs: typing.Sequence[IO[typing.Any] | Path],
) -> None:
    """Reject an output path that is a directory or one of the inputs.

    Runs before the output is opened, because opening it truncates it.
    """
    if not output or output == '-':
        return
    output_path: Path = pathlib.Path(output)
    if not output_path.exists():
        return
    if output_path.is_dir():
        parser.error(f'Output is a directory: {output}')
    if not output_path.is_file():
        # Devices (two names of one tty, /dev/null) share an inode without
        # sharing data, so only a regular file can be truncated away
        return
    for input_path in inputs:
        if isinstance(input_path, Path) and output_path.samefile(input_path):
            parser.error(f'Output file is also an input: {output}')


def _open_input(
    input_path: IO[typing.Any] | Path,
    line_mode: bool,
) -> typing.ContextManager[IO[typing.Any]]:
    """Open a path input, or wrap a stdin stream without closing it."""
    if isinstance(input_path, Path):
        if line_mode:
            # newline='' disables universal-newline translation so the
            # byte count matches the file size for CRLF files as well
            return input_path.open('r', newline='')
        return input_path.open('rb')
    return contextlib.nullcontext(input_path)


def _copy_stream(
    input_stream: IO[typing.Any],
    output_stream: IO[typing.Any],
    bar: progressbar.ProgressBar,
    line_mode: bool,
    buffer_size: int,
    rate_limit: int | None,
    started_at: float,
    transferred: int,
) -> int:
    """Copy one input to the output, updating `bar`.

    Returns:
        The running total of bytes transferred.
    """
    while True:
        data: str | bytes
        if line_mode:
            data = input_stream.readline(buffer_size)
        else:
            data = input_stream.read(buffer_size)

        if not data:
            return transferred

        output_stream.write(data)
        if isinstance(data, str):
            # The total size is measured in bytes, so progress must be
            # tracked in bytes as well
            encoding: str = getattr(input_stream, 'encoding', None) or 'utf-8'
            transferred += len(data.encode(encoding, errors='replace'))
        else:
            transferred += len(data)

        bar.update(transferred)
        _sleep_for_rate_limit(rate_limit, transferred, started_at)


def _discard_broken_stdout() -> None:
    """Point fd 1 at `os.devnull` after a broken pipe on stdout.

    The copy loop has already stopped, but the interpreter flushes
    `sys.stdout` once more at exit, and that flush would raise the same
    `BrokenPipeError` again (status 120, "Exception ignored on flushing
    sys.stdout"). Redirecting the descriptor makes that last flush
    succeed, which is what the Python docs recommend for a pipeline
    whose reader went away.
    """
    try:
        fd: int = sys.stdout.fileno()
    except (OSError, ValueError, AttributeError):
        return  # not descriptor-backed (io.StringIO under a test runner)
    if fd != 1:
        return  # a replacement stdout owns that descriptor, leave it alone
    try:
        devnull: int = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(devnull, fd)
        finally:
            os.close(devnull)
    except OSError:  # pragma: no cover
        pass


def main(argv: list[str] | None = None) -> None:
    """Run the `progressbar` command.

    All arguments are validated before the output file is opened, so an
    invalid invocation exits with status 2 and leaves `-o` untouched. An
    interrupted transfer (Ctrl-C) exits with status 130 after the bar
    is finished. A downstream pipe that closes early ends the copy
    quietly with status 0, so `... | head` stays clean under pipefail.

    Args:
        argv: Command-line arguments. Defaults to `sys.argv[1:]`.
    """
    parser: argparse.ArgumentParser = create_argument_parser()
    args: argparse.Namespace = parser.parse_args(argv)

    inputs, total_size, filesize_available = _collect_inputs(parser, args)
    if args.size:
        total_size = _parse_size_option(parser, '--size', args.size, 0)
        filesize_available = True
    buffer_size: int = (
        _parse_size_option(parser, '--buffer-size', args.buffer_size, 1)
        if args.buffer_size
        else 1024
    )
    rate_limit: int | None = (
        _parse_size_option(parser, '--rate-limit', args.rate_limit, 0)
        if args.rate_limit
        else None
    )
    _check_output_path(parser, args.output, inputs)

    widgets = _build_widgets(args, filesize_available)
    progress_bar_class: type[progressbar.ProgressBar] = (
        progressbar.NullBar if args.quiet else progressbar.ProgressBar
    )
    exit_status: int = 0

    with contextlib.ExitStack() as stack:
        output_stream: typing.IO[typing.Any] = _get_output_stream(
            args.output, args.line_mode, stack
        )
        bar = progress_bar_class(
            widgets=widgets,
            max_value=total_size if filesize_available else None,
            max_error=False,
            line_breaks=True if args.numeric else None,
        )
        started_at: float = time.monotonic()
        transferred: int = 0

        bar.start()
        try:
            for input_path in inputs:
                with _open_input(input_path, args.line_mode) as input_stream:
                    transferred = _copy_stream(
                        input_stream,
                        output_stream,
                        bar,
                        args.line_mode,
                        buffer_size,
                        rate_limit,
                        started_at,
                        transferred,
                    )
        except KeyboardInterrupt:
            exit_status = EXIT_INTERRUPTED
        except BrokenPipeError:
            # The reader went away (`... | head`): finish quietly with
            # status 0, as 4.6.0 did and as a pipeline under pipefail
            # expects
            if output_stream is sys.stdout or output_stream is getattr(
                sys.stdout, 'buffer', None
            ):
                _discard_broken_stdout()

        bar.finish(dirty=True)

    if exit_status:
        raise SystemExit(exit_status)


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
