from __future__ import annotations

import sys


def getch() -> str:
    # `termios` and `tty` are imported lazily: they are only needed to put
    # a real terminal into raw mode, and they are absent from restricted
    # builds such as Pyodide, where importing this module must still work.
    import termios
    import tty

    if not sys.stdin.isatty():
        # Raw mode is unavailable (and unnecessary) without a tty
        return sys.stdin.read(1)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)  # type: ignore
    try:
        tty.setraw(sys.stdin.fileno())  # type: ignore
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)  # type: ignore

    return ch
