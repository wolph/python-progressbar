import collections
import threading

from . import utils
from .os_functions import getch

ESC = '\x1B'
CSI = ESC + '['

CUP = CSI + '{row};{column}H'  # Cursor Position [row;column] (default = [1,1])


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
SGR = CSI + '{n}m'  # Character Attributes


class ENCIRCLED(str):
    '''
    Your guess is as good as mine.
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=52), args[1], SGR.format(n=54)])
        return super(ENCIRCLED, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Removes encircled?
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=52), SGR.format(n=54))


class FRAMED(str):
    '''
    Your guess is as good as mine.
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=51), args[1], SGR.format(n=54)])
        return super(FRAMED, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Removes Frame?
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=51), SGR.format(n=54))


class GOTHIC(str):
    '''
    Changes text font to Gothic
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=20), args[1], SGR.format(n=10)])
        return super(GOTHIC, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Makes text font normal
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=20), SGR.format(n=10))


class ITALIC(str):
    '''
    Makes the text italic
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=3), args[1], SGR.format(n=23)])
        return super(ITALIC, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Removes the italic.
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=3), SGR.format(n=23))


class STRIKE_THROUGH(str):
    '''
    Strikes through the text.
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=9), args[1], SGR.format(n=29)])
        return super(STRIKE_THROUGH, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Removes the strike through
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=9), SGR.format(n=29))


class FAST_BLINK(str):
    '''
    Makes the text blink fast
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=6), args[1], SGR.format(n=25)])
        return super(FAST_BLINK, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Makes the text steady
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=6), SGR.format(n=25))


class SLOW_BLINK(str):
    '''
    Makes the text blonk slowely.
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=5), args[1], SGR.format(n=25)])
        return super(SLOW_BLINK, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Makes the text steady
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=5), SGR.format(n=25))


class OVERLINE(str):
    '''
    Overlines the text provided.
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=53), args[1], SGR.format(n=55)])
        return super(OVERLINE, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Removes the overline from the text
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=53), SGR.format(n=55))


class UNDERLINE(str):
    '''
    Underlines the text provided.
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=4), args[1], SGR.format(n=24)])
        return super(UNDERLINE, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Removes the underline from the text
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=4), SGR.format(n=24))


class DOUBLE_UNDERLINE(str):
    '''
    Double underlines the text provided.
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=21), args[1], SGR.format(n=24)])
        return super(DOUBLE_UNDERLINE, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Removes the double underline from the text
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=21), SGR.format(n=24))


class BOLD(str):
    '''
    Makes the supplied text BOLD
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=1), args[1], SGR.format(n=22)])
        return super(BOLD, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Removes the BOLD from the text.
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=1), SGR.format(n=22))


class FAINT(str):
    '''
    Makes the supplied text FAINT
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=2), args[1], SGR.format(n=22)])
        return super(FAINT, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Removes the FAINT from the text.
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=2), SGR.format(n=22))


class INVERT_COLORS(str):
    '''
    Switches the background and forground colors.
    '''

    @classmethod
    def __new__(cls, *args, **kwargs):
        args = list(args)
        args[1] = ''.join([SGR.format(n=7), args[1], SGR.format(n=27)])
        return super(INVERT_COLORS, cls).__new__(*args, **kwargs)

    @property
    def raw(self):
        '''
        Removes the color inversion and returns the original text provided.
        '''
        text = self.__str__()
        return utils.remove_ansi(text, SGR.format(n=7), SGR.format(n=27))


RGB = collections.namedtuple('RGB', ['r', 'g', 'b'])


