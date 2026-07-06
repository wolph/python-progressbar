"""Terminal-detection error handling in `progressbar.env`.

`is_ansi_terminal` and `is_terminal` used to wrap their `fd.isatty()`
probing in blanket exception handlers. Only the failures a stream can
legitimately produce — `OSError` (real I/O), `ValueError` (closed or
detached file objects), `AttributeError` (objects without `isatty`) —
may be treated as "not a terminal"; anything else is a bug and must
propagate.
"""

from __future__ import annotations

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
