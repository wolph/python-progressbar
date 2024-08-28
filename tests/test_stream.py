import io
import os
import sys

import pytest

import progressbar
from progressbar import terminal


def test_nowrap() -> None:
    # Make sure we definitely unwrap
    for _i in range(5):
        progressbar.streams.unwrap(stderr=True, stdout=True)

    stdout = sys.stdout
    stderr = sys.stderr

    progressbar.streams.wrap()

    assert stdout == sys.stdout
    assert stderr == sys.stderr

    progressbar.streams.unwrap()

    assert stdout == sys.stdout
    assert stderr == sys.stderr

    # Make sure we definitely unwrap
    for _i in range(5):
        progressbar.streams.unwrap(stderr=True, stdout=True)


def test_wrap() -> None:
    # Make sure we definitely unwrap
    for _i in range(5):
        progressbar.streams.unwrap(stderr=True, stdout=True)

    stdout = sys.stdout
    stderr = sys.stderr

    progressbar.streams.wrap(stderr=True, stdout=True)

    assert stdout != sys.stdout
    assert stderr != sys.stderr

    # Wrap again
    stdout = sys.stdout
    stderr = sys.stderr

    progressbar.streams.wrap(stderr=True, stdout=True)

    assert stdout == sys.stdout
    assert stderr == sys.stderr

    # Make sure we definitely unwrap
    for _i in range(5):
        progressbar.streams.unwrap(stderr=True, stdout=True)


def test_excepthook() -> None:
    progressbar.streams.wrap(stderr=True, stdout=True)

    try:
        raise RuntimeError()  # noqa: TRY301
    except RuntimeError:
        progressbar.streams.excepthook(*sys.exc_info())

    progressbar.streams.unwrap_excepthook()
    progressbar.streams.unwrap_excepthook()


def test_fd_as_io_stream() -> None:
    stream = io.StringIO()
    with progressbar.ProgressBar(fd=stream) as pb:
        for i in range(101):
            pb.update(i)
    stream.close()


def test_no_newlines() -> None:
    kwargs = dict(
        redirect_stderr=True,
        redirect_stdout=True,
        line_breaks=False,
        is_terminal=True,
    )

    with progressbar.ProgressBar(**kwargs) as bar:
        for i in range(5):
            bar.update(i)

        for i in range(5, 10):
            try:
                print('\n\n', file=progressbar.streams.stdout)
                print('\n\n', file=progressbar.streams.stderr)
            except ValueError:
                pass
            bar.update(i)


@pytest.mark.parametrize('stream', [sys.__stdout__, sys.__stderr__])
@pytest.mark.skipif(os.name == 'nt', reason='Windows does not support this')
def test_fd_as_standard_streams(stream) -> None:
    with progressbar.ProgressBar(fd=stream) as pb:
        for i in range(101):
            pb.update(i)


def test_line_offset_stream_wrapper() -> None:
    stream = terminal.LineOffsetStreamWrapper(5, io.StringIO())
    stream.write('Hello World!')


def test_last_line_stream_methods() -> None:
    stream = terminal.LastLineStream(io.StringIO())

    # Test write method
    stream.write('Hello World!')
    assert stream.read() == 'Hello World!'
    assert stream.read(5) == 'Hello'

    # Test flush method
    stream.flush()
    assert stream.line == 'Hello World!'
    assert stream.readline() == 'Hello World!'
    assert stream.readline(5) == 'Hello'

    # Test truncate method
    stream.truncate(5)
    assert stream.line == 'Hello'
    stream.truncate()
    assert stream.line == ''

    # Test seekable/readable
    assert not stream.seekable()
    assert stream.readable()

    stream.writelines(['a', 'b', 'c'])
    assert stream.read() == 'c'

    assert list(stream) == ['c']

    with stream:
        stream.write('Hello World!')
        assert stream.read() == 'Hello World!'
        assert stream.read(5) == 'Hello'

    # Test close method
    stream.close()
