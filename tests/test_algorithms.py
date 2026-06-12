from datetime import timedelta

import pytest

from progressbar import algorithms


def test_ema_initialization() -> None:
    ema = algorithms.ExponentialMovingAverage()
    assert ema.alpha == 0.5
    assert ema.value is None


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
    # The first update seeds the average, so blending starts from an
    # explicit zero observation: alpha * new_value + (1 - alpha) * 0
    ema = algorithms.ExponentialMovingAverage(alpha)
    ema.update(0, timedelta(seconds=1))
    result = ema.update(new_value, timedelta(seconds=1))
    assert result == expected


def test_dema_initialization() -> None:
    dema = algorithms.DoubleExponentialMovingAverage()
    assert dema.alpha == 0.5
    assert dema.ema1 is None
    assert dema.ema2 is None


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
    # Seeded with an explicit zero observation, a single update yields
    # ema1 = alpha * v, ema2 = alpha^2 * v, so the result is
    # alpha * v * (2 - alpha) which matches the historical values
    dema = algorithms.DoubleExponentialMovingAverage(alpha)
    dema.update(0, timedelta(seconds=1))
    result = dema.update(new_value, timedelta(seconds=1))
    assert result == pytest.approx(expected)


# Additional test functions can be added here as needed.


def test_ema_seeds_from_first_value() -> None:
    # Regression: B8 - the average started at 0, biasing early values
    # toward zero instead of the first observation.
    ema = algorithms.ExponentialMovingAverage(0.5)
    assert ema.update(100, timedelta(seconds=1)) == 100
    assert ema.update(50, timedelta(seconds=1)) == 75


def test_dema_seeds_from_first_value() -> None:
    # Regression: B8 - same zero bias for the double EMA.
    dema = algorithms.DoubleExponentialMovingAverage(0.5)
    assert dema.update(100, timedelta(seconds=1)) == 100
    assert dema.update(50, timedelta(seconds=1)) == 62.5
