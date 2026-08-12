"""Import an example module from its path.

Examples are loaded by path rather than by package import so that the
``docs/`` directory never has to end up on ``sys.path`` for consumers
other than the test suite, and so no example can shadow the top-level
``examples.py``.
"""

from __future__ import annotations

import importlib.util
import types

from ._registry import Demo

MODULE_PREFIX = 'progressbar_docs_examples'


def load_example(demo: Demo) -> types.ModuleType:
    module_name = f'{MODULE_PREFIX}.{demo.name.replace("/", ".")}'
    spec = importlib.util.spec_from_file_location(module_name, demo.path)
    if spec is None or spec.loader is None:  # pragma: no cover - unreachable
        raise ImportError(f'cannot load example: {demo.path}')

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
