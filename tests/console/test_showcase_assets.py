"""The homepage's raw HTML recordings fail the build when an asset is absent."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import types
import typing

import pytest
from sphinx.errors import ExtensionError

ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('name', ['readme/colors', 'readme/multibar', 'readme/hero'])
def test_missing_showcase_recording_is_a_build_error(
    name: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec: importlib.machinery.ModuleSpec | None = (
        importlib.util.spec_from_file_location(
            'showcase_demo_test', ROOT / 'docs' / '_ext' / 'demo.py'
        )
    )
    assert spec is not None and spec.loader is not None
    module: types.ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, 'validate_showcase_assets')
    entries: dict[str, typing.Any] = dict(module.DEMOS_BY_NAME)
    entries[name] = types.SimpleNamespace(svg_path=tmp_path / 'missing.svg')
    monkeypatch.setattr(module, 'DEMOS_BY_NAME', entries)
    with pytest.raises(
        ExtensionError, match=f'showcase animation not rendered: {name}'
    ):
        module.validate_showcase_assets(None)
