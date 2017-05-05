import sys
import progressbar


def test_nowrap():
    stdout = sys.stdout
    stderr = sys.stderr

    progressbar.streams.wrap()

    assert stdout == sys.stdout
    assert stderr == sys.stderr

    progressbar.streams.unwrap()

    assert stdout == sys.stdout
    assert stderr == sys.stderr


def test_wrap():
    stdout = sys.stdout
    stderr = sys.stderr

    progressbar.streams.wrap(stderr=True, stdout=True)

    assert stdout != sys.stdout
    assert stderr != sys.stderr

    # Wrap again
    stdout = sys.stdout
    stderr = sys.stderr

    progressbar.streams.wrap(stderr=True, stdout=True)

    assert stdout == sys.stdout
    assert stderr == sys.stderr

    progressbar.streams.unwrap(stderr=True, stdout=True)
    progressbar.streams.unwrap(stderr=True, stdout=True)
    progressbar.streams.unwrap(stderr=True, stdout=True)