class Color(str):
    '''
    Color base class

    This class is a wrapper for the  `str` class that adds a couple of
    class methods. It makes it easier to add and remove an ansi color escape
    sequence from a string of text.

    There are 141 HTML colors that have already been provided however you can
    make a custom color if you would like.

    To make a custom color simply subclass this class and override the `_rgb`
    class attribute supplying your own RGB value as a tuple (R, G, B)
    '''
    _rgb: RGB = RGB(0, 0, 0)

    @classmethod
    def fg(cls, text):
        '''
        Adds the ansi escape codes to set the foreground color to this color.
        '''
        return cls(
            ''.join(
                [
                    CSI,
                    '38;2;{0};{1};{2}m'.format(*cls._rgb),
                    text,
                    SGR.format(n=39)
                ]
            )
        )

    @classmethod
    def bg(cls, text):
        '''
        Adds the ansi escape codes to set the background color to this color.
        '''
        return cls(
            ''.join(
                [
                    CSI,
                    '48;2;{0};{1};{2}m'.format(*cls._rgb),
                    text,
                    SGR.format(n=49)
                ]
            )
        )

    @classmethod
    def ul(cls, text):
        '''
        Adds the ansi escape codes to set the underline color to this color.
        '''
        return cls(
            ''.join(
                [
                    CSI,
                    '58;2;{0};{1};{2}m'.format(*cls._rgb),
                    text,
                    SGR.format(n=59)
                ]
            )
        )

    @property
    def raw(self):
        '''
        Removes this color from the text provided
        '''
        text = self.__str__()

        if text.startswith(CSI + '48;2'):
            text = utils.remove_ansi(
                text,
                CSI + '48;2;{0};{1};{2}m'.format(*self._rgb),
                SGR.format(n=49)
            )
        elif text.startswith(CSI + '38;2'):
            text = utils.remove_ansi(
                text,
                CSI + '38;2;{0};{1};{2}m'.format(*self._rgb),
                SGR.format(n=39)
            )

        else:
            text = utils.remove_ansi(
                text,
                CSI + '58;2;{0};{1};{2}m'.format(*self._rgb),
                SGR.format(n=59)
            )

        return text


class INDIAN_RED(Color):
    _rgb = RGB(205, 92, 92)


class LIGHT_CORAL(Color):
    _rgb = RGB(240, 128, 128)


class SALMON(Color):
    _rgb = RGB(250, 128, 114)


class DARK_SALMON(Color):
    _rgb = RGB(233, 150, 122)


class LIGHT_SALMON(Color):
    _rgb = RGB(255, 160, 122)


class CRIMSON(Color):
    _rgb = RGB(220, 20, 60)


class RED(Color):
    _rgb = RGB(255, 0, 0)


class FIRE_BRICK(Color):
    _rgb = RGB(178, 34, 34)


class DARK_RED(Color):
    _rgb = RGB(139, 0, 0)


class PINK(Color):
    _rgb = RGB(255, 192, 203)


class LIGHT_PINK(Color):
    _rgb = RGB(255, 182, 193)


class HOT_PINK(Color):
    _rgb = RGB(255, 105, 180)


class DEEP_PINK(Color):
    _rgb = RGB(255, 20, 147)


class MEDIUM_VIOLET_RED(Color):
    _rgb = RGB(199, 21, 133)


class PALE_VIOLET_RED(Color):
    _rgb = RGB(219, 112, 147)


class CORAL(Color):
    _rgb = RGB(255, 127, 80)


class TOMATO(Color):
    _rgb = RGB(255, 99, 71)


class ORANGE_RED(Color):
    _rgb = RGB(255, 69, 0)


class DARK_ORANGE(Color):
    _rgb = RGB(255, 140, 0)


class ORANGE(Color):
    _rgb = RGB(255, 165, 0)


class GOLD(Color):
    _rgb = RGB(255, 215, 0)


class YELLOW(Color):
    _rgb = RGB(255, 255, 0)


class LIGHT_YELLOW(Color):
    _rgb = RGB(255, 255, 224)


class LEMON_CHIFFON(Color):
    _rgb = RGB(255, 250, 205)


class LIGHT_GOLDENROD_YELLOW(Color):
    _rgb = RGB(250, 250, 210)


class PAPAYA_WHIP(Color):
    _rgb = RGB(255, 239, 213)


class MOCCASIN(Color):
    _rgb = RGB(255, 228, 181)


class PEACH_PUFF(Color):
    _rgb = RGB(255, 218, 185)


class PALE_GOLDENROD(Color):
    _rgb = RGB(238, 232, 170)


class KHAKI(Color):
    _rgb = RGB(240, 230, 140)


class DARK_KHAKI(Color):
    _rgb = RGB(189, 183, 107)


class LAVENDER(Color):
    _rgb = RGB(230, 230, 250)


class THISTLE(Color):
    _rgb = RGB(216, 191, 216)


class PLUM(Color):
    _rgb = RGB(221, 160, 221)


class VIOLET(Color):
    _rgb = RGB(238, 130, 238)


class ORCHID(Color):
    _rgb = RGB(218, 112, 214)


class FUCHSIA(Color):
    _rgb = RGB(255, 0, 255)


