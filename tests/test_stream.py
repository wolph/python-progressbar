import io
import logging
import os
import sys

import pytest

import progressbar
from progressbar import terminal


def reset_wrapped_streams() -> None:
    while progressbar.streams.wrapped_logging:
        progressbar.streams.unwrap_logging()
    while (
        progressbar.streams.wrapped_stdout
        or progressbar.streams.wrapped_stderr
    ):
        progressbar.streams.unwrap(stderr=True, stdout=True)
    progressbar.streams.wrapped_logging = 0
    progressbar.streams.wrapped_stdout = 0
    progressbar.streams.wrapped_stderr = 0
    progressbar.streams.logging_handlers.clear()
    for listener in list(progressbar.streams.listeners):
        listener._finished = True
    progressbar.streams.listeners.clear()
    progressbar.streams.capturing = 0
    progressbar.streams.update_capturing()


def test_nowrap() -> None:
    # Make sure we definitely unwrap
    reset_wrapped_streams()

    stdout = sys.stdout
    stderr = sys.stderr

    progressbar.streams.wrap()

    assert stdout == sys.stdout
    assert stderr == sys.stderr

    progressbar.streams.unwrap()

    assert stdout == sys.stdout
    assert stderr == sys.stderr

    # Make sure we definitely unwrap
    reset_wrapped_streams()


def test_wrap() -> None:
    # Make sure we definitely unwrap
    reset_wrapped_streams()

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
    reset_wrapped_streams()


def test_wrap_logging_retargets_existing_stderr_handler(monkeypatch) -> None:
    reset_wrapped_streams()

    stream = io.StringIO()
    monkeypatch.setattr(progressbar.streams, 'original_stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'stderr', stream)
    monkeypatch.setattr(sys, 'stderr', stream)

    logger = logging.getLogger('progressbar-test-wrap-logging')
    logger.handlers = []
    logger.propagate = False
    handler = logging.StreamHandler(sys.stderr)
    logger.addHandler(handler)

    progressbar.streams.wrap_stderr()
    progressbar.streams.wrap_logging()
    try:
        assert handler.stream is progressbar.streams.stderr
    finally:
        progressbar.streams.unwrap_logging()
        progressbar.streams.unwrap(stderr=True)
        logger.handlers = []


def test_unwrap_logging_restores_handler_stream(monkeypatch) -> None:
    reset_wrapped_streams()

    stream = io.StringIO()
    monkeypatch.setattr(sys, 'stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'original_stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'stderr', stream)

    logger = logging.getLogger('progressbar-test-unwrap-logging')
    logger.handlers = []
    logger.propagate = False
    handler = logging.StreamHandler(sys.stderr)
    logger.addHandler(handler)

    progressbar.streams.wrap_stderr()
    progressbar.streams.wrap_logging()
    progressbar.streams.unwrap_logging()

    try:
        assert handler.stream is stream
    finally:
        progressbar.streams.unwrap(stderr=True)
        logger.handlers = []


def test_unwrap_logging_restores_handler_created_after_stderr_wrap(
    monkeypatch,
) -> None:
    reset_wrapped_streams()

    stream = io.StringIO()
    monkeypatch.setattr(sys, 'stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'original_stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'stderr', stream)

    logger = logging.getLogger('progressbar-test-wrapped-stderr-handler')
    logger.handlers = []
    logger.propagate = False

    progressbar.streams.wrap_stderr()
    wrapped_stderr = progressbar.streams.stderr
    handler = logging.StreamHandler(sys.stderr)
    logger.addHandler(handler)

    try:
        assert handler.stream is wrapped_stderr

        progressbar.streams.wrap_logging()
        progressbar.streams.unwrap_logging()
        progressbar.streams.unwrap(stderr=True)

        assert handler.stream is stream
    finally:
        progressbar.streams.unwrap_logging()
        progressbar.streams.unwrap(stderr=True)
        logger.handlers = []


def test_wrap_logging_handles_nested_calls(monkeypatch) -> None:
    reset_wrapped_streams()

    stream = io.StringIO()
    monkeypatch.setattr(sys, 'stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'original_stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'stderr', stream)

    logger = logging.getLogger('progressbar-test-nested-wrap-logging')
    logger.handlers = []
    logger.propagate = False
    handler = logging.StreamHandler(sys.stderr)
    logger.addHandler(handler)

    progressbar.streams.wrap_stderr()
    progressbar.streams.wrap_logging()
    progressbar.streams.wrap_logging()
    try:
        assert progressbar.streams.wrapped_logging == 2
        progressbar.streams.unwrap_logging()
        assert progressbar.streams.wrapped_logging == 1
    finally:
        progressbar.streams.unwrap_logging()
        progressbar.streams.unwrap(stderr=True)
        logger.handlers = []


def test_wrap_logging_retargets_existing_stdout_handler(monkeypatch) -> None:
    reset_wrapped_streams()

    stream = io.StringIO()
    monkeypatch.setattr(sys, 'stdout', stream)
    monkeypatch.setattr(progressbar.streams, 'original_stdout', stream)
    monkeypatch.setattr(progressbar.streams, 'stdout', stream)

    logger = logging.getLogger('progressbar-test-wrap-stdout-logging')
    logger.handlers = []
    logger.propagate = False
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)

    progressbar.streams.wrap_stdout()
    progressbar.streams.wrap_logging()
    try:
        assert handler.stream is progressbar.streams.stdout
    finally:
        progressbar.streams.unwrap_logging()
        progressbar.streams.unwrap(stdout=True)
        logger.handlers = []


