from datetime import timedelta

import pytest

from progressbar import algorithms


def test_ema_initialization() -> None:
    ema = algorithms.ExponentialMovingAverage()
    assert ema.alpha == 0.5
    assert ema.value == 0


@pytest.mark.parametrize(
    'alpha, new_value, expected',
    [
        (0.5, 10, 5),
        (0.1, 20, 2),
        (0.9, 30, 27),
        (0.3, 15, 4.5),
        (0.7, 40, 28),
        (0.5, 0, 0),
        (0.2, 100, 20),
        (0.8, 50, 40),
    ],
)
def test_ema_update(alpha, new_value: float, expected) -> None:
    ema = algorithms.ExponentialMovingAverage(alpha)
    result = ema.update(new_value, timedelta(seconds=1))
    assert result == expected


def test_dema_initialization() -> None:
    dema = algorithms.DoubleExponentialMovingAverage()
    assert dema.alpha == 0.5
    assert dema.ema1 == 0
    assert dema.ema2 == 0


@pytest.mark.parametrize(
    'alpha, new_value, expected',
    [
        (0.5, 10, 7.5),
        (0.1, 20, 3.8),
        (0.9, 30, 29.7),
        (0.3, 15, 7.65),
        (0.5, 0, 0),
        (0.2, 100, 36.0),
        (0.8, 50, 48.0),
    ],
)
def test_dema_update(alpha, new_value: float, expected) -> None:
    dema = algorithms.DoubleExponentialMovingAverage(alpha)
    result = dema.update(new_value, timedelta(seconds=1))
    assert result == expected


# Additional test functions can be added here as needed.
