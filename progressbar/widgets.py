"""Widget implementations for progress bars.

A widget is a callable rendering one segment of a bar's line. See
:class:`WidgetBase` (fixed-width) and :class:`AutoWidthWidgetBase`
(stretches to fill the remaining space) for the call protocol every
widget implements.
"""

from __future__ import annotations

import abc
import collections.abc
import contextlib
import datetime
import functools
import logging
import typing
from typing import ClassVar

from python_utils import containers, converters

from . import algorithms, base, terminal, utils
from .terminal import colors

if typing.TYPE_CHECKING:
    from .bar import NumberT, ProgressBarMixinBase

logger = logging.getLogger(__name__)

MAX_DATE = datetime.date.max
MAX_TIME = datetime.time.max
MAX_DATETIME = datetime.datetime.max

Data = dict[str, typing.Any]
FormatString = str | None

T = typing.TypeVar('T')


def string_or_lambda(
    input_: str | collections.abc.Callable[..., str],
) -> collections.abc.Callable[..., str]:
    """Turn a `%`-format string into a `(progress, data, width)` renderer.

    A callable `input_` is returned unchanged.
    """
    if isinstance(input_, str):

        def render_input(progress, data, width):
            return input_ % data

        return render_input
    else:
        return input_


def create_wrapper(
    wrapper: str | tuple[str | None, str | None] | None,
) -> str | None:
    """Convert a wrapper tuple or format string to a format string.

    >>> create_wrapper('')

    >>> print(create_wrapper('a{}b'))
    a{}b

    >>> print(create_wrapper(('a', 'b')))
    a{}b
    """
    if isinstance(wrapper, tuple) and len(wrapper) == 2:
        a, b = wrapper
        wrapper = (a or '') + '{}' + (b or '')
    elif not wrapper:
        return None

    if isinstance(wrapper, str):
        if '{}' not in wrapper:
            raise ValueError('Expected string with {} for formatting')
    else:
        raise RuntimeError(  # noqa: TRY004
            'Pass either a begin/end string as a tuple or a template string '
            'with `{}`',
        )

    return wrapper


def wrapper(function, wrapper_):
    """Wrap `function`'s return value using `wrapper_`.

    `wrapper_` is resolved through :func:`create_wrapper`. If that
    yields `None` (no wrapping configured), `function` is returned
    unchanged.
    """
    wrapper_ = create_wrapper(wrapper_)
    if not wrapper_:
        return function

    @functools.wraps(function)
    def wrap(*args: typing.Any, **kwargs: typing.Any):
        return wrapper_.format(function(*args, **kwargs))

    return wrap


def create_marker(
    marker: str | collections.abc.Callable[..., str],
    wrap: str | tuple[str | None, str | None] | None = None,
) -> collections.abc.Callable[..., str]:
    """Build a marker-rendering callable from a character or callable.

    A single-character `marker` string becomes a callable that repeats
    it proportionally to where `progress.value` sits between
    `progress.min_value` and `progress.max_value`, clamped to `width`.
    A callable `marker` is used as-is. Either way, the result is passed
    through :func:`wrapper` so `wrap` still applies.

    Raises:
        ValueError: `marker` is a string that isn't exactly one
            character.
    """
    if isinstance(marker, str):
        # Narrow to ``str`` once, in a fresh local, so the ``_marker`` closure
        # below closes over a plain ``str`` (no cast needed). ``_marker`` is
        # only ever wrapped in this branch.
        marker_str = converters.to_unicode(marker)
        if utils.len_color(marker_str) != 1:
            raise ValueError('Markers are required to be 1 char')

        def _marker(progress, data, width):
            if (
                progress.max_value is not base.UnknownLength
                and progress.max_value > 0
            ):
                # The fill length is based on the progress relative to
                # min_value. The max() guards against a zero range and the
                # min() keeps the marker within the allotted width when the
                # value exceeds max_value (with max_error=False)
                length = min(
                    width,
                    int(
                        (progress.value - progress.min_value)
                        / max(progress.max_value - progress.min_value, 1e-6)
                        * width,
                    ),
                )
                return marker_str * length
            else:
                return marker_str

        return wrapper(_marker, wrap)
    else:
        return wrapper(marker, wrap)


class FormatWidgetMixin:
    """Mixin to format widgets using a %- or `str.format`-style string.

    :py:meth:`~progressbar.bar.ProgressBar.data` is the authoritative
    definition of the keys a `format=` string can reference (`value`,
    `max_value`, `percentage`, the elapsed-time fields, and so on).
    """

    def __init__(
        self, format: str, new_style: bool = False, **kwargs: typing.Any
    ):
        """Store the format string.

        Args:
            format: The template to render with, `%`-style unless
                `new_style` is set.
            new_style: Use `str.format()` semantics instead of `%`.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.new_style = new_style
        self.format = format
        # Cooperative: forward remaining kwargs to the next base. ``format`` is
        # consumed here and deliberately not forwarded onward.
        super().__init__(**kwargs)

    def get_format(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        format: str | None = None,
    ) -> str:
        """Return the format string to render with, default `self.format`."""
        return format or self.format

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        format: str | None = None,
    ) -> str:
        """Formats the widget into a string."""
        format_ = self.get_format(progress, data, format)
        try:
            if self.new_style:
                return format_.format(**data)
            else:
                return format_ % data
        except (TypeError, KeyError):
            logger.exception(
                'Error while formatting %r with data: %r',
                format_,
                data,
            )
            raise


class _WidgetKwargsSink:
    """Terminates cooperative ``__init__`` chains for widgets.

    Absorbs keyword arguments no widget class consumed so a cooperative
    chain never reaches ``object.__init__`` with leftovers. Tolerated
    silently for backwards compatibility: third-party widgets have passed
    stray kwargs to their parents for years.
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        super().__init__()


