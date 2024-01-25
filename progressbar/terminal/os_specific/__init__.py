import sys

if sys.platform.startswith('win'):
    from .windows import (
        get_console_mode as _get_console_mode,
        getch as _getch,
        reset_console_mode as _reset_console_mode,
        set_console_mode as _set_console_mode,
    )

else:
    from .posix import getch as _getch

    def _reset_console_mode():
        pass

    def _set_console_mode():
        pass

    def _get_console_mode():
        return 0


getch = _getch
reset_console_mode = _reset_console_mode
set_console_mode = _set_console_mode
get_console_mode = _get_console_mode
