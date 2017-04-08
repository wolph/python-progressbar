import pytest
import progressbar


@pytest.mark.parametrize('total_seconds_elapsed,value,expected', [
    (1, 0, '  0.0 s/B'),
    (1, 0.01, '100.0 s/B'),
    (1, 0.1, '  0.1 B/s'),
    (1, 1, '  1.0 B/s'),
    (1, 2 ** 10 - 1, '1023.0 B/s'),
    (1, 2 ** 10 + 0, '  1.0 KiB/s'),
    (1, 2 ** 20, '  1.0 MiB/s'),
    (1, 2 ** 30, '  1.0 GiB/s'),
    (1, 2 ** 40, '  1.0 TiB/s'),
    (1, 2 ** 50, '  1.0 PiB/s'),
    (1, 2 ** 60, '  1.0 EiB/s'),
    (1, 2 ** 70, '  1.0 ZiB/s'),
    (1, 2 ** 80, '  1.0 YiB/s'),
    (1, 2 ** 90, '1024.0 YiB/s'),
])
def test_file_transfer_speed(total_seconds_elapsed, value, expected):
    widget = progressbar.FileTransferSpeed()
    assert widget(None, dict(
        total_seconds_elapsed=total_seconds_elapsed,
        value=value,
    )) == expected

