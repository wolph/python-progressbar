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
