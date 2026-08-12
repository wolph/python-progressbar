from __future__ import annotations

import importlib
import os
import sys

import pytest

# A platform check, not `importorskip`: this module now imports cleanly on
# every platform -- that is the point of the lazy imports it tests -- so an
# import-failure guard would no longer skip anything on Windows, and
# `getch()` would then hit the genuinely absent `termios` there. Matches the
# convention in `tests/test_os_specific.py`.
if os.name == 'nt':
    pytest.skip('POSIX-only tests', allow_module_level=True)

from progressbar.terminal.os_specific import posix


def test_imports_without_termios(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pyodide and other restricted builds ship no termios module.

    Setting the entry to ``None`` makes ``import termios`` raise
    ``ImportError``, which is what a build lacking the module looks like
    from the importer's point of view.
    """
    monkeypatch.setitem(sys.modules, 'termios', None)
    monkeypatch.setitem(sys.modules, 'tty', None)
    monkeypatch.delitem(
        sys.modules,
        'progressbar.terminal.os_specific.posix',
        raising=False,
    )
    module = importlib.import_module(
        'progressbar.terminal.os_specific.posix',
    )
    assert callable(module.getch)


def test_getch_without_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeStdin:
        def isatty(self) -> bool:
            return False

        def read(self, size: int) -> str:
            return 'x'[:size]

    monkeypatch.setattr(posix.sys, 'stdin', FakeStdin())
    assert posix.getch() == 'x'
