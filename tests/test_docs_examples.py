from __future__ import annotations

import importlib.util
import io
import pathlib
import sys
import types

import pytest

import progressbar.utils

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_docs_examples(repo_root: pathlib.Path) -> types.ModuleType:
    """Import ``docs/examples`` by path, under a private module name.

    ``docs/examples`` cannot be imported as top-level ``examples`` -- e.g.
    via ``sys.path.insert(0, str(repo_root / 'docs'))`` followed by
    ``import examples`` -- because that name collides with the real
    top-level ``examples.py`` demo runner. Once Python caches the wrong
    module under ``sys.modules['examples']`` the collision is permanent
    for the rest of the process: ``tests/test_progressbar.py`` does
    ``import examples`` expecting the real module, and broke with
    ``AttributeError: module 'examples' has no attribute 'examples'`` the
    first time this was tried via ``sys.path``. Loading by file path
    under a private name sidesteps ``sys.path`` and the ``examples`` name
    entirely. ``docs/examples/__init__.py`` re-exports everything a
    caller needs (``Demo``, ``DEMOS``, ``DEMOS_BY_NAME``, ``EXAMPLES_DIR``,
    ``load_example``), so this one call is all any consumer needs.
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


docs_examples = load_docs_examples(ROOT)
load_example = docs_examples.load_example
DEMOS = docs_examples.DEMOS
DEMOS_BY_NAME = docs_examples.DEMOS_BY_NAME
EXAMPLES_DIR = docs_examples.EXAMPLES_DIR


class FakeTerminal(io.StringIO):
    """A StringIO that claims to be a terminal, like a real pty would."""

    encoding = 'utf-8'

    def isatty(self) -> bool:
        return True


def test_every_demo_has_a_module() -> None:
    missing = [demo.name for demo in DEMOS if not demo.path.is_file()]
    assert not missing


def test_every_module_has_a_demo() -> None:
    known = {demo.path for demo in DEMOS}
    on_disk = {
        path
        for path in EXAMPLES_DIR.rglob('*.py')
        if not path.name.startswith('_')
    }
    assert on_disk == known


def test_demo_names_are_unique() -> None:
    assert len(DEMOS_BY_NAME) == len(DEMOS)


@pytest.fixture
def terminal(monkeypatch: pytest.MonkeyPatch) -> FakeTerminal:
    """A fake pty-like stdout that examples' rendered output actually reaches.

    Patching ``sys.stdout`` alone is not enough. ``progressbar.utils``
    builds a module-level ``StreamWrapper`` singleton (``streams``) once,
    at first import, snapshotting whatever ``sys.stdout``/``sys.stderr``
    were at that moment into ``original_stdout``/``original_stderr``
    (progressbar/utils.py:297-298). In a pytest session that import
    happens via ``tests/conftest.py`` at collection time -- long before
    this fixture ever runs -- so the snapshot is stale real streams, not
    this test's fake terminal.

    ``DefaultFdMixin.__init__`` (progressbar/bar.py:245-247) then remaps
    any ``fd`` that ``is sys.stdout``/``is sys.stderr`` back to that
    snapshot. That is deliberate: it is what stops ``redirect_stdout=True``
    from writing into the very ``WrappingIO`` it uses to capture prints,
    which would recurse. The side effect is that patching ``sys.stdout``
    alone is invisible to progressbar -- every example's bar output keeps
    going to whatever the stale snapshot points at, never to this fixture.

    So patch the snapshot too, and also ``streams.stdout``/``streams.stderr``
    (the "currently active, possibly wrapped" stream the singleton tracks),
    so both resolve to this fake terminal for the duration of the test.
    ``monkeypatch`` restores all four attributes afterwards regardless of
    what an example did to them in between -- important because examples
    that call ``wrap_stdout()``/``wrap_stderr()`` (via
    ``redirect_stdout=True``/``redirect_stderr=True``) mutate
    ``streams.stdout``/``streams.stderr`` in place; without restoring
    those too, a wrap left active by one example would leak into whatever
    example or test runs next.

    Deliberately does NOT patch the raw ``sys.stdout``/``sys.stderr``
    globals here. pytest's own capture manager reinstalls its own
    stdout/stderr wrapper when the test's "call" phase begins -- a
    fixture's setup-phase ``sys.stdout`` patch is silently gone by the
    time the test body runs (confirmed with a minimal reproduction
    outside this project's conftest.py entirely: a fixture that does
    ``monkeypatch.setattr(sys, 'stdout', fake)`` and a test that asserts
    ``sys.stdout is fake`` on its first line fails every time under
    pytest's default capture; the same assertion made directly in the
    test body, not a fixture, passes every time). Examples whose fd
    resolution goes through ``streams.original_stdout``/``.original_stderr``
    (the whole point of the two paragraphs above) are unaffected. An
    example that reads ``sys.stdout`` directly needs it patched again in
    the test body -- see ``test_example_runs``.
    """
    fake_terminal = FakeTerminal()
    monkeypatch.setattr(
        progressbar.utils.streams, 'original_stdout', fake_terminal
    )
    monkeypatch.setattr(progressbar.utils.streams, 'stdout', fake_terminal)
    monkeypatch.setattr(
        progressbar.utils.streams, 'original_stderr', fake_terminal
    )
    monkeypatch.setattr(progressbar.utils.streams, 'stderr', fake_terminal)
    return fake_terminal


@pytest.mark.no_freezegun
@pytest.mark.parametrize('demo', DEMOS, ids=lambda demo: demo.name)
def test_example_runs(
    demo, terminal: FakeTerminal, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Must happen here, in the test body, not inside the `terminal`
    # fixture -- see the fixture's docstring for why a fixture-time patch
    # of the raw sys.stdout global does not survive into this function.
    monkeypatch.setattr(sys, 'stdout', terminal)
    monkeypatch.setenv('COLUMNS', str(demo.term_width))
    load_example(demo).main()
    assert terminal.getvalue()


def test_examples_py_runs_every_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, 'stdout', FakeTerminal())
    spec = importlib.util.spec_from_file_location(
        'progressbar_root_examples', ROOT / 'examples.py'
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert {demo.name for demo in module.DEMOS} == set(DEMOS_BY_NAME)


@pytest.mark.no_freezegun
def test_logging_integration_retargets_preexisting_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`howto/logging-integration` must retarget its handler, not just run.

    ``test_example_runs`` only proves the bar rendered -- it never proves
    the demo's actual point (a ``logging`` call landing cleanly above the
    bar) works, because a fresh ``logging.StreamHandler()`` binds whatever
    raw ``sys.stderr`` is at construction time, and the shared ``terminal``
    fixture above patches only ``streams.original_stderr``/``streams.
    stderr``, not that raw global -- so ``wrap_logging()``'s identity-keyed
    matching never finds the handler, and the assertion in
    ``test_example_runs`` passes on bar output alone regardless of whether
    retargeting works.

    Fixing that means also patching raw ``sys.stderr`` (in the body, same
    reason as ``test_example_runs``'s ``sys.stdout`` patch), which this
    test does -- but scoped to its own demo rather than the shared
    ``test_example_runs``, which patches ``sys.stdout``/``sys.stderr`` for
    all 50 demos at once: doing that broadly breaks every *other* demo's
    default (``fd=sys.stderr``) resolution instead, since ``ProgressBar``'s
    ``fd`` default is only remapped to the fixture's fake stream when it
    ``is`` the live ``sys.stderr`` at construction time -- confirmed
    empirically, patching ``sys.stderr`` there failed 43 of the other
    parametrised cases.

    This also needs *two distinct* fake streams, not the shared `terminal`
    fixture's single object for both stdout and stderr: `wrap_logging()`
    builds its retarget map as a dict keyed by stream identity, and when
    `original_stdout` and `original_stderr` are the same object, the
    stdout-keyed entry silently overwrites the stderr-keyed one, so the
    handler's stream is left unretargeted purely as an artifact of the two
    streams coinciding -- confirmed by reproducing it with the shared
    single-object fixture before switching to two here. That coincidence
    never happens in a real process (stdout and stderr are always
    different objects), so this is specific to a single-stream test
    double, not a bug in the demo -- worth a heads up to whoever owns
    `wrap_logging()` next, since any demo combining `wrap_stdout()` +
    `wrap_stderr()` + `wrap_logging()` would hit the same thing.

    The assertion checks for *clean* separation, not mere presence: without
    retargeting, the log line is written unwrapped, mid-redraw, landing
    glued onto the tail of the bar's last render with no separating
    carriage return; with it, the bar clears its line first. Confirmed by
    temporarily removing the demo's ``wrap_logging()`` call and re-running
    this test: it failed, with the log line stuck onto the end of the
    previous bar redraw instead of following a carriage return.
    """
    # Defensive: an unrelated leak elsewhere in the suite (a ProgressBar
    # built with redirect_stdout=True/redirect_stderr=True whose finish()
    # never runs -- confirmed of tests/terminal.py's test_stdout_
    # redirection/test_stderr_redirection, which leak streams.
    # wrapped_stdout/wrapped_stderr at 1 for the rest of the process,
    # since a bar registered as a listener but never unregistered via
    # stop_capturing() keeps `streams` holding a reference to it forever,
    # so it's never garbage-collected and __del__ never runs) can leave
    # these counters stuck above zero before this test even starts.
    # wrap_stdout()/wrap_stderr() only build a fresh WrappingIO when their
    # counter is currently zero, so a stuck counter would make this demo's
    # own wrap_stderr() silently reuse a stale wrapper bound to some
    # earlier test's stream instead of stderr_fake -- the same failure
    # this test exists to catch, but from the wrong cause. Force a clean
    # slate first, the same way tests/test_stream.py's
    # reset_wrapped_streams() does.
    progressbar.utils.streams.wrapped_stdout = 0
    progressbar.utils.streams.wrapped_stderr = 0
    progressbar.utils.streams.wrapped_logging = 0
    progressbar.utils.streams.logging_handlers.clear()
    progressbar.utils.streams.listeners.clear()
    progressbar.utils.streams.capturing = 0

    stdout_fake = FakeTerminal()
    stderr_fake = FakeTerminal()
    monkeypatch.setattr(
        progressbar.utils.streams, 'original_stdout', stdout_fake
    )
    monkeypatch.setattr(progressbar.utils.streams, 'stdout', stdout_fake)
    monkeypatch.setattr(
        progressbar.utils.streams, 'original_stderr', stderr_fake
    )
    monkeypatch.setattr(progressbar.utils.streams, 'stderr', stderr_fake)
    monkeypatch.setattr(sys, 'stdout', stdout_fake)
    monkeypatch.setattr(sys, 'stderr', stderr_fake)
    monkeypatch.setenv('COLUMNS', '112')

    demo = DEMOS_BY_NAME['howto/logging-integration']
    load_example(demo).main()

    output = stderr_fake.getvalue()
    marker = 'completed step 8'
    index = output.index(marker)
    assert output[index - 1] == '\r', (
        'log line is not cleanly separated from the bar redraw -- '
        f'wrap_logging() did not retarget the handler: '
        f'{output[max(0, index - 60) : index + len(marker)]!r}'
    )
