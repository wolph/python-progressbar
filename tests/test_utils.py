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


@pytest.mark.parametrize(
    'value,expected',
    [
        ('', ''),
        (b'', b''),
        ('\x1b[31m', ''),
        (b'\x1b[31m', b''),
        ('\x1b[1m\x1b[31mtext\x1b[0m', 'text'),
        (b'\x1b[1m\x1b[31mtext\x1b[0m', b'text'),
        ('\x1b[38;5;208mhello world\x1b[0m', 'hello world'),
    ],
)
def test_no_color(value, expected) -> None:
    assert progressbar.utils.no_color(value) == expected


def test_no_color_type_error() -> None:
    with pytest.raises(TypeError):
        progressbar.utils.no_color(123)


@pytest.mark.parametrize(
    'value,expected',
    [
        ('', 0),
        (b'', 0),
        ('\x1b[31m', 0),
        ('\x1b[1m\x1b[31mtext\x1b[0m', 4),
        ('\x1b[38;5;208mhello world\x1b[0m', 11),
    ],
)
def test_len_color(value, expected) -> None:
    assert progressbar.utils.len_color(value) == expected


def test_attribute_dict_empty() -> None:
    attrs = progressbar.utils.AttributeDict()
    assert len(attrs) == 0
    with pytest.raises(AttributeError):
        attrs.missing


def test_attribute_dict_set_get_del() -> None:
    attrs = progressbar.utils.AttributeDict()
    attrs.spam = 123
    assert attrs['spam'] == 123
    assert attrs.spam == 123
    del attrs.spam
    with pytest.raises(AttributeError):
        attrs.spam
    with pytest.raises(AttributeError):
        del attrs.spam
