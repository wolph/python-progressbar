"""`run()`: execute a shell command per item, in parallel, with a bar.

A progress-bar'd ``xargs -P`` in Python. Templates never go through
`str.format` -- only the exact placeholder tokens ``{}`` and ``{item}``
are substituted -- so commands containing literal braces (``awk
'{print $1}'``) pass through untouched.
"""

from __future__ import annotations

import functools
import os
import shlex
import subprocess
import typing

from . import _sync

#: The two placeholder spellings recognized in command templates.
_PLACEHOLDERS: tuple[str, str] = ('{}', '{item}')

#: A command template: a string, an argv list, or a callable that
#: builds the argv for one item.
CommandT = (
    str
    | typing.Sequence[str]
    | typing.Callable[[typing.Any], typing.Sequence[str]]
)


def _substitute(token: str, item_text: str) -> str:
    """Replace the placeholder spellings inside one token."""
    for placeholder in _PLACEHOLDERS:
        token = token.replace(placeholder, item_text)
    return token


def _has_placeholder(tokens: typing.Iterable[str]) -> bool:
    """Return whether any token contains a placeholder."""
    return any(
        placeholder in token
        for token in tokens
        for placeholder in _PLACEHOLDERS
    )


def build_argv(
    command: CommandT, item: typing.Any, *, shell: bool
) -> list[str] | str:
    """Build the command for one item from a template.

    Args:
        command: A str template (split with `shlex.split`, non-POSIX
            mode on Windows so backslash paths survive), an argv list
            template, or a callable returning the argv. In the str and
            list forms every ``{}``/``{item}`` inside a token is
            replaced by ``str(item)`` -- an item containing spaces
            stays a single argv element. Without any placeholder the
            item is appended as the final argument (the ``xargs``
            convention).
        item: The batch item; substituted as ``str(item)``.
        shell: With the str form, substitute into (and return) the
            whole command string for ``subprocess.run(shell=True)``;
            an appended item is `shlex.quote`-escaped. The caller must
            trust its items -- see `run`.

    Returns:
        The argv list, or the command string when ``shell=True``.
    """
    item_text: str = str(item)
    if callable(command):
        return [str(part) for part in command(item)]
    if isinstance(command, str):
        if shell:
            if _has_placeholder((command,)):
                return _substitute(command, item_text)
            return f'{command} {shlex.quote(item_text)}'
        tokens: list[str] = shlex.split(command, posix=os.name != 'nt')
    else:
        tokens = list(command)
    if _has_placeholder(tokens):
        return [_substitute(token, item_text) for token in tokens]
    return [*tokens, item_text]


def _run_one(
    command: CommandT,
    item: typing.Any,
    *,
    check: bool,
    capture_output: bool,
    text: bool,
    shell: bool,
    cwd: typing.Any,
    env: typing.Any,
) -> subprocess.CompletedProcess[typing.Any]:
    """Execute the command for one item (thread-pool worker)."""
    argv: list[str] | str = build_argv(command, item, shell=shell)
    # The argv is assembled from the caller's own template and items;
    # shell=True is opt-in and documented as trusting both.
    return subprocess.run(  # noqa: S603, PLW1510
        argv,
        check=check,
        capture_output=capture_output,
        text=text,
        shell=shell,  # noqa: S602
        cwd=cwd,
        env=env,
    )


def make_runner(
    command: CommandT,
    *,
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
    shell: bool = False,
    cwd: typing.Any = None,
    env: typing.Any = None,
) -> typing.Callable[[typing.Any], subprocess.CompletedProcess[typing.Any]]:
    """Bind a command template into a per-item callable for `map`."""
    return functools.partial(
        _run_one,
        command,
        check=check,
        capture_output=capture_output,
        text=text,
        shell=shell,
        cwd=cwd,
        env=env,
    )


def run(
    command: CommandT,
    items: typing.Iterable[typing.Any],
    /,
    *,
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
    shell: bool = False,
    cwd: typing.Any = None,
    env: typing.Any = None,
    **kwargs: typing.Any,
) -> list[subprocess.CompletedProcess[typing.Any]]:
    """Run a shell command for every item in parallel, with a bar.

    ``progressbar.run('gzip -k {}', files, workers=4)`` is a
    progress-bar'd ``xargs -P``. Subprocesses release the GIL, so this
    always runs on threads (`Pool.run` reuses a pool's executor).

    Args:
        command: Template -- see `build_argv` for the three forms and
            the placeholder rules.
        items: The batch; each becomes one subprocess.
        check: Raise `subprocess.CalledProcessError` on a non-zero
            exit (feeding `on_error` like any other worker error).
        capture_output: Capture stdout/stderr into the results --
            the default, so child output cannot corrupt the bar.
        text: Decode captured output as text.
        shell: Run through the shell (str form only). The items are
            substituted into the command line: only use with trusted
            items, this is the documented injection risk.
        cwd: Working directory for the subprocesses.
        env: Environment for the subprocesses.
        **kwargs: The shared execution keywords (`workers`, `bar`,
            `on_error`, `timeout`, ...); see `_sync.execute`.

    Returns:
        One `subprocess.CompletedProcess` per item, in input order
        (exceptions in place under ``on_error='return'``).
    """
    if 'pool' in kwargs:
        raise TypeError(
            'run() always uses threads (subprocesses release the GIL); '
            'use Pool.run() to reuse an existing pool'
        )
    runner = make_runner(
        command,
        check=check,
        capture_output=capture_output,
        text=text,
        shell=shell,
        cwd=cwd,
        env=env,
    )
    return _sync.map(runner, items, pool='thread', **kwargs)
