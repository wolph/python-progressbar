import ctypes
from ctypes.wintypes import (
    DWORD as _DWORD,
    HANDLE as _HANDLE,
    BOOL as _BOOL,
    WORD as _WORD,
    UINT as _UINT,
    WCHAR as _WCHAR,
    CHAR as _CHAR,
    SHORT as _SHORT,
)

_kernel32 = ctypes.windll.Kernel32

_ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200
_ENABLE_PROCESSED_OUTPUT = 0x0001
_ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

_STD_INPUT_HANDLE = _DWORD(-10)
_STD_OUTPUT_HANDLE = _DWORD(-11)


_GetConsoleMode = _kernel32.GetConsoleMode
_GetConsoleMode.restype = _BOOL

_SetConsoleMode = _kernel32.SetConsoleMode
_SetConsoleMode.restype = _BOOL

_GetStdHandle = _kernel32.GetStdHandle
_GetStdHandle.restype = _HANDLE

_ReadConsoleInput = _kernel32.ReadConsoleInputA
_ReadConsoleInput.restype = _BOOL


_hConsoleInput = _GetStdHandle(_STD_INPUT_HANDLE)
_input_mode = _DWORD()
_GetConsoleMode(_HANDLE(_hConsoleInput), ctypes.byref(_input_mode))

_hConsoleOutput = _GetStdHandle(_STD_OUTPUT_HANDLE)
_output_mode = _DWORD()
_GetConsoleMode(_HANDLE(_hConsoleOutput), ctypes.byref(_output_mode))


class _COORD(ctypes.Structure):
    _fields_ = [('X', _SHORT), ('Y', _SHORT)]


class _FOCUS_EVENT_RECORD(ctypes.Structure):
    _fields_ = [('bSetFocus', _BOOL)]


class _KEY_EVENT_RECORD(ctypes.Structure):
    class _uchar(ctypes.Union):
        _fields_ = [('UnicodeChar', _WCHAR), ('AsciiChar', _CHAR)]

    _fields_ = [
        ('bKeyDown', _BOOL),
        ('wRepeatCount', _WORD),
        ('wVirtualKeyCode', _WORD),
        ('wVirtualScanCode', _WORD),
        ('uChar', _uchar),
        ('dwControlKeyState', _DWORD),
    ]


class _MENU_EVENT_RECORD(ctypes.Structure):
    _fields_ = [('dwCommandId', _UINT)]


class _MOUSE_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ('dwMousePosition', _COORD),
        ('dwButtonState', _DWORD),
        ('dwControlKeyState', _DWORD),
        ('dwEventFlags', _DWORD),
    ]


class _WINDOW_BUFFER_SIZE_RECORD(ctypes.Structure):
    _fields_ = [('dwSize', _COORD)]


class _INPUT_RECORD(ctypes.Structure):
    class _Event(ctypes.Union):
        _fields_ = [
            ('KeyEvent', _KEY_EVENT_RECORD),
            ('MouseEvent', _MOUSE_EVENT_RECORD),
            ('WindowBufferSizeEvent', _WINDOW_BUFFER_SIZE_RECORD),
            ('MenuEvent', _MENU_EVENT_RECORD),
            ('FocusEvent', _FOCUS_EVENT_RECORD),
        ]

    _fields_ = [('EventType', _WORD), ('Event', _Event)]


def reset_console_mode():
    _SetConsoleMode(_HANDLE(_hConsoleInput), _DWORD(_input_mode.value))
    _SetConsoleMode(_HANDLE(_hConsoleOutput), _DWORD(_output_mode.value))


def set_console_mode():
    mode = _input_mode.value | _ENABLE_VIRTUAL_TERMINAL_INPUT
    _SetConsoleMode(_HANDLE(_hConsoleInput), _DWORD(mode))

    mode = (
        _output_mode.value
        | _ENABLE_PROCESSED_OUTPUT
        | _ENABLE_VIRTUAL_TERMINAL_PROCESSING
    )
    _SetConsoleMode(_HANDLE(_hConsoleOutput), _DWORD(mode))


def getch():
    lpBuffer = (_INPUT_RECORD * 2)()
    nLength = _DWORD(2)
    lpNumberOfEventsRead = _DWORD()

    _ReadConsoleInput(
        _HANDLE(_hConsoleInput),
        lpBuffer,
        nLength,
        ctypes.byref(lpNumberOfEventsRead),
    )

    char = lpBuffer[1].Event.KeyEvent.uChar.AsciiChar.decode('ascii')
    return None if char == '\x00' else char
