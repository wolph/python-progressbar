from __future__ import print_function

import sys
import time
import signal
import progressbar
from datetime import timedelta


def test_left_justify():
    '''Left justify using the terminal width'''
    p = progressbar.ProgressBar(
        widgets=[progressbar.BouncingBar(marker=progressbar.RotatingMarker())],
        max_value=100, term_width=20, left_justify=True)

    assert p.term_width is not None
    for i in range(100):
        p.update(i)


def test_right_justify():
    '''Right justify using the terminal width'''
    p = progressbar.ProgressBar(
        widgets=[progressbar.BouncingBar(marker=progressbar.RotatingMarker())],
        max_value=100, term_width=20, left_justify=False)

    assert p.term_width is not None
    for i in range(100):
        p.update(i)


def test_auto_width(monkeypatch):
    '''Right justify using the terminal width'''

    def ioctl(*args):
        return '\xbf\x00\xeb\x00\x00\x00\x00\x00'

    def fake_signal(signal, func):
        pass

    try:
        import fcntl
        monkeypatch.setattr(fcntl, 'ioctl', ioctl)
        monkeypatch.setattr(signal, 'signal', fake_signal)
        p = progressbar.ProgressBar(
            widgets=[
                progressbar.BouncingBar(marker=progressbar.RotatingMarker())],
            max_value=100, left_justify=True, term_width=None)

        assert p.term_width is not None
        for i in range(100):
            p.update(i)
    except ImportError:
        pass  # Skip on Windows


def test_fill_right():
    '''Right justify using the terminal width'''
    p = progressbar.ProgressBar(
        widgets=[progressbar.BouncingBar(fill_left=False)],
        max_value=100, term_width=20)

    assert p.term_width is not None
    for i in range(100):
        p.update(i)


def test_fill_left():
    '''Right justify using the terminal width'''
    p = progressbar.ProgressBar(
        widgets=[progressbar.BouncingBar(fill_left=True)],
        max_value=100, term_width=20)

    assert p.term_width is not None
    for i in range(100):
        p.update(i)


def test_no_fill(monkeypatch):
    '''Simply bounce within the terminal width'''
    bar = progressbar.BouncingBar()
    bar.INTERVAL = timedelta(seconds=1)
    p = progressbar.ProgressBar(
        widgets=[bar],
        max_value=progressbar.UnknownLength,
        term_width=20)

    assert p.term_width is not None
    for i in range(30):
        p.update(i, force=True)
        # Fake the start time so we can actually emulate a moving progress bar
        p.start_time = p.start_time - timedelta(seconds=i)


def test_stdout_redirection():
    p = progressbar.ProgressBar(fd=sys.stdout, max_value=10,
                                redirect_stdout=True)

    for i in range(10):
        print('', file=sys.stdout)
        p.update(i)


def test_double_stdout_redirection():
    p = progressbar.ProgressBar(max_value=10, redirect_stdout=True)
    p2 = progressbar.ProgressBar(max_value=10, redirect_stdout=True)

    for i in range(10):
        print('', file=sys.stdout)
        p.update(i)
        p2.update(i)


def test_stderr_redirection():
    p = progressbar.ProgressBar(max_value=10, redirect_stderr=True)

    for i in range(10):
        print('', file=sys.stderr)
        p.update(i)


def test_stdout_stderr_redirection():
    p = progressbar.ProgressBar(max_value=10, redirect_stdout=True,
                                redirect_stderr=True)
    p.start()

    for i in range(10):
        time.sleep(0.01)
        print('', file=sys.stdout)
        print('', file=sys.stderr)
        p.update(i)

    p.finish()


def test_resize(monkeypatch):
    def ioctl(*args):
        return '\xbf\x00\xeb\x00\x00\x00\x00\x00'

    def fake_signal(signal, func):
        pass

    try:
        import fcntl
        monkeypatch.setattr(fcntl, 'ioctl', ioctl)
        monkeypatch.setattr(signal, 'signal', fake_signal)

        p = progressbar.ProgressBar(max_value=10)
        p.start()

        for i in range(10):
            p.update(i)
            p._handle_resize()

        p.finish()
    except ImportError:
        pass  # Skip on Windows

