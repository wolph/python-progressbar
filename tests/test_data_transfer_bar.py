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