class MAGENTA(Color):
    _rgb = RGB(255, 0, 255)


class MEDIUM_ORCHID(Color):
    _rgb = RGB(186, 85, 211)


class MEDIUM_PURPLE(Color):
    _rgb = RGB(147, 112, 219)


class REBECCA_PURPLE(Color):
    _rgb = RGB(102, 51, 153)


class BLUE_VIOLET(Color):
    _rgb = RGB(138, 43, 226)


class DARK_VIOLET(Color):
    _rgb = RGB(148, 0, 211)


class DARK_ORCHID(Color):
    _rgb = RGB(153, 50, 204)


class DARK_MAGENTA(Color):
    _rgb = RGB(139, 0, 139)


class PURPLE(Color):
    _rgb = RGB(128, 0, 128)


class INDIGO(Color):
    _rgb = RGB(75, 0, 130)


class SLATE_BLUE(Color):
    _rgb = RGB(106, 90, 205)


class DARK_SLATE_BLUE(Color):
    _rgb = RGB(72, 61, 139)


class MEDIUM_SLATE_BLUE(Color):
    _rgb = RGB(123, 104, 238)


class GREEN_YELLOW(Color):
    _rgb = RGB(173, 255, 47)


class CHARTREUSE(Color):
    _rgb = RGB(127, 255, 0)


class LAWN_GREEN(Color):
    _rgb = RGB(124, 252, 0)


class LIME(Color):
    _rgb = RGB(0, 255, 0)


class LIME_GREEN(Color):
    _rgb = RGB(50, 205, 50)


class PALE_GREEN(Color):
    _rgb = RGB(152, 251, 152)


class LIGHT_GREEN(Color):
    _rgb = RGB(144, 238, 144)


class MEDIUM_SPRING_GREEN(Color):
    _rgb = RGB(0, 250, 154)


class SPRING_GREEN(Color):
    _rgb = RGB(0, 255, 127)


class MEDIUM_SEA_GREEN(Color):
    _rgb = RGB(60, 179, 113)


class SEA_GREEN(Color):
    _rgb = RGB(46, 139, 87)


class FOREST_GREEN(Color):
    _rgb = RGB(34, 139, 34)


class GREEN(Color):
    _rgb = RGB(0, 128, 0)


class DARK_GREEN(Color):
    _rgb = RGB(0, 100, 0)


class YELLOW_GREEN(Color):
    _rgb = RGB(154, 205, 50)


class OLIVE_DRAB(Color):
    _rgb = RGB(107, 142, 35)


class OLIVE(Color):
    _rgb = RGB(128, 128, 0)


class DARK_OLIVE_GREEN(Color):
    _rgb = RGB(85, 107, 47)


class MEDIUM_AQUAMARINE(Color):
    _rgb = RGB(102, 205, 170)


class DARK_SEA_GREEN(Color):
    _rgb = RGB(143, 188, 139)


class LIGHT_SEA_GREEN(Color):
    _rgb = RGB(32, 178, 170)


class DARK_CYAN(Color):
    _rgb = RGB(0, 139, 139)


class TEAL(Color):
    _rgb = RGB(0, 128, 128)


class AQUA(Color):
    _rgb = RGB(0, 255, 255)


class CYAN(Color):
    _rgb = RGB(0, 255, 255)


class LIGHT_CYAN(Color):
    _rgb = RGB(224, 255, 255)


class PALE_TURQUOISE(Color):
    _rgb = RGB(175, 238, 238)


class AQUAMARINE(Color):
    _rgb = RGB(127, 255, 212)


class TURQUOISE(Color):
    _rgb = RGB(64, 224, 208)


class MEDIUM_TURQUOISE(Color):
    _rgb = RGB(72, 209, 204)


class DARK_TURQUOISE(Color):
    _rgb = RGB(0, 206, 209)


class CADET_BLUE(Color):
    _rgb = RGB(95, 158, 160)


class STEEL_BLUE(Color):
    _rgb = RGB(70, 130, 180)


class LIGHT_STEEL_BLUE(Color):
    _rgb = RGB(176, 196, 222)


class POWDER_BLUE(Color):
    _rgb = RGB(176, 224, 230)


class LIGHT_BLUE(Color):
    _rgb = RGB(173, 216, 230)


class SKY_BLUE(Color):
    _rgb = RGB(135, 206, 235)


class LIGHT_SKY_BLUE(Color):
    _rgb = RGB(135, 206, 250)


