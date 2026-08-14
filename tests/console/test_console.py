"""Smoke test for the in-browser console.

This is the only guard against the Pyodide layer breaking silently: the
worker, the wheels and the directive all have to work for it to pass, and
Read the Docs rebuilds -- and republishes -- on every commit whether or
not this test ran. See ``.github/workflows/docs.yml`` for the job that
runs it on every push and pull request.

Reading terminal content: the vendored xterm.js renders to a ``<canvas>``,
not to text nodes -- confirmed empirically here (a naive
``.demo-terminal`` ``.innerText`` check never observes any content, even
seconds after a run finishes and xterm's own buffer holds the right
text). So every assertion about what the terminal shows reads xterm's
buffer API directly (``terminal.buffer.active``), reached by wrapping the
page's global ``Terminal`` constructor before livecode.js constructs one
(see ``CONSOLE_TEST_INIT_SCRIPT``) -- not the DOM.

Three things are covered, chosen by what would hurt most if it broke
silently:

* ``test_run_button_streams_progress_to_completion`` -- the console runs
  a real demo to completion, and does so *progressively*: frames have to
  arrive as the interpreter executes, not as one write at the very end.
  A regression that buffered all output until the last moment would
  still reach 100% (a naive "did it finish" assertion would pass), so
  the discrete-writes-over-time shape is asserted directly, from a
  timestamped log of every message the worker posts (independent of
  xterm entirely).
* ``test_multibar_demos_have_no_run_button`` -- ``MultiBar``'s ``with``
  form starts a real OS thread, which Pyodide cannot provide
  (``Thread.start()`` raises there). ``howto/multibar`` is the one page
  in the built site that uses it (``readme/multibar`` is registered for
  SVG rendering only -- ``README.md`` embeds it as a static image for
  PyPI/GitHub, never through the ``.. demo::`` directive, so it never
  produces a ``.demo-run`` element to test). The Run button must never
  be offered there, and the contrast case
  (``howto/multibar-line-offset``, which does not use the threaded
  form) must still get one -- otherwise this test would pass whether or
  not the exclusion list actually did anything.
* ``test_boot_failure_retries_with_a_fresh_worker`` -- regression test
  for the bug fixed in af7bcf2 (refined in 61c10a3): the worker posts one
  ``error`` shape for both boot-phase and run-phase failures.
  ``bootWorker()`` used to settle its promise on neither for a boot-phase
  error, so a missing wheel or a 404 on ``wheels.json`` hung the
  awaiting click forever, and the *cached* promise made every later
  click hang too, stuck on "Downloading Python...". A 404'd
  ``wheels.json`` reproduces the original bug's exact trigger.
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import json
import os
import pathlib
import threading
import typing

import pytest

# Skipping is right locally -- playwright is not in the default test
# extra. It is wrong in CI: this suite is the only automated gate on the
# in-browser console, and a console that is dead publishes silently on
# every Read the Docs rebuild. A green job that ran nothing is worse than
# a red one, so under CI a missing playwright is a hard failure.
if os.environ.get('CI'):
    import playwright.sync_api as playwright_api
else:
    playwright_api = pytest.importorskip('playwright.sync_api')

if typing.TYPE_CHECKING:
    from playwright.sync_api import Browser, Page, Route

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUILD = ROOT / 'docs' / '_build' / 'html'

# Pyodide is a multi-megabyte cold download (the runtime plus its stdlib
# zip), fetched from jsdelivr's CDN over real network in CI -- not
# something a fixed few-second timeout survives. Both tests below that
# boot the worker use this budget; a browser context is shared across the
# module (see `browser` fixture) so the second boot mostly hits the
# in-context HTTP cache instead of paying the download twice.
BOOT_TIMEOUT_MS = 180_000

# Installed via `page.add_init_script`, so it runs before livecode.js on
# every navigation. Two independent pieces of instrumentation, neither
# reachable from outside the page any other way:
#
# * Wraps the global `Worker` constructor to record, for every worker
#   the page creates, a timestamped log of every message it posts back --
#   independent of livecode.js's own `onmessage` handling (a second
#   `addEventListener('message', ...)` on the same worker does not
#   interfere with the `onmessage=` assignment livecode.js makes; both
#   fire). Gives an exact count of discrete `type: 'output'` writes (to
#   catch a regression that buffers into one write) and an exact count of
#   `new Worker(...)` calls (to prove a retry after failure builds a real
#   new worker rather than hanging on the first one).
# * Wraps the global `Terminal` constructor -- via a property setter,
#   since (unlike `Worker`) `Terminal` does not exist yet when this
#   script runs; it is assigned later by the vendored xterm.js UMD
#   bundle, which this setter intercepts -- so `.buffer.active` is
#   reachable from Python for whichever demo panel gets created.
CONSOLE_TEST_INIT_SCRIPT = """
window.__consoleTestEvents = [];
window.__consoleTestWorkerCount = 0;
window.__consoleTestTerminal = null;
(() => {
  const OriginalWorker = window.Worker;
  window.Worker = new Proxy(OriginalWorker, {
    construct(target, args) {
      window.__consoleTestWorkerCount += 1;
      const worker = new target(...args);
      worker.addEventListener('message', (event) => {
        const data = event.data || {};
        const t = performance.now();
        window.__consoleTestEvents.push({t, type: data.type});
      });
      return worker;
    },
  });
})();
(() => {
  let realTerminal;
  Object.defineProperty(window, 'Terminal', {
    configurable: true,
    get() { return realTerminal; },
    set(value) {
      realTerminal = new Proxy(value, {
        construct(target, args) {
          const instance = new target(...args);
          window.__consoleTestTerminal = instance;
          return instance;
        },
      });
    },
  });
})();
window.__consoleTestTerminalText = () => {
  const term = window.__consoleTestTerminal;
  if (!term) return null;
  const buffer = term.buffer.active;
  const lines = [];
  for (let i = 0; i < buffer.length; i++) {
    lines.push(buffer.getLine(i).translateToString(true));
  }
  return lines.join('\\n');
};
"""

# Passed to `page.wait_for_function`: polls xterm's buffer (not the DOM --
# see the module docstring) for a substring. `%s` is filled with a JSON
# string, not interpolated from anywhere untrusted.
_WAIT_FOR_TERMINAL_TEXT = """
() => {
  const text = window.__consoleTestTerminalText();
  return !!text && text.includes(%s);
}
"""


@pytest.fixture(scope='module')
def server() -> typing.Iterator[str]:
    if not BUILD.is_dir():
        # Same reasoning as the playwright import above: locally this is a
        # convenience, in CI it would mean the console's only gate reported
        # green without testing anything.
        message = 'docs are not built; run `tox -e docs` first'
        if os.environ.get('CI'):
            pytest.fail(message)
        pytest.skip(message)

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(BUILD),
    )
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{httpd.server_address[1]}'
    finally:
        httpd.shutdown()


@pytest.fixture(scope='module')
def browser() -> typing.Iterator[Browser]:
    # Module-scoped and shared across every test below (each test gets
    # its own page/context via the `page` fixture) so that jsdelivr's
    # Pyodide download -- the expensive part -- is subject to a single
    # browser process's HTTP cache rather than re-paid per test.
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        with contextlib.suppress(playwright_api.Error):
            browser.close()


@pytest.fixture()
def page(
    browser: Browser,
) -> typing.Iterator[tuple[Page, list[str]]]:
    context = browser.new_context()
    context.add_init_script(CONSOLE_TEST_INIT_SCRIPT)
    page = context.new_page()
    errors: list[str] = []
    page.on(
        'console',
        lambda message: (
            errors.append(message.text) if message.type == 'error' else None
        ),
    )
    yield page, errors
    with contextlib.suppress(playwright_api.Error):
        context.close()


def _worker_events(page: Page) -> list[dict]:
    return page.evaluate('window.__consoleTestEvents')


def _worker_count(page: Page) -> int:
    return page.evaluate('window.__consoleTestWorkerCount')


def _wait_for_terminal_text(page: Page, needle: str, timeout: int) -> None:
    """Wait until xterm's buffer (not the DOM) contains ``needle``."""

    page.wait_for_function(
        _WAIT_FOR_TERMINAL_TEXT % json.dumps(needle),
        timeout=timeout,
    )


