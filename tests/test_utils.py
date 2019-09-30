import io
import pytest
import progressbar


@pytest.mark.parametrize('value,expected', [
    (None, None),
    ('', None),
    ('1', True),
    ('y', True),
    ('t', True),
    ('yes', True),
    ('true', True),
    ('0', False),
    ('n', False),
    ('f', False),
    ('no', False),
    ('false', False),
])
def test_env_flag(value, expected, monkeypatch):
    if value is not None:
        monkeypatch.setenv('TEST_ENV', value)
    assert progressbar.utils.env_flag('TEST_ENV') == expected

    if value:
        monkeypatch.setenv('TEST_ENV', value.upper())
        assert progressbar.utils.env_flag('TEST_ENV') == expected

    monkeypatch.undo()


def test_is_terminal(monkeypatch):
    fd = io.StringIO()

    monkeypatch.delenv('PROGRESSBAR_IS_TERMINAL', raising=False)
    monkeypatch.delenv('JPY_PARENT_PID', raising=False)

    assert progressbar.utils.is_terminal(fd) is False
    assert progressbar.utils.is_terminal(fd, True) is True
    assert progressbar.utils.is_terminal(fd, False) is False

    monkeypatch.setenv('JPY_PARENT_PID', '123')
    assert progressbar.utils.is_terminal(fd) is True
    monkeypatch.delenv('JPY_PARENT_PID')

    # Sanity check
    assert progressbar.utils.is_terminal(fd) is False

    monkeypatch.setenv('PROGRESSBAR_IS_TERMINAL', 'true')
    assert progressbar.utils.is_terminal(fd) is True
    monkeypatch.setenv('PROGRESSBAR_IS_TERMINAL', 'false')
    assert progressbar.utils.is_terminal(fd) is False
    monkeypatch.delenv('PROGRESSBAR_IS_TERMINAL')

    # Sanity check
    assert progressbar.utils.is_terminal(fd) is False