class WidthWidgetMixin(_WidgetKwargsSink):
    """Hide the widget outside a configured terminal-width range.

    So a progress bar can carry extra decoration that only fits on wide
    terminals without breaking narrow ones.

    Variables available:
     - min_width: Only display the widget if at least `min_width` is left
     - max_width: Only display the widget if at most `max_width` is left

    >>> class Progress:
    ...     term_width = 0

    >>> WidthWidgetMixin(5, 10).check_size(Progress)
    False
    >>> Progress.term_width = 5
    >>> WidthWidgetMixin(5, 10).check_size(Progress)
    True
    >>> Progress.term_width = 10
    >>> WidthWidgetMixin(5, 10).check_size(Progress)
    True
    >>> Progress.term_width = 11
    >>> WidthWidgetMixin(5, 10).check_size(Progress)
    False
    """

    def __init__(
        self,
        min_width: int | None = None,
        max_width: int | None = None,
        **kwargs: typing.Any,
    ):
        """Store the width bounds `check_size` gates on.

        Args:
            min_width: Hide the widget when the terminal is narrower
                than this.
            max_width: Hide the widget when the terminal is wider than
                this.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.min_width = min_width
        self.max_width = max_width
        super().__init__(**kwargs)

    def check_size(self, progress: ProgressBarMixinBase) -> bool:
        """Return whether the widget fits at the current terminal width."""
        max_width = self.max_width
        min_width = self.min_width
        if min_width and min_width > progress.term_width:
            return False
        elif max_width and max_width < progress.term_width:  # noqa: SIM103
            return False
        else:
            return True


class TGradientColors(typing.TypedDict):
    """Shape of `WidgetBase._gradient_colors`: colors by percentage."""

    fg: terminal.OptionalColor
    bg: terminal.OptionalColor


class TFixedColors(typing.TypedDict):
    """Shape of `WidgetBase._fixed_colors`: colors with no percentage."""

    fg_none: terminal.Color | None
    bg_none: terminal.Color | None


class WidgetBase(WidthWidgetMixin, metaclass=abc.ABCMeta):
    """The base class for all widgets.

    The ProgressBar will call the widget's update value when the widget should
    be updated. The widget's size may change between calls, but the widget may
    display incorrectly if the size changes drastically and repeatedly.

    The INTERVAL timedelta informs the ProgressBar that it should be
    updated more often because it is time sensitive.

    The widgets are only visible if the screen is within a
    specified size range so the progressbar fits on both large and small
    screens.

    State specific to one progressbar belongs in `progress.extra` (see
    e.g. `SamplesMixin`) rather than on the widget, which keeps the
    widget stateless: the bar owns the state and clears it on restart.
    Widgets passed via `widgets=` are deep-copied per bar by
    `ProgressBar._copy_widgets` unless they set ``copy = False``, so a
    genuinely shared instance is the exception -- but a widget that
    keeps per-bar state on itself breaks in exactly that case.

    Variables available:
     - min_width: Only display the widget if at least `min_width` is left
     - max_width: Only display the widget if at most `max_width` is left
     - weight: Widgets with a higher `weight` will be calculated before widgets
       with a lower one
     - copy: Copy this widget when initializing the progress bar so the
       progressbar can be reused. Some widgets such as the FormatCustomText
       require the shared state so this needs to be optional

    """

    copy = True

    @abc.abstractmethod
    def __call__(self, progress: ProgressBarMixinBase, data: Data) -> str:
        """Updates the widget.

        progress - a reference to the calling ProgressBar
        """

    # Class-level defaults. Instances may hold their own copy when a
    # ``fixed_colors``/``gradient_colors`` override is passed (copy-on-write in
    # ``__init__``), so these are not ``ClassVar``.
    _fixed_colors: TFixedColors = TFixedColors(
        fg_none=None,
        bg_none=None,
    )
    _gradient_colors: TGradientColors = TGradientColors(
        fg=None,
        bg=None,
    )
    _len: collections.abc.Callable[[str | bytes], int] = len

    @functools.cached_property
    def uses_colors(self):
        """Return whether any fixed or gradient color is configured."""
        for value in self._gradient_colors.values():  # pragma: no branch
            if value is not None:  # pragma: no branch
                return True

        return any(value is not None for value in self._fixed_colors.values())

    def _apply_colors(self, text: str, data: Data) -> str:
        """Wrap `text` in the configured fixed/gradient colors, if any."""
        if self.uses_colors:
            return terminal.apply_colors(
                text,
                data.get('percentage'),
                **self._gradient_colors,
                **self._fixed_colors,
            )
        else:
            return text

    def __init__(
        self,
        *args: typing.Any,
        # Not typed as ``TFixedColors``/``TGradientColors``: callers pass
        # partial overrides (e.g. just ``fg_none``), and a ``TypedDict``'s
        # ``.update()`` only accepts a same-shaped partial, not an
        # arbitrary mapping - so these are deliberately left unannotated
        # rather than typed as something stricter than what's accepted.
        fixed_colors=None,
        gradient_colors=None,
        **kwargs: typing.Any,
    ):
        """Apply optional per-instance color overrides.

        Args:
            fixed_colors: Partial override of `_fixed_colors` (e.g. just
                `fg_none`).
            gradient_colors: Partial override of `_gradient_colors`.
            *args: Forwarded to the next class in the cooperative
                `__init__` chain.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.

        Both overrides are merged on top of the class-level default into
        a fresh per-instance dict rather than mutating it in place, so
        one instance's `fixed_colors`/`gradient_colors` never leaks into
        another instance or subclass sharing the same class default. Any
        cached `uses_colors` is also dropped, so a cooperative `__init__`
        chain that applies colors on a later pass than the one that
        first computed `uses_colors` doesn't keep a stale
        `uses_colors=False` from before the colors were applied.
        """
        if fixed_colors is not None:
            merged_fixed = type(self)._fixed_colors.copy()
            merged_fixed.update(fixed_colors)
            self._fixed_colors = merged_fixed

        if gradient_colors is not None:
            merged_gradient = type(self)._gradient_colors.copy()
            merged_gradient.update(gradient_colors)
            self._gradient_colors = merged_gradient

        # Drop any cached ``uses_colors`` (see the docstring for why).
        vars(self).pop('uses_colors', None)

        if self.uses_colors:
            self._len = utils.len_color

        super().__init__(*args, **kwargs)


class AutoWidthWidgetBase(WidgetBase, metaclass=abc.ABCMeta):
    r"""The base class for all variable width widgets.

    This widget is much like the \hfill command in TeX, it will expand to
    fill the line. You can use more than one in the same line, and they will
    all have the same width, and together will fill the line.

    Called as `widget(progress, data, width)`, receiving the exact pixel
    budget it must fill (see `WidgetBase.__call__` for the fixed-width
    counterpart). It must pad or truncate its own output to exactly
    `width`.
    """

    @abc.abstractmethod
    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        width: int = 0,
    ) -> str:
        """Updates the widget providing the total width the widget must fill.

        progress - a reference to the calling ProgressBar
        width - The total width the widget must fill
        """


class TimeSensitiveWidgetBase(WidgetBase, metaclass=abc.ABCMeta):
    """The base class for all time sensitive widgets.

    Some widgets like timers would become out of date unless updated at least
    every `INTERVAL`
    """

    INTERVAL = datetime.timedelta(milliseconds=100)


class FormatLabel(FormatWidgetMixin, WidgetBase):
    """Displays a formatted label.

    >>> label = FormatLabel('%(value)s', min_width=5, max_width=10)
    >>> class Progress:
    ...     pass
    >>> label = FormatLabel('{value} :: {value:^6}', new_style=True)
    >>> str(label(Progress, dict(value='test')))
    'test ::  test '

    """

    mapping: ClassVar[dict[str, tuple[str, typing.Any]]] = dict(
        finished=('end_time', None),
        last_update=('last_update_time', None),
        max=('max_value', None),
        seconds=('seconds_elapsed', None),
        start=('start_time', None),
        elapsed=('total_seconds_elapsed', utils.format_time),
        value=('value', None),
    )

    def __init__(self, format: str, **kwargs: typing.Any):
        """Create a `FormatLabel` for the given `format` string."""
        super().__init__(format=format, **kwargs)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        format: str | None = None,
    ):
        """Populate `self.mapping`'s aliases into `data`, then format.

        Avoids a per-entry `contextlib.suppress` on the redraw hot path:
        a missing key is the only common "miss", so membership is tested
        directly and only the transform call (which can raise on bad
        values) is guarded with try/except.
        """
        for name, (key, transform) in self.mapping.items():
            if key not in data:
                continue
            if transform is None:
                data[name] = data[key]
            else:
                with contextlib.suppress(ValueError, IndexError):
                    data[name] = transform(data[key])

        return FormatWidgetMixin.__call__(self, progress, data, format)


class Timer(FormatLabel, TimeSensitiveWidgetBase):
    """WidgetBase which displays the elapsed seconds."""

    def __init__(
        self, format='Elapsed Time: %(elapsed)s', **kwargs: typing.Any
    ):
        """Create a `Timer`, rewriting a legacy bare `%s` placeholder.

        Very old configs used a bare `%s` placeholder for the elapsed
        time. It is silently rewritten here to the named `%(elapsed)s`
        form this widget actually formats with.
        """
        if '%s' in format and '%(elapsed)s' not in format:
            format = format.replace('%s', '%(elapsed)s')

        super().__init__(format=format, **kwargs)

    # This is exposed as a static method for backwards compatibility
    format_time = staticmethod(utils.format_time)


class SamplesMixin(TimeSensitiveWidgetBase, metaclass=abc.ABCMeta):
    """Mixin for widgets that average multiple measurements.

    `samples` can be either an integer sample count or a timedelta
    window.

    >>> class progress:
    ...     last_update_time = datetime.datetime.now()
    ...     value = 1
    ...     extra = dict()

    >>> samples = SamplesMixin(samples=2)
    >>> samples(progress, None, True)
    (None, None)
    >>> progress.last_update_time += datetime.timedelta(seconds=1)
    >>> samples(progress, None, True) == (datetime.timedelta(seconds=1), 0)
    True

    >>> progress.last_update_time += datetime.timedelta(seconds=1)
    >>> samples(progress, None, True) == (datetime.timedelta(seconds=1), 0)
    True

    >>> samples = SamplesMixin(samples=datetime.timedelta(seconds=1))
    >>> _, value = samples(progress, None)
    >>> value
    SliceableDeque([1, 1])

    >>> samples(progress, None, True) == (datetime.timedelta(seconds=1), 0)
    True
    """

    def __init__(
        self,
        samples: datetime.timedelta | int = datetime.timedelta(seconds=2),
        key_prefix=None,
        **kwargs,
    ):
        """Configure the sample window.

        Args:
            samples: Either a max sample count, or a `timedelta` window
                measured back from the most recent sample.
            key_prefix: Prefix for the `progress.extra` keys the sample
                deques are stored under. Defaults to the class name so
                sibling widget classes on the same bar don't collide.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.samples = samples
        self.key_prefix = (key_prefix or self.__class__.__name__) + '_'
        super().__init__(**kwargs)

    def get_sample_times(self, progress: ProgressBarMixinBase, data: Data):
        """Return this bar's sample-time deque, creating it if needed.

        Stored on `progress.extra` (keyed by `self.key_prefix`), not on
        `self`, which keeps the widget stateless: the history belongs to
        the bar, so `ProgressBar.init()` clears it when a bar is
        restarted, and a widget instance that does end up shared between
        bars cannot mix their samples together. Widgets passed via
        `widgets=` are deep-copied per bar by
        `ProgressBar._copy_widgets`, so sharing is the exception rather
        than the rule.
        """
        return progress.extra.setdefault(
            f'{self.key_prefix}sample_times',
            containers.SliceableDeque(),
        )

    def get_sample_values(self, progress: ProgressBarMixinBase, data: Data):
        """Return this bar's sample-value deque, creating it if needed.

        See `get_sample_times` for why this lives on `progress.extra`.
        """
        return progress.extra.setdefault(
            f'{self.key_prefix}sample_values',
            containers.SliceableDeque(),
        )

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        delta: bool = False,
    ):
        """Record a sample and return the current rolling window.

        At most once per `INTERVAL`, appends `progress.value` to the
        window and then trims it: by count when `self.samples` is an
        `int`, or by dropping samples older than `self.samples` when
        it's a `timedelta` (always keeping at least the two most recent
        so a delta can still be computed). The window itself lives in
        `progress.extra`, not on the widget. See `get_sample_times` for
        why.

        Args:
            progress: The calling `ProgressBar`.
            data: The `data()` snapshot for this redraw (unused, samples
                are read from `progress` directly).
            delta: If set, return `(delta_time, delta_value)` between
                the oldest and newest sample instead of the raw window,
                or `(None, None)` if the window doesn't span any time
                yet.

        Returns:
            `(sample_times, sample_values)` deques, or the delta tuple
            described above when `delta` is set.
        """
        sample_times = self.get_sample_times(progress, data)
        sample_values = self.get_sample_values(progress, data)

        if sample_times:
            sample_time = sample_times[-1]
        else:
            sample_time = datetime.datetime.min

        if progress.last_update_time - sample_time > self.INTERVAL:
            # Add a sample, then trim the window back to `self.samples`
            sample_times.append(progress.last_update_time)
            sample_values.append(progress.value)

            if isinstance(self.samples, datetime.timedelta):
                minimum_time = progress.last_update_time - self.samples
                while sample_times[2:] and minimum_time > sample_times[1]:
                    sample_times.pop(0)
                    sample_values.pop(0)
            elif len(sample_times) > self.samples:
                sample_times.pop(0)
                sample_values.pop(0)

        if delta:
            if delta_time := sample_times[-1] - sample_times[0]:
                delta_value = sample_values[-1] - sample_values[0]
                return delta_time, delta_value
            else:
                return None, None
        else:
            return sample_times, sample_values


