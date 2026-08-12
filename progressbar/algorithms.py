"""Smoothing algorithms backing `SmoothingETA` and similar widgets.

Both concrete implementations below seed their running state with the
*first* observed value rather than `0`, so an EMA/DEMA-backed ETA doesn't
start out biased toward zero before enough samples have arrived. Both
`update` methods also accept an `elapsed` argument that they currently
ignore -- it's part of the `SmoothingAlgorithm` contract (for algorithms
that might weight by time rather than call count) but neither
implementation here uses it.
"""

from __future__ import annotations

import abc
import typing
from datetime import timedelta


class SmoothingAlgorithm(abc.ABC):
    """Contract for a stateful value smoother fed one sample at a time."""

    @abc.abstractmethod
    def __init__(self, **kwargs: typing.Any):
        """Configure the algorithm.

        Args:
            **kwargs: Algorithm-specific parameters (e.g. `alpha`).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, new_value: float, elapsed: timedelta) -> float:
        """Updates the algorithm with a new value and returns the smoothed
        value.
        """
        raise NotImplementedError


class ExponentialMovingAverage(SmoothingAlgorithm):
    """
    The Exponential Moving Average (EMA) is an exponentially weighted moving
    average that reduces the lag that's typically associated with a simple
    moving average. It's more responsive to recent changes in data.
    """

    def __init__(self, alpha: float = 0.5) -> None:
        """Set the smoothing factor.

        Args:
            alpha: Weight given to the newest observation on each
                `update()` (0-1); higher tracks recent values more
                closely, lower smooths harder.
        """
        self.alpha: float = alpha
        self.value: float | None = None

    def update(self, new_value: float, elapsed: timedelta) -> float:
        """Fold `new_value` into the running average.

        Args:
            new_value: Latest observed value.
            elapsed: Accepted for `SmoothingAlgorithm` compatibility but
                not used by this implementation -- the average is weighted
                by call count, not by wall-clock time.

        Returns:
            The updated EMA.
        """
        if self.value is None:
            # Seed with the first observation instead of biasing towards 0
            self.value = new_value
        else:
            self.value = self.alpha * new_value + (1 - self.alpha) * self.value

        return self.value


class DoubleExponentialMovingAverage(SmoothingAlgorithm):
    """
    The Double Exponential Moving Average (DEMA) is essentially an EMA of an
    EMA, which reduces the lag that's typically associated with a simple EMA.
    It's more responsive to recent changes in data.
    """

    def __init__(self, alpha: float = 0.5) -> None:
        """Set the smoothing factor.

        Args:
            alpha: Weight given to the newest observation in each of the
                two nested EMAs (0-1); higher tracks recent values more
                closely, lower smooths harder.
        """
        self.alpha: float = alpha
        self.ema1: float | None = None
        self.ema2: float | None = None

    def update(self, new_value: float, elapsed: timedelta) -> float:
        """Fold `new_value` into both nested EMAs.

        Args:
            new_value: Latest observed value.
            elapsed: Accepted for `SmoothingAlgorithm` compatibility but
                not used by this implementation -- both EMAs are weighted
                by call count, not by wall-clock time.

        Returns:
            The DEMA estimate, `2 * ema1 - ema2`.
        """
        if self.ema1 is None or self.ema2 is None:
            # Seed with the first observation instead of biasing towards 0
            self.ema1 = self.ema2 = new_value
        else:
            self.ema1 = self.alpha * new_value + (1 - self.alpha) * self.ema1
            self.ema2 = self.alpha * self.ema1 + (1 - self.alpha) * self.ema2

        return 2 * self.ema1 - self.ema2
