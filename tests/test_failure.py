import time
import pytest
import progressbar


def test_missing_format_values():
    with pytest.raises(KeyError):
        p = progressbar.ProgressBar(
            widgets=[progressbar.widgets.FormatLabel('%(x)s')],
        )
        p.update(5)


def test_max_smaller_than_min():
    with pytest.raises(ValueError):
        progressbar.ProgressBar(min_value=10, max_value=5)


def test_no_max_value():
    '''Looping up to 5 without max_value? No problem'''
    p = progressbar.ProgressBar()
    p.start()
    for i in range(5):
        time.sleep(1)
        p.update(i)


def test_correct_max_value():
    '''Looping up to 5 when max_value is 10? No problem'''
    p = progressbar.ProgressBar(max_value=10)
    for i in range(5):
        time.sleep(1)
        p.update(i)


def test_minus_max_value():
    '''negative max_value, shouldn't work'''
    p = progressbar.ProgressBar(min_value=-2, max_value=-1)

    with pytest.raises(ValueError):
        p.update(-1)


def test_zero_max_value():
    '''max_value of zero, it could happen'''
    p = progressbar.ProgressBar(max_value=0)

    p.update(0)
    with pytest.raises(ValueError):
        p.update(1)


def test_one_max_value():
    '''max_value of one, another corner case'''
    p = progressbar.ProgressBar(max_value=1)

    p.update(0)
    p.update(0)
    p.update(1)
    with pytest.raises(ValueError):
        p.update(2)


def test_changing_max_value():
    '''Changing max_value? No problem'''
    p = progressbar.ProgressBar(max_value=10)(range(20), max_value=20)
    for i in p:
        time.sleep(1)


def test_backwards():
    '''progressbar going backwards'''
    p = progressbar.ProgressBar(max_value=1)

    p.update(1)
    p.update(0)


def test_incorrect_max_value():
    '''Looping up to 10 when max_value is 5? This is madness!'''
    p = progressbar.ProgressBar(max_value=5)
    for i in range(5):
        time.sleep(1)
        p.update(i)

    with pytest.raises(ValueError):
        for i in range(5, 10):
            time.sleep(1)
            p.update(i)


def test_deprecated_maxval():
    with pytest.warns(DeprecationWarning):
        progressbar.ProgressBar(maxval=5)


def test_deprecated_poll():
    with pytest.warns(DeprecationWarning):
        progressbar.ProgressBar(poll=5)


def test_unexpected_update_keyword_arg():
    p = progressbar.ProgressBar(max_value=10)
    with pytest.raises(TypeError):
        for i in range(10):
            time.sleep(1)
            p.update(i, foo=10)


def test_variable_not_str():
    with pytest.raises(TypeError):
        progressbar.Variable(1)


def test_variable_too_many_strs():
    with pytest.raises(ValueError):
        progressbar.Variable('too long')
