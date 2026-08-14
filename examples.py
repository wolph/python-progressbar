#!/usr/bin/env python3
"""Run every documented example in sequence.

The examples themselves live in ``docs/examples/`` so that the
documentation, the generated animations, the browser console and the
test suite all read the same files. This script only sequences them.
"""

import importlib.util
import pathlib
import sys
import time
import types

ROOT = pathlib.Path(__file__).resolve().parent


def load_docs_examples(repo_root: pathlib.Path) -> types.ModuleType:
    """Import ``docs/examples`` by path, under a private module name.

    Never put ``docs/`` on ``sys.path``: ``docs/examples`` would be cached
    as ``sys.modules['examples']`` and permanently shadow *this* module for
    the rest of the process.
    """
    examples_dir = repo_root / 'docs' / 'examples'
    spec = importlib.util.spec_from_file_location(
        'docs_examples',
        examples_dir / '__init__.py',
        submodule_search_locations=[str(examples_dir)],
    )
    if spec is None or spec.loader is None:  # pragma: no cover - unreachable
        raise ImportError(
            f'cannot load docs examples package from {examples_dir}'
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_docs_examples = load_docs_examples(ROOT)
DEMOS = _docs_examples.DEMOS
load_example = _docs_examples.load_example


def main(*filters: str) -> None:
    """Run every demo whose name contains one of ``filters`` (or all, if none).

    Mirrors the pre-migration script's ``python examples.py <substring>``
    entry point, now matched against ``Demo.name`` (e.g. ``howto/multibar``)
    instead of a bare function name.
    """
    demos = [
        demo
        for demo in DEMOS
        if not filters or any(f in demo.name for f in filters)
    ]
    if filters and not demos:
        print(f'No demo matches: {" ".join(filters)}', file=sys.stderr)
        sys.exit(1)

    for demo in demos:
        print(f'\n### {demo.title} ({demo.name})')
        try:
            load_example(demo).main()
        except KeyboardInterrupt:
            print(f'\nSkipping {demo.name}.')
            # Sleep a bit so a second, impatient Ctrl-C lands here rather
            # than mid-render -- and escapes to the top-level handler below,
            # quitting the whole run instead of only skipping one demo.
            time.sleep(0.2)


if __name__ == '__main__':
    try:
        main(*sys.argv[1:])
    except KeyboardInterrupt:
        print('\nQuitting examples.')