def test_run_button_streams_progress_to_completion(
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    browser_page, errors = page
    browser_page.goto(f'{server}/widgets/bar.html')
    browser_page.click('.demo-button')
    _wait_for_terminal_text(browser_page, '100%', timeout=BOOT_TIMEOUT_MS)

    output_events = [
        event
        for event in _worker_events(browser_page)
        if event['type'] == 'output'
    ]
    # The demo (widgets/bar.py) calls `bar.update()` 24 times, but the
    # library's own update-rate gate (min_poll_interval) can coalesce
    # several of those into one redraw depending on real elapsed time, so
    # the exact count isn't stable across machines. >= 3 is chosen to sit
    # well clear of both ends: comfortably above what a single
    # buffered-to-one-write regression would produce (1), and comfortably
    # below what was actually observed in manual runs (5).
    assert len(output_events) >= 3, (
        f'expected several discrete writes as the bar progressed, got '
        f'{len(output_events)}: a burst-at-the-end regression would '
        f'still reach 100% but would show up here as ~1 write'
    )
    span_ms = output_events[-1]['t'] - output_events[0]['t']
    assert span_ms >= 20, (
        f'writes spanned only {span_ms:.2f}ms -- that is one JS tick, '
        f'not output arriving as the interpreter actually runs'
    )

    assert not errors, f'console errors during a normal run: {errors}'


def test_multibar_demos_have_no_run_button(
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    browser_page, _errors = page
    browser_page.goto(f'{server}/howto/multibar.html')
    container = browser_page.locator('.demo-run[data-demo="howto/multibar"]')
    expect_ = playwright_api.expect
    expect_(container).to_have_class('demo-run demo-run-unavailable')
    assert container.locator('.demo-button').count() == 0
    assert 'cannot start one' in container.inner_text()

    # Contrast case: a demo that stacks bars by hand (no `MultiBar`, no
    # thread) must still get a Run button, so this isn't just "nothing on
    # this page ever runs" passing by coincidence.
    browser_page.goto(f'{server}/howto/multibar-line-offset.html')
    other = browser_page.locator(
        '.demo-run[data-demo="howto/multibar-line-offset"]'
    )
    expect_(other.locator('.demo-button')).to_have_count(1)


def test_boot_failure_retries_with_a_fresh_worker(
    server: str,
    page: tuple[Page, list[str]],
) -> None:
    """Regression test for af7bcf2 / 61c10a3.

    A 404 on ``wheels.json`` reproduces the original bug's exact
    trigger: the worker reaches its 'installing' stage (so it has
    already loaded the real Pyodide runtime) and then fails before ever
    posting 'ready'.
    """
    browser_page, _errors = page

    def fail_wheels_manifest(route: Route) -> None:
        route.fulfill(status=404, body='not found')

    browser_page.route('**/_static/wheels/wheels.json', fail_wheels_manifest)
    browser_page.goto(f'{server}/widgets/bar.html')

    browser_page.click('.demo-button')
    # Before the fix this hung on "Downloading Python..." forever; this
    # wait_for_function times out (test fails) rather than hanging if
    # that regresses.
    _wait_for_terminal_text(
        browser_page, 'Failed to start Python', timeout=BOOT_TIMEOUT_MS
    )
    browser_page.wait_for_function(
        "!document.querySelector('.demo-button').disabled",
        timeout=5_000,
    )

    browser_page.click('.demo-button')
    _wait_for_terminal_text(
        browser_page, 'Failed to start Python', timeout=BOOT_TIMEOUT_MS
    )

    # The real assertion: a second, independent `new Worker(...)` was
    # constructed for the retry -- not the first (dead) worker reused,
    # and not a hang. `resetWorker()` nulling out the cached `booting`
    # promise is what makes this 2 instead of 1.
    assert _worker_count(browser_page) == 2
