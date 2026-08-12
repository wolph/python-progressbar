"""The ``.. demo::`` directive.

Expands one registry name into three views of the same example file: the
generated animation, the source, and a placeholder the console script
upgrades into a Run button.
"""

from __future__ import annotations

import html
import importlib.util
import pathlib
import sys
import types
import typing

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.application import Sphinx
from sphinx.errors import NoUri
from sphinx.util.osutil import relative_uri

if typing.TYPE_CHECKING:
    from docutils.nodes import Node

# This file lives at ``docs/_ext/demo.py``, two directories below the repo
# root (``_ext`` -> ``docs`` -> root), so ``parents[2]`` is the root.
#
# Derived from ``__file__`` rather than the ``app.confdir``/``app.srcdir``
# the Sphinx application object exposes, because ``DEMOS_BY_NAME`` below
# has to exist at *import* time: Sphinx imports an extension module --
# running this file top to bottom -- before it calls the module's
# ``setup(app)``, so no ``app`` (and so no ``confdir``/``srcdir``) exists
# yet while this line runs.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_docs_examples(repo_root: pathlib.Path) -> types.ModuleType:
    """Import ``docs/examples`` by path, under a private module name.

    ``docs/examples`` cannot be imported as top-level ``examples`` -- e.g.
    via ``sys.path.insert(0, str(repo_root / 'docs'))`` followed by
    ``import examples`` -- because that name collides with the real
    top-level ``examples.py`` demo runner. Once Python caches the wrong
    module under ``sys.modules['examples']`` the collision is permanent
    for the rest of the process. Loading by file path under a private
    name sidesteps ``sys.path`` and the ``examples`` name entirely.
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


DEMOS_BY_NAME = load_docs_examples(REPO_ROOT).DEMOS_BY_NAME


class DemoDirective(Directive):
    required_arguments = 1
    optional_arguments = 0
    has_content = False
    option_spec: typing.ClassVar[dict[str, typing.Any]] = {}

    def run(self) -> list[Node]:
        name = self.arguments[0].strip()
        demo = DEMOS_BY_NAME.get(name)
        if demo is None:
            raise self.error(f'unknown demo: {name}')

        if not demo.svg_path.exists():
            # A raw HTML <img> (below) is invisible to every Sphinx/
            # docutils image check: it is not an `image`/`figure` node, so
            # nothing validates its src, copies it as a build dependency,
            # or warns about it going missing. conf.py's
            # ``suppress_warnings = ['image.nonlocal_uri']`` does not
            # cover this either -- that category is about non-local
            # (external) URIs on real image nodes, not local files that
            # simply don't exist. Without this explicit check, a demo
            # whose SVG has not been rendered yet (see
            # scripts/render_demos.py) would build clean and 404 in
            # production instead of failing loudly here.
            raise self.error(
                f'demo animation not rendered: {demo.svg_path} '
                f'(run: python scripts/render_demos.py --only {name})'
            )

        source = demo.path.read_text(encoding='utf-8')
        stem = name.replace('/', '-')

        # Read the Docs serves this site under `/en/<version>/`, so every
        # asset URL must be relative to the current page. A root-absolute
        # `/_static/...` resolves to the domain root and 404s there while
        # working perfectly in a local build -- the worst kind of bug.
        env = self.state.document.settings.env
        try:
            here = env.app.builder.get_target_uri(env.docname)
        except NoUri:
            # Non-HTML builders (latex, epub, texinfo) raise NoUri for any
            # document outside their own tree. They ignore the format='html'
            # raw nodes below anyway, so an empty base is right: it makes
            # relative_uri return the plain path rather than crashing the
            # build. Read the Docs builds pdf and epub on every commit, and
            # no CI job runs a non-HTML builder, so this crashed silently
            # in production.
            here = ''
        svg_uri = relative_uri(here, f'_static/demos/{demo.svg_path.name}')
        source_uri = relative_uri(here, f'_static/examples/{stem}.py')

        container = nodes.container(classes=['demo'])
        container += nodes.raw(
            '',
            f'<img class="demo-animation" src="{svg_uri}" '
            f'alt="{html.escape(demo.title, quote=True)}">',
            format='html',
        )
        container += nodes.literal_block(
            source,
            source,
            language='python',
            classes=['demo-source'],
        )
        safe_name = html.escape(name, quote=True)
        container += nodes.raw(
            '',
            f'<div class="demo-run" data-demo="{safe_name}" '
            f'data-source="{source_uri}"></div>',
            format='html',
        )
        return [container]


def copy_example_sources(app: Sphinx, exception: Exception | None) -> None:
    """Publish each example as a fetchable file for the browser console."""
    if exception is not None:
        return

    target = pathlib.Path(app.outdir) / '_static' / 'examples'
    target.mkdir(parents=True, exist_ok=True)
    for name, demo in DEMOS_BY_NAME.items():
        destination = target / f'{name.replace("/", "-")}.py'
        destination.write_text(
            demo.path.read_text(encoding='utf-8'),
            encoding='utf-8',
        )


def setup(app: Sphinx) -> dict[str, typing.Any]:
    app.add_directive('demo', DemoDirective)
    app.connect('build-finished', copy_example_sources)
    app.add_css_file('vendor/xterm.css')
    app.add_css_file('livecode/livecode.css')
    app.add_js_file('vendor/xterm.js')
    app.add_js_file('livecode/livecode.js')
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
