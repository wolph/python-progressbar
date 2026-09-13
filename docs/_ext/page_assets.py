"""Register page assets with Sphinx so their URLs include content checksums."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from docutils import nodes
    from sphinx.application import Sphinx


def add_page_assets(
    app: Sphinx,
    pagename: str,
    _templatename: str,
    _context: dict[str, typing.Any],
    _doctree: nodes.document | None,
) -> None:
    if app.builder is None or app.builder.name != 'html':
        return
    if pagename == 'index':
        app.add_css_file('home.css', priority=900)
        app.add_js_file('showcase.js', loading_method='defer', priority=900)
    if pagename in (
        'tutorial/index',
        'howto/index',
        'reference/index',
        'explanation/index',
        'installation',
    ):
        app.add_css_file('guide-cards.css', priority=900)
    if pagename in ('reference/index', 'explanation/index', 'installation'):
        app.add_css_file('section-pages.css', priority=900)


def setup(app: Sphinx) -> dict[str, bool]:
    app.connect('html-page-context', add_page_assets)
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
