"""Guard the three hand-synced export lists in ``progressbar/__init__.py``.

``_NAME_TO_MODULE`` is the single source of truth for the lazily re-exported
public names. ``__all__`` and the ``TYPE_CHECKING`` import block must stay in
sync with it; these tests fail loudly if any of the three drift apart.
"""

from __future__ import annotations

import ast
import pathlib

import progressbar
from progressbar import _NAME_TO_MODULE

#: Dunders that are eagerly imported (not part of ``_NAME_TO_MODULE``) but are
#: still part of the public ``__all__``.
_EAGER_DUNDERS: frozenset[str] = frozenset({'__author__', '__version__'})


def test_every_mapping_name_resolves() -> None:
    # Each lazily re-exported name must be reachable via attribute access
    # (which drives ``__getattr__``'s import machinery).
    for name in _NAME_TO_MODULE:
        assert getattr(progressbar, name) is not None, name


def test_all_matches_mapping_plus_dunders() -> None:
    # ``__all__`` must contain exactly the mapping names plus the eager
    # dunders. The concrete ordering is delegated to ruff's RUF022, so this
    # compares contents rather than the exact list order.
    assert set(progressbar.__all__) == set(_NAME_TO_MODULE) | _EAGER_DUNDERS


def test_all_has_no_duplicates() -> None:
    assert len(progressbar.__all__) == len(set(progressbar.__all__))


def test_type_checking_block_imports_exactly_the_mapping() -> None:
    source: str = pathlib.Path(progressbar.__file__).read_text()
    tree: ast.Module = ast.parse(source)

    imported: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue

        test = node.test
        is_type_checking = (
            isinstance(test, ast.Attribute) and test.attr == 'TYPE_CHECKING'
        ) or (isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING')
        if not is_type_checking:
            continue

        for stmt in node.body:
            if isinstance(stmt, ast.ImportFrom):
                for alias in stmt.names:
                    imported.add(alias.asname or alias.name)

    assert imported == set(_NAME_TO_MODULE)
