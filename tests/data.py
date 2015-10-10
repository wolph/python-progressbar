import pytest
import progressbar


@pytest.mark.parametrize('value,expected', [
    (None, '  0.0 B'),
    (1, '  1.0 B'),
    (2 ** 10 - 1, '1023.0 B'),
    (2 ** 10 + 0, '  1.0 KiB'),
    (2 ** 20, '  1.0 MiB'),
    (2 ** 30, '  1.0 GiB'),
    (2 ** 40, '  1.0 TiB'),
    (2 ** 50, '  1.0 PiB'),
    (2 ** 60, '  1.0 EiB'),
    (2 ** 70, '  1.0 ZiB'),
    (2 ** 80, '  1.0 YiB'),
    (2 ** 90, '1024.0 YiB'),
])
def test_data_size(value, expected):
    widget = progressbar.DataSize()
    assert widget(None, dict(value=value)) == expected
