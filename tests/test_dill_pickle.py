import dill  # type: ignore

import progressbar


def test_dill() -> None:
    bar = progressbar.ProgressBar()
    assert bar._started is False
    assert bar._finished is False

    assert dill.pickles(bar) is False

    assert bar._started is False
    # Should be false because it never should have started/initialized
    assert bar._finished is False
