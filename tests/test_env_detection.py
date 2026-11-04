"""Terminal-detection error handling in `progressbar.env`.

`is_ansi_terminal` and `is_terminal` used to wrap their `fd.isatty()`
probing in blanket exception handlers. Only the failures a stream can
legitimately produce — `OSError` (real I/O), `ValueError` (closed or
detached file objects), `AttributeError` (objects without `isatty`) —
may be treated as "not a terminal"; anything else is a bug and must
propagate.
"""

from __future__ import annotations

import enum
import io
import os
import sys
import types
import typing

import pytest

from progressbar import env


class RaisingFd:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def isatty(self) -> bool:
        raise self._error

    def write(self, value: str) -> None:  # pragma: no cover - never called
        pass


class TtyFd:
    def __init__(self, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty

    def write(self, value: str) -> None:  # pragma: no cover - never called
        pass


@pytest.fixture
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ('PROGRESSBAR_IS_TERMINAL', 'ANSICON', 'TERM'):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    'error', [OSError('io'), ValueError('closed'), AttributeError('no tty')]
)
def test_ansi_detection_tolerates_stream_errors(
    error: Exception,
    clean_environment: None,
) -> None:
    fd = typing.cast(typing.IO[str], RaisingFd(error))
    assert env.is_ansi_terminal(fd) is None


def test_ansi_detection_propagates_unexpected_errors(
    clean_environment: None,
) -> None:
    fd = typing.cast(typing.IO[str], RaisingFd(RuntimeError('bug')))
    with pytest.raises(RuntimeError):
        env.is_ansi_terminal(fd)


@pytest.mark.parametrize(
    'error', [OSError('io'), ValueError('closed'), AttributeError('no tty')]
)
def test_is_terminal_tolerates_stream_errors(
    error: Exception,
    clean_environment: None,
) -> None:
    fd = typing.cast(typing.IO[str], RaisingFd(error))
    assert env.is_terminal(fd) is False


def test_is_terminal_propagates_unexpected_errors(
    clean_environment: None,
) -> None:
    fd = typing.cast(typing.IO[str], RaisingFd(RuntimeError('bug')))
    with pytest.raises(RuntimeError):
        env.is_terminal(fd)


def test_is_terminal_plain_tty_without_ansi(clean_environment: None) -> None:
    # A tty that matches no ANSI heuristics is still a terminal: the ANSI
    # probe returns None and the final isatty() fallback decides.
    fd = typing.cast(typing.IO[str], TtyFd(True))
    assert env.is_terminal(fd) is True


def test_is_terminal_non_tty(clean_environment: None) -> None:
    fd = typing.cast(typing.IO[str], TtyFd(False))
    assert env.is_terminal(fd) is False


def test_windows_console_mode_ignored_for_non_tty(
    clean_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The console-mode probe reads the process console, not `fd`: a
    # redirected stream must not be reported as an ANSI terminal just
    # because the console happens to have processed output enabled.
    fake_windows: types.ModuleType = types.ModuleType('fake_windows')

    class FakeFlags(enum.IntFlag):
        ENABLE_PROCESSED_OUTPUT = 1

    def get_console_mode() -> int:  # pragma: no cover - must not be called
        return 1

    fake_windows.WindowsConsoleModeFlags = FakeFlags  # type: ignore[attr-defined]
    fake_windows.get_console_mode = get_console_mode  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules, 'progressbar.terminal.os_specific.windows', fake_windows
    )
    monkeypatch.setattr(
        'progressbar.terminal.os_specific.windows',
        fake_windows,
        raising=False,
    )
    monkeypatch.setattr(os, 'name', 'nt')
    assert env.is_ansi_terminal(io.StringIO()) is not True
