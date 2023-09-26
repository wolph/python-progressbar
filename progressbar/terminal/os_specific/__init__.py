import sys

if sys.platform.startswith('win'):
    from .windows import (
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


getch = _getch
reset_console_mode = _reset_console_mode
set_console_mode = _set_console_mode
