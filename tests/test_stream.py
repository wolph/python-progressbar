from __future__ import print_function

import io
import sys
import pytest
import progressbar


def test_nowrap():
    # Make sure we definitely unwrap
    for i in range(5):
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
    for i in range(5):
        progressbar.streams.unwrap(stderr=True, stdout=True)


def test_wrap():
    # Make sure we definitely unwrap
    for i in range(5):
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
    for i in range(5):
        progressbar.streams.unwrap(stderr=True, stdout=True)


def test_excepthook():
    progressbar.streams.wrap(stderr=True, stdout=True)

    try:
        raise RuntimeError()
    except RuntimeError:
        progressbar.streams.excepthook(*sys.exc_info())

    progressbar.streams.unwrap_excepthook()
    progressbar.streams.unwrap_excepthook()


def test_fd_as_io_stream():
    stream = io.StringIO()
    with progressbar.ProgressBar(fd=stream) as pb:
        for i in range(101):
            pb.update(i)
    stream.close()


def test_no_newlines():
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
def test_fd_as_standard_streams(stream):
    with progressbar.ProgressBar(fd=stream) as pb:
        for i in range(101):
            pb.update(i)