class ETA(Timer):
    """WidgetBase which attempts to estimate the time of arrival."""

    def __init__(
        self,
        format_not_started='ETA:  --:--:--',
        format_finished='Time: %(elapsed)8s',
        format='ETA:  %(eta)8s',
        format_zero='ETA:  00:00:00',
        format_na='ETA:      N/A',
        **kwargs,
    ):
        """Create an `ETA`, rewriting a legacy bare `%s` placeholder.

        Args:
            format_not_started: Format used before any progress has
                been made (`value == min_value`).
            format_finished: Format used once the bar has finished.
            format: Format used once an ETA is available.
            format_zero: Format used when elapsed time is exactly zero.
            format_na: Format used when no ETA can be computed (unknown
                `max_value`).
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.

        Rewrites a legacy bare `%s` placeholder to the named `%(eta)s`
        form (see `Timer.__init__` for the same elapsed-time shim).
        """
        if '%s' in format and '%(eta)s' not in format:
            format = format.replace('%s', '%(eta)s')

        # ``super().__init__`` (Timer) sets ``self.format`` to the
        # elapsed-time default. The ETA-specific ``self.format*`` assignments
        # below MUST stay after it or ETA renders 'Elapsed Time:' not 'ETA:'.
        super().__init__(**kwargs)
        self.format_not_started = format_not_started
        self.format_finished = format_finished
        self.format = format
        self.format_zero = format_zero
        self.format_NA = format_na

    def _calculate_eta(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        value: float,
        elapsed: datetime.timedelta | None,
    ) -> float:
        """Return the estimated remaining seconds, 0 if `elapsed` is falsy."""
        if elapsed:
            # The max() prevents zero division errors. ``value`` is always a
            # number here (``_resolve_value_elapsed`` fills the default).
            per_item = elapsed.total_seconds() / max(value, 1e-6)
            remaining = progress.max_value - data['value']
            return remaining * per_item
        else:
            return 0

    def _resolve_value_elapsed(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        value,
        elapsed,
    ):
        """Fill in the value/elapsed defaults shared by the ETA variants.

        When a caller does not supply them, the per-item rate is based on the
        progress relative to ``min_value`` (not the raw value) and the elapsed
        time is taken from the data snapshot.
        """
        if value is None:
            value = data['value'] - progress.min_value

        if elapsed is None:
            elapsed = data['time_elapsed']

        return value, elapsed

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        value=None,
        elapsed=None,
    ):
        """Render the ETA, choosing one of five formats for the state.

        In order: `format_not_started` (no progress yet),
        `format_finished` (bar is done), `format` (a real ETA was
        computed), `format_NA` (no ETA is computable - unknown
        `max_value`), else `format_zero` (elapsed time is exactly zero).
        """
        value, elapsed = self._resolve_value_elapsed(
            progress, data, value, elapsed
        )

        # Gated on ``elapsed`` too (not just ``max_value``) so an
        # ``elapsed == 0`` call still falls through to ``format_zero``
        # below instead of being reported as N/A.
        eta_na = False
        if elapsed and (
            progress.max_value is None
            or progress.max_value is base.UnknownLength
        ):
            data['eta_seconds'] = None
            eta_na = True
        else:
            data['eta_seconds'] = self._calculate_eta(
                progress,
                data,
                value=value,
                elapsed=elapsed,
            )

        data['eta'] = None
        if data['eta_seconds']:
            with contextlib.suppress(ValueError, OverflowError, OSError):
                data['eta'] = utils.format_time(data['eta_seconds'])

        if data['value'] == progress.min_value:
            fmt = self.format_not_started
        elif progress.end_time:
            fmt = self.format_finished
        elif data['eta']:
            fmt = self.format
        elif eta_na:
            fmt = self.format_NA
        else:
            fmt = self.format_zero

        return Timer.__call__(self, progress, data, format=fmt)


class AbsoluteETA(ETA):
    """Widget which attempts to estimate the absolute time of arrival."""

    def _calculate_eta(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        value: float,
        elapsed: datetime.timedelta | None,
    ) -> datetime.datetime:
        """Convert the relative ETA into an absolute point in time.

        Clamped to `datetime.datetime.max` if adding the estimate would
        overflow.
        """
        eta_seconds = ETA._calculate_eta(self, progress, data, value, elapsed)
        now = datetime.datetime.now()
        try:
            return now + datetime.timedelta(seconds=eta_seconds)
        except OverflowError:  # pragma: no cover
            return datetime.datetime.max

    def __init__(
        self,
        format_not_started='Estimated finish time:  ----/--/-- --:--:--',
        format_finished='Finished at: %(elapsed)s',
        format='Estimated finish time: %(eta)s',
        **kwargs,
    ):
        """Create an `AbsoluteETA` with clock-time-flavoured defaults."""
        super().__init__(
            format_not_started=format_not_started,
            format_finished=format_finished,
            format=format,
            **kwargs,
        )


