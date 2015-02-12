import pytest
import progressbar


def test_no_maxval():
    '''Looping up to 5 when maxval is 10? No problem'''
    p = progressbar.ProgressBar()
    p.start()
    for i in range(5):
        p.update(i)


def test_correct_maxval():
    '''Looping up to 5 when maxval is 10? No problem'''
    p = progressbar.ProgressBar(maxval=10)
    for i in range(5):
        p.update(i)


def test_minus_maxval():
    '''negative maxval, shouldn't work'''
    p = progressbar.ProgressBar(maxval=-1)

    with pytest.raises(ValueError):
        p.update(-1)


def test_zero_maxval():
    '''maxval of zero, it could happen'''
    p = progressbar.ProgressBar(maxval=0)

    p.update(0)
    with pytest.raises(ValueError):
        p.update(1)


def test_one_maxval():
    '''maxval of one, another corner case'''
    p = progressbar.ProgressBar(maxval=1)

    p.update(0)
    p.update(1)
    with pytest.raises(ValueError):
        p.update(2)


def test_changing_maxval():
    '''Changing maxval? No problem'''
    p = progressbar.ProgressBar(maxval=10)(range(20), maxval=20)
    for i in p:
        pass


def test_backwards():
    '''progressbar going backwards'''
    p = progressbar.ProgressBar(maxval=1)

    p.update(1)
    p.update(0)


def test_incorrect_maxval():
    '''Looping up to 10 when maxval is 5? This is madness!'''
    p = progressbar.ProgressBar(maxval=5)
    for i in range(5):
        p.update(i)

    with pytest.raises(ValueError):
        for i in range(5, 10):
            p.update(i)


