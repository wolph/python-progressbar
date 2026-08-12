# ruff: noqa: N801
"""Windows specific code for the terminal.

Talks to Kernel32 directly through `ctypes` for single-key input and
console-mode control, since neither has a `termios`/`tty` equivalent
on Windows. The naming convention here is non-pythonic because it
matches the Windows API naming.
"""

from __future__ import annotations

import ctypes
import enum
from ctypes.wintypes import (
    BOOL as _BOOL,
    CHAR as _CHAR,
    DWORD as _DWORD,
    HANDLE as _HANDLE,
    SHORT as _SHORT,
    UINT as _UINT,
    WCHAR as _WCHAR,
    WORD as _WORD,
)

_kernel32 = ctypes.windll.Kernel32  # type: ignore

_STD_INPUT_HANDLE = _DWORD(-10)
_STD_OUTPUT_HANDLE = _DWORD(-11)
# GetStdHandle returns INVALID_HANDLE_VALUE (-1) when no console is
# attached (piped output, pythonw, services)
_INVALID_HANDLE_VALUE = _HANDLE(-1).value
# The EventType of a KEY_EVENT_RECORD in an INPUT_RECORD
_KEY_EVENT = 0x0001


def _valid_handle(handle) -> bool:
    # Handles may be plain ints (from a HANDLE restype) or ctypes
    # instances, so normalize before comparing.
    value = getattr(handle, 'value', handle)
    return value is not None and value != _INVALID_HANDLE_VALUE


class WindowsConsoleModeFlags(enum.IntFlag):
    """`GetConsoleMode`/`SetConsoleMode` bits, for both handle kinds.

    Input-handle and output-handle modes are two separate C bit
    spaces that happen to share this one Python `IntFlag`. Several
    `*_OUTPUT` members below have the same numeric value as an
    `*_INPUT` member declared earlier (e.g. `ENABLE_PROCESSED_OUTPUT`
    and `ENABLE_PROCESSED_INPUT` are both `0x0001`). Python's `enum`
    then treats the later name as an alias of the first, so accessing
    it yields a member whose `.name` (and `__str__`) is the *input*
    name even when read through the output-side alias. Only
    meaningful when combined with the handle it was read from/is
    being written to.
    """

    ENABLE_ECHO_INPUT = 0x0004
    ENABLE_EXTENDED_FLAGS = 0x0080
    ENABLE_INSERT_MODE = 0x0020
    ENABLE_LINE_INPUT = 0x0002
    ENABLE_MOUSE_INPUT = 0x0010
    ENABLE_PROCESSED_INPUT = 0x0001
    ENABLE_QUICK_EDIT_MODE = 0x0040
    ENABLE_WINDOW_INPUT = 0x0008
    ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200

    ENABLE_PROCESSED_OUTPUT = 0x0001
    ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    DISABLE_NEWLINE_AUTO_RETURN = 0x0008
    ENABLE_LVB_GRID_WORLDWIDE = 0x0010

    def __str__(self) -> str:
        """Render as ``NAME (0xHHHH)``, e.g. for debug logging."""
        return f'{self.name} (0x{self.value:04X})'


# The Kernel32 entry points below need explicit argtypes/restype:
# without them ctypes passes and returns values as 32-bit C ints,
# silently truncating 64-bit HANDLEs. Four of the five take a HANDLE
# argument. `GetStdHandle` instead takes a DWORD and *returns* a
# HANDLE, so for that one it is the restype that matters.
_GetConsoleMode = _kernel32.GetConsoleMode
_GetConsoleMode.argtypes = (_HANDLE, ctypes.POINTER(_DWORD))
_GetConsoleMode.restype = _BOOL

_SetConsoleMode = _kernel32.SetConsoleMode
_SetConsoleMode.argtypes = (_HANDLE, _DWORD)
_SetConsoleMode.restype = _BOOL

_GetStdHandle = _kernel32.GetStdHandle
_GetStdHandle.argtypes = (_DWORD,)
_GetStdHandle.restype = _HANDLE

