"""Browser checks for the documentation homepage and its existing console."""

from __future__ import annotations

import typing

import pytest

from .test_console import (
    BOOT_TIMEOUT_MS,
    _wait_for_terminal_text,
    _worker_count,
    browser as browser,
    page as page,
    playwright_api,
    server as server,
)

if typing.TYPE_CHECKING:
    from playwright.sync_api import (
        Browser,
        BrowserContext,
        Locator,
        Page,
        Request,
        Route,
    )


def _missing(route: Route) -> None:
    route.fulfill(status=404, body='not found')


def _stale_home_styles(route: Route) -> None:
    route.fulfill(
        content_type='text/css',
        body='.home-quickstart .demo-source { display: none; }',
    )


def _stale_example_source(route: Route) -> None:
    route.fulfill(
        content_type='text/plain',
        body="print('Cached example from an earlier build')",
    )


def test_homepage_loads_python_only_after_run(
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    browser_page: Page = page[0]
    downloads: list[str] = []

    def record_download(request: Request) -> None:
        if 'pyodide' in request.url or '/wheels/' in request.url:
            downloads.append(request.url)

    browser_page.on('request', record_download)
    browser_page.route('**/_static/home.css', _stale_home_styles)
    browser_page.goto(f'{server}/index.html')
    button: Locator = browser_page.locator('.home-quickstart .demo-button')
    playwright_api.expect(button).to_be_visible()
    source: Locator = browser_page.locator('.home-quickstart .demo-source')
    playwright_api.expect(source).to_be_visible()
    theme: str
    for theme in ('light', 'dark'):
        browser_page.locator('body').evaluate(
            '(body, theme) => body.dataset.theme = theme', theme
        )
        assert source.locator('.kn').first.evaluate(
            '(node) => getComputedStyle(node).color'
        ) != source.locator('pre').evaluate(
            '(node) => getComputedStyle(node).color'
        )
    assert _worker_count(browser_page) == 0
    assert not downloads
    button.click()
    _wait_for_terminal_text(browser_page, '100%', BOOT_TIMEOUT_MS)
    assert _worker_count(browser_page) == 1
    assert not page[1]


def test_homepage_can_edit_run_and_reset_the_example(
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    browser_page: Page = page[0]
    browser_page.goto(f'{server}/index.html')
    source: Locator = browser_page.locator('.home-quickstart .demo-source')
    editor: Locator = browser_page.get_by_role(
        'textbox', name='Python example source'
    )
    edit: Locator = browser_page.get_by_role('button', name='Edit code')
    edit.click()
    playwright_api.expect(editor).to_be_focused()
    playwright_api.expect(source).to_be_hidden()
    original: str = editor.input_value()
    editor.fill("print('Edited example ran')")
    browser_page.get_by_role('button', name='Run', exact=True).click()
    _wait_for_terminal_text(
        browser_page, 'Edited example ran', BOOT_TIMEOUT_MS
    )
    browser_page.get_by_role('button', name='Reset example').click()
    playwright_api.expect(source).to_be_visible()
    playwright_api.expect(editor).to_be_hidden()
    playwright_api.expect(edit).to_be_focused()
    assert browser_page.locator('.demo-editor').input_value() == original
    assert not page[1]


def test_homepage_output_has_colour_and_fits_after_resizing(
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    browser_page: Page = page[0]
    browser_page.goto(f'{server}/index.html')
    width: int
    for width in (1440, 768, 375):
        browser_page.set_viewport_size({'width': width, 'height': 1000})
        browser_page.get_by_role('button', name='Run', exact=True).click()
        _wait_for_terminal_text(browser_page, '100%', BOOT_TIMEOUT_MS)
        browser_page.wait_for_function("""() => {
            const term = window.__consoleTestTerminal;
            const line = term.buffer.active.getLine(0);
            return [...Array(term.cols).keys()].some(x => {
                const cell = line.getCell(x);
                return cell.getChars() === '#' && !cell.isFgDefault();
            });
        }""")
        geometry: dict[str, float | str] = browser_page.locator(
            '.home-quickstart .demo-terminal'
        ).evaluate("""panel => {
            const viewport = panel.querySelector('.xterm-viewport');
            return {
                width: panel.clientWidth,
                scrollWidth: panel.scrollWidth,
                height: panel.clientHeight,
                viewportHeight: viewport.clientHeight,
                scrollHeight: viewport.scrollHeight,
                overflowY: getComputedStyle(viewport).overflowY,
            };
        }""")
        assert geometry['scrollWidth'] <= geometry['width']
        assert geometry['scrollHeight'] <= geometry['viewportHeight']
        assert geometry['height'] < 100
        assert geometry['overflowY'] == 'auto'
    assert not page[1]


@pytest.mark.parametrize(
    'path',
    [
        'tutorial/step1.html',
        'howto/iterable-wrapper.html',
        'widgets/bar.html',
    ],
)
def test_guide_example_has_one_code_view_and_coloured_output(
    server: str,
    page: tuple[Page, list[str]],
    path: str,
) -> None:
    browser_page: Page = page[0]
    browser_page.route('**/_static/examples/*.py', _stale_example_source)
    browser_page.goto(f'{server}/{path}')
    source: Locator = browser_page.locator('.demo-source')
    editor: Locator = browser_page.locator('.demo-editor')
    playwright_api.expect(editor).to_be_attached()
    playwright_api.expect(source).to_be_visible()
    playwright_api.expect(editor).to_be_hidden()
    assert editor.input_value().strip() == source.inner_text().strip()
    browser_page.get_by_role('button', name='Run', exact=True).click()
    _wait_for_terminal_text(browser_page, '100%', BOOT_TIMEOUT_MS)
    browser_page.wait_for_function(
        """() => {
        const term = window.__consoleTestTerminal;
        const line = term.buffer.active.getLine(0);
        return [...Array(term.cols).keys()].some(x => {
            const cell = line.getCell(x);
            return cell.getChars() === '#' && !cell.isFgDefault();
        });
    }""",
        timeout=5000,
    )
    browser_page.get_by_role('button', name='Edit code').click()
    playwright_api.expect(source).to_be_hidden()
    playwright_api.expect(editor).to_be_focused()
    browser_page.get_by_role('button', name='Reset example').click()
    playwright_api.expect(source).to_be_visible()
    playwright_api.expect(editor).to_be_hidden()
    assert not page[1]


def test_showcase_keyboard_updates_recording_title_and_guide(
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    browser_page: Page = page[0]
    browser_page.goto(f'{server}/index.html')
    tabs: Locator = browser_page.get_by_role('tab')
    recording: Locator = browser_page.locator('#showcase-recording')
    title: Locator = browser_page.locator('#showcase-title')
    guide: Locator = browser_page.locator('#showcase-guide')
    playwright_api.expect(tabs).to_have_count(3)
    tabs.first.focus()
    browser_page.keyboard.press('ArrowRight')
    playwright_api.expect(tabs.nth(1)).to_be_focused()
    playwright_api.expect(tabs.nth(1)).to_have_attribute(
        'aria-selected', 'true'
    )
    playwright_api.expect(recording).to_have_attribute(
        'data', '_static/demos/readme-multibar.svg'
    )
    playwright_api.expect(title).to_have_text('Several jobs in one terminal')
    playwright_api.expect(guide).to_have_attribute(
        'href', 'howto/multibar.html'
    )
    browser_page.keyboard.press('End')
    playwright_api.expect(tabs.last).to_be_focused()
    playwright_api.expect(guide).to_have_attribute(
        'href', 'howto/redirect-stdout.html'
    )
    browser_page.keyboard.press('Home')
    playwright_api.expect(tabs.first).to_be_focused()


def test_showcase_pause_survives_tab_change(
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    browser_page: Page = page[0]
    browser_page.goto(f'{server}/index.html')
    pause: Locator = browser_page.get_by_role('button', name='Pause recording')
    playwright_api.expect(pause).to_be_enabled()
    pause.click()
    browser_page.wait_for_function(
        "document.querySelector('#showcase-recording')"
        '.contentDocument?.documentElement.animationsPaused()'
    )
    browser_page.get_by_role('tab', name='Multiple jobs').click()
    browser_page.wait_for_function(
        "document.querySelector('#showcase-recording')"
        '.contentDocument?.documentElement.animationsPaused()'
    )
    browser_page.get_by_role('button', name='Resume recording').click()
    browser_page.wait_for_function(
        "!document.querySelector('#showcase-recording')"
        '.contentDocument.documentElement.animationsPaused()'
    )


def test_homepage_theme_and_no_javascript_fallback(
    server: str,
    browser: Browser,
    page: tuple[Page, list[str]],
) -> None:
    browser_page: Page = page[0]
    browser_page.goto(f'{server}/index.html')
    browser_page.emulate_media(color_scheme='dark')
    toggle: Locator = browser_page.get_by_role(
        'button', name='Toggle Light / Dark / Auto colour theme'
    )
    theme: str
    for theme in ('light', 'dark', 'auto'):
        toggle.click()
        playwright_api.expect(browser_page.locator('body')).to_have_attribute(
            'data-theme', theme
        )
    context: BrowserContext = browser.new_context(java_script_enabled=False)
    try:
        static_page: Page = context.new_page()
        static_page.goto(f'{server}/index.html')
        playwright_api.expect(
            static_page.get_by_role(
                'heading', name='Your work. In full colour.'
            )
        ).to_be_visible()
        playwright_api.expect(
            static_page.locator('.home-quickstart .demo-source')
        ).to_be_visible()
        playwright_api.expect(
            static_page.get_by_role('link', name='Get started', exact=True)
        ).to_be_visible()
        playwright_api.expect(
            static_page.locator('#showcase-recording')
        ).to_be_visible()
        assert static_page.get_by_role('tab').count() == 0
    finally:
        context.close()


def test_homepage_source_failure_keeps_readable_example(
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    browser_page: Page = page[0]
    browser_page.route('**/_static/examples/homepage-quickstart.py*', _missing)
    browser_page.goto(f'{server}/index.html')
    playwright_api.expect(
        browser_page.locator('.home-quickstart .demo-run')
    ).to_have_text('Live console unavailable.')
    playwright_api.expect(
        browser_page.locator('.home-quickstart .demo-source')
    ).to_be_visible()
    playwright_api.expect(
        browser_page.get_by_role('link', name='Follow the tutorial')
    ).to_be_visible()


def test_showcase_animates_under_reduced_motion_and_failed_recording_keep_guides(  # noqa: E501
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    browser_page: Page = page[0]
    # The recording must keep playing even when the visitor's OS asks for
    # reduced motion (e.g. Windows with "Animation effects" turned off).
    browser_page.emulate_media(reduced_motion='reduce')
    browser_page.goto(f'{server}/index.html')
    playwright_api.expect(
        browser_page.get_by_role('button', name='Pause recording')
    ).to_be_enabled()
    browser_page.wait_for_function(
        """() => {
            const root = document.querySelector('#showcase-recording')
                .contentDocument.documentElement;
            const groups = Array.from(root.querySelectorAll('g'));
            const visible = groups.filter(
                (group) => getComputedStyle(group).opacity === '1');
            return !root.animationsPaused()
                && root.getCurrentTime() > 1
                && visible.length === 1
                && visible[0] !== groups[groups.length - 1];
        }"""
    )
    browser_page.route('**/readme-multibar.svg', _missing)
    browser_page.get_by_role('tab', name='Multiple jobs').click()
    guide: Locator = browser_page.locator('#showcase-guide')
    playwright_api.expect(guide).to_have_attribute(
        'href', 'howto/multibar.html'
    )
    playwright_api.expect(guide).to_be_visible()
    playwright_api.expect(
        browser_page.locator('#showcase-pause')
    ).to_be_disabled()
