"""ANSI/SGR terminal primitives and the color model.

Defines the CSI/SGR escape-sequence helpers, the RGB/HSL/Color/
ColorGradient color model, and `apply_colors`, the entry point
`WidgetBase._apply_colors` uses to turn a percentage plus
foreground/background colors into a styled string.

Every non-underscore name here is re-exported by
`progressbar.terminal` (``from .base import *``, no ``__all__``),
so it is part of the public `progressbar.terminal` surface.
"""

from __future__ import annotations

import abc
import collections.abc
import colorsys
import enum
import typing
from collections import defaultdict

# Ruff is being stupid and doesn't understand `ClassVar` if it comes from the
# `types` module
from typing import ClassVar

from python_utils import converters

from .. import (
    base as pbase,
    env,
)

# Re-exported for backwards compatibility (previously consumed by the removed
# ``_CPR`` cursor-position helper, guarded by the API snapshot). The redundant
# alias marks the re-export as intentional so it is not stripped as unused.
from .os_specific import getch as getch

#: ANSI escape character (``\x1b``), the CSI/SGR sequence prefix.
ESC = '\x1b'


class CSI:
    """A single ANSI CSI (Control Sequence Introducer) escape sequence.

    Wraps one CSI final byte/code (e.g. ``'H'`` for Cursor Position)
    and renders it as ``ESC [ args code``. Calling the instance with
    no arguments falls back to the default argument(s) supplied at
    construction.
    """

    _code: str
    _template = ESC + '[{args}{code}'

    def __init__(self, code: str, *default_args: typing.Any) -> None:
        """Store the final byte/code and its default argument(s).

        Args:
            code: The CSI final byte(s) appended after the argument
                list, e.g. ``'H'`` for Cursor Position.
            *default_args: Arguments used when the instance is
                called without any, e.g. ``(1, 1)`` for CUP's
                default row/column.
        """
        self._code = code
        self._default_args = default_args

    def __call__(self, *args: typing.Any) -> str:
        r"""Render the escape sequence for the given arguments.

        Args:
            *args: Numeric CSI parameters. Falls back to the
                default arguments given at construction when
                omitted.

        Returns:
            The full escape sequence, e.g. ``'\x1b[1;1H'``.
        """
        return self._template.format(
            args=';'.join(map(str, args or self._default_args)),
            code=self._code,
        )

    def __str__(self) -> str:
        """Render using the default arguments (see `__call__`)."""
        return self()


class CSINoArg(CSI):
    """A `CSI` whose escape sequence never takes parameters.

    Narrows `__call__` to accept no arguments, since sequences such
    as `HIDE_CURSOR` (``?25l``) are parameterless. The base
    `CSI.__call__` signature would otherwise let callers pass values
    that are silently ignored (falling back to the default
    arguments).
    """

    def __call__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
    ) -> str:
        """Render the escape sequence using the default arguments."""
        return super().__call__()


#: Cursor Position [row;column] (default = [1,1])
CUP: CSI = CSI('H', 1, 1)

#: Cursor Up Ps Times (default = 1) (CUU)
UP: CSI = CSI('A', 1)

#: Cursor Down Ps Times (default = 1) (CUD)
DOWN: CSI = CSI('B', 1)

#: Cursor Forward Ps Times (default = 1) (CUF)
RIGHT: CSI = CSI('C', 1)

#: Cursor Backward Ps Times (default = 1) (CUB)
LEFT: CSI = CSI('D', 1)

#: Cursor Next Line Ps Times (default = 1) (CNL)
#: Same as Cursor Down Ps Times
NEXT_LINE: CSI = CSI('E', 1)

#: Cursor Preceding Line Ps Times (default = 1) (CPL)
#: Same as Cursor Up Ps Times
PREVIOUS_LINE: CSI = CSI('F', 1)

#: Cursor Character Absolute  [column] (default = [row,1]) (CHA)
COLUMN: CSI = CSI('G', 1)

