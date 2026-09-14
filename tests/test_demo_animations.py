"""The documentation demos must animate for every visitor.

The demo SVGs, and the homepage player that embeds them, used to stop
animating under ``prefers-reduced-motion: reduce``. Chrome on Windows
reports that preference whenever "Animation effects" is off, so the
README and docs showed a frozen final frame that looked broken. This
check runs on every platform (unlike tests/test_readme_demos.py, which
needs a pty) so the rule cannot quietly come back.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMOS = ROOT / 'docs' / '_static' / 'demos'
SOURCES = [
    ROOT / 'scripts' / 'render_demos.py',
    ROOT / 'docs' / '_static' / 'showcase.js',
    ROOT / 'docs' / '_static' / 'home.css',
    ROOT / 'docs' / 'index.rst',
    *sorted(DEMOS.glob('*.svg')),
]


def test_demo_svgs_exist() -> None:
    assert sorted(DEMOS.glob('*.svg'))


@pytest.mark.parametrize(
    'path', SOURCES, ids=[str(p.relative_to(ROOT)) for p in SOURCES]
)
def test_demos_ignore_reduced_motion(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    assert 'prefers-reduced-motion' not in text, (
        f'{path.relative_to(ROOT)} must not stop the demo animations for '
        'reduced-motion users; the demos should animate for everyone.'
    )
