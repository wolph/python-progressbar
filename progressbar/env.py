"""Environment-driven terminal capability detection.

Resolves two independent questions about an output stream: whether it is
a terminal at all (`is_terminal`, via `is_ansi_terminal`) and how many
colors it can display (`ColorSupport`, computed once at import time as
`COLOR_SUPPORT`). See docs/explanation/terminal-detection.rst for the
full precedence rules and worked examples.
"""

from __future__ import annotations

import contextlib
import enum
import os
import re
import typing


@typing.overload
def env_flag(name: str, default: bool) -> bool: ...


@typing.overload
def env_flag(name: str, default: bool | None = None) -> bool | None: ...


def env_flag(name: str, default: bool | None = None) -> bool | None:
    """Read a boolean-ish environment variable.

    Args:
        name: Environment variable to read.
        default: Returned when `name` is unset or its value isn't
            recognized.

    Returns:
        `True` for y/yes/t/true/on/1, `False` for n/no/f/false/off/0
        (case-insensitive), otherwise `default`.
    """
    v = os.getenv(name)
    if v and v.lower() in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    if v and v.lower() in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    return default


class ColorSupport(enum.IntEnum):
    """Color support for the terminal."""

    NONE = 0
    XTERM = 16
    XTERM_256 = 256
    XTERM_TRUECOLOR = 16777216
    WINDOWS = 8

    @classmethod
    def from_env(cls) -> ColorSupport:
        """Get the color support from the environment.

        A variable containing `24bit` or `truecolor`, a `TERM` naming a
        truecolor terminal (see `TRUECOLOR_TERMS`), or a Jupyter kernel
        (`JUPYTER_COLUMNS`/`JUPYTER_LINES`/`JPY_PARENT_PID` set) enables
        true color. A value containing `256` enables 256-color support,
        and a match against a known ANSI terminal (see `ANSI_TERM_RE`,
        e.g. `xterm-color`, `screen`, `tmux`) enables 16-color support.
        Otherwise no color support is assumed. The highest depth seen
        wins: `COLORTERM=truecolor` overrides `TERM=xterm-256color`.
        """
        variables = (
            'FORCE_COLOR',
            'PROGRESSBAR_ENABLE_COLORS',
            'COLORTERM',
            'TERM',
        )

        # Precedence order is significant: an interactive Jupyter kernel and
        # the Windows console probe each take priority over (and short-circuit)
        # the env-var scan below.
        if JUPYTER:
            return cls._from_jupyter()
        elif os.name == 'nt':
            return cls._from_windows()

        return cls._from_term_variables(variables)

    @classmethod
    def _from_jupyter(cls) -> ColorSupport:
        """Jupyter notebooks always support true color."""
        return cls.XTERM_TRUECOLOR

    @classmethod
    def _from_windows(cls) -> ColorSupport:  # pragma: no cover
        """Detect color support from the Windows console mode.

        We can't reliably detect true color support on Windows, so we assume
        it is supported when the console is configured to support it.
        """
        from .terminal.os_specific import windows

        if (
            windows.get_console_mode()
            & windows.WindowsConsoleModeFlags.ENABLE_PROCESSED_OUTPUT
        ):
            return cls.XTERM_TRUECOLOR
        else:
            return cls.WINDOWS

    @classmethod
    def _from_term_variables(
        cls,
        variables: tuple[str, ...],
    ) -> ColorSupport:
        """Pick the highest color support advertised by the terminal env vars.

        The first `truecolor`/`24bit` value wins immediately; otherwise the
        highest depth seen across all variables is returned. A generic truthy
        flag such as `FORCE_COLOR=1` carries no depth and implies full color
        support, analogous to the Jupyter handling above.
        """
        support = cls.NONE
        for variable in variables:
            value = os.environ.get(variable)
            if value is None:
                continue
            elif value in {'truecolor', '24bit'}:
                # Truecolor support, we don't need to check anything else.
                support = cls.XTERM_TRUECOLOR
                break
            elif value in TRUECOLOR_TERMS:
                # A TERM name that itself guarantees a 24-bit terminal.
                support = max(cls.XTERM_TRUECOLOR, support)
            elif '256' in value:
                support = max(cls.XTERM_256, support)
            elif ANSI_TERM_RE.match(value):
                # Any recognized ANSI terminal (xterm-color, screen, tmux,
                # konsole, rxvt, linux, ...) advertises at least 16 colors,
                # matching is_ansi_terminal()'s use of the same pattern.
                support = max(cls.XTERM, support)
            elif env_flag(variable, default=False):
                return cls.XTERM_TRUECOLOR

        return support