#: Erase in Display (ED)
CLEAR_SCREEN: CSI = CSI('J', 0)

#: Erase till end of screen
CLEAR_SCREEN_TILL_END: CSINoArg = CSINoArg('0J')

#: Erase till start of screen
CLEAR_SCREEN_TILL_START: CSINoArg = CSINoArg('1J')

#: Erase whole screen
CLEAR_SCREEN_ALL: CSINoArg = CSINoArg('2J')

#: Erase whole screen and history
CLEAR_SCREEN_ALL_AND_HISTORY: CSINoArg = CSINoArg('3J')

#: Erase in Line (EL)
CLEAR_LINE_ALL: CSI = CSI('K')

#: Erase in Line from Cursor to End of Line (default)
CLEAR_LINE_RIGHT: CSINoArg = CSINoArg('0K')

#: Erase in Line from Cursor to Beginning of Line
CLEAR_LINE_LEFT: CSINoArg = CSINoArg('1K')

#: Erase Line containing Cursor
CLEAR_LINE: CSINoArg = CSINoArg('2K')

#: Scroll up Ps lines (default = 1) (SU)
#: Scroll down Ps lines (default = 1) (SD)
SCROLL_UP: CSI = CSI('S')
SCROLL_DOWN: CSI = CSI('T')

#: Save Cursor Position (SCP)
SAVE_CURSOR: CSINoArg = CSINoArg('s')

#: Restore Cursor Position (RCP)
RESTORE_CURSOR: CSINoArg = CSINoArg('u')

#: Cursor Visibility (DECTCEM)
HIDE_CURSOR: CSINoArg = CSINoArg('?25l')
SHOW_CURSOR: CSINoArg = CSINoArg('?25h')


def clear_line(n: int) -> str:
    """Clear the terminal line `n` rows above the cursor.

    Moves the cursor up `n` lines, erases that line completely,
    then moves back down `n` lines, leaving the cursor position
    unchanged.

    Args:
        n: Number of lines above the cursor to clear.

    Returns:
        The combined escape sequence performing the move, clear,
        and move back.
    """
    return UP(n) + CLEAR_LINE_ALL() + DOWN(n)


class WindowsColors(enum.Enum):
    """The 16 colors the legacy Windows console can render.

    Named after the classic 16-color console palette (black through
    intense white). `from_rgb` maps an arbitrary RGB color to its
    nearest member for terminals without ANSI/truecolor support.
    """

    BLACK = 0, 0, 0
    BLUE = 0, 0, 128
    GREEN = 0, 128, 0
    CYAN = 0, 128, 128
    RED = 128, 0, 0
    MAGENTA = 128, 0, 128
    YELLOW = 128, 128, 0
    GREY = 192, 192, 192
    INTENSE_BLACK = 128, 128, 128
    INTENSE_BLUE = 0, 0, 255
    INTENSE_GREEN = 0, 255, 0
    INTENSE_CYAN = 0, 255, 255
    INTENSE_RED = 255, 0, 0
    INTENSE_MAGENTA = 255, 0, 255
    INTENSE_YELLOW = 255, 255, 0
    INTENSE_WHITE = 255, 255, 255

    @staticmethod
    def from_rgb(rgb: tuple[int, int, int]) -> WindowsColors:
        """Find the closest WindowsColors to the given RGB color.

        Uses squared Euclidean distance in RGB space against all 16
        palette members and returns the nearest.

        Args:
            rgb: The color to match, as an ``(r, g, b)`` tuple.

        Returns:
            The closest palette member.

        >>> WindowsColors.from_rgb((0, 0, 0))
        <WindowsColors.BLACK: (0, 0, 0)>

        >>> WindowsColors.from_rgb((255, 255, 255))
        <WindowsColors.INTENSE_WHITE: (255, 255, 255)>

        >>> WindowsColors.from_rgb((0, 255, 0))
        <WindowsColors.INTENSE_GREEN: (0, 255, 0)>

        >>> WindowsColors.from_rgb((45, 45, 45))
        <WindowsColors.BLACK: (0, 0, 0)>

        >>> WindowsColors.from_rgb((128, 0, 128))
        <WindowsColors.MAGENTA: (128, 0, 128)>
        """

        def color_distance(
            rgb1: tuple[int, int, int],
            rgb2: tuple[int, int, int],
        ) -> int:
            return sum(
                (c1 - c2) ** 2 for c1, c2 in zip(rgb1, rgb2, strict=False)
            )

        return min(
            WindowsColors,
            key=lambda color: color_distance(color.value, rgb),
        )