class AdaptiveETA(ETA, SamplesMixin):
    """WidgetBase which attempts to estimate the time of arrival.

    Uses a sampled average of the speed based on the 10 last updates.
    Very convenient for resuming the progress halfway. For an estimate based
    on an exponential moving average (EMA) of the speed instead of a windowed
    sample, use `SmoothingETA`.
    """

    exponential_smoothing: bool
    exponential_smoothing_factor: float

    def __init__(
        self,
        exponential_smoothing=True,
        exponential_smoothing_factor=0.1,
        **kwargs,
    ):
        """Store exponential-smoothing config.

        Args:
            exponential_smoothing: Accepted for backward compatibility;
                not read by `AdaptiveETA.__call__`, which always
                averages over the sampled window (see `SamplesMixin`).
                Use `SmoothingETA` for an actual EMA-based estimate.
            exponential_smoothing_factor: Same caveat as
                `exponential_smoothing`.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.exponential_smoothing = exponential_smoothing
        self.exponential_smoothing_factor = exponential_smoothing_factor
        super().__init__(**kwargs)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        value=None,
        elapsed=None,
    ):
        """Estimate the ETA from the delta across the sampled window.

        Uses the delta between the oldest and newest sample in
        `SamplesMixin`'s rolling window as the per-item rate. Falls
        back to an unsampled `elapsed=0` (rendering `format_zero`) when
        the window doesn't span any time yet.
        """
        elapsed, value = SamplesMixin.__call__(
            self,
            progress,
            data,
            delta=True,
        )
        if not elapsed:
            value = None
            elapsed = 0

        return ETA.__call__(self, progress, data, value=value, elapsed=elapsed)


class SmoothingETA(ETA):
    """WidgetBase which estimates the ETA from an exponential moving average.

    EMA applies more weight to recent data points and less to older ones,
    and doesn't require storing all past values. This approach works well
    with varying data points and smooths out fluctuations effectively.
    """

    smoothing_algorithm: algorithms.SmoothingAlgorithm
    smoothing_parameters: dict[str, float]

    def __init__(
        self,
        smoothing_algorithm: type[
            algorithms.SmoothingAlgorithm
        ] = algorithms.ExponentialMovingAverage,
        smoothing_parameters: dict[str, float] | None = None,
        **kwargs,
    ):
        """Instantiate the smoothing algorithm.

        Args:
            smoothing_algorithm: `SmoothingAlgorithm` subclass to
                instantiate. Defaults to `ExponentialMovingAverage`.
            smoothing_parameters: Keyword arguments passed to
                `smoothing_algorithm`'s constructor.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.smoothing_parameters = smoothing_parameters or {}
        self.smoothing_algorithm = smoothing_algorithm(
            **self.smoothing_parameters,
        )
        super().__init__(**kwargs)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        value=None,
        elapsed=None,
    ):
        """Smooth `value` through `smoothing_algorithm` before estimating."""
        value, elapsed = self._resolve_value_elapsed(
            progress, data, value, elapsed
        )
        value = self.smoothing_algorithm.update(value, elapsed)
        return ETA.__call__(self, progress, data, value=value, elapsed=elapsed)


class DataSize(FormatWidgetMixin, WidgetBase):
    """Widget for showing an amount of data transferred/processed.

    Automatically formats the value (assumed to be a count of bytes) with an
    appropriate sized unit, based on the IEC binary prefixes (powers of 1024).
    """

    def __init__(
        self,
        variable='value',
        format='%(scaled)5.1f %(prefix)s%(unit)s',
        unit='B',
        prefixes=('', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
        **kwargs,
    ):
        """Create a `DataSize`.

        Args:
            variable: Key in `data` holding the byte count to render.
            format: The template string (see `FormatWidgetMixin`).
            unit: Unit label appended after the IEC prefix.
            prefixes: IEC binary prefixes, smallest (none) to largest.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.variable = variable
        self.unit = unit
        self.prefixes = prefixes
        super().__init__(format=format, **kwargs)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        format: str | None = None,
    ):
        """Scale `data[self.variable]` to the largest fitting IEC prefix."""
        value = data[self.variable]
        if value is not None:
            scaled, power = utils.scale_1024(value, len(self.prefixes))
        else:
            scaled = power = 0

        data['scaled'] = scaled
        data['prefix'] = self.prefixes[power]
        data['unit'] = self.unit

        return FormatWidgetMixin.__call__(self, progress, data, format)


class FileTransferSpeed(FormatWidgetMixin, TimeSensitiveWidgetBase):
    """Widget showing the transfer speed (useful for file transfers)."""

    def __init__(
        self,
        format='%(scaled)5.1f %(prefix)s%(unit)-s/s',
        inverse_format='%(scaled)5.1f s/%(prefix)s%(unit)-s',
        unit='B',
        prefixes=('', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
        **kwargs,
    ):
        """Create a `FileTransferSpeed`.

        Args:
            format: Template used once a speed can be computed.
            inverse_format: Template used for slow transfers (see
                `__call__`), rendering seconds-per-unit instead of
                units-per-second.
            unit: Unit label appended after the IEC prefix.
            prefixes: IEC binary prefixes, smallest (none) to largest.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.unit = unit
        self.prefixes = prefixes
        self.inverse_format = inverse_format
        super().__init__(format=format, **kwargs)

    def _speed(self, value, elapsed):
        """Return `(scaled, power)` for `value` bytes in `elapsed` seconds."""
        speed = float(value) / elapsed
        return utils.scale_1024(speed, len(self.prefixes))

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data,
        value=None,
        total_seconds_elapsed=None,
    ):
        """Updates the widget with the current SI prefixed speed."""
        if value is None:
            value = data['value']

        elapsed = utils.deltas_to_seconds(
            total_seconds_elapsed,
            data['total_seconds_elapsed'],
        )

        if (
            value is not None
            and elapsed is not None
            and elapsed > 2e-6
            and value > 2e-6
        ):  # =~ 0
            scaled, power = self._speed(value, elapsed)
        else:
            scaled = power = 0

        data['unit'] = self.unit
        if power == 0 and 0 < scaled < 0.1:
            # Slow transfers are shown as seconds per unit instead. Note
            # that this is only done when there is actual data. Before the
            # first data arrives the regular format is used.
            data['scaled'] = 1 / scaled
            data['prefix'] = self.prefixes[0]
            return FormatWidgetMixin.__call__(
                self,
                progress,
                data,
                self.inverse_format,
            )
        else:
            data['scaled'] = scaled
            data['prefix'] = self.prefixes[power]
            return FormatWidgetMixin.__call__(self, progress, data)


class AdaptiveTransferSpeed(FileTransferSpeed, SamplesMixin):
    """Widget for showing the transfer speed based on the last X samples."""

    def __init__(self, **kwargs: typing.Any):
        """Create an `AdaptiveTransferSpeed` (see `FileTransferSpeed`)."""
        super().__init__(**kwargs)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data,
        value=None,
        total_seconds_elapsed=None,
    ):
        """Compute speed from the delta across `SamplesMixin`'s window."""
        elapsed, value = SamplesMixin.__call__(
            self,
            progress,
            data,
            delta=True,
        )
        return FileTransferSpeed.__call__(self, progress, data, value, elapsed)


