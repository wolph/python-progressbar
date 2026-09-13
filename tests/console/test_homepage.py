"""Browser checks for the documentation homepage and its existing console."""

from __future__ import annotations

import typing

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
    browser_page.route('**/_static/examples/tutorial-step1.py', _missing)
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


def test_showcase_reduced_motion_and_failed_recording_keep_guides(
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    browser_page: Page = page[0]
    browser_page.emulate_media(reduced_motion='reduce')
    browser_page.goto(f'{server}/index.html')
    playwright_api.expect(
        browser_page.get_by_role('button', name='Reduced motion')
    ).to_be_disabled()
    browser_page.wait_for_function(
        """() => {
            const root = document.querySelector('#showcase-recording')
                .contentDocument.documentElement;
            const groups = root.querySelectorAll('g');
            return getComputedStyle(groups[0]).display === 'none'
                && getComputedStyle(groups[groups.length - 1]).opacity === '1';
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