class WindowsColor:
    """Windows-compatible color wrapper for when ANSI is not supported.

    Currently a no-op: real color output would require calling the
    Windows console API directly, but every caller expects a
    buffered string return instead (see the commented-out
    implementation in `__call__`), so this always returns text
    unchanged.

    >>> WindowsColor(WindowsColors.RED)('test')
    'test'
    """

    __slots__ = ('color',)

    def __init__(self, color: Color) -> None:
        """Wrap a `Color` for eventual Windows-console rendering.

        Args:
            color: The (already-resolved) color to wrap.
        """
        self.color = color

    def __call__(self, text: str) -> str:
        """Return `text` unchanged (see the class docstring)."""
        return text


class RGB(typing.NamedTuple):
    """Red, Green, Blue color, each channel 0-255."""

    #: Red channel, 0-255.
    red: int
    #: Green channel, 0-255.
    green: int
    #: Blue channel, 0-255.
    blue: int

    def __str__(self) -> str:
        """Return the CSS-style `rgb(...)` string (see `rgb`)."""
        return self.rgb

    @property
    def rgb(self) -> str:
        """The `rgb(r, g, b)` CSS color string."""
        return f'rgb({self.red}, {self.green}, {self.blue})'

    @property
    def hex(self) -> str:
        """The `#rrggbb` hex color string."""
        return f'#{self.red:02x}{self.green:02x}{self.blue:02x}'

    @property
    def to_ansi_16(self) -> int:
        """Nearest ANSI 16-color-palette index (0-7) for this color.

        Thresholds each channel at half intensity (>=128) into its
        bit of the 3-bit RGB code, rather than only lighting a
        channel at full intensity: an ``int(c / 255)`` threshold was
        only ever 1 at exactly 255, which collapsed almost every
        color (e.g. maroon 128,0,0) to black.
        """
        red = int(self.red >= 128)
        green = int(self.green >= 128)
        blue = int(self.blue >= 128)
        return (blue << 2) | (green << 1) | red

    @property
    def to_ansi_256(self) -> int:
        """Nearest xterm 256-color index (16-231, the 6x6x6 cube).

        Rounds each channel to the nearest of 6 steps and combines
        them into the standard ``16 + 36r + 6g + b`` cube index.
        """
        red = round(self.red / 255 * 5)
        green = round(self.green / 255 * 5)
        blue = round(self.blue / 255 * 5)
        return 16 + 36 * red + 6 * green + blue

    @property
    def to_windows(self) -> WindowsColors:
        """Closest Windows 16-color-palette member for this color."""
        return WindowsColors.from_rgb((self.red, self.green, self.blue))

    def interpolate(self, end: RGB, step: float) -> RGB:
        """Linearly interpolate between this color and `end`.

        Args:
            end: The color to interpolate toward.
            step: Interpolation position. 0 returns this color, 1
                returns `end`. Not clamped to
                ``[0, 1]`` -- a value outside that range
                extrapolates past whichever endpoint it's beyond.

        Returns:
            The interpolated color, each channel computed
            independently and truncated (not rounded) to an int.
        """
        return RGB(
            int(self.red + (end.red - self.red) * step),
            int(self.green + (end.green - self.green) * step),
            int(self.blue + (end.blue - self.blue) * step),
        )


