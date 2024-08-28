import io

import pytest

import progressbar
import progressbar.env


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