class AnimatedMarker(TimeSensitiveWidgetBase):
    """An animated marker that defaults to appearing as if it were rotating."""

    def __init__(
        self,
        markers: str = '|/-\\',
        default: str | None = None,
        fill: str = '',
        marker_wrap: str | tuple[str | None, str | None] | None = None,
        fill_wrap: str | tuple[str | None, str | None] | None = None,
        **kwargs: typing.Any,
    ):
        """Create an `AnimatedMarker`.

        Args:
            markers: Sequence of single-character frames cycled through
                on every redraw.
            default: Frame shown once finished when `fill` is unset;
                defaults to `markers[0]`.
            fill: Marker character/callable used to pad the frame to
                `width` (see `create_marker`). Unset means no filling.
            marker_wrap: Begin/end strings or template wrapped around
                the marker frame (see `create_wrapper`).
            fill_wrap: Same as `marker_wrap`, for the fill.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.markers = markers
        self.marker_wrap = create_wrapper(marker_wrap)
        self.default = default or markers[0]
        self.fill_wrap = create_wrapper(fill_wrap)
        self.fill = create_marker(fill, self.fill_wrap) if fill else None
        super().__init__(**kwargs)

    def __call__(self, progress: ProgressBarMixinBase, data: Data, width=None):
        """Render the next animation frame, or the finished marker."""
        if progress.end_time:
            # When finished, keep a filling marker full instead of
            # collapsing to a single character. A plain marker has no fill
            # so it falls back to its default character.
            if self.fill:
                return self.fill(progress, data, width)
            return self.default

        marker = self.markers[data['updates'] % len(self.markers)]
        if self.marker_wrap:
            marker = self.marker_wrap.format(marker)

        if self.fill:
            # Cut the last character so we can replace it with our marker
            fill = self.fill(
                progress,
                data,
                width - progress.custom_len(marker),  # type: ignore
            )
        else:
            fill = ''

        # Python 3 returns an int when indexing bytes
        if isinstance(marker, int):  # pragma: no cover
            marker = bytes(marker)
            fill = fill.encode()
        else:
            # cast fill to the same type as marker
            fill = type(marker)(fill)

        return fill + marker  # type: ignore


# Legacy alias for `AnimatedMarker`, kept for backwards compatibility. Kept as
# a plain alias (no DeprecationWarning) until the next major version.
RotatingMarker = AnimatedMarker


class Counter(FormatWidgetMixin, WidgetBase):
    """Displays the current count."""

    def __init__(self, format='%(value)d', **kwargs: typing.Any):
        """Create a `Counter` with the given `format` string."""
        # ``format`` is consumed by ``FormatWidgetMixin``. Do not leak it into
        # the ``WidgetBase`` tail of the cooperative chain.
        super().__init__(format=format, **kwargs)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        format=None,
    ):
        """Render `self.format` (or `format`, if given) against `data`."""
        return FormatWidgetMixin.__call__(self, progress, data, format)


class ColoredMixin:
    """Yellow/gradient color defaults for `Percentage`/`SimpleProgress`."""

    # See ``WidgetBase``: class-level defaults, overridable per instance.
    _fixed_colors: TFixedColors = TFixedColors(
        fg_none=colors.yellow,
        bg_none=None,
    )
    _gradient_colors: TGradientColors = TGradientColors(
        fg=colors.gradient,
        bg=None,
    )


class Percentage(FormatWidgetMixin, ColoredMixin, WidgetBase):
    """Displays the current percentage as a number with a percent sign."""

    def __init__(
        self, format='%(percentage)3d%%', na='N/A%%', **kwargs: typing.Any
    ):
        """Create a `Percentage`.

        Args:
            format: Template used once a percentage is available.
            na: Template used when it isn't (`data['percentage']` is
                `None`).
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.na = na
        super().__init__(format=format, **kwargs)

    def get_format(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        format=None,
    ):
        """Return `self.na`, colored, when no percentage is available yet."""
        # If percentage is not available, display N/A%
        percentage = data.get('percentage', base.Undefined)
        if not percentage and percentage != 0:
            output = self.na
        else:
            output = FormatWidgetMixin.get_format(self, progress, data, format)

        return self._apply_colors(output, data)


UNIT_PREFIXES = ('', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi')
DEFAULT_UNIT = object()


def format_unit_value(
    value: NumberT | type[base.UnknownLength] | None,
    unit: str = 'it',
    unit_scale: bool = False,
) -> str:
    """Render a count with its unit, optionally IEC-scaled.

    Args:
        value: The count to render. `None` or `UnknownLength` renders
            as `'N/A'`.
        unit: Unit label appended after the value (and IEC prefix, if
            `unit_scale`).
        unit_scale: Scale `value` by IEC binary prefixes (`Ki`, `Mi`,
            ...) instead of rendering the raw count.
    """
    if value is None or value is base.UnknownLength:
        return 'N/A'
    value = typing.cast('NumberT', value)
    if unit_scale:
        scaled, power = utils.scale_1024(float(value), len(UNIT_PREFIXES))
        prefix = UNIT_PREFIXES[int(power)]
        return f'{scaled:.1f} {prefix}{unit}'
    if isinstance(value, float):
        return f'{value:g} {unit}'
    return f'{value} {unit}'


class UnitProgress(WidgetBase):
    """Displays progress as a count with an optional unit and 1024 scaling."""

    def __init__(
        self,
        unit=DEFAULT_UNIT,
        unit_scale=DEFAULT_UNIT,
        **kwargs: typing.Any,
    ):
        """Create a `UnitProgress`.

        Args:
            unit: Unit label. Defaults to following `data['unit']`
                (the bar's own `unit=`) rather than a fixed value.
            unit_scale: Whether to IEC-scale the count. Defaults to
                following `data['unit_scale']`.
            **kwargs: Forwarded to `WidgetBase.__init__`.
        """
        self.use_progress_unit = unit is DEFAULT_UNIT
        self.use_progress_unit_scale = unit_scale is DEFAULT_UNIT
        self.unit: str = (
            'it' if unit is DEFAULT_UNIT else typing.cast(str, unit)
        )
        self.unit_scale: bool = (
            False
            if unit_scale is DEFAULT_UNIT
            else typing.cast(bool, unit_scale)
        )
        WidgetBase.__init__(self, **kwargs)

    def __call__(self, progress: ProgressBarMixinBase, data: Data) -> str:
        """Render `'<value> of <max_value>'` in the resolved unit."""
        unit = typing.cast(str, data.get('unit', self.unit))
        unit_scale = typing.cast(bool, data.get('unit_scale', self.unit_scale))
        if not self.use_progress_unit:
            unit = self.unit
        if not self.use_progress_unit_scale:
            unit_scale = self.unit_scale
        value = format_unit_value(data.get('value'), unit, unit_scale)
        max_value = format_unit_value(data.get('max_value'), unit, unit_scale)
        return f'{value} of {max_value}'


class SimpleProgress(FormatWidgetMixin, ColoredMixin, WidgetBase):
    """Returns progress as a count of the total (e.g.: "5 of 47")."""

    max_width_cache: dict[
        str
        | tuple[
            NumberT | type[base.UnknownLength] | None,
            NumberT | type[base.UnknownLength] | None,
        ],
        int | None,
    ]

    DEFAULT_FORMAT = '%(value_s)s of %(max_value_s)s'

    def __init__(self, format=DEFAULT_FORMAT, **kwargs: typing.Any):
        """Create a `SimpleProgress` with the given `format` string."""
        super().__init__(format=format, **kwargs)
        # ``max_width_cache`` reads ``self.max_width``. Keep it after super().
        self.max_width_cache = dict()
        # Pyright isn't happy when we set the key in the initialiser
        self.max_width_cache['default'] = self.max_width or 0

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        format=None,
    ):
        """Render `'<value> of <max_value>'`, padded to a stable width.

        The width is guessed once per `(min_value, max_value)` pair by
        rendering both endpoints and caching the wider of the two in
        `max_width_cache`. Without this, the column would jitter left
        and right as the rendered value's digit count grows (e.g. `9 of
        10` vs `10 of 10`).
        """
        # If max_value is not available, display N/A
        if data.get('max_value'):
            data['max_value_s'] = data['max_value']
        else:
            data['max_value_s'] = 'N/A'

        # if value is not available it's the zeroth iteration
        if data.get('value'):
            data['value_s'] = data['value']
        else:
            data['value_s'] = 0

        formatted = FormatWidgetMixin.__call__(
            self,
            progress,
            data,
            format=format,
        )

        # Guess the maximum width from the min and max value
        key = progress.min_value, progress.max_value
        max_width: int | None = self.max_width_cache.get(
            key,
            self.max_width,
        )
        if not max_width:
            temporary_data = data.copy()
            for value in key:
                if value is None:  # pragma: no cover
                    continue

                temporary_data['value'] = value
                if width := progress.custom_len(  # pragma: no branch
                    FormatWidgetMixin.__call__(
                        self,
                        progress,
                        temporary_data,
                        format=format,
                    ),
                ):
                    max_width = max(max_width or 0, width)

            self.max_width_cache[key] = max_width

        # Adjust the output to have a consistent size in all cases
        if max_width:  # pragma: no branch
            formatted = formatted.rjust(max_width)

        return self._apply_colors(formatted, data)