def is_ansi_terminal(
    fd: typing.IO[typing.Any],
    is_terminal: bool | None = None,
) -> bool | None:  # pragma: no cover
    """Detect whether `fd` looks like an ANSI-capable terminal.

    Tri-state, not boolean: `True` is a confirmed ANSI terminal, and
    `None` means detection was inconclusive rather than negative.
    Outside the Windows branch this function never returns `False` on
    its own: an unmatched `TERM`, no `ANSICON`, or a stream that can't
    answer `isatty()` is left as `None`, so callers such as
    `is_terminal` keep falling back instead of concluding "not a
    terminal" from missing information. The Windows console-mode probe
    is the one exception: it is authoritative there and can return a
    definite `False`.

    Detection order: an interactive Jupyter kernel or a modern-enough
    PyCharm terminal (not under pytest) short-circuits straight to
    `True`, since both render ANSI without being a tty. Otherwise,
    `fd.isatty()` plus a `TERM` match against `ANSI_TERM_RE`, or
    `ANSICON` being set, or (on Windows) the console-mode probe (see
    `os_specific.windows.get_console_mode` for what that probe actually
    tests, which is not what its flag name suggests). Only the errors a
    stream can legitimately raise while being probed are swallowed:
    `OSError` (real I/O), `ValueError` (closed/detached file) and
    `AttributeError` (no `isatty` at all). Anything else is a bug and
    propagates.

    Args:
        fd: Stream to probe.
        is_terminal: Already-known answer, if any, passed straight
            through unchanged. Only `None` triggers detection.

    Returns:
        `True`, `False`, or `None` (undetermined) -- see above.
    """
    if is_terminal is None:
        # Jupyter Notebooks support progress bars
        if JUPYTER:
            is_terminal = True
        # This works for newer versions of pycharm only. With older versions
        # there is no way to check.
        elif os.environ.get('PYCHARM_HOSTED') == '1' and not os.environ.get(
            'PYTEST_CURRENT_TEST'
        ):
            is_terminal = True

    if is_terminal is None:
        # Probe errors treated as "undetermined": see the docstring.
        with contextlib.suppress(OSError, ValueError, AttributeError):
            is_tty: bool = fd.isatty()
            # Try and match any of the huge amount of Linux/Unix ANSI consoles
            if is_tty and ANSI_TERM_RE.match(os.environ.get('TERM', '')):
                is_terminal = True
            # ANSICON is a Windows ANSI compatible console
            elif 'ANSICON' in os.environ:
                is_terminal = True
            elif os.name == 'nt':
                from .terminal.os_specific import windows

                return bool(
                    windows.get_console_mode()
                    & windows.WindowsConsoleModeFlags.ENABLE_PROCESSED_OUTPUT,
                )
            else:
                is_terminal = None

    return is_terminal


def is_terminal(
    fd: typing.IO[typing.Any],
    is_terminal: bool | None = None,
) -> bool | None:
    """Resolve whether `fd` should be treated as an interactive terminal.

    Falls back through the following, stopping at the first non-`None`
    result: the `is_terminal` argument if the caller already knows.
    Then `is_ansi_terminal(fd)`, with any falsy result normalized back
    to `None` (including the definite `False` the Windows branch can
    return, because "no ANSI support" is not the same answer as "not a
    terminal"). Then the `PROGRESSBAR_IS_TERMINAL` environment
    variable, an explicit override for cases auto-detection can't
    cover. Finally a bare `fd.isatty()`, defaulting to `False` if the
    stream can't answer at all (closed, detached, or missing
    `isatty`).

    Args:
        fd: Stream to probe.
        is_terminal: Known answer, if already determined by the caller.

    Returns:
        `True` or `False` once resolved -- the final fallback always
        settles on a boolean, so a caller never sees `None` back.
    """
    if is_terminal is None:
        # Full ansi support encompasses what we expect from a terminal
        is_terminal = is_ansi_terminal(fd) or None

    if is_terminal is None:
        # Allow a environment variable override
        is_terminal = env_flag('PROGRESSBAR_IS_TERMINAL', None)

    if is_terminal is None:
        # If we do get a TTY we know this is a valid terminal. Probe
        # errors are treated as "not a terminal": see the docstring.
        try:
            is_terminal = fd.isatty()
        except (OSError, ValueError, AttributeError):
            is_terminal = False

    return is_terminal


#: Whether this process looks like it's running inside a Jupyter kernel,
#: computed once at import time from JUPYTER_COLUMNS/JUPYTER_LINES/
#: JPY_PARENT_PID. Jupyter and Windows short-circuit color/terminal
#: detection ahead of everything else -- see `ColorSupport.from_env` and
#: `is_ansi_terminal`.
JUPYTER: bool = bool(
    os.environ.get('JUPYTER_COLUMNS')
    or os.environ.get('JUPYTER_LINES')
    or os.environ.get('JPY_PARENT_PID')
)
#: Regex fragments (unanchored) recognized as ANSI-capable `TERM` values.
ANSI_TERMS: tuple[str, ...] = (
    '([xe]|bv)term',
    '(sco)?ansi',
    'cygwin',
    'konsole',
    'linux',
    'rxvt',
    'screen',
    'tmux',
    'vt(10[02]|220|320)',
)
#: Compiled prefix match against `ANSI_TERMS`, case-insensitive.
ANSI_TERM_RE: re.Pattern[str] = re.compile(
    f'^({"|".join(ANSI_TERMS)})', re.IGNORECASE
)

#: TERM values that on their own guarantee a truecolor-capable terminal, so
#: 24-bit color still engages when ``COLORTERM`` is stripped (e.g. over ssh
#: or sudo). Limited to names that *are* the terminal, since generic values
#: such as ``xterm-256color`` are used by plenty of 256-only emulators.
TRUECOLOR_TERMS: frozenset[str] = frozenset({'xterm-kitty', 'xterm-ghostty'})

#: The color depth this environment can support, computed once at import
#: time (see `ColorSupport.from_env`). This is a ceiling, not a per-bar
#: decision -- `DefaultFdMixin._determine_enable_colors` is what decides
#: whether any given bar actually uses color.
# Defined after ANSI_TERM_RE / TRUECOLOR_TERMS because from_env() reads them.
COLOR_SUPPORT: ColorSupport = ColorSupport.from_env()