class HSL(typing.NamedTuple):
    """Hue, Saturation, Lightness color.

    Hue is a value between 0 and 360, saturation and lightness are
    between 0(%) and 100(%).
    """

    hue: float
    saturation: float
    lightness: float

    @classmethod
    def from_rgb(cls, rgb: RGB) -> HSL:
        """Convert a 0-255 RGB color to an HSL color.

        `colorsys.rgb_to_hls` returns **HLS** (hue, lightness,
        saturation) order, not HSL: its second element is lightness
        and its third is saturation. This reorders those into this
        class's HSL fields (``hls[2]`` -> `saturation`, ``hls[1]``
        -> `lightness`).

        Args:
            rgb: The color to convert.

        Returns:
            The equivalent HSL color.
        """
        hls = colorsys.rgb_to_hls(
            rgb.red / 255,
            rgb.green / 255,
            rgb.blue / 255,
        )
        return cls(
            round(hls[0] * 360),
            round(hls[2] * 100),
            round(hls[1] * 100),
        )

    def interpolate(self, end: HSL, step: float) -> HSL:
        """Linearly interpolate between this color and `end`.

        Args:
            end: The color to interpolate toward.
            step: Interpolation position. 0 returns this color, 1
                returns `end`. Not clamped to ``[0, 1]``.

        Returns:
            The interpolated color.
        """
        return HSL(
            self.hue + (end.hue - self.hue) * step,
            self.saturation + (end.saturation - self.saturation) * step,
            self.lightness + (end.lightness - self.lightness) * step,
        )


