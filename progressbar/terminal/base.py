from __future__ import annotations

import collections
import colorsys
import enum
import os
import threading
from collections import defaultdict

from python_utils import types

from .os_specific import getch

ESC = '\x1B'
CSI = ESC + '['

CUP = CSI + '{row};{column}H'  # Cursor Position [row;column] (default = [1,1])


class ColorSupport(enum.Enum):
    '''Color support for the terminal.'''
    NONE = 0
    XTERM = 1
    XTERM_256 = 2
    XTERM_TRUECOLOR = 3

    @classmethod
    def from_env(cls):
        '''Get the color support from the environment.'''
        if os.getenv('COLORTERM') == 'truecolor':
            return cls.XTERM_TRUECOLOR
        elif os.getenv('TERM') == 'xterm-256color':
            return cls.XTERM_256
        elif os.getenv('TERM') == 'xterm':
            return cls.XTERM
        else:
            return cls.NONE


color_support = ColorSupport.from_env()


# Report Cursor Position (CPR), response = [row;column] as row;columnR
class _CPR(str):
    _response_lock = threading.Lock()

    def __call__(self, stream):
        res = ''

        with self._response_lock:
            stream.write(str(self))
            stream.flush()

            while not res.endswith('R'):
                char = getch()

                if char is not None:
                    res += char

            res = res[2:-1].split(';')

            res = tuple(int(item) if item.isdigit() else item for item in res)

            if len(res) == 1:
                return res[0]

            return res

    def row(self, stream):
        row, _ = self(stream)
        return row

    def column(self, stream):
        _, column = self(stream)
        return column


DSR = CSI + '{n}n'  # Device Status Report (DSR)
CPR = _CPR(DSR.format(n=6))

IL = CSI + '{n}L'  # Insert n Line(s) (default = 1)

DECRST = CSI + '?{n}l'  # DEC Private Mode Reset
DECRTCEM = DECRST.format(n=25)  # Hide Cursor

DECSET = CSI + '?{n}h'  # DEC Private Mode Set
DECTCEM = DECSET.format(n=25)  # Show Cursor


# possible values:
# 0 = Normal (default)
# 1 = Bold
# 2 = Faint
# 3 = Italic
# 4 = Underlined
# 5 = Slow blink (appears as Bold)
# 6 = Rapid Blink
# 7 = Inverse
# 8 = Invisible, i.e., hidden (VT300)
# 9 = Strike through
# 10 = Primary (default) font
# 20 = Gothic Font
# 21 = Double underline
# 22 = Normal intensity (neither bold nor faint)
# 23 = Not italic
# 24 = Not underlined
# 25 = Steady (not blinking)
# 26 = Proportional spacing
# 27 = Not inverse
# 28 = Visible, i.e., not hidden (VT300)
# 29 = No strike through
# 30 = Set foreground color to Black
# 31 = Set foreground color to Red
# 32 = Set foreground color to Green
# 33 = Set foreground color to Yellow
# 34 = Set foreground color to Blue
# 35 = Set foreground color to Magenta
# 36 = Set foreground color to Cyan
# 37 = Set foreground color to White
# 39 = Set foreground color to default (original)
# 40 = Set background color to Black
# 41 = Set background color to Red
# 42 = Set background color to Green
# 43 = Set background color to Yellow
# 44 = Set background color to Blue
# 45 = Set background color to Magenta
# 46 = Set background color to Cyan
# 47 = Set background color to White
# 49 = Set background color to default (original).
# 50 = Disable proportional spacing
# 51 = Framed
# 52 = Encircled
# 53 = Overlined
# 54 = Neither framed nor encircled
# 55 = Not overlined
# 58 = Set underine color (2;r;g;b)
# 59 = Default underline color
# If 16-color support is compiled, the following apply.
# Assume that xterm’s resources are set so that the ISO color codes are the
# first 8 of a set of 16. Then the aixterm colors are the bright versions of
# the ISO colors:
# 90 = Set foreground color to Black
# 91 = Set foreground color to Red
# 92 = Set foreground color to Green
# 93 = Set foreground color to Yellow
# 94 = Set foreground color to Blue
# 95 = Set foreground color to Magenta
# 96 = Set foreground color to Cyan
# 97 = Set foreground color to White
# 100 = Set background color to Black
# 101 = Set background color to Red
# 102 = Set background color to Green
# 103 = Set background color to Yellow
# 104 = Set background color to Blue
# 105 = Set background color to Magenta
# 106 = Set background color to Cyan
# 107 = Set background color to White
#
# If xterm is compiled with the 16-color support disabled, it supports the
# following, from rxvt:
# 100 = Set foreground and background color to default

# If 88- or 256-color support is compiled, the following apply.
# 38;5;x = Set foreground color to x
# 48;5;x = Set background color to x