_SetConsoleTextAttribute = _kernel32.SetConsoleTextAttribute
_SetConsoleTextAttribute.argtypes = (_HANDLE, _WORD)
_SetConsoleTextAttribute.restype = _BOOL

_h_console_input = _GetStdHandle(_STD_INPUT_HANDLE)
_input_mode = _DWORD()
if _valid_handle(_h_console_input):
    _GetConsoleMode(_HANDLE(_h_console_input), ctypes.byref(_input_mode))

_h_console_output = _GetStdHandle(_STD_OUTPUT_HANDLE)
_output_mode = _DWORD()
if _valid_handle(_h_console_output):
    _GetConsoleMode(_HANDLE(_h_console_output), ctypes.byref(_output_mode))


# The structures and unions below mirror, field-for-field, the C
# layout of the Win32 console input records used by
# `ReadConsoleInput` (`COORD`, `*_EVENT_RECORD`, `INPUT_RECORD`, and
# the `Event`/`uChar` unions within them). ctypes marshals a raw
# buffer into Python by matching this declared layout byte-for-byte
# against the C struct, so they exist purely to make that marshaling
# possible and are not meant to be used as general-purpose Python
# types.
class _COORD(ctypes.Structure):
    _fields_ = (('X', _SHORT), ('Y', _SHORT))


class _FOCUS_EVENT_RECORD(ctypes.Structure):
    _fields_ = (('bSetFocus', _BOOL),)


class _KEY_EVENT_RECORD(ctypes.Structure):
    class _uchar(ctypes.Union):
        _fields_ = (('UnicodeChar', _WCHAR), ('AsciiChar', _CHAR))

    _fields_ = (
        ('bKeyDown', _BOOL),
        ('wRepeatCount', _WORD),
        ('wVirtualKeyCode', _WORD),
        ('wVirtualScanCode', _WORD),
        ('uChar', _uchar),
        ('dwControlKeyState', _DWORD),
    )


class _MENU_EVENT_RECORD(ctypes.Structure):
    _fields_ = (('dwCommandId', _UINT),)


class _MOUSE_EVENT_RECORD(ctypes.Structure):
    _fields_ = (
        ('dwMousePosition', _COORD),
        ('dwButtonState', _DWORD),
        ('dwControlKeyState', _DWORD),
        ('dwEventFlags', _DWORD),
    )


class _WINDOW_BUFFER_SIZE_RECORD(ctypes.Structure):
    _fields_ = (('dwSize', _COORD),)


class _INPUT_RECORD(ctypes.Structure):
    class _Event(ctypes.Union):
        _fields_ = (
            ('KeyEvent', _KEY_EVENT_RECORD),
            ('MouseEvent', _MOUSE_EVENT_RECORD),
            ('WindowBufferSizeEvent', _WINDOW_BUFFER_SIZE_RECORD),
            ('MenuEvent', _MENU_EVENT_RECORD),
            ('FocusEvent', _FOCUS_EVENT_RECORD),
        )

    _fields_ = (('EventType', _WORD), ('Event', _Event))


_ReadConsoleInput = _kernel32.ReadConsoleInputA
_ReadConsoleInput.argtypes = (
    _HANDLE,
    ctypes.POINTER(_INPUT_RECORD),
    _DWORD,
    ctypes.POINTER(_DWORD),
)
_ReadConsoleInput.restype = _BOOL


def reset_console_mode() -> None:
    """Restore the input/output console modes saved at import time.

    Writes `_input_mode`/`_output_mode`, captured once before
    `set_console_mode` ever ran, back via `SetConsoleMode`. A no-op
    for either handle that was never valid (e.g. no console
    attached).
    """
    if _valid_handle(_h_console_input):
        _SetConsoleMode(_HANDLE(_h_console_input), _DWORD(_input_mode.value))

    if _valid_handle(_h_console_output):
        _SetConsoleMode(_HANDLE(_h_console_output), _DWORD(_output_mode.value))


