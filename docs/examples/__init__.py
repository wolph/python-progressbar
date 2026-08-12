"""Public facade for the example registry and loader.

Definitions live in ``_registry.py`` and ``_loader.py``; this module only
re-exports them so every consumer -- the test suite, the pty renderer, the
Sphinx ``.. demo::`` directive, and the Pyodide worker -- can import this
package by path (never as top-level ``examples``, which collides with the
real ``examples.py`` demo runner) and reach everything through plain
attribute access, without a second import for each submodule.
"""

from __future__ import annotations

from ._loader import load_example
from ._registry import DEMOS, DEMOS_BY_NAME, EXAMPLES_DIR, Demo

__all__ = [
    'DEMOS',
    'DEMOS_BY_NAME',
    'EXAMPLES_DIR',
    'Demo',
    'load_example',
]