class RGB(collections.namedtuple('RGB', ['red', 'green', 'blue'])):
    __slots__ = ()

    def __str__(self):
        return f'rgb({self.red}, {self.green}, {self.blue})'

    @property
    def hex(self):
        return f'#{self.red:02x}{self.green:02x}{self.blue:02x}'

    @property
    def to_ansi_16(self):
        # Using int instead of round because it maps slightly better
        red = int(self.red / 255)
        green = int(self.green / 255)
        blue = int(self.blue / 255)
        return (blue << 2) | (green << 1) | red

    @property
    def to_ansi_256(self):
        red = round(self.red / 255 * 5)
        green = round(self.green / 255 * 5)
        blue = round(self.blue / 255 * 5)
        return 16 + 36 * red + 6 * green + blue


class HLS(collections.namedtuple('HLS', ['hue', 'lightness', 'saturation'])):
    __slots__ = ()

    @classmethod
    def from_rgb(cls, rgb: RGB) -> HLS:
        return cls(
            *colorsys.rgb_to_hls(rgb.red / 255, rgb.green / 255, rgb.blue / 255)
        )


class Color(
    collections.namedtuple(
        'Color', [
            'rgb',
            'hls',
            'name',
            'xterm',
        ]
    )
):
    '''
    Color base class

    This class contains the colors in RGB (Red, Green, Blue), HLS (Hue,
    Lightness, Saturation) and Xterm (8-bit) formats. It also contains the
    color name.

    To make a custom color the only required arguments are the RGB values.
    The other values will be automatically interpolated from that if needed,
    but you can be more explicity if you wish.
    '''
    __slots__ = ()

    @property
    def fg(self):
        return SGRColor(self, 38, 39)

    @property
    def bg(self):
        return SGRColor(self, 48, 49)

    @property
    def underline(self):
        return SGRColor(self, 58, 59)

    @property
    def ansi(self) -> types.Optional[str]:
        if color_support is ColorSupport.XTERM_TRUECOLOR:
            return f'2;{self.rgb.red};{self.rgb.green};{self.rgb.blue}'

        if self.xterm:
            color = self.xterm
        elif color_support is ColorSupport.XTERM_256:
            color = self.rgb.to_ansi_256
        elif color_support is ColorSupport.XTERM:
            color = self.rgb.to_ansi_16
        else:
            return None

        return f'5;{color}'

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'{self.__class__.__name__}({self.name!r})'

    def __hash__(self):
        return hash(self.rgb)


class Colors:
    by_name: defaultdict[str, types.List[Color]] = collections.defaultdict(list)
    by_lowername: defaultdict[str, types.List[Color]] = collections.defaultdict(
        list
    )
    by_hex: defaultdict[str, types.List[Color]] = collections.defaultdict(list)
    by_rgb: defaultdict[RGB, types.List[Color]] = collections.defaultdict(list)
    by_hls: defaultdict[HLS, types.List[Color]] = collections.defaultdict(list)
    by_xterm: dict[int, Color] = dict()

    @classmethod
    def register(
        cls,
        rgb: RGB,
        hls: types.Optional[HLS] = None,
        name: types.Optional[str] = None,
        xterm: types.Optional[int] = None,
    ) -> Color:
        color = Color(rgb, hls, name, xterm)

        if name:
            cls.by_name[name].append(color)
            cls.by_lowername[name.lower()].append(color)

        if hls is None:
            hls = HLS.from_rgb(rgb)

        cls.by_hex[rgb.hex].append(color)
        cls.by_rgb[rgb].append(color)
        cls.by_hls[hls].append(color)

        if xterm is not None:
            cls.by_xterm[xterm] = color

        return color


class SGR:
    _start_code: int
    _end_code: int
    _template = CSI + '{n}m'
    __slots__ = '_start_code', '_end_code'

    def __init__(self, start_code: int, end_code: int):
        self._start_code = start_code
        self._end_code = end_code

    @property
    def _start_template(self):
        return self._template.format(n=self._start_code)

    @property
    def _end_template(self):
        return self._template.format(n=self._end_code)

    def __call__(self, text):
        return self._start_template + text + self._end_template


class SGRColor(SGR):
    __slots__ = '_color', '_start_code', '_end_code'
    _color_template = CSI + '{n};{color}m'

    def __init__(self, color: Color, start_code: int, end_code: int):
        self._color = color
        super().__init__(start_code, end_code)

    @property
    def _start_template(self):
        return self._color_template.format(
            n=self._start_code,
            color=self._color.ansi
        )


encircled = SGR(52, 54)
framed = SGR(51, 54)
overline = SGR(53, 55)
bold = SGR(1, 22)
gothic = SGR(20, 10)
italic = SGR(3, 23)
strike_through = SGR(9, 29)
fast_blink = SGR(6, 25)
slow_blink = SGR(5, 25)
underline = SGR(4, 24)
double_underline = SGR(21, 24)
faint = SGR(2, 22)
inverse = SGR(7, 27)
