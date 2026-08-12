"""POSIX single-key input, via `termios`/`tty` raw mode."""

from __future__ import annotations

import sys


def getch() -> str:
    """Read a single character from stdin without waiting for Enter.

    Puts the terminal into raw mode for the duration of one read, so
    the keypress is returned immediately instead of after the next
    newline, then always restores the previous terminal settings.

    Returns:
        The character read, or the byte read verbatim (as `str`) if
        stdin is not a tty.
    """
    # `termios` and `tty` are imported lazily: they are only needed to put
    # a real terminal into raw mode, and they are absent from restricted
    # builds such as Pyodide, where importing this module must still work.
    # A module-scope import would make `import progressbar` fail outright
    # there. This bug was real and has already been fixed once.
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
