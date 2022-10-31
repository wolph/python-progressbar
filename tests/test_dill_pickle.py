import pickle

import dill

import progressbar


def test_dill():
    bar = progressbar.ProgressBar()
    assert bar._started == False
    assert bar._finished == False

    assert not dill.pickles(bar)

    assert bar._started == False
    # Should be false because it never should have started/initialized
    assert bar._finished == False
