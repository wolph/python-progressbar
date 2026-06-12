import io
import os
import sys

import pytest

if os.name == 'nt':
    pytest.skip('POSIX-only tests', allow_module_level=True)

from progressbar.terminal import os_specific


def test_getch_with_non_tty_stdin(monkeypatch) -> None:
    # Regression: E6 - getch() crashed with termios.error (or
    # io.UnsupportedOperation) when stdin was not a tty.
    monkeypatch.setattr(sys, 'stdin', io.StringIO('x'))
    assert os_specific.getch() == 'x'
