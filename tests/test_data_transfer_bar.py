import progressbar
from progressbar import DataTransferBar


def test_known_length():
    dtb = DataTransferBar().start(max_value=50)
    for i in range(50):
        dtb.update(i)
    dtb.finish()


def test_unknown_length():
    dtb = DataTransferBar().start(max_value=progressbar.UnknownLength)
    for i in range(50):
        dtb.update(i)
    dtb.finish()
