import time
import pytest
import progressbar


def test_list():
    '''Progressbar can guess max_value automatically.'''
    p = progressbar.ProgressBar()
    for i in p(range(10)):
        time.sleep(0.001)


def test_iterator_with_max_value():
    '''Progressbar can't guess max_value.'''
    p = progressbar.ProgressBar(max_value=10)
    for i in p((i for i in range(10))):
        time.sleep(0.001)


def test_iterator_without_max_value_error():
    '''Progressbar can't guess max_value.'''
    p = progressbar.ProgressBar()

    for i in p((i for i in range(10))):
        time.sleep(0.001)

    assert p.max_value is progressbar.UnknownLength


def test_iterator_without_max_value():
    '''Progressbar can't guess max_value.'''
    p = progressbar.ProgressBar(widgets=[
        progressbar.AnimatedMarker(),
        progressbar.FormatLabel('%(value)d'),
        progressbar.BouncingBar(),
        progressbar.BouncingBar(marker=progressbar.RotatingMarker()),
    ])
    for i in p((i for i in range(10))):
        time.sleep(0.001)


def test_iterator_with_incorrect_max_value():
    '''Progressbar can't guess max_value.'''
    p = progressbar.ProgressBar(max_value=10)
    with pytest.raises(ValueError):
        for i in p((i for i in range(20))):
            time.sleep(0.001)


def test_adding_value():
    p = progressbar.ProgressBar(max_value=10)
    p.start()
    p.update(5)
    p += 5
    with pytest.raises(ValueError):
        p += 5

