import gc
import io
import logging
import sys
import time

import pytest

import progressbar
from progressbar import utils


def test_missing_format_values(caplog) -> None:
    caplog.set_level(logging.CRITICAL, logger='progressbar.widgets')
    with pytest.raises(KeyError):
        p = progressbar.ProgressBar(
            widgets=[progressbar.widgets.FormatLabel('%(x)s')],
        )
        p.update(5)


def test_max_smaller_than_min() -> None:
    with pytest.raises(ValueError):
        progressbar.ProgressBar(min_value=10, max_value=5)


def test_no_max_value() -> None:
    """Looping up to 5 without max_value? No problem"""
    p = progressbar.ProgressBar()
    p.start()
    for i in range(5):
        time.sleep(1)
        p.update(i)


def test_correct_max_value() -> None:
    """Looping up to 5 when max_value is 10? No problem"""
    p = progressbar.ProgressBar(max_value=10)
    for i in range(5):
        time.sleep(1)
        p.update(i)


def test_minus_max_value() -> None:
    """negative max_value, shouldn't work"""
    p = progressbar.ProgressBar(min_value=-2, max_value=-1)

    with pytest.raises(ValueError):
        p.update(-1)


def test_zero_max_value() -> None:
    """max_value of zero, it could happen"""
    p = progressbar.ProgressBar(max_value=0)

    p.update(0)
    with pytest.raises(ValueError):
        p.update(1)


def test_one_max_value() -> None:
    """max_value of one, another corner case"""
    p = progressbar.ProgressBar(max_value=1)

    p.update(0)
    p.update(0)
    p.update(1)
    with pytest.raises(ValueError):
        p.update(2)


def test_changing_max_value() -> None:
    """Changing max_value? No problem"""
    p = progressbar.ProgressBar(max_value=10)(range(20), max_value=20)
    for _i in p:
        time.sleep(1)


def test_backwards() -> None:
    """progressbar going backwards"""
    p = progressbar.ProgressBar(max_value=1)

    p.update(1)
    p.update(0)


def test_incorrect_max_value() -> None:
    """Looping up to 10 when max_value is 5? This is madness!"""
    p = progressbar.ProgressBar(max_value=5)
    for i in range(5):
        time.sleep(1)
        p.update(i)

    with pytest.raises(ValueError):
        for i in range(5, 10):
            time.sleep(1)
            p.update(i)


def test_deprecated_maxval() -> None:
    with pytest.warns(DeprecationWarning):
        progressbar.ProgressBar(maxval=5)


def test_deprecated_poll() -> None:
    with pytest.warns(DeprecationWarning):
        progressbar.ProgressBar(poll=5)


def test_deprecated_currval() -> None:
    with pytest.warns(DeprecationWarning):
        bar = progressbar.ProgressBar(max_value=5)
        bar.update(2)
        assert bar.currval == 2


def test_unexpected_update_keyword_arg() -> None:
    p = progressbar.ProgressBar(max_value=10)
    with pytest.raises(TypeError):
        for i in range(10):
            time.sleep(1)
            p.update(i, foo=10)


def test_variable_not_str() -> None:
    with pytest.raises(TypeError):
        progressbar.Variable(1)


def test_variable_too_many_strs() -> None:
    with pytest.raises(ValueError):
        progressbar.Variable('too long')


def test_negative_value() -> None:
    bar = progressbar.ProgressBar(max_value=10)
    with pytest.raises(ValueError):
        bar.update(value=-1)


def test_increment() -> None:
    bar = progressbar.ProgressBar(max_value=10)
    bar.increment()
    del bar


def test_unexpected_update_keyword_arg_message() -> None:
    # Regression: A3 - the error message contained the literal text
    # '{key!r}' because the string was not an f-string.
    bar = progressbar.ProgressBar(max_value=10)
    with pytest.raises(TypeError, match='foo'):
        bar.update(1, foo=10)


def test_iterable_interrupt_unwraps_stdout() -> None:
    # Regression #212: when an iterable-wrapped bar (no context manager) is
    # interrupted by an exception in the loop body, the bar must still be
    # finished and sys.stdout must be unwrapped.
    original = sys.stdout
    bar = progressbar.ProgressBar(redirect_stdout=True, fd=io.StringIO())
    with pytest.raises(ValueError):
        for i in bar(range(100)):
            if i == 3:
                raise ValueError('boom')
    gc.collect()
    assert bar._finished
    assert sys.stdout is original
    assert not isinstance(sys.stdout, utils.WrappingIO)


def test_iterable_break_unwraps_stdout() -> None:
    # Regression #212: breaking out of an iterable-wrapped bar must also
    # finish the bar and unwrap sys.stdout.
    original = sys.stdout
    bar = progressbar.ProgressBar(redirect_stdout=True, fd=io.StringIO())
    for i in bar(range(100)):
        if i == 3:
            break
    gc.collect()
    assert bar._finished
    assert sys.stdout is original
    assert not isinstance(sys.stdout, utils.WrappingIO)


def test_iterable_direct_next_still_works() -> None:
    # The generator-based __iter__ must not break direct iterator usage.
    bar = progressbar.ProgressBar(max_value=10, fd=io.StringIO())
    it = bar(range(3))
    assert next(it) == 0
    assert next(it) == 1