class Bar(AutoWidthWidgetBase):
    """A progress bar which stretches to fill the line."""

    fg: terminal.OptionalColor = colors.gradient
    bg: terminal.OptionalColor = None

    def __init__(
        self,
        marker='#',
        left='|',
        right='|',
        fill=' ',
        fill_left=True,
        marker_wrap=None,
        **kwargs,
    ):
        """Create the bar with its marker and border characters.

        Args:
            marker: Character, or `(progress, data, width) -> str`
                callable, used for the filled portion.
            left: Character, or callable, used as the left border.
            right: Character, or callable, used as the right border.
            fill: Character used for the empty part of the bar.
            fill_left: Fill/grow from the left. If `False`, from the
                right.
            marker_wrap: Begin/end strings or template wrapped around
                a string `marker` (see `create_wrapper`). Ignored for a
                callable `marker`.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.marker = create_marker(marker, marker_wrap)
        self.left = string_or_lambda(left)
        self.right = string_or_lambda(right)
        self.fill = string_or_lambda(fill)
        self.fill_left = fill_left

        super().__init__(**kwargs)

    def _render_borders(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        width: int,
    ) -> tuple[str, str, int]:
        """Resolve the left/right borders and the width left for the body.

        The borders may be callables, so they are resolved against
        ``progress``/``data`` and their visible length subtracted from
        ``width``. Shared by every :class:`Bar` subclass' ``__call__``.
        """
        left = converters.to_unicode(self.left(progress, data, width))
        right = converters.to_unicode(self.right(progress, data, width))
        width -= progress.custom_len(left) + progress.custom_len(right)
        return left, right, width

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        width: int = 0,
        color: bool = True,
    ):
        """Render the bar: borders, filled marker, and padding to `width`.

        Args:
            progress: The calling `ProgressBar`.
            data: The `data()` snapshot for this redraw.
            width: Exact pixel width to fill (see `AutoWidthWidgetBase`).
            color: Apply `self._apply_colors` to the marker. Callers
                that color the whole line themselves (e.g.
                `FormatLabelBar`) pass `False` to avoid doubling up.
        """
        left, right, width = self._render_borders(progress, data, width)
        marker = converters.to_unicode(self.marker(progress, data, width))
        fill = converters.to_unicode(self.fill(progress, data, width))

        # ``marker`` may contain invisible ANSI color codes (``len()`` counts
        # them, ``custom_len()`` doesn't). Pad ``width`` back out by the
        # difference so the *visible* fill width still comes out right.
        width += len(marker) - progress.custom_len(marker)

        if self.fill_left:
            marker = marker.ljust(width, fill)
        else:
            marker = marker.rjust(width, fill)

        if color:
            marker = self._apply_colors(marker, data)

        return left + marker + right


class ReverseBar(Bar):
    """A bar which has a marker that goes from right to left."""

    def __init__(
        self,
        marker='#',
        left='|',
        right='|',
        fill=' ',
        fill_left=False,
        **kwargs,
    ):
        """Create a `Bar` that fills from the right by default.

        See `Bar.__init__` for parameter meaning. `fill_left` defaults
        to `False` here instead of `True`.
        """
        super().__init__(
            marker=marker,
            left=left,
            right=right,
            fill=fill,
            fill_left=fill_left,
            **kwargs,
        )


class BouncingBar(Bar, TimeSensitiveWidgetBase):
    """A bar which has a marker which bounces from side to side."""

    INTERVAL = datetime.timedelta(milliseconds=100)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        width: int = 0,
        color: bool = True,
    ):
        """Updates the progress bar and its subcomponents."""
        left, right, width = self._render_borders(progress, data, width)
        marker = converters.to_unicode(self.marker(progress, data, width))

        fill = converters.to_unicode(self.fill(progress, data, width))

        if width:  # pragma: no branch
            value = int(
                data['total_seconds_elapsed'] / self.INTERVAL.total_seconds(),
            )

            a = value % width
            b = width - a - 1
            if value % (width * 2) >= width:
                a, b = b, a

            if self.fill_left:
                marker = a * fill + marker + b * fill
            else:
                marker = b * fill + marker + a * fill

        return left + marker + right


class FormatCustomText(FormatWidgetMixin, WidgetBase):
    """A widget that formats its own mapping instead of `data()`.

    Not driven by the bar's progress at all: `update_mapping` lets
    calling code push arbitrary key/value pairs to render, so this acts
    as a free-form status line alongside the bar. `copy = False`
    because its whole point is shared, externally-updated state, unlike
    ordinary widgets (see `WidgetBase`'s `copy` note).
    """

    mapping: dict[str, typing.Any] = dict()  # noqa: RUF012
    copy = False

    def __init__(
        self,
        format: str,
        mapping: dict[str, typing.Any] | None = None,
        **kwargs,
    ):
        """Create a `FormatCustomText`.

        Args:
            format: The template string. Keys come from `self.mapping`,
                not the bar's `data()`.
            mapping: Initial mapping. Defaults to a copy of the class-
                level `mapping` (empty unless a subclass overrides it).
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        # A fresh per-instance dict so update_mapping() never mutates the
        # shared class-level default.
        self.mapping = dict(self.mapping if mapping is None else mapping)
        super().__init__(format=format, **kwargs)

    def update_mapping(self, **mapping: typing.Any):
        """Merge `mapping` into `self.mapping` for the next render."""
        self.mapping.update(mapping)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        format: str | None = None,
    ):
        """Render `self.format` against `self.mapping` (not `data`)."""
        return FormatWidgetMixin.__call__(
            self,
            progress,
            self.mapping,
            format or self.format,
        )


class VariableMixin(_WidgetKwargsSink):
    """Mixin to display a custom user variable."""

    def __init__(self, name, **kwargs: typing.Any):
        """Store the `data['variables']` key this widget reads.

        Args:
            name: A single word, used to look up the value in
                `data['variables']`/`bar.update(name=value)`.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.

        Raises:
            TypeError: `name` isn't a string.
            ValueError: `name` contains whitespace.
        """
        if not isinstance(name, str):
            raise TypeError('Variable(): argument must be a string')
        if len(name.split()) > 1:
            raise ValueError('Variable(): argument must be single word')
        self.name = name
        super().__init__(**kwargs)


class Postfix(VariableMixin, WidgetBase):
    """Displays a live postfix string or key-value mapping."""

    def __init__(
        self,
        name='postfix',
        prefix=' ',
        separator=', ',
        **kwargs: typing.Any,
    ):
        """Create a `Postfix`.

        Args:
            name: `data['variables']` key to read (see `VariableMixin`).
            prefix: Prepended to the rendered value. Empty when the
                value itself is falsy (nothing to show).
            separator: Joins `key=value` pairs when the variable holds
                a `dict`.
            **kwargs: Forwarded to `WidgetBase.__init__`.
        """
        self.prefix = prefix
        self.separator = separator
        VariableMixin.__init__(self, name=name)
        WidgetBase.__init__(self, **kwargs)

    def __call__(self, progress: ProgressBarMixinBase, data: Data) -> str:
        """Render the variable, or `''` if it's unset/empty."""
        value = data['variables'].get(self.name)
        if value is None or (
            isinstance(value, (str, dict, list, set, tuple)) and not value
        ):
            return ''
        if isinstance(value, str):
            rendered = value
        elif isinstance(value, dict):
            rendered = self.separator.join(
                f'{key}={value[key]}' for key in sorted(value)
            )
        else:
            rendered = str(value)
        return f'{self.prefix}{rendered}'


class MultiRangeBar(Bar, VariableMixin):
    """A bar with multiple sub-ranges, each represented by a different symbol.

    The various ranges are represented on a user-defined variable, formatted as

    .. code-block:: python

        [['Symbol1', amount1], ['Symbol2', amount2], ...]
    """

    def __init__(self, name, markers, **kwargs: typing.Any):
        """Create a `MultiRangeBar`.

        Args:
            name: `data['variables']` key holding the range amounts
                (see `VariableMixin`).
            markers: One single-character marker (or callable, see
                `string_or_lambda`) per range, in the same order as the
                amounts in `data['variables'][name]`.
            **kwargs: Forwarded to `Bar.__init__`.
        """
        # ``name`` rides through Bar's cooperative chain to VariableMixin.
        super().__init__(name=name, **kwargs)
        self.markers = [string_or_lambda(marker) for marker in markers]

    def get_values(self, progress: ProgressBarMixinBase, data: Data):
        """Return the configured `[amount, ...]` list, or `[]` if unset."""
        return data['variables'][self.name] or []

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        width: int = 0,
        color: bool = True,
    ):
        """Render each range's share of `width` in its own marker.

        Args:
            progress: The calling `ProgressBar`.
            data: The `data()` snapshot for this redraw.
            width: Exact pixel width to fill.
            color: Unused here (ranges aren't colored). Kept for
                signature compatibility with `Bar.__call__`.
        """
        left, right, width = self._render_borders(progress, data, width)
        values = self.get_values(progress, data)

        values_sum = sum(values)
        if width and values_sum:
            middle = ''
            values_accumulated = 0
            width_accumulated = 0
            for marker, value in zip(self.markers, values, strict=False):
                marker = converters.to_unicode(marker(progress, data, width))
                if progress.custom_len(marker) != 1:
                    raise ValueError('Markers are required to be 1 char')

                values_accumulated += value
                item_width = int(values_accumulated / values_sum * width)
                item_width -= width_accumulated
                width_accumulated += item_width
                middle += item_width * marker
        else:
            fill = converters.to_unicode(self.fill(progress, data, width))
            if progress.custom_len(fill) != 1:
                raise ValueError(
                    f'Fill is required to be 1 char, got {fill!r}'
                )
            middle = fill * width

        return left + middle + right


