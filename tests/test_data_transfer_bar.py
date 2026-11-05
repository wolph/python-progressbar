import io

import progressbar
from progressbar import DataTransferBar


def test_known_length() -> None:
    dtb = DataTransferBar().start(max_value=50)
    for i in range(50):
        dtb.update(i)
    dtb.finish()


def test_unknown_length() -> None:
    dtb = DataTransferBar().start(max_value=progressbar.UnknownLength)
    for i in range(50):
        dtb.update(i)
    dtb.finish()


def test_file_transfer_speed_before_any_data() -> None:
    # Regression: B6 - before any data was transferred the widget
    # rendered '0.0 s/B' using the inverse format.
    widget = progressbar.FileTransferSpeed()
    bar = progressbar.ProgressBar(
        max_value=10, widgets=[widget], fd=io.StringIO(), term_width=60
    )
    bar.start()
    output = widget(bar, bar.data())
    assert 's/' not in output
    bar.finish(dirty=True)


def test_data_size_below_one_byte_keeps_the_bare_unit() -> None:
    # B28: python-utils before 4.1.4 scaled 0.0001 to (0.1024, -1), and
    # the negative power picked the largest prefix ('Yi') off the end
    # of the tuple. The dependency floor must rule that version out.
    widget = progressbar.DataSize()
    bar = progressbar.ProgressBar(
        max_value=10, widgets=[widget], fd=io.StringIO(), term_width=60
    )
    bar.start()
    rendered = widget(bar, {'value': 0.0001})
    bar.finish(dirty=True)
    assert rendered.strip() == '0.0 B'


def test_format_unit_value_below_one_keeps_the_bare_unit() -> None:
    from progressbar.widgets import format_unit_value

    assert format_unit_value(0.0001, unit='B', unit_scale=True) == '0.0 B'
