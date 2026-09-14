"""Run every published example and check its actual terminal colours."""

from __future__ import annotations

import os
import pathlib
import re
import typing

import pytest

from .test_console import (
    BOOT_TIMEOUT_MS,
    CONSOLE_TEST_INIT_SCRIPT,
    ROOT,
    browser as browser,
    playwright_api,
    server as server,
)

if typing.TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Locator, Page


def example_pages() -> list[tuple[str, str]]:
    """Find every demo placed on a documentation page."""
    examples: list[tuple[str, str]] = []
    path: pathlib.Path
    for path in sorted((ROOT / 'docs').rglob('*.rst')):
        relative: pathlib.Path = path.relative_to(ROOT / 'docs')
        if any(part.startswith('_') for part in relative.parts):
            continue
        names: list[str] = re.findall(
            r'^\s*\.\. demo:: (\S+)',
            path.read_text(encoding='utf-8'),
            re.M,
        )
        examples.extend(
            (relative.with_suffix('.html').as_posix(), name) for name in names
        )
    return sorted(set(examples))


@pytest.fixture(scope='module')
def colour_context(browser: Browser) -> typing.Iterator[BrowserContext]:
    context: BrowserContext = browser.new_context(
        viewport={'width': 1440, 'height': 1000}
    )
    context.add_init_script(CONSOLE_TEST_INIT_SCRIPT)
    yield context
    context.close()


@pytest.mark.parametrize('path,name', example_pages())
def test_every_runnable_example_has_colour(
    server: str,
    colour_context: BrowserContext,
    path: str,
    name: str,
) -> None:
    base_url: str = os.environ.get('DOCS_CONSOLE_BASE_URL', server)
    page: Page = colour_context.new_page()
    errors: list[str] = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on(
        'console',
        lambda message: (
            errors.append(message.text)
            if message.type == 'error'
            and not message.location.get('url', '').startswith(
                'https://media.ethicalads.io/'
            )
            else None
        ),
    )
    try:
        page.goto(f'{base_url.rstrip("/")}/{path}')
        panel: Locator = page.locator(f'.demo-run[data-demo="{name}"]')
        if name in {'howto/multibar', 'howto/parallel-execution'}:
            playwright_api.expect(panel).to_have_class(
                re.compile('demo-run-unavailable')
            )
            return
        button: Locator = panel.get_by_role('button', name='Run', exact=True)
        button.click()
        page.wait_for_function(
            'window.__consoleTestEvents.some(event => '
            "event.type === 'done' || event.type === 'error')",
            timeout=BOOT_TIMEOUT_MS,
        )
        assert not page.evaluate(
            "window.__consoleTestEvents.some(event => event.type === 'error')"
        ), panel.inner_text()
        page.wait_for_function('window.__consoleTestHasColour', timeout=3000)
        if name in {
            'tutorial/step2',
            'howto/unknown-length',
            'widgets/animated-marker',
        }:
            assert (
                page.evaluate('window.__consoleTestSpinnerColours.length') >= 3
            )
        assert not errors
    finally:
        page.close()