class ColorBase(abc.ABC):
    """Deprecated common base for color-like classes, unused.

    `typing.NamedTuple` doesn't support multiple inheritance, so
    this class can't actually be mixed into `Color`, and nothing
    subclasses it.
    """

    def get_color(self, value: float) -> Color:
        """Unimplemented, deprecated and unused (see class docstring).

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError()


class Color(typing.NamedTuple):
    """Color base class.

    Contains the color in RGB (Red, Green, Blue), HSL (Hue,
    Saturation, Lightness) and Xterm (8-bit) representations, plus
    an optional name.

    To make a custom color the only required argument is `rgb`. The
    other values are automatically derived from it if omitted, but
    you can be more explicit if you wish.

    """

    #: The RGB representation.
    rgb: RGB
    #: The HSL representation. Note the field is named `hls` but holds an
    #: `HSL` value (hue, saturation, lightness) -- see `HSL.from_rgb`.
    hls: HSL
    #: An optional human-readable name, e.g. ``'red'``.
    name: str | None
    #: An optional registered xterm 256-color palette index, used by
    #: `Colors.register`/`ansi`.
    xterm: int | None

    def __call__(self, value: str) -> str:
        """Shorthand for `self.fg(value)`.

        Args:
            value: The text to style.

        Returns:
            `value` wrapped in this color's foreground escape
            sequence.
        """
        return self.fg(value)

    @property
    def fg(self) -> SGRColor | WindowsColor:
        """Foreground-color callable for this color.

        Reads `env.COLOR_SUPPORT` live, at call time (not when this
        `Color` was constructed): a `Color` built long before
        rendering still styles according to whatever color support
        is detected when `fg` is actually accessed.

        Returns:
            A `WindowsColor` on the legacy Windows console,
            otherwise an `SGRColor` (start code 38, end code 39).
        """
        if env.COLOR_SUPPORT is env.ColorSupport.WINDOWS:
            return WindowsColor(self)
        else:
            return SGRColor(self, 38, 39)

    @property
    def bg(self) -> DummyColor | SGRColor:
        """Background-color callable for this color.

        Reads `env.COLOR_SUPPORT` live, at call time, like `fg`.

        Returns:
            A no-op `DummyColor` on the legacy Windows console (no
            background-color support there), otherwise an
            `SGRColor` (start code 48, end code 49).
        """
        if env.COLOR_SUPPORT is env.ColorSupport.WINDOWS:
            return DummyColor()
        else:
            return SGRColor(self, 48, 49)

    @property
    def underline(self) -> DummyColor | SGRColor:
        """Underline-color callable for this color.

        Reads `env.COLOR_SUPPORT` live, at call time, like `fg`.

        Returns:
            A no-op `DummyColor` on the legacy Windows console,
            otherwise an `SGRColor` (start code 58, end code 59: the
            underline color, distinct from text color).
        """
        if env.COLOR_SUPPORT is env.ColorSupport.WINDOWS:
            return DummyColor()
        else:
            return SGRColor(self, 58, 59)

    @property
    def ansi(self) -> str | None:
        """ANSI SGR color parameter for this color, or `None`.

        Picks the encoding by resolving, in order: truecolor (if
        `env.COLOR_SUPPORT` is `XTERM_TRUECOLOR`), 16-color (if
        `env.COLOR_SUPPORT` is `XTERM`, via `RGB.to_ansi_16`), this
        color's own registered `xterm` index, if it has one
        (checked with ``is not None``, so a registered index of 0
        counts -- rendering an SGR at all means the caller already
        decided colors are wanted, even if global detection reports
        no support), then 256-color (`RGB.to_ansi_256`) if
        `env.COLOR_SUPPORT` is `XTERM_256`. Reads
        `env.COLOR_SUPPORT` live, at call time, like `fg`.

        Returns:
            The SGR color parameter (e.g. ``'5;196'``), or `None`
            if no color encoding applies.
        """
        if (
            env.COLOR_SUPPORT is env.ColorSupport.XTERM_TRUECOLOR
        ):  # pragma: no branch
            return f'2;{self.rgb.red};{self.rgb.green};{self.rgb.blue}'

        if env.COLOR_SUPPORT is env.ColorSupport.XTERM:
            color = self.rgb.to_ansi_16
        elif self.xterm is not None:
            color = self.xterm
        elif (
            env.COLOR_SUPPORT is env.ColorSupport.XTERM_256
        ):  # pragma: no branch
            color = self.rgb.to_ansi_256
        else:  # pragma: no branch
            return None

        return f'5;{color}'

    def interpolate(self, end: Color, step: float) -> Color:
        """Linearly interpolate between this color and `end`.

        Args:
            end: The color to interpolate toward.
            step: Interpolation position for `rgb`/`hls`, 0 returns
                this color's, 1 returns `end`'s. `name`/`xterm`
                aren't numeric, so instead of interpolating they
                snap to whichever endpoint `step` is closer to
                (below 0.5 keeps this color's, otherwise `end`'s).

        Returns:
            The interpolated color.
        """
        return Color(
            self.rgb.interpolate(end.rgb, step),
            self.hls.interpolate(end.hls, step),
            self.name if step < 0.5 else end.name,
            self.xterm if step < 0.5 else end.xterm,
        )

    def __str__(self) -> str:
        """Return `name` if set, else the `rgb` string form."""
        if self.name:
            return self.name
        else:
            return str(self.rgb)

    def __repr__(self) -> str:
        """Debug repr with the class name and `name`, e.g. `Color('red')`."""
        return f'{self.__class__.__name__}({self.name!r})'

    def __hash__(self) -> int:
        """Hash by `rgb`, ignoring `hls`/`name`/`xterm`."""
        return hash(self.rgb)


class Colors:
    """Registry of `Color` instances, indexed for lookup.

    `register` files a new `Color` into the dicts below, keyed by
    each representation, so a color can be looked up by any of
    them.

    """

    #: Registered colors keyed by `name`, as given.
    by_name: ClassVar[defaultdict[str, list[Color]]] = defaultdict(list)
    #: Registered colors keyed by `name.lower()`.
    by_lowername: ClassVar[defaultdict[str, list[Color]]] = defaultdict(list)
    #: Registered colors keyed by `RGB.hex`.
    by_hex: ClassVar[defaultdict[str, list[Color]]] = defaultdict(list)
    #: Registered colors keyed by `RGB`.
    by_rgb: ClassVar[defaultdict[RGB, list[Color]]] = defaultdict(list)
    #: Registered colors keyed by `HSL`.
    by_hls: ClassVar[defaultdict[HSL, list[Color]]] = defaultdict(list)
    #: Registered colors keyed by xterm palette index, at most one color per
    #: index, later registrations overwrite earlier ones.
    by_xterm: ClassVar[dict[int, Color]] = dict()

    @classmethod
    def register(
        cls,
        rgb: RGB,
        hls: HSL | None = None,
        name: str | None = None,
        xterm: int | None = None,
    ) -> Color:
        """Create a `Color`, index it, and return it.

        Args:
            rgb: The color's RGB representation.
            hls: The color's HSL representation, derived from
                `rgb` via `HSL.from_rgb` if omitted.
            name: An optional human-readable name to index by
                (both as given and lowercased).
            xterm: An optional xterm 256-color palette index to
                index by.

        Returns:
            The newly created and registered `Color`.
        """
        if hls is None:
            hls = HSL.from_rgb(rgb)

        color = Color(rgb, hls, name, xterm)

        if name:
            cls.by_name[name].append(color)
            cls.by_lowername[name.lower()].append(color)

        cls.by_hex[rgb.hex].append(color)
        cls.by_rgb[rgb].append(color)
        cls.by_hls[hls].append(color)

        if xterm is not None:
            cls.by_xterm[xterm] = color

        return color

    @classmethod
    def interpolate(cls, color_a: Color, color_b: Color, step: float) -> Color:
        """Shorthand for `color_a.interpolate(color_b, step)`.

        Args:
            color_a: The color at `step=0`.
            color_b: The color at `step=1`.
            step: Interpolation position between the two colors.

        Returns:
            The interpolated color.
        """
        return color_a.interpolate(color_b, step)


class ColorGradient:
    """A sequence of colors interpolated across a 0-1 value range.

    Used for widgets whose color should shift with progress (e.g. a
    bar that goes from red to yellow to green as it nears
    completion). See `get_color` for how a value maps to a `Color`.
    """

    interpolate: collections.abc.Callable[[Color, Color, float], Color] | None
    colors: tuple[Color, ...]

    def __init__(
        self,
        *colors: Color,
        interpolate: (
            collections.abc.Callable[[Color, Color, float], Color] | None
        ) = Colors.interpolate,
    ) -> None:
        """Store the gradient's colors and interpolation function.

        Args:
            *colors: The colors to interpolate across, in order;
                at least one is required.
            interpolate: The function used to blend between two
                adjacent colors given a 0-1 step. Pass `None` to
                disable blending and snap to the nearest color
                instead (see `get_color`).
        """
        assert colors
        self.colors = colors
        self.interpolate = interpolate

    def __call__(self, value: float) -> Color:
        """Shorthand for `get_color(value)`."""
        return self.get_color(value)

    def get_color(self, value: float) -> Color:
        """Map `value` (0-1) to a `Color` from this gradient.

        `value` is clamped to the gradient's ends: `<= 0` (or
        `pbase.Undefined`/`pbase.UnknownLength`) returns the first
        color, `>= 1` returns the last. Otherwise, if `interpolate`
        is `None`, the nearest color by index is returned with no
        blending. If it's set, `value` is split into a segment
        index (the pair of adjacent colors to blend between) and a
        0-1 step within that segment, then blended via
        `self.interpolate`.

        Note:
            The segment index and the within-segment step are each
            computed from a separate remap of `value`: the index
            uses a span of ``max_color_idx - 1`` (so, for four or
            more colors, the first and last segments end up half
            the width of the interior ones), while the step assumes
            every segment is an equal ``1 / max_color_idx`` wide.
            For gradients of four or more colors this mismatch
            means `step` can fall outside ``[0, 1]`` near an
            interior segment boundary, and `Color.interpolate` does not
            clamp it, so colors near those boundaries can
            extrapolate past the two blended stops rather than
            blend smoothly between them. Left as-is here (fixing it
            changes rendered gradient output) and documented as a
            known quirk rather than silently worked around.

        Args:
            value: Position in the gradient, 0-1.

        Returns:
            The color at `value`.
        """
        if (
            value == pbase.Undefined
            or value == pbase.UnknownLength
            or value <= 0
        ):
            return self.colors[0]
        elif value >= 1:
            return self.colors[-1]

        max_color_idx = len(self.colors) - 1
        if max_color_idx == 0:
            return self.colors[0]
        elif self.interpolate:
            if max_color_idx > 1:
                index = round(
                    converters.remap(value, 0, 1, 0, max_color_idx - 1),
                )
            else:
                index = 0

            step = converters.remap(
                value,
                index / (max_color_idx),
                (index + 1) / (max_color_idx),
                0,
                1,
            )
            color = self.interpolate(
                self.colors[index],
                self.colors[index + 1],
                float(step),
            )
        else:
            index = round(converters.remap(value, 0, 1, 0, max_color_idx))
            color = self.colors[index]

        return color


#: A `Color`, a `ColorGradient` to resolve one from, or no color.
OptionalColor = Color | ColorGradient | None


def get_color(value: float, color: OptionalColor) -> Color | None:
    """Resolve `color` to a concrete `Color` for the given `value`.

    If `color` is a `ColorGradient`, resolve it via
    `ColorGradient.get_color`. A plain `Color` (or `None`) passes
    through unchanged.

    Args:
        value: Position used to resolve a gradient, 0-1 (ignored
            for a plain `Color`).
        color: The color or gradient to resolve.

    Returns:
        The resolved color, or `None` if `color` was `None`.
    """
    if isinstance(color, ColorGradient):
        color = color(value)
    return color


def apply_colors(
    text: str,
    percentage: float | None = None,
    *,
    fg: OptionalColor = None,
    bg: OptionalColor = None,
    fg_none: Color | None = None,
    bg_none: Color | None = None,
    **kwargs: typing.Any,
) -> str:
    """Apply colors/gradients to a string depending on the given percentage.

    When percentage is `None`, the `fg_none` and `bg_none` colors will be used.
    Otherwise, the `fg` and `bg` colors will be used. If the colors are
    gradients, the color will be interpolated depending on the percentage.
    """
    if percentage is None:
        if fg_none is not None:
            text = fg_none.fg(text)
        if bg_none is not None:
            text = bg_none.bg(text)
    elif fg is not None or bg is not None:
        fg = get_color(percentage * 0.01, fg)
        bg = get_color(percentage * 0.01, bg)

        if fg is not None:  # pragma: no branch
            text = fg.fg(text)
        if bg is not None:  # pragma: no branch
            text = bg.bg(text)

    return text


class DummyColor:
    """No-op color: renders text unstyled.

    Used where a real styling callable is expected (`Color.fg`/
    `Color.bg`/`Color.underline`) but the terminal can't render
    this kind of styling, e.g. background/underline color on the
    legacy Windows console.
    """

    def __call__(self, text: str) -> str:
        """Return `text` unchanged."""
        return text

    def __repr__(self) -> str:
        """Return `'DummyColor()'`."""
        return 'DummyColor()'


class SGR(CSI):
    r"""A paired start/end SGR (Select Graphic Rendition) style.

    Wraps two SGR codes -- one that turns a style on (`start_code`),
    one that turns it back off (`end_code`) -- and calling the
    instance wraps text between them, e.g. ``bold('hi')`` ->
    ``'\x1b[1mhi\x1b[22m'``.
    """

    _start_code: int
    _end_code: int
    _code = 'm'
    __slots__ = '_end_code', '_start_code'

    def __init__(self, start_code: int, end_code: int) -> None:
        """Store the start/end SGR codes.

        Args:
            start_code: The SGR code that turns the style on.
            end_code: The SGR code that turns the style back off.
        """
        self._start_code = start_code
        self._end_code = end_code

    @property
    def _start_template(self) -> str:
        return super().__call__(self._start_code)

    @property
    def _end_template(self) -> str:
        return super().__call__(self._end_code)

    def __call__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        text: str,
        *args: typing.Any,
    ) -> str:
        """Wrap `text` between the start and end SGR sequences.

        Args:
            text: The text to style.
            *args: Unused, accepted for signature compatibility
                with other CSI callables.

        Returns:
            `text` wrapped between the start and end escape
            sequences.
        """
        return self._start_template + text + self._end_template


class SGRColor(SGR):
    """An `SGR` style parameterized by a `Color`.

    Used for `Color.fg`/`Color.bg`/`Color.underline`: the start
    sequence carries both `start_code` and the color's `ansi`
    parameter (e.g. ``'38;5;196'``), rather than just a bare code.
    """

    __slots__ = '_color', '_end_code', '_start_code'

    def __init__(self, color: Color, start_code: int, end_code: int) -> None:
        """Store the color and the start/end SGR codes.

        Args:
            color: The color to render.
            start_code: The SGR code that turns the style on.
            end_code: The SGR code that turns the style back off.
        """
        self._color = color
        super().__init__(start_code, end_code)

    def __call__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        text: str,
        *args: typing.Any,
    ) -> str:
        """Wrap `text` between the start and end SGR sequences.

        Args:
            text: The text to style.
            *args: Unused, accepted for signature compatibility
                with other CSI callables.

        Returns:
            `text` unchanged if `self._color.ansi` is `None` (no
            usable color representation for this terminal, e.g.
            color support is `NONE`) -- returning early here avoids
            emitting a malformed escape code containing the literal
            string ``'None'``. Otherwise, `text` wrapped between
            the start and end escape sequences (see `SGR.__call__`).
        """
        if self._color.ansi is None:
            # No usable color representation for this terminal (e.g. color
            # support is NONE): leave the text unstyled instead of emitting
            # a malformed escape code containing the literal string 'None'.
            return text
        return super().__call__(text, *args)

    @property
    def _start_template(self) -> str:
        return CSI.__call__(self, self._start_code, self._color.ansi)


#: Encircled text (SGR 52/54).
encircled: SGR = SGR(52, 54)

#: Framed text (SGR 51/54).
framed: SGR = SGR(51, 54)

#: Overlined text (SGR 53/55).
overline: SGR = SGR(53, 55)

#: Bold (increased intensity) text (SGR 1/22).
bold: SGR = SGR(1, 22)

#: Gothic/Fraktur text (SGR 20/10), rarely supported by terminals.
gothic: SGR = SGR(20, 10)

#: Italic text (SGR 3/23).
italic: SGR = SGR(3, 23)

#: Strikethrough text (SGR 9/29).
strike_through: SGR = SGR(9, 29)

#: Fast-blinking text (SGR 6/25).
fast_blink: SGR = SGR(6, 25)

#: Slow-blinking text (SGR 5/25).
slow_blink: SGR = SGR(5, 25)

#: Underlined text (SGR 4/24).
underline: SGR = SGR(4, 24)

#: Double-underlined text (SGR 21/24).
double_underline: SGR = SGR(21, 24)

#: Faint (decreased intensity) text (SGR 2/22).
faint: SGR = SGR(2, 22)

#: Inverse/reverse video text, foreground and background swapped
#: (SGR 7/27).
inverse: SGR = SGR(7, 27)