class DEEP_SKY_BLUE(Color):
    _rgb = RGB(0, 191, 255)


class DODGER_BLUE(Color):
    _rgb = RGB(30, 144, 255)


class CORNFLOWER_BLUE(Color):
    _rgb = RGB(100, 149, 237)


class ROYAL_BLUE(Color):
    _rgb = RGB(65, 105, 225)


class BLUE(Color):
    _rgb = RGB(0, 0, 255)


class MEDIUM_BLUE(Color):
    _rgb = RGB(0, 0, 205)


class DARK_BLUE(Color):
    _rgb = RGB(0, 0, 139)


class NAVY(Color):
    _rgb = RGB(0, 0, 128)


class MIDNIGHT_BLUE(Color):
    _rgb = RGB(25, 25, 112)


class CORNSILK(Color):
    _rgb = RGB(255, 248, 220)


class BLANCHED_ALMOND(Color):
    _rgb = RGB(255, 235, 205)


class BISQUE(Color):
    _rgb = RGB(255, 228, 196)


class NAVAJO_WHITE(Color):
    _rgb = RGB(255, 222, 173)


class WHEAT(Color):
    _rgb = RGB(245, 222, 179)


class BURLY_WOOD(Color):
    _rgb = RGB(222, 184, 135)


class TAN(Color):
    _rgb = RGB(210, 180, 140)


class ROSY_BROWN(Color):
    _rgb = RGB(188, 143, 143)


class SANDY_BROWN(Color):
    _rgb = RGB(244, 164, 96)


class GOLDENROD(Color):
    _rgb = RGB(218, 165, 32)


class DARK_GOLDENROD(Color):
    _rgb = RGB(184, 134, 11)


class PERU(Color):
    _rgb = RGB(205, 133, 63)


class CHOCOLATE(Color):
    _rgb = RGB(210, 105, 30)


class SADDLE_BROWN(Color):
    _rgb = RGB(139, 69, 19)


class SIENNA(Color):
    _rgb = RGB(160, 82, 45)


class BROWN(Color):
    _rgb = RGB(165, 42, 42)


class MAROON(Color):
    _rgb = RGB(128, 0, 0)


class WHITE(Color):
    _rgb = RGB(255, 255, 255)


class SNOW(Color):
    _rgb = RGB(255, 250, 250)


class HONEY_DEW(Color):
    _rgb = RGB(240, 255, 240)


class MINT_CREAM(Color):
    _rgb = RGB(245, 255, 250)


class AZURE(Color):
    _rgb = RGB(240, 255, 255)


class ALICE_BLUE(Color):
    _rgb = RGB(240, 248, 255)


class GHOST_WHITE(Color):
    _rgb = RGB(248, 248, 255)


class WHITE_SMOKE(Color):
    _rgb = RGB(245, 245, 245)


class SEA_SHELL(Color):
    _rgb = RGB(255, 245, 238)


class BEIGE(Color):
    _rgb = RGB(245, 245, 220)


class OLD_LACE(Color):
    _rgb = RGB(253, 245, 230)


class FLORAL_WHITE(Color):
    _rgb = RGB(255, 250, 240)


class IVORY(Color):
    _rgb = RGB(255, 255, 240)


class ANTIQUE_WHITE(Color):
    _rgb = RGB(250, 235, 215)


class LINEN(Color):
    _rgb = RGB(250, 240, 230)


class LAVENDER_BLUSH(Color):
    _rgb = RGB(255, 240, 245)


class MISTY_ROSE(Color):
    _rgb = RGB(255, 228, 225)


class GAINSBORO(Color):
    _rgb = RGB(220, 220, 220)


class LIGHT_GRAY(Color):
    _rgb = RGB(211, 211, 211)


class SILVER(Color):
    _rgb = RGB(192, 192, 192)


class DARK_GRAY(Color):
    _rgb = RGB(169, 169, 169)


class GRAY(Color):
    _rgb = RGB(128, 128, 128)


class DIM_GRAY(Color):
    _rgb = RGB(105, 105, 105)


class LIGHT_SLATE_GRAY(Color):
    _rgb = RGB(119, 136, 153)


class SLATE_GRAY(Color):
    _rgb = RGB(112, 128, 144)


class DARK_SLATE_GRAY(Color):
    _rgb = RGB(47, 79, 79)


class BLACK(Color):
    _rgb = RGB(0, 0, 0)
