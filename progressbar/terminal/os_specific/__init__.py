"""Platform dispatch for single-key input and Windows console mode.

Picks the `.windows` or `.posix` implementation of `getch` based on
`os.name`, and re-exports it (plus the Windows-only console-mode
functions) under the same four names on both platforms. POSIX has
no console-mode API to speak of: `.posix.getch` puts the terminal
into raw mode itself, locally, via `termios`/`tty` for the duration
of a single read. So on POSIX the console-mode functions are filled
in below with no-op stubs matching the Windows signatures, meaning
callers can call `set_console_mode()` / `reset_console_mode()` /
`get_console_mode()` unconditionally, without an `if os.name == 'nt':`
branch of their own. `bar.py` does exactly that. `env.py` does not use
this shim at all, importing `windows.get_console_mode` directly from
inside its own `os.name == 'nt'` branches.
"""

import os

if os.name == 'nt':
    from .windows import (
        get_console_mode as _get_console_mode,
        getch as _getch,
        reset_console_mode as _reset_console_mode,
        set_console_mode as _set_console_mode,
    )

else:
    from .posix import getch as _getch

    def _reset_console_mode() -> None:
        """No-op: POSIX has no console-mode state to restore."""

    def _set_console_mode() -> bool:
        """No-op: report failure, as no VT processing was enabled."""
        return False

    def _get_console_mode() -> int:
        """No-op: POSIX has no console-mode bitmask to report."""
        return 0


#: Read a single keypress from stdin without waiting for Enter.
getch = _getch
#: Restore the console mode saved before `set_console_mode` ran.
#: No-op on POSIX.
reset_console_mode = _reset_console_mode
#: Enable virtual-terminal (ANSI) processing on the console. Returns
#: whether it succeeded, always `False` on POSIX.
set_console_mode = _set_console_mode
#: The current console input mode as a bitmask. Always `0` on POSIX.
get_console_mode = _get_console_mode