def test_wrap_logging_ignores_handlers_that_reject_streams(
    monkeypatch,
) -> None:
    class RejectingHandler(logging.StreamHandler):
        def setStream(self, stream):  # noqa: N802
            raise ValueError('stream rejected')

    reset_wrapped_streams()

    stream = io.StringIO()
    monkeypatch.setattr(sys, 'stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'original_stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'stderr', stream)

    logger = logging.getLogger('progressbar-test-rejecting-handler')
    logger.handlers = []
    logger.propagate = False
    handler = RejectingHandler(sys.stderr)
    logger.addHandler(handler)

    progressbar.streams.wrap_stderr()
    try:
        progressbar.streams.wrap_logging()
        assert all(
            logged_handler is not handler
            for logged_handler, _stream in progressbar.streams.logging_handlers
        )
    finally:
        progressbar.streams.unwrap_logging()
        progressbar.streams.unwrap(stderr=True)
        logger.handlers = []


def test_wrap_logging_uses_handler_snapshot(monkeypatch) -> None:
    reset_wrapped_streams()

    stream = io.StringIO()
    monkeypatch.setattr(sys, 'stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'original_stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'stderr', stream)

    logger = logging.getLogger('progressbar-test-mutating-handlers')
    logger.handlers = []
    logger.propagate = False
    first_handler = logging.StreamHandler(sys.stderr)
    late_handler = logging.StreamHandler(sys.stderr)
    logger.addHandler(first_handler)

    wrapped_handlers: list[logging.StreamHandler] = []
    original_wrap_handler = progressbar.streams._wrap_logging_handler

    def mutating_wrap_handler(handler, wrapped_streams, restore_streams):
        wrapped_handlers.append(handler)
        if handler is first_handler:
            logger.addHandler(late_handler)
        original_wrap_handler(handler, wrapped_streams, restore_streams)

    monkeypatch.setattr(
        progressbar.streams,
        '_wrap_logging_handler',
        mutating_wrap_handler,
    )

    progressbar.streams.wrap_stderr()
    try:
        progressbar.streams.wrap_logging()
        assert first_handler in wrapped_handlers
        assert late_handler not in wrapped_handlers
        assert late_handler.stream is stream
    finally:
        progressbar.streams.unwrap_logging()
        progressbar.streams.unwrap(stderr=True)
        logger.handlers = []


def test_unwrap_logging_ignores_dynamic_stderr_handler(monkeypatch) -> None:
    reset_wrapped_streams()

    stream = io.StringIO()
    monkeypatch.setattr(sys, 'stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'original_stderr', stream)
    monkeypatch.setattr(progressbar.streams, 'stderr', stream)

    logger = logging.getLogger('progressbar-test-dynamic-stderr-handler')
    logger.handlers = []
    logger.propagate = False
    handler = logging._StderrHandler()  # type: ignore[attr-defined]
    logger.addHandler(handler)

    try:
        progressbar.streams.wrap_stderr()
        assert handler.stream is progressbar.streams.stderr

        progressbar.streams.wrap_logging()
        progressbar.streams.unwrap_logging()
    finally:
        progressbar.streams.unwrap_logging()
        progressbar.streams.unwrap(stderr=True)
        logger.handlers = []


def test_redirected_stdout_lines_are_flushed_above_bar(monkeypatch) -> None:
    reset_wrapped_streams()
    output = io.StringIO()
    monkeypatch.setattr(progressbar.streams, 'original_stdout', output)
    monkeypatch.setattr(progressbar.streams, 'stdout', output)
    monkeypatch.setattr(sys, 'stdout', output)

    with progressbar.ProgressBar(
        max_value=2,
        fd=output,
        redirect_stdout=True,
        line_breaks=False,
        is_terminal=True,
        term_width=40,
    ) as bar:
        print('phase one')
        bar.update(1, force=True)
        print('phase two')
        bar.update(2, force=True)

    rendered = output.getvalue()
    assert 'phase one' in rendered
    assert 'phase two' in rendered
    assert '\r' + ' ' * 40 + '\rphase two\n' in rendered
    assert rendered.endswith('\n')


def test_redirected_stderr_lines_are_flushed_above_bar(monkeypatch) -> None:
    reset_wrapped_streams()
    output = io.StringIO()
    monkeypatch.setattr(progressbar.streams, 'original_stderr', output)
    monkeypatch.setattr(progressbar.streams, 'stderr', output)
    monkeypatch.setattr(sys, 'stderr', output)

    with progressbar.ProgressBar(
        max_value=2,
        fd=output,
        redirect_stderr=True,
        line_breaks=False,
        is_terminal=True,
        term_width=40,
    ) as bar:
        print('warning one', file=sys.stderr)
        bar.update(1, force=True)
        print('warning two', file=sys.stderr)
        bar.update(2, force=True)

    rendered = output.getvalue()
    assert 'warning one' in rendered
    assert 'warning two' in rendered
    assert '\r' + ' ' * 40 + '\rwarning two\n' in rendered
    assert rendered.endswith('\n')


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


def test_update_keeps_colors_when_enabled() -> None:
    stream = io.StringIO()
    with progressbar.ProgressBar(
        fd=stream,
        widgets=['\033[92mgreen\033[0m'],
        max_value=1,
        enable_colors=True,
    ) as bar:
        bar.update(1)

    assert '\033[92mgreen\033[0m' in stream.getvalue()


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


def test_line_offset_stream_wrapper_write_length_and_flush() -> None:
    # Regression: C5/C6 - write() returned the newline-stripped length
    # and flush() never reached the wrapped stream.
    class CountingIO(io.StringIO):
        def __init__(self) -> None:
            super().__init__()
            self.flushes = 0

        def flush(self) -> None:
            self.flushes += 1
            super().flush()

    target = CountingIO()
    wrapper = progressbar.LineOffsetStreamWrapper(lines=2, stream=target)

    written = wrapper.write('hello\n')
    assert written == 6
    assert target.flushes >= 1
