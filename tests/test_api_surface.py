"""Public API surface snapshot.

Guards the backwards-compatibility contract while the quality-audit
refactors land: every public module keeps its public names, and every
public callable keeps its parameter names and kinds.

The snapshot deliberately records only parameter *names* and *kinds*
(positional / keyword / var-positional / var-keyword) plus whether a
default exists. Annotations and default-value reprs are excluded so a
single snapshot is stable across Python 3.10-3.15 and so widening a type
annotation does not require a snapshot update. Removing or renaming a
parameter, changing its kind, or dropping a public name fails the test.

Regenerate after a deliberate, reviewed API addition with:

    PROGRESSBAR_UPDATE_API_SNAPSHOT=1 pytest tests/test_api_surface.py
"""

from __future__ import annotations

import enum
import importlib
import inspect
import json
import os
import pathlib
import types
import typing

import pytest

SNAPSHOT_PATH: pathlib.Path = (
    pathlib.Path(__file__).parent / 'api_surface_snapshot.json'
)

#: Modules whose public surface is under the compatibility contract.
PUBLIC_MODULES: tuple[str, ...] = (
    'progressbar',
    'progressbar.algorithms',
    'progressbar.bar',
    'progressbar.base',
    'progressbar.env',
    'progressbar.fast',
    'progressbar.multi',
    'progressbar.shortcuts',
    'progressbar.terminal',
    'progressbar.terminal.base',
    'progressbar.terminal.colors',
    'progressbar.terminal.stream',
    'progressbar.utils',
    'progressbar.widgets',
)


def _describe_signature(obj: typing.Any) -> str:
    """Return a version-stable signature descriptor for a callable."""
    try:
        signature = inspect.signature(obj)
    except (ValueError, TypeError):
        return 'signature-unavailable'

    parts: list[str] = []
    for name, parameter in signature.parameters.items():
        prefix = {
            inspect.Parameter.VAR_POSITIONAL: '*',
            inspect.Parameter.VAR_KEYWORD: '**',
        }.get(parameter.kind, '')
        suffix = '=?' if parameter.default is not parameter.empty else ''
        parts.append(f'{prefix}{name}{suffix}')

        if parameter.kind is inspect.Parameter.KEYWORD_ONLY and (
            '*' not in ''.join(parts[:-1])
        ):
            # Mark the keyword-only boundary once so converting a
            # positional parameter to keyword-only is visible.
            parts.insert(len(parts) - 1, '*')

    return f'({", ".join(parts)})'


def _describe(obj: typing.Any) -> str:
    # typing constructs (Union aliases, parameterized generics, TypeVars)
    # change type/callability across Python versions (e.g. typing.Union
    # aliases became instances of a Union class in 3.14), so they get one
    # stable descriptor everywhere.
    if (
        typing.get_origin(obj) is not None
        or getattr(type(obj), '__module__', '') == 'typing'
    ):
        return 'type-alias'
    if inspect.isclass(obj):
        if issubclass(obj, enum.Enum):
            # Enum constructor signatures are metaclass artifacts that vary
            # across Python versions; the compatibility contract is the
            # member list.
            enum_class = typing.cast('type[enum.Enum]', obj)
            members = ','.join(member.name for member in enum_class)
            return f'enum({members})'
        if not getattr(obj, '__module__', '').startswith('progressbar'):
            # Stdlib/third-party re-exports (TracebackType, timedelta, ...)
            # picked up by the no-__all__ fallback: their signatures are not
            # part of this package's contract and vary across versions.
            return 're-export'
        return f'class{_describe_signature(obj)}'
    if callable(obj):
        return f'callable{_describe_signature(obj)}'
    # Describe instances by their first non-freezegun class: if an earlier
    # test imported a module under freezegun, module constants like
    # widgets.MAX_DATE are Fake* instances forever, which would make this
    # snapshot order-dependent (FakeDate vs date).
    return next(
        cls.__name__
        for cls in type(obj).__mro__
        if 'freezegun' not in cls.__module__
    )


def _public_names(module: types.ModuleType) -> list[str]:
    explicit = getattr(module, '__all__', None)
    if explicit is not None:
        return sorted(explicit)
    return sorted(
        name
        for name in dir(module)
        if not name.startswith('_')
        and not isinstance(getattr(module, name), types.ModuleType)
    )


def build_surface() -> dict[str, dict[str, str]]:
    surface: dict[str, dict[str, str]] = {}
    for module_name in PUBLIC_MODULES:
        module = importlib.import_module(module_name)
        surface[module_name] = {
            name: _describe(getattr(module, name))
            for name in _public_names(module)
        }
    return surface


@pytest.mark.no_freezegun
def test_api_surface_snapshot() -> None:
    # no_freezegun: the surface describes module constants by type name;
    # freezegun would report FakeDate/FakeDatetime for MAX_DATE/MAX_DATETIME.
    surface: dict[str, dict[str, str]] = build_surface()

    if os.environ.get('PROGRESSBAR_UPDATE_API_SNAPSHOT'):
        SNAPSHOT_PATH.write_text(
            json.dumps(surface, indent=2, sort_keys=True) + '\n',
        )
        pytest.skip('API surface snapshot regenerated')

    assert SNAPSHOT_PATH.exists(), (
        'Missing API snapshot; generate it with '
        'PROGRESSBAR_UPDATE_API_SNAPSHOT=1 pytest tests/test_api_surface.py'
    )
    snapshot: dict[str, dict[str, str]] = json.loads(
        SNAPSHOT_PATH.read_text(),
    )

    problems: list[str] = []
    for module_name, expected in snapshot.items():
        current = surface.get(module_name)
        if current is None:
            problems.append(f'module removed: {module_name}')
            continue
        for name, descriptor in expected.items():
            if name not in current:
                problems.append(f'{module_name}.{name}: removed')
            elif current[name] != descriptor:
                problems.append(
                    f'{module_name}.{name}: {descriptor} -> {current[name]}',
                )

    assert not problems, (
        'Public API changed; if the change is a deliberate, reviewed '
        'widening, regenerate the snapshot:\n' + '\n'.join(problems)
    )
