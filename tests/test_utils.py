import contextlib
import io
import sys

import pytest

import progressbar
import progressbar.env
from progressbar import utils


@pytest.mark.parametrize(
    'value,expected',
    [
        (None, None),
        ('', None),
        ('1', True),
        ('y', True),
        ('t', True),
        ('yes', True),
        ('true', True),
        ('True', True),
        ('0', False),
        ('n', False),
        ('f', False),
        ('no', False),
        ('false', False),
        ('False', False),
    ],
)
def test_env_flag(value, expected, monkeypatch) -> None:
    if value is not None:
        monkeypatch.setenv('TEST_ENV', value)
    assert progressbar.env.env_flag('TEST_ENV') == expected

    if value:
        monkeypatch.setenv('TEST_ENV', value.upper())
        assert progressbar.env.env_flag('TEST_ENV') == expected

    monkeypatch.undo()


def test_is_terminal(monkeypatch) -> None:
    fd = io.StringIO()

    monkeypatch.delenv('PROGRESSBAR_IS_TERMINAL', raising=False)
    monkeypatch.setattr(progressbar.env, 'JUPYTER', False)

    assert progressbar.env.is_terminal(fd) is False
    assert progressbar.env.is_terminal(fd, True) is True
    assert progressbar.env.is_terminal(fd, False) is False

    monkeypatch.setattr(progressbar.env, 'JUPYTER', True)
    assert progressbar.env.is_terminal(fd) is True

    # Sanity check
    monkeypatch.setattr(progressbar.env, 'JUPYTER', False)
    assert progressbar.env.is_terminal(fd) is False

    monkeypatch.setenv('PROGRESSBAR_IS_TERMINAL', 'true')
    assert progressbar.env.is_terminal(fd) is True
    monkeypatch.setenv('PROGRESSBAR_IS_TERMINAL', 'false')
    assert progressbar.env.is_terminal(fd) is False
    monkeypatch.delenv('PROGRESSBAR_IS_TERMINAL')

    # Sanity check
    assert progressbar.env.is_terminal(fd) is False


def test_is_ansi_terminal(monkeypatch) -> None:
    fd = io.StringIO()

    monkeypatch.delenv('PROGRESSBAR_IS_TERMINAL', raising=False)
    monkeypatch.setattr(progressbar.env, 'JUPYTER', False)

    assert not progressbar.env.is_ansi_terminal(fd)
    assert progressbar.env.is_ansi_terminal(fd, True) is True
    assert progressbar.env.is_ansi_terminal(fd, False) is False

    monkeypatch.setattr(progressbar.env, 'JUPYTER', True)
    assert progressbar.env.is_ansi_terminal(fd) is True
    monkeypatch.setattr(progressbar.env, 'JUPYTER', False)

    # Sanity check
    assert not progressbar.env.is_ansi_terminal(fd)

    monkeypatch.setenv('PROGRESSBAR_IS_TERMINAL', 'true')
    assert not progressbar.env.is_ansi_terminal(fd)
    monkeypatch.setenv('PROGRESSBAR_IS_TERMINAL', 'false')
    assert not progressbar.env.is_ansi_terminal(fd)
    monkeypatch.delenv('PROGRESSBAR_IS_TERMINAL')

    # Sanity check
    assert not progressbar.env.is_ansi_terminal(fd)

    # Fake TTY mode for environment testing
    fd.isatty = lambda: True
    monkeypatch.setenv('TERM', 'xterm')
    assert progressbar.env.is_ansi_terminal(fd) is True
    monkeypatch.setenv('TERM', 'xterm-256')
    assert progressbar.env.is_ansi_terminal(fd) is True
    monkeypatch.setenv('TERM', 'xterm-256color')
    assert progressbar.env.is_ansi_terminal(fd) is True
    monkeypatch.setenv('TERM', 'xterm-24bit')
    assert progressbar.env.is_ansi_terminal(fd) is True
    monkeypatch.delenv('TERM')

    monkeypatch.setenv('ANSICON', 'true')
    assert progressbar.env.is_ansi_terminal(fd) is True
    monkeypatch.delenv('ANSICON')
    assert not progressbar.env.is_ansi_terminal(fd)

    def raise_error():
        raise RuntimeError('test')

    fd.isatty = raise_error
    assert not progressbar.env.is_ansi_terminal(fd)


def test_stream_wrapper_unwrap_restores_excepthook() -> None:
    # Regression: C7 - unwrap_stdout/unwrap_stderr left the custom
    # excepthook installed forever.
    wrapper = utils.StreamWrapper()
    hook_before = sys.excepthook
    wrapper.wrap_stdout()
    try:
        wrapper.unwrap_stdout()
        assert sys.excepthook is hook_before

        # With both streams wrapped, the hook is only restored once the
        # last stream is unwrapped
        wrapper.wrap_stdout()
        wrapper.wrap_stderr()
        wrapper.unwrap_stdout()
        # Bound methods are recreated on attribute access, so compare
        # with == instead of `is`
        assert sys.excepthook == wrapper.excepthook
        wrapper.unwrap_stderr()
        assert sys.excepthook is hook_before

        # Same in reverse order: stderr first, then stdout
        wrapper.wrap_stdout()
        wrapper.wrap_stderr()
        wrapper.unwrap_stderr()
        assert sys.excepthook == wrapper.excepthook
        wrapper.unwrap_stdout()
        assert sys.excepthook is hook_before
    finally:
        sys.excepthook = wrapper.original_excepthook
        sys.stdout = wrapper.original_stdout
        sys.stderr = wrapper.original_stderr


def test_stream_wrapper_flush_unsupported_keeps_int_counter() -> None:
    # Regression: C2 - the unsupported-operation handler assigned False
    # to the int wrap counter.
    class UnsupportedIO(io.StringIO):
        def write(self, value: str) -> int:
            raise io.UnsupportedOperation('write')

    wrapper = utils.StreamWrapper()
    wrapper.stdout = utils.WrappingIO(UnsupportedIO())
    wrapper.stdout.buffer.write('x')
    wrapper.wrapped_stdout = 1
    wrapper.flush()

    assert wrapper.wrapped_stdout == 0
    assert type(wrapper.wrapped_stdout) is int


def test_wrapping_io_flush_does_not_duplicate_after_error() -> None:
    # Regression: C3 - a failed target.write() left the buffer intact, so
    # the next flush wrote the same data again.
    class FlakyIO(io.StringIO):
        def __init__(self) -> None:
            super().__init__()
            self.fail_once = True

        def write(self, value: str) -> int:
            result = super().write(value)
            if self.fail_once:
                self.fail_once = False
                raise OSError('disk full')
            return result

    target = FlakyIO()
    wrapped = utils.WrappingIO(target)
    wrapped.buffer.write('hello')
    with pytest.raises(OSError):
        wrapped._flush()
    with contextlib.suppress(OSError):
        wrapped._flush()

    assert target.getvalue().count('hello') == 1


def test_wrapping_io_flush_with_closed_target() -> None:
    # Regression: C4 - flushing into an already closed target (e.g. from
    # the atexit hook at interpreter shutdown) raised ValueError.
    target = io.StringIO()
    wrapped = utils.WrappingIO(target)
    wrapped.buffer.write('data')
    target.close()
    wrapped._flush()  # must not raise