class MultiProgressBar(MultiRangeBar):
    """A bar summarising many sub-progresses as a per-marker histogram.

    `data['variables'][name]` holds one entry per sub-progress, each
    either a `0..1` fraction or a `(value, max)` pair. `get_values`
    buckets them into `len(markers)` histogram slots (see its
    docstring for the bucketing rule).
    """

    def __init__(
        self,
        name,
        # NOTE: the markers are not whitespace even though some
        # terminals don't show the characters correctly!
        markers=' ▁▂▃▄▅▆▇█',
        **kwargs,
    ):
        """Create a `MultiProgressBar`.

        Args:
            name: `data['variables']` key holding the sub-progress list
                (see the class docstring).
            markers: Ascending-height marker characters, sparsest (0%)
                to fullest (100%). Reversed internally to match
                `MultiRangeBar`'s marker order.
            **kwargs: Forwarded to `MultiRangeBar.__init__`.
        """
        super().__init__(
            name=name,
            markers=list(reversed(markers)),
            **kwargs,
        )

    def get_values(self, progress: ProgressBarMixinBase, data: Data):
        """Bucket each sub-progress fraction into the marker histogram.

        Each value maps to a position along `len(markers) - 1` slots;
        since that position is usually fractional, it spills across its
        two neighbouring slots weighted by how close it lands to each
        (e.g. a value 30% of the way from slot 2 to slot 3 adds 0.7 to
        slot 2's count and 0.3 to slot 3's), so the histogram reflects
        fractional progress rather than rounding every value to its
        nearest marker.
        """
        ranges = [0.0] * len(self.markers)
        for value in data['variables'][self.name] or []:
            if not isinstance(value, (int, float)):
                # Progress is (value, max). A zero maximum means the total
                # is not known (yet), so no progress can be shown.
                progress_value, progress_max = value
                if progress_max:
                    value = float(progress_value) / float(progress_max)
                else:
                    value = 0.0

            if not 0 <= value <= 1:
                raise ValueError(
                    'Range value needs to be in the range [0..1], '
                    f'got {value}',
                )

            range_ = value * (len(ranges) - 1)
            pos = int(range_)
            frac = range_ % 1
            ranges[pos] += 1 - frac
            if frac:
                ranges[pos + 1] += frac

        if self.fill_left:  # pragma: no branch
            ranges = list(reversed(ranges))

        return ranges


class GranularMarkers:
    """Preset marker strings for `GranularBar`, sparsest to fullest."""

    smooth = ' ▏▎▍▌▋▊▉█'
    bar = ' ▁▂▃▄▅▆▇█'
    snake = ' ▖▌▛█'
    fade_in = ' ░▒▓█'
    dots = ' ⡀⡄⡆⡇⣇⣧⣷⣿'
    growing_circles = ' .oO'


class GranularBar(AutoWidthWidgetBase):
    """A progressbar with sub-character granularity via multiple markers.

    Examples of markers:
     - Smooth: ` ▏▎▍▌▋▊▉█` (default)
     - Bar: ` ▁▂▃▄▅▆▇█`
     - Snake: ` ▖▌▛█`
     - Fade in: ` ░▒▓█`
     - Dots: ` ⡀⡄⡆⡇⣇⣧⣷⣿`
     - Growing circles: ` .oO`

    The markers can be accessed through GranularMarkers. GranularMarkers.dots
    for example
    """

    def __init__(
        self,
        markers=GranularMarkers.smooth,
        left='|',
        right='|',
        **kwargs,
    ):
        """Create a `GranularBar` with its marker ramp and borders.

        Args:
            markers: String of characters to use as granular progress
                markers. The first character should represent 0% and
                the last 100%. Ex: ` .oO`.
            left: String or callable object to use as a left border.
            right: String or callable object to use as a right border.
            **kwargs: Forwarded to `AutoWidthWidgetBase.__init__`.
        """
        self.markers = markers
        self.left = string_or_lambda(left)
        self.right = string_or_lambda(right)

        super().__init__(**kwargs)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        width: int = 0,
    ):
        """Render the bar at sub-character granularity.

        The filled width in fractional characters (`num_chars`) splits
        into whole columns rendered with `markers[-1]` and, if there's
        a fractional remainder, one partial column chosen from
        `markers` by how far into it progress has reached.
        """
        # `GranularBar` descends from `AutoWidthWidgetBase`, not `Bar`, so
        # it can't reach `Bar._render_borders`. The border preamble below
        # is intentionally duplicated rather than hoisting that helper onto
        # a shared base that width-only widgets would inherit.
        left = converters.to_unicode(self.left(progress, data, width))
        right = converters.to_unicode(self.right(progress, data, width))
        width -= progress.custom_len(left) + progress.custom_len(right)

        max_value = progress.max_value
        if (
            max_value is not base.UnknownLength
            and typing.cast(float, max_value) > 0
        ):
            percent = progress.value / max_value  # type: ignore
        else:
            percent = 0

        num_chars = percent * width

        marker = self.markers[-1] * int(num_chars)

        if marker_idx := int((num_chars % 1) * (len(self.markers) - 1)):
            marker += self.markers[marker_idx]

        marker = converters.to_unicode(marker)

        # Make sure we ignore invisible characters when filling
        width += len(marker) - progress.custom_len(marker)
        marker = marker.ljust(width, self.markers[0])

        return left + marker + right


class FormatLabelBar(FormatLabel, Bar):
    """A bar which has a formatted label in the center."""

    def __init__(self, format, **kwargs: typing.Any):
        """Create a `FormatLabelBar` with the given `format` string.

        Args:
            format: The label template (see `FormatLabel`).
            **kwargs: Forwarded to `Bar.__init__`.
        """
        super().__init__(format=format, **kwargs)

    def __call__(  # type: ignore
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        width: int = 0,
        format: FormatString = None,
    ):
        """Render the bar with the formatted label centred over it."""
        center = FormatLabel.__call__(self, progress, data, format=format)
        bar = Bar.__call__(self, progress, data, width, color=False)

        # Aligns the center of the label to the center of the bar
        center_len = progress.custom_len(center)
        center_left = int((width - center_len) / 2)
        center_right = center_left + center_len

        return (
            self._apply_colors(
                bar[:center_left],
                data,
            )
            + self._apply_colors(
                center,
                data,
            )
            + self._apply_colors(
                bar[center_right:],
                data,
            )
        )


class PercentageLabelBar(Percentage, FormatLabelBar):
    """A bar which displays the current percentage in the center."""

    # %3d adds an extra space that makes it look off-center
    # %2d keeps the label somewhat consistently in-place
    def __init__(
        self, format='%(percentage)2d%%', na='N/A%%', **kwargs: typing.Any
    ):
        """Create a `PercentageLabelBar`.

        Args:
            format: The percentage template (see `Percentage`). Uses
                `%2d` rather than `Percentage`'s default `%3d`, which
                adds a padding space that looks off-centre here.
            na: Template used when no percentage is available.
            **kwargs: Forwarded to `FormatLabelBar.__init__`.
        """
        super().__init__(format=format, na=na, **kwargs)

    def __call__(  # type: ignore
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        width: int = 0,
        format: FormatString = None,
    ):
        """Render the bar with the percentage centred over it."""
        return super().__call__(progress, data, width, format=format)