def set_console_mode() -> bool:
    """Enable ANSI/VT escape-sequence processing on the console.

    ORs `ENABLE_VIRTUAL_TERMINAL_INPUT` into the saved input mode
    (best effort, not reflected in the return value) and
    `ENABLE_PROCESSED_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING`
    into the saved output mode, on top of whatever was already set,
    so the console starts accepting ANSI color/cursor escapes without
    losing its existing behavior. `reset_console_mode` restores the
    pre-call state saved at import time.

    Returns:
        Whether the output-mode change succeeded. `False` if there
        is no valid output handle (e.g. piped output).
    """
    if not _valid_handle(_h_console_output):
        return False

    if _valid_handle(_h_console_input):
        mode = (
            _input_mode.value
            | WindowsConsoleModeFlags.ENABLE_VIRTUAL_TERMINAL_INPUT
        )
        _SetConsoleMode(_HANDLE(_h_console_input), _DWORD(mode))

    mode = (
        _output_mode.value
        | WindowsConsoleModeFlags.ENABLE_PROCESSED_OUTPUT
        | WindowsConsoleModeFlags.ENABLE_VIRTUAL_TERMINAL_PROCESSING
    )
    return bool(_SetConsoleMode(_HANDLE(_h_console_output), _DWORD(mode)))


def get_console_mode() -> int:
    """Return the input console mode captured at import, as a bitmask.

    This is the snapshot taken once at import time, not a live
    re-query of the console, so it does not reflect changes made by a
    later `set_console_mode` call.

    Note:
        `env.py` tests this against `ENABLE_PROCESSED_OUTPUT` for
        color-support detection, which is almost certainly not what it
        means to do. This is the *input* handle's mode, and
        `ENABLE_PROCESSED_OUTPUT` is 0x0001, the same value as
        `ENABLE_PROCESSED_INPUT`, so `enum.IntFlag` makes the former
        a plain alias of the latter. The check therefore asks whether
        processed *input* is enabled, which is on by default for
        essentially every real console, rather than anything about VT
        or ANSI output support. Left as-is: correcting it would change
        color detection on Windows, which cannot be verified from this
        repository's CI.
    """
    return _input_mode.value


def set_text_color(color: int) -> None:
    """Set the console's current text-attribute color.

    Args:
        color: A `SetConsoleTextAttribute` attribute bitmask (as a
            `WORD`), combining foreground/background color bits.
    """
    if _valid_handle(_h_console_output):
        _SetConsoleTextAttribute(_HANDLE(_h_console_output), _WORD(color))


def print_color(text: str, color: int) -> None:
    """Print `text` in `color`, then reset to the default grey."""
    set_text_color(color)
    print(text)  # noqa: T201
    set_text_color(7)  # Reset to default color, grey


def getch() -> str | None:
    """Read a single keypress via `ReadConsoleInput`, without echo.

    `ReadConsoleInput` reports every kind of console event (mouse,
    focus, window-resize, menu, key), not just keypresses, so the
    records read back must be filtered down to `KEY_EVENT` entries,
    and further to key-down (not key-up) ones, before a character can
    be pulled out. Non-ASCII bytes are replaced rather than raising.

    Returns:
        The character read, or `None` if there is no valid console
        input handle, the read call failed, or neither record read
        turned out to be a usable key-down event.
    """
    if not _valid_handle(_h_console_input):
        return None

    lp_buffer = (_INPUT_RECORD * 2)()
    n_length = _DWORD(2)
    lp_number_of_events_read = _DWORD()

    if not _ReadConsoleInput(
        _HANDLE(_h_console_input),
        lp_buffer,
        n_length,
        ctypes.byref(lp_number_of_events_read),
    ):
        return None

    # Only the records that were actually read contain valid data. The
    # Event field is a union, so the KeyEvent member may only be read
    # for KEY_EVENT records, and non-ASCII keys must not crash the
    # decode.
    for i in range(min(lp_number_of_events_read.value, len(lp_buffer))):
        record = lp_buffer[i]
        if record.EventType != _KEY_EVENT:
            continue

        key_event = record.Event.KeyEvent
        if not key_event.bKeyDown:
            continue

        char = key_event.uChar.AsciiChar.decode('ascii', errors='replace')
        if char != '\x00':
            return char

    return None
