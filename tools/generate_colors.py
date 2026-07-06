#!/usr/bin/env python3
"""Regenerate ``progressbar/terminal/colors.py`` with canonical HSL values.

The 256-colour table is *data*, not logic. For every entry the RGB triple,
the xterm index, the canonical colour name and the Python binding name are
authoritative and must never change: importers reference the binding names
directly, including the deliberate last-wins duplicates (``blue3``,
``deep_sky_blue4``, ...). Only the HSL triple is *derived*, and it is
derived here from the RGB via :meth:`progressbar.terminal.base.HSL.from_rgb`
so the stored value can never drift away from the RGB again.

The hand-entered HSL column had corrupted rows -- for example
``DeepSkyBlue4`` (``#005f87``) stored hue ``97`` where the real hue is
``198`` -- which made every gradient that interpolated through those
colours blend through the wrong hue. Recomputing from RGB fixes the data at
its source.

Usage (rewrites the file in place)::

    python tools/generate_colors.py progressbar/terminal/colors.py

The generator parses the *current* file to recover the ordered
``(binding, RGB, name, xterm)`` tuples, so name/order fidelity is
guaranteed however the file happens to be reflowed. It is idempotent:
running it twice produces a byte-identical file, because the HSL column is
always recomputed from RGB and never read back. Pass ``--check`` to verify
that without writing (exit status 1 if the file is stale).
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys
import typing

# Import the real HSL/RGB so the generated values match runtime exactly.
_REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from progressbar.terminal.base import HSL, RGB  # noqa: E402

#: Maximum line length (matches ``ruff.toml``); longer calls are wrapped one
#: argument per line, exactly as ``ruff format`` would.
LINE_LENGTH: int = 79


class Entry(typing.NamedTuple):
    """One authoritative colour-table row; HSL is derived, not stored here."""

    binding: str
    rgb: RGB
    name: str
    xterm: int


def _int_constant(node: ast.expr) -> int:
    if not isinstance(node, ast.Constant) or not isinstance(node.value, int):
        raise TypeError(f'expected an int literal, got {ast.dump(node)}')
    return node.value


def _str_constant(node: ast.expr) -> str:
    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
        raise TypeError(f'expected a str literal, got {ast.dump(node)}')
    return node.value


def _is_register_call(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == 'register'
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.value.id == 'Colors'
    )


def _parse_rgb(node: ast.expr) -> RGB:
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == 'RGB'
        and len(node.args) == 3
    ):
        raise ValueError(f'expected an RGB(...) call, got {ast.dump(node)}')
    return RGB(*(_int_constant(arg) for arg in node.args))


def parse_entries(source: str) -> tuple[list[Entry], str, str]:
    """Extract the ordered colour entries plus the file header and footer.

    The header is everything before the first ``Colors.register`` assignment
    and the footer everything after the last one; both are copied verbatim so
    the non-generated aliases and gradients survive untouched.
    """
    tree = ast.parse(source)
    register_nodes = [
        typing.cast('ast.Assign', node)
        for node in tree.body
        if _is_register_call(node)
    ]
    if not register_nodes:
        raise ValueError('no Colors.register(...) assignments found')

    first, last = register_nodes[0], register_nodes[-1]
    # The register block must be one contiguous run; a stray statement in the
    # middle would be silently dropped by the header/footer split below.
    for node in tree.body:
        if (
            first.lineno <= node.lineno <= last.lineno
            and not _is_register_call(node)
        ):
            raise ValueError(
                f'unexpected non-register statement at line {node.lineno}',
            )

    entries: list[Entry] = []
    for node in register_nodes:
        call = typing.cast('ast.Call', node.value)
        if len(call.args) != 4 or call.keywords:
            raise ValueError(
                f'unexpected register signature at line {node.lineno}',
            )
        target = typing.cast('ast.Name', node.targets[0])
        entries.append(
            Entry(
                binding=target.id,
                rgb=_parse_rgb(call.args[0]),
                name=_str_constant(call.args[2]),
                xterm=_int_constant(call.args[3]),
            ),
        )

    lines = source.splitlines(keepends=True)
    header = ''.join(lines[: first.lineno - 1])
    footer = ''.join(lines[last.end_lineno :])
    return entries, header, footer


def render_entry(entry: Entry) -> str:
    """Render one register call, wrapping only when it exceeds the limit."""
    hsl = HSL.from_rgb(entry.rgb)
    rgb_src = f'RGB({entry.rgb.red}, {entry.rgb.green}, {entry.rgb.blue})'
    # ``from_rgb`` rounds to ints; render them as ints (no trailing ``.0``).
    hsl_src = (
        f'HSL({int(hsl.hue)}, {int(hsl.saturation)}, {int(hsl.lightness)})'
    )
    args = f'{rgb_src}, {hsl_src}, {entry.name!r}, {entry.xterm}'
    single = f'{entry.binding} = Colors.register({args})'
    if len(single) <= LINE_LENGTH:
        return single + '\n'

    # Black/ruff style: one argument per line with a magic trailing comma.
    return (
        f'{entry.binding} = Colors.register(\n'
        f'    {rgb_src},\n'
        f'    {hsl_src},\n'
        f'    {entry.name!r},\n'
        f'    {entry.xterm},\n'
        ')\n'
    )


def render(source: str) -> str:
    entries, header, footer = parse_entries(source)
    body = ''.join(render_entry(entry) for entry in entries)
    return header + body + footer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'path',
        type=pathlib.Path,
        help='colors.py to regenerate in place',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='do not write; exit 1 if the file would change',
    )
    args = parser.parse_args(argv)

    source = args.path.read_text()
    generated = render(source)

    if args.check:
        if generated != source:
            sys.stderr.write(
                f'{args.path} is out of date; run generate_colors.py\n',
            )
            return 1
        return 0

    if generated != source:
        args.path.write_text(generated)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