class Variable(FormatWidgetMixin, VariableMixin, WidgetBase):
    """Displays a custom variable."""

    def __init__(
        self,
        name,
        format='{name}: {formatted_value}',
        width=6,
        precision=3,
        **kwargs,
    ):
        """Create a `Variable` rendering the bar variable `name`.

        Args:
            name: `data['variables']` key to read (see `VariableMixin`).
            format: `str.format()` template. Besides the usual keys it
                gets `name`, `value`, `width`, `precision`, and
                `formatted_value` (`value` formatted per `width`/
                `precision` if numeric, else `'-' * width` if falsy).
            width: Minimum field width used to format a numeric value.
            precision: Decimal precision used to format a numeric
                value.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.width = width
        self.precision = precision
        # FormatWidgetMixin (first in the MRO) now sets ``self.format``;
        # ``name`` rides the cooperative chain to VariableMixin.
        super().__init__(name=name, format=format, **kwargs)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        format: str | None = None,
    ):
        """Render `self.format` with the variable's value substituted in."""
        value = data['variables'][self.name]
        context = data.copy()
        context['value'] = value
        context['name'] = self.name
        context['width'] = self.width
        context['precision'] = self.precision

        try:
            # Cast first: a precision is not allowed in an integer
            # format specifier, so formatting an int with `.precision`
            # raises ValueError. This is a long-standing format-spec
            # rule, not a recent Python change.
            value = float(value)
            fmt = '{value:{width}.{precision}}'
            context['formatted_value'] = fmt.format(**context)
        except (TypeError, ValueError):
            if value:
                context['formatted_value'] = '{value:{width}}'.format(
                    **context,
                )
            else:
                context['formatted_value'] = '-' * self.width

        return self.format.format(**context)


class DynamicMessage(Variable):
    """Legacy alias for `Variable`. Prefer `Variable` in new code.

    Kept as a plain subclass (no DeprecationWarning) until the next major
    version.
    """


class CurrentTime(FormatWidgetMixin, TimeSensitiveWidgetBase):
    """Widget which displays the current (date)time with seconds resolution."""

    INTERVAL = datetime.timedelta(seconds=1)

    def __init__(
        self,
        format='Current Time: %(current_time)s',
        microseconds=False,
        **kwargs,
    ):
        """Create a `CurrentTime`.

        Args:
            format: Template string. Adds `current_time`/
                `current_datetime` keys on top of the usual `data()`
                set.
            microseconds: Keep microsecond resolution instead of
                truncating to whole seconds.
            **kwargs: Forwarded to the next class in the cooperative
                `__init__` chain.
        """
        self.microseconds = microseconds
        super().__init__(format=format, **kwargs)

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        format: str | None = None,
    ):
        """Stamp `current_time`/`current_datetime` into `data`, then format."""
        data['current_time'] = self.current_time()
        data['current_datetime'] = self.current_datetime()

        return FormatWidgetMixin.__call__(self, progress, data, format=format)

    def current_datetime(self):
        """Return `datetime.now()`, seconds-truncated unless `microseconds`."""
        now = datetime.datetime.now()
        if not self.microseconds:
            now = now.replace(microsecond=0)

        return now

    def current_time(self):
        """Return `self.current_datetime()`'s time-of-day component."""
        return self.current_datetime().time()


class JobStatusBar(Bar, VariableMixin):
    """Widget which displays the job status as markers on the bar.

    The status updates can be given either as a boolean or as a string. If it's
    a string, it will be displayed as-is. If it's a boolean, it will be
    displayed as a marker (default: '█' for success, 'X' for failure)
    configurable through the `success_marker` and `failure_marker`
    parameters. See `__init__` for the full parameter list.
    """

    success_fg_color: terminal.Color | None = colors.green
    success_bg_color: terminal.Color | None = None
    success_marker: str = '█'
    failure_fg_color: terminal.Color | None = colors.red
    failure_bg_color: terminal.Color | None = None
    failure_marker: str = 'X'
    job_markers: list[str]
    """Unused, retained for backwards compatibility only.

    Per-run marker state lives in ``progress.extra`` instead (see
    :py:meth:`get_job_markers`).
    """

    def __init__(
        self,
        name: str,
        left='|',
        right='|',
        fill=' ',
        fill_left=True,
        success_fg_color=colors.green,
        success_bg_color=None,
        success_marker='█',
        failure_fg_color=colors.red,
        failure_bg_color=None,
        failure_marker='X',
        **kwargs,
    ):
        """Create a `JobStatusBar`.

        Args:
            name: `data['variables']` key holding each status update.
            left: The left border of the bar.
            right: The right border of the bar.
            fill: The fill character of the bar.
            fill_left: Whether to fill the bar from the left or the
                right.
            success_fg_color: Foreground color for successful jobs.
            success_bg_color: Background color for successful jobs.
            success_marker: Marker character for successful jobs.
            failure_fg_color: Foreground color for failed jobs.
            failure_bg_color: Background color for failed jobs.
            failure_marker: Marker character for failed jobs.
            **kwargs: Forwarded to `Bar.__init__`.
        """
        # Retained for backward compatibility only. Render state now lives
        # in ``progress.extra`` (see get_job_markers), keyed per bar.
        self.job_markers = []
        # Unique per-widget key so multiple JobStatusBars on the same bar do
        # not share storage either.
        self._markers_key = f'{type(self).__name__}_{id(self)}_job_markers'
        self.success_fg_color = success_fg_color
        self.success_bg_color = success_bg_color
        self.success_marker = success_marker
        self.failure_fg_color = failure_fg_color
        self.failure_bg_color = failure_bg_color
        self.failure_marker = failure_marker

        # ``name`` rides Bar's cooperative chain to VariableMixin (which also
        # validates it). Bar re-sets left/right/fill from the same values.
        super().__init__(
            name=name,
            left=left,
            right=right,
            fill=fill,
            fill_left=fill_left,
            **kwargs,
        )

    def get_job_markers(self, progress: ProgressBarMixinBase) -> list[str]:
        """Return this bar's colored marker history, creating it if needed.

        Per-bar marker history, following `SamplesMixin`'s
        `progress.extra` pattern so the widget itself stays stateless;
        see `SamplesMixin.get_sample_times` for why that matters.
        """
        return progress.extra.setdefault(self._markers_key, [])

    def __call__(
        self,
        progress: ProgressBarMixinBase,
        data: Data,
        width: int = 0,
        color: bool = True,
    ):
        """Append the latest status marker, evicting old ones to fit `width`.

        Args:
            progress: The calling `ProgressBar`.
            data: The `data()` snapshot for this redraw.
            width: Exact pixel width to fill.
            color: Unused (markers are always colored by success/
                failure). Kept for signature compatibility with
                `Bar.__call__`.

        Each new marker is colored before being stored, so eviction
        compares `progress.custom_len` (which strips ANSI color codes)
        of the joined markers against `width` and drops the oldest
        marker until the *visible* history fits, regardless of how much
        color escape-code overhead it carries.
        """
        left, right, width = self._render_borders(progress, data, width)

        status: str | bool | None = data['variables'].get(self.name)

        if width and status is not None:
            if status is True:
                marker = self.success_marker
                fg_color = self.success_fg_color
                bg_color = self.success_bg_color
            elif status is False:  # pragma: no branch
                marker = self.failure_marker
                fg_color = self.failure_fg_color
                bg_color = self.failure_bg_color
            else:  # pragma: no cover
                marker = status
                fg_color = bg_color = None

            marker = converters.to_unicode(marker)
            if fg_color:  # pragma: no branch
                marker = fg_color.fg(marker)
            if bg_color:  # pragma: no cover
                marker = bg_color.bg(marker)

            job_markers = self.get_job_markers(progress)
            job_markers.append(marker)
            # Drop the oldest markers when they no longer fit the
            # available width
            while (
                len(job_markers) > 1
                and progress.custom_len(''.join(job_markers)) > width
            ):
                job_markers.pop(0)

            marker = ''.join(job_markers)
            width -= progress.custom_len(marker)

            fill = converters.to_unicode(self.fill(progress, data, width))
            fill = self._apply_colors(fill * max(width, 0), data)

            if self.fill_left:  # pragma: no branch
                marker += fill
            else:  # pragma: no cover
                marker = fill + marker
        else:
            marker = ''

        return left + marker + right
