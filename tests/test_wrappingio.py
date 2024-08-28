import io
import sys

import pytest

from progressbar import utils


def test_wrappingio() -> None:
    # Test the wrapping of our version of sys.stdout`   `   q
    fd = utils.WrappingIO(sys.stdout)
    assert fd.fileno()
    assert not fd.isatty()

    assert not fd.read()
    assert not fd.readline()
    assert not fd.readlines()
    assert fd.readable()

    assert not fd.seek(0)
    assert fd.seekable()
    assert not fd.tell()

    assert not fd.truncate()
    assert fd.writable()
    assert fd.write('test')
    assert not fd.writelines(['test'])

    with pytest.raises(StopIteration):
        next(fd)
    with pytest.raises(StopIteration):
        next(iter(fd))


def test_wrapping_stringio() -> None:
    # Test the wrapping of our version of sys.stdout`   `   q
    string_io = io.StringIO()
    fd = utils.WrappingIO(string_io)
    with fd:
        with pytest.raises(io.UnsupportedOperation):
            fd.fileno()

        assert not fd.isatty()

        assert not fd.read()
        assert not fd.readline()
        assert not fd.readlines()
        assert fd.readable()

        assert not fd.seek(0)
        assert fd.seekable()
        assert not fd.tell()

        assert not fd.truncate()
        assert fd.writable()
        assert fd.write('test')
        assert not fd.writelines(['test'])

        with pytest.raises(StopIteration):
            next(fd)
        with pytest.raises(StopIteration):
            next(iter(fd))
