"""The deprecation warnings must point at the caller, not at progressbar.

A warning attributed to `progressbar/bar.py` tells the user nothing about
which of their own lines used the deprecated name. Each test below records
the warning and checks that it lands in this file, on the line that used
`maxval`, `poll` or `currval`, whatever the depth of the `__init__` chain
in between.
"""

from __future__ import annotations

import sys
import typing
import warnings

import progressbar


def _line_before() -> int:
    """Return the line number of the statement above the calling line."""
    return sys._getframe(1).f_lineno - 1


def _single_deprecation(
    caught: list[warnings.WarningMessage],
) -> warnings.WarningMessage:
    assert len(caught) == 1
    assert caught[0].category is DeprecationWarning
    return caught[0]


class _BarWithOwnInit(progressbar.ProgressBar):
    """A user subclass that adds one frame between the caller and the bar."""

    super_call_line: int

    def __init__(self, **kwargs: typing.Any) -> None:
        super().__init__(**kwargs)
        self.super_call_line = _line_before()


def test_maxval_warning_points_at_caller() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', DeprecationWarning)
        progressbar.ProgressBar(maxval=10)
        expected_line: int = _line_before()

    warning: warnings.WarningMessage = _single_deprecation(caught)
    assert warning.filename == __file__
    assert warning.lineno == expected_line


def test_poll_warning_points_at_caller() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', DeprecationWarning)
        progressbar.ProgressBar(poll=1)
        expected_line: int = _line_before()

    warning: warnings.WarningMessage = _single_deprecation(caught)
    assert warning.filename == __file__
    assert warning.lineno == expected_line


def test_currval_warning_points_at_caller() -> None:
    bar: progressbar.ProgressBar = progressbar.ProgressBar(max_value=10)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', DeprecationWarning)
        assert bar.currval == 0
        expected_line: int = _line_before()

    warning: warnings.WarningMessage = _single_deprecation(caught)
    assert warning.filename == __file__
    assert warning.lineno == expected_line


def test_subclass_maxval_warning_points_at_caller() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', DeprecationWarning)
        progressbar.DataTransferBar(maxval=10)
        expected_line: int = _line_before()

    warning: warnings.WarningMessage = _single_deprecation(caught)
    assert warning.filename == __file__
    assert warning.lineno == expected_line


def test_user_subclass_init_warning_points_at_super_call() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', DeprecationWarning)
        bar: _BarWithOwnInit = _BarWithOwnInit(maxval=10)

    warning: warnings.WarningMessage = _single_deprecation(caught)
    assert warning.filename == __file__
    assert warning.lineno == bar.super_call_line
