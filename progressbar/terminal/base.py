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


class CSI:
    _code: str
    _template = ESC + '[{args}{code}'

    def __init__(self, code, *default_args):
        self._code = code
        self._default_args = default_args

    def __call__(self, *args):
        return self._template.format(
            args=';'.join(map(str, args or self._default_args)),
            code=self._code
        )

    def __str__(self):
        return self()


class CSINoArg(CSI):

    def __call__(self):
        return super().__call__()


#: Cursor Position [row;column] (default = [1,1])
CUP = CSI('H', 1, 1)

#: Cursor Up Ps Times (default = 1) (CUU)
UP = CSI('A', 1)

#: Cursor Down Ps Times (default = 1) (CUD)
DOWN = CSI('B', 1)

#: Cursor Forward Ps Times (default = 1) (CUF)
RIGHT = CSI('C', 1)

#: Cursor Backward Ps Times (default = 1) (CUB)
LEFT = CSI('D', 1)

#: Cursor Next Line Ps Times (default = 1) (CNL)
#: Same as Cursor Down Ps Times
NEXT_LINE = CSI('E', 1)

#: Cursor Preceding Line Ps Times (default = 1) (CPL)
#: Same as Cursor Up Ps Times
PREVIOUS_LINE = CSI('F', 1)

#: Cursor Character Absolute  [column] (default = [row,1]) (CHA)
COLUMN = CSI('G', 1)

#: Erase in Display (ED)
CLEAR_SCREEN = CSI('J', 0)

#: Erase till end of screen
CLEAR_SCREEN_TILL_END = CSINoArg('0J')

#: Erase till start of screen
CLEAR_SCREEN_TILL_START = CSINoArg('1J')

#: Erase whole screen
CLEAR_SCREEN_ALL = CSINoArg('2J')

#: Erase whole screen and history
CLEAR_SCREEN_ALL_AND_HISTORY = CSINoArg('3J')

#: Erase in Line (EL)
CLEAR_LINE_ALL = CSI('K')

#: Erase in Line from Cursor to End of Line (default)
CLEAR_LINE_RIGHT = CSINoArg('0K')

#: Erase in Line from Cursor to Beginning of Line
CLEAR_LINE_LEFT = CSINoArg('1K')

#: Erase Line containing Cursor
CLEAR_LINE = CSINoArg('2K')

#: Scroll up Ps lines (default = 1) (SU)
#: Scroll down Ps lines (default = 1) (SD)
SCROLL_UP = CSI('S')
SCROLL_DOWN = CSI('T')

#: Save Cursor Position (SCP)
SAVE_CURSOR = CSINoArg('s')

#: Restore Cursor Position (RCP)
RESTORE_CURSOR = CSINoArg('u')

#: Cursor Visibility (DECTCEM)
HIDE_CURSOR = CSINoArg('?25l')
SHOW_CURSOR = CSINoArg('?25h')


#
# UP = CSI + '{n}A'  # Cursor Up
# DOWN = CSI + '{n}B'  # Cursor Down
# RIGHT = CSI + '{n}C'  # Cursor Forward
# LEFT = CSI + '{n}D'  # Cursor Backward
# NEXT = CSI + '{n}E'  # Cursor Next Line
# PREV = CSI + '{n}F'  # Cursor Previous Line
# MOVE_COLUMN = CSI + '{n}G'  # Cursor Horizontal Absolute
# MOVE = CSI + '{row};{column}H'  # Cursor Position [row;column] (default = [
# 1,1])
#
# CLEAR = CSI + '{n}J'  # Clear (part of) the screen
# CLEAR_BOTTOM = CLEAR.format(n=0)  # Clear from cursor to end of screen
# CLEAR_TOP = CLEAR.format(n=1)  # Clear from cursor to beginning of screen
# CLEAR_SCREEN = CLEAR.format(n=2)  # Clear Screen
# CLEAR_WIPE = CLEAR.format(n=3)  # Clear Screen and scrollback buffer
#
# CLEAR_LINE = CSI + '{n}K'  # Erase in Line
# CLEAR_LINE_RIGHT = CLEAR_LINE.format(n=0)  # Clear from cursor to end of line
# CLEAR_LINE_LEFT = CLEAR_LINE.format(n=1)  # Clear from cursor to beginning
# of line
# CLEAR_LINE_ALL = CLEAR_LINE.format(n=2)  # Clear Line

def clear_line(n):
    return UP(n) + CLEAR_LINE_ALL() + DOWN(n)


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


class SGR(CSI):
    _start_code: int
    _end_code: int
    _code = 'm'
    __slots__ = '_start_code', '_end_code'

    def __init__(self, start_code: int, end_code: int):
        self._start_code = start_code
        self._end_code = end_code

    @property
    def _start_template(self):
        return super().__call__(self._start_code)

    @property
    def _end_template(self):
        return super().__call__(self._end_code)

    def __call__(self, text):
        return self._start_template + text + self._end_template


class SGRColor(SGR):
    __slots__ = '_color', '_start_code', '_end_code'

    def __init__(self, color: Color, start_code: int, end_code: int):
        self._color = color
        super().__init__(start_code, end_code)

    @property
    def _start_template(self):
        return CSI.__call__(self, self._start_code, self._color.ansi)


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
