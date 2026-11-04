import contextlib
import io
import random
import threading
import time

import pytest

import progressbar

N = 10
BARS = 3
SLEEP = 0.002


def test_multi_progress_bar_out_of_range() -> None:
    widgets = [
        progressbar.MultiProgressBar('multivalues'),
    ]

    bar = progressbar.ProgressBar(widgets=widgets, max_value=10)
    with pytest.raises(ValueError):
        bar.update(multivalues=[123])

    with pytest.raises(ValueError):
        bar.update(multivalues=[-1])


def test_multibar() -> None:
    multibar = progressbar.MultiBar(
        sort_keyfunc=lambda bar: bar.label,
        remove_finished=0.005,
    )
    multibar.show_initial = False
    multibar.render(force=True)
    multibar.show_initial = True
    multibar.render(force=True)
    multibar.start()

    multibar.append_label = False
    multibar.prepend_label = True

    # Test handling of progressbars that don't call the super constructors
    bar = progressbar.ProgressBar(max_value=N)
    bar.index = -1
    multibar['x'] = bar
    bar.start()
    # Test twice for other code paths
    multibar['x'] = bar
    multibar._label_bar(bar)
    multibar._label_bar(bar)
    bar.finish()
    del multibar['x']

    multibar.prepend_label = False
    multibar.append_label = True

    append_bar = progressbar.ProgressBar(max_value=N)
    append_bar.start()
    multibar._label_bar(append_bar)
    multibar['append'] = append_bar
    multibar.render(force=True)

    def do_something(bar):
        for j in bar(range(N)):
            time.sleep(0.01)
            bar.update(j)

    for i in range(BARS):
        thread = threading.Thread(
            target=do_something,
            args=(multibar[f'bar {i}'],),
        )
        thread.start()

    for bar in list(multibar.values()):
        for j in range(N):
            bar.update(j)
            time.sleep(SLEEP)

        multibar.render(force=True)

    multibar.remove_finished = False
    multibar.show_finished = False
    append_bar.finish()
    multibar.render(force=True)

    multibar.join(0.1)
    multibar.stop(0.1)


@pytest.mark.parametrize(
    'sort_key',
    [
        None,
        'index',
        'label',
        'value',
        'percentage',
        progressbar.SortKey.CREATED,
        progressbar.SortKey.LABEL,
        progressbar.SortKey.VALUE,
        progressbar.SortKey.PERCENTAGE,
    ],
)
def test_multibar_sorting(sort_key) -> None:
    with progressbar.MultiBar() as multibar:
        for i in range(BARS):
            label = f'bar {i}'
            multibar[label] = progressbar.ProgressBar(max_value=N)

        for bar in multibar.values():
            for _j in bar(range(N)):
                assert bar.started()
                time.sleep(SLEEP)

        for bar in multibar.values():
            assert bar.finished()


def test_offset_bar() -> None:
    with progressbar.ProgressBar(line_offset=2) as bar:
        for i in range(N):
            bar.update(i)


def test_multibar_show_finished() -> None:
    multibar = progressbar.MultiBar(show_finished=True)
    multibar['bar'] = progressbar.ProgressBar(max_value=N)
    multibar.render(force=True)
    with progressbar.MultiBar(show_finished=False) as multibar:
        multibar.finished_format = 'finished: {label}'

        for i in range(3):
            multibar[f'bar {i}'] = progressbar.ProgressBar(max_value=N)

        for bar in multibar.values():
            for i in range(N):
                bar.update(i)
                time.sleep(SLEEP)

            # The context manager waits for all bars to finish
            bar.finish()

        multibar.render(force=True)


def test_multibar_show_initial() -> None:
    multibar = progressbar.MultiBar(show_initial=False)
    multibar['bar'] = progressbar.ProgressBar(max_value=N)
    multibar.render(force=True)


def test_multibar_empty_key() -> None:
    multibar = progressbar.MultiBar()
    multibar[''] = progressbar.ProgressBar(max_value=N)

    for name in multibar:
        assert name == ''
        bar = multibar[name]
        bar.update(1)

    multibar.render(force=True)


def test_started_flag_not_observable_before_widgets(monkeypatch) -> None:
    """Regression: ``_started`` must not flip True before widgets are built.

    ``MultiBar.render()`` (potentially from a background thread) reads
    ``bar.started()`` and then ``_label_bar`` asserts ``bar.widgets``. If
    ``start()`` sets ``_started`` before populating ``default_widgets()`` there
    is a window where a concurrent reader observes ``started() is True`` with
    an empty ``widgets`` list and crashes on that assertion. Reproduced
    deterministically by capturing the widget list at the exact ``_started``
    flip.
    """
    import progressbar.bar as bar_module

    original_start = bar_module.ProgressBarMixinBase.start
    observed: dict[str, bool] = {}

    def recording_start(self, **kwargs):
        result = original_start(self, **kwargs)
        # `_started` has just flipped True here; capture whether the widget
        # list is already populated at this exact moment.
        observed['widgets_at_flip'] = bool(self.widgets)
        observed['started_at_flip'] = self.started()
        # update() re-enters start() while start_time is None, so a
        # concurrent update(force=True) would double-run the start path.
        observed['start_time_at_flip'] = self.start_time is not None
        return result

    monkeypatch.setattr(
        bar_module.ProgressBarMixinBase, 'start', recording_start
    )

    bar = progressbar.ProgressBar(max_value=N, fd=io.StringIO())
    bar.start()

    assert observed.get('started_at_flip') is True
    assert observed.get('widgets_at_flip') is True, (
        'widgets must be populated before started() can observe _started'
    )
    assert observed.get('start_time_at_flip') is True, (
        'start_time must be set before started() can observe _started'
    )


def test_multibar_print() -> None:
    bars = 5
    n = 10

    def print_sometimes(bar, probability, seed):
        # A per-thread seeded RNG keeps the interleaving jittery but fully
        # reproducible: a thread only ever touches its own RNG, so thread
        # scheduling cannot reorder its draws. Combined with the never/always
        # threads below this makes the print-guard branch coverage
        # deterministic instead of flakily depending on the global RNG.
        rng = random.Random(seed)
        for i in bar(range(n)):
            # Sleep a small, deterministic fraction of a second
            time.sleep(rng.random() * 0.01)

            # print messages at random intervals to show how extra output works
            if rng.random() < probability:
                bar.print('random message for bar', bar, i)

    with progressbar.MultiBar() as multibar:
        seed = 0
        threads: list[threading.Thread] = []
        for i in range(bars):
            # Get a progressbar
            bar = multibar[f'Thread label here {i}']
            bar.max_error = False
            # Create a thread and pass the progressbar. Print never (0.0),
            # sometimes (0.5) and always (1.0): the 0.0 and 1.0 threads
            # deterministically exercise both sides of the print guard on
            # every run, independent of the seeded middle thread.
            for probability in (0.0, 0.5, 1.0):
                thread = threading.Thread(
                    target=print_sometimes, args=(bar, probability, seed)
                )
                thread.start()
                threads.append(thread)
                seed += 1

        for i in range(5):
            multibar.print(f'{i}', flush=False)

        # Join the workers before leaving the context so none outlives the
        # multibar (a stray thread writing to a torn-down fd raised
        # "I/O operation on closed file") and every print branch has run.
        for thread in threads:
            thread.join()

        # Note: MultiBar inherits from dict, so update() would be
        # dict.update and insert bogus entries; render() is intended here
        multibar.render(force=True, flush=False)
        multibar.render(force=True, flush=True)


def test_multibar_no_format() -> None:
    with progressbar.MultiBar(
        initial_format=None, finished_format=None
    ) as multibar:
        bar = multibar['a']

        for i in bar(range(5)):
            bar.print(i)


def test_multibar_finished() -> None:
    multibar = progressbar.MultiBar(initial_format=None, finished_format=None)
    bar = multibar['bar'] = progressbar.ProgressBar(max_value=5)
    bar2 = multibar['bar2']
    multibar.render(force=True)
    multibar.print('Hi')
    multibar.render(force=True, flush=False)

    for i in range(6):
        bar.update(i)
        bar2.update(i)

    multibar.render(force=True)


def test_multibar_render_writes_started_bar_text() -> None:
    fd = io.StringIO()
    multibar = progressbar.MultiBar(
        fd=fd,
        initial_format=None,
        finished_format=None,
        remove_finished=None,
        sort_reverse=False,
        total=3,
        term_width=64,
    )
    build = multibar['build']
    test = multibar['test']
    multibar.render(force=True, flush=True)
    fd.seek(0)
    fd.truncate(0)

    build.update(1, force=True)
    test.update(1, force=True)
    multibar.render(force=True, flush=True)

    output = fd.getvalue()
    assert 'build' in output
    assert 'test' in output
    assert '(1 of 3)' in output


def test_multibar_wraps_pre_labeled_bar_stream() -> None:
    fd = io.StringIO()
    multibar = progressbar.MultiBar(
        fd=fd,
        initial_format=None,
        finished_format=None,
        remove_finished=None,
        sort_reverse=False,
        total=3,
        term_width=64,
    )
    bar = progressbar.ProgressBar(max_value=3)
    bar.label = 'build'
    multibar['build'] = bar

    bar.update(1, force=True)
    multibar.render(force=True, flush=True)

    output = fd.getvalue()
    assert 'build' in output
    assert '(1 of 3)' in output


def test_multibar_constructor_wraps_external_bar_stream() -> None:
    fd = io.StringIO()
    bar = progressbar.ProgressBar(max_value=3)
    multibar = progressbar.MultiBar(
        [('build', bar)],
        fd=fd,
        initial_format=None,
        finished_format=None,
        remove_finished=None,
        sort_reverse=False,
        total=3,
        term_width=64,
    )

    bar.update(1, force=True)
    multibar.render(force=True, flush=True)

    output = fd.getvalue()
    assert 'build' in output
    assert '(1 of 3)' in output


def test_multibar_constructor_accepts_mapping() -> None:
    fd = io.StringIO()
    bar = progressbar.ProgressBar(max_value=3)
    multibar = progressbar.MultiBar(
        {'build': bar},
        fd=fd,
        initial_format=None,
        finished_format=None,
        remove_finished=None,
        sort_reverse=False,
        total=3,
        term_width=64,
    )

    bar.update(1, force=True)
    multibar.render(force=True, flush=True)

    output = fd.getvalue()
    assert 'build' in output
    assert '(1 of 3)' in output


def test_multibar_finished_format() -> None:
    multibar = progressbar.MultiBar(
        finished_format='Finished {label}', show_finished=True
    )
    bar = multibar['bar'] = progressbar.ProgressBar(max_value=5)
    bar2 = multibar['bar2']
    multibar.render(force=True)
    multibar.print('Hi')
    multibar.render(force=True, flush=False)
    bar.start()
    bar2.start()
    multibar.render(force=True)
    multibar.print('Hi')
    multibar.render(force=True, flush=False)

    for i in range(6):
        bar.update(i)
        bar2.update(i)

    multibar.render(force=True)


def test_multibar_threads() -> None:
    multibar = progressbar.MultiBar(finished_format=None, show_finished=True)
    bar = multibar['bar'] = progressbar.ProgressBar(max_value=5)
    multibar.start()
    time.sleep(0.1)
    bar.update(3)
    time.sleep(0.1)
    # join() waits until all bars have finished, so finish first
    bar.finish()
    multibar.join()
    multibar.join()
    multibar.render(force=True)


def test_multibar_join_timeout_abandons_unfinished_bar() -> None:
    # A never-finishing bar must not hang a clean context-manager exit when
    # join_timeout is set; the unfinished bar is abandoned once it elapses.
    multibar = progressbar.MultiBar(fd=io.StringIO(), join_timeout=0.1)
    bar = progressbar.ProgressBar(max_value=10)
    multibar['stuck'] = bar
    # Fully start the bar before the render thread exists: started() flips
    # true before the widgets are populated, so a render tick during a
    # concurrent bar.start() can crash the render thread on the
    # empty-widgets assert -- join() then succeeds on a dead thread and the
    # timeout path this test exists to exercise is never taken.
    bar.start()
    bar.update(5)  # never reaches max_value / finish()

    def exit_context() -> None:
        with multibar:
            pass

    thread = threading.Thread(target=exit_context, daemon=True)
    thread.start()
    thread.join(timeout=5)
    exited = not thread.is_alive()

    # join_timeout leaves the render thread (a daemon) running so the
    # program can exit; stop it explicitly so it cannot leak into and
    # pollute later tests in the same process.
    multibar.stop()

    assert exited, 'clean context exit blocked despite join_timeout'


def test_multibar_instances_do_not_share_thread_state() -> None:
    # Regression: D1 - thread primitives were class attributes shared
    # between all MultiBar instances.
    multibar_a = progressbar.MultiBar(fd=io.StringIO())
    multibar_b = progressbar.MultiBar(fd=io.StringIO())

    assert multibar_a._thread_finished is not multibar_b._thread_finished
    assert multibar_a._thread_closed is not multibar_b._thread_closed
    assert multibar_a._print_lock is not multibar_b._print_lock


def test_multibar_stop_does_not_poison_new_instances() -> None:
    # Regression: D1 - stop() set a class-level Event, killing the render
    # loop of every MultiBar created afterwards.
    multibar = progressbar.MultiBar(fd=io.StringIO())
    multibar.start()
    multibar.stop(timeout=5)

    fresh = progressbar.MultiBar(fd=io.StringIO())
    assert not fresh._thread_finished.is_set()


def test_multibar_start_keeps_render_thread_alive() -> None:
    # Regression: D6 - start() called _thread_closed.set() instead of
    # clearing it, so an empty multibar's render thread exited before
    # any bars could be added.
    multibar = progressbar.MultiBar(fd=io.StringIO())
    multibar.start()
    try:
        assert not multibar._thread_closed.is_set()
        assert multibar._thread is not None
        multibar._thread.join(timeout=0.5)
        assert multibar._thread.is_alive()
    finally:
        multibar.stop(timeout=5)


def test_multibar_flush_does_not_emit_nul_bytes() -> None:
    # Regression: D3 - flush() truncated the buffer without seeking back,
    # so later writes padded the gap with NUL characters.
    fd = io.StringIO()
    multibar = progressbar.MultiBar(fd=fd)
    multibar.print('hello')
    multibar.print('world')

    assert '\x00' not in fd.getvalue()


def test_multibar_prepend_and_append_label() -> None:
    # Regression: D7 - the append_label branch was unreachable when
    # prepend_label was enabled as well.
    multibar = progressbar.MultiBar(
        prepend_label=True,
        append_label=True,
        fd=io.StringIO(),
    )
    bar = progressbar.ProgressBar(
        max_value=N,
        widgets=['x'],
        fd=io.StringIO(),
    )
    multibar['job'] = bar
    multibar._label_bar(bar)

    assert str(bar.widgets[0]).startswith('job')
    assert str(bar.widgets[-1]).startswith('job')


def test_multibar_join_timeout_keeps_thread_reference() -> None:
    # Regression: D8 - join(timeout) dropped the thread reference even
    # when the thread was still running.
    multibar = progressbar.MultiBar(fd=io.StringIO())
    assert multibar['unfinished'] is not None  # creates an unfinished bar
    multibar.start()
    try:
        multibar.join(timeout=0.01)
        assert multibar._thread is not None
        assert multibar._thread.is_alive()
    finally:
        multibar.stop(timeout=5)


def test_multibar_exception_in_context_exits_promptly() -> None:
    # Regression: D4 - an exception inside `with MultiBar()` hung forever
    # in __exit__ because join() waited for bars that never finish.
    holder: dict[str, progressbar.MultiBar] = {}

    def scenario() -> None:
        multibar = holder['multibar'] = progressbar.MultiBar(
            fd=io.StringIO(),
        )
        # Pre-fix the event is shared class state which other tests may
        # have set; post-fix this only touches this instance.
        multibar._thread_finished.clear()
        # The bar must exist before the render thread starts so the
        # thread observes an unfinished bar.
        multibar['a'].update(0)
        with contextlib.suppress(RuntimeError), multibar:
            raise RuntimeError('boom')

    worker = threading.Thread(target=scenario, daemon=True)
    worker.start()
    worker.join(timeout=5)
    try:
        assert not worker.is_alive(), '__exit__ hung on unfinished bars'
    finally:
        # Unstick the render thread regardless of the outcome
        holder['multibar']._thread_finished.set()


@pytest.mark.no_freezegun
def test_multibar_concurrent_mutation() -> None:
    # Real sleeps let the renderer yield while the main thread mutates bars.
    # Regression: D2 - the render thread iterated self.values() without a
    # snapshot while other threads add/remove bars.
    errors: list[threading.ExceptHookArgs] = []
    original_excepthook = threading.excepthook
    threading.excepthook = errors.append
    multibar = progressbar.MultiBar(fd=io.StringIO())
    # Pre-fix the event is shared class state which other tests may have
    # set; post-fix this only touches this instance.
    multibar._thread_finished.clear()
    assert multibar['keep'] is not None  # creates an unfinished bar
    multibar.start()
    try:
        for i in range(300):
            assert multibar[f'bar {i}'] is not None
            del multibar[f'bar {i}']
    finally:
        multibar.stop(timeout=5)
        threading.excepthook = original_excepthook

    assert not errors
    assert not multibar._thread or not multibar._thread.is_alive()


def test_render_of_a_bar_removed_mid_frame_does_not_leak() -> None:
    # The render thread snapshots the bars, then a worker deletes one
    # (task_finished); the finished-bar path must not stamp it back
    # into _finished_at after __delitem__ popped it.
    multibar = progressbar.MultiBar(fd=io.StringIO())
    bar_ = multibar['gone']
    bar_.start()
    bar_.finish()
    del multibar['gone']
    lines = list(
        multibar._render_finished_bar(
            bar_, time.monotonic(), None, lambda **kw: None
        )
    )
    assert lines == []
    assert bar_ not in multibar._finished_at


@pytest.mark.parametrize('mutation', ['assign', 'update', 'ior'])
def test_expiry_keeps_concurrent_replacement(mutation: str) -> None:
    import inspect
    import sys
    import types
    import typing

    multibar: progressbar.MultiBar = progressbar.MultiBar(
        fd=io.StringIO(), remove_finished=1
    )
    old: progressbar.ProgressBar = multibar['task']
    replacement: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO()
    )
    multibar._finished_at[old] = 0
    multibar._labeled.add(old)
    reached: threading.Event = threading.Event()
    resume: threading.Event = threading.Event()
    errors: list[BaseException] = []
    lines, first = inspect.getsourcelines(multibar._render_finished_bar)
    pause_line: int = first + next(
        i for i, line in enumerate(lines) if 'self.remove_finished' in line
    )

    def trace(
        frame: types.FrameType, event: str, arg: typing.Any
    ) -> typing.Any:
        if (
            event == 'line'
            and frame.f_code is multibar._render_finished_bar.__func__.__code__
            and frame.f_lineno == pause_line
        ):
            reached.set()
            assert resume.wait(3)
        return trace

    def render() -> None:
        sys.settrace(trace)
        try:
            list(
                multibar._render_finished_bar(old, 10, 9, lambda **kwargs: '')
            )
        except BaseException as error:
            errors.append(error)
        finally:
            sys.settrace(None)

    thread: threading.Thread = threading.Thread(target=render)
    thread.start()
    try:
        assert reached.wait(3)
        if mutation == 'assign':
            multibar['task'] = replacement
        elif mutation == 'update':
            multibar.update(task=replacement)
        else:
            multibar |= {'task': replacement}
    finally:
        resume.set()
        thread.join(3)
    assert not thread.is_alive()
    assert errors == []
    assert multibar.get('task') is replacement
    assert old not in multibar._finished_at
    assert old not in multibar._labeled
    assert replacement.label == 'task'


@pytest.mark.parametrize('removal', ['pop', 'popitem', 'clear', 'del'])
def test_membership_removal_cleans_tracking(removal: str) -> None:
    multibar: progressbar.MultiBar = progressbar.MultiBar(fd=io.StringIO())
    progress: progressbar.ProgressBar = multibar['task']
    multibar._finished_at[progress] = 0
    multibar._labeled.add(progress)
    if removal == 'pop':
        assert multibar.pop('task') is progress
    elif removal == 'popitem':
        assert multibar.popitem() == ('task', progress)
    elif removal == 'clear':
        multibar.clear()
    else:
        del multibar['task']
    assert not multibar
    assert not multibar._finished_at
    assert not multibar._labeled


def test_membership_dict_defaults_and_update_iterable() -> None:
    multibar: progressbar.MultiBar = progressbar.MultiBar(fd=io.StringIO())
    progress: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO()
    )
    assert multibar.setdefault('task', progress) is progress
    assert multibar.setdefault('task') is progress
    assert multibar.setdefault('none') is None
    assert multibar.pop('none') is None
    assert multibar.pop('missing', 42) == 42
    with pytest.raises(KeyError):
        multibar.pop('missing')
    with pytest.raises(TypeError):
        multibar.pop('missing', 1, 2)
    multibar.clear()
    with pytest.raises(KeyError):
        multibar.popitem()
    multibar.update([('task', progress)])
    assert multibar['task'] is progress


def test_membership_guard_is_released_before_finished_update() -> None:
    multibar: progressbar.MultiBar = progressbar.MultiBar(fd=io.StringIO())
    progress: progressbar.ProgressBar = multibar['task']
    unlocked: list[bool] = []

    def update(**kwargs: object) -> str:
        def observer() -> None:
            acquired: bool = multibar._membership_lock.acquire(timeout=1)
            unlocked.append(acquired)
            if acquired:
                multibar._membership_lock.release()

        thread: threading.Thread = threading.Thread(target=observer)
        thread.start()
        thread.join(2)
        assert not thread.is_alive()
        return ''

    list(multibar._render_finished_bar(progress, 10, None, update))
    assert unlocked == [True]


@pytest.mark.parametrize(
    'operation', ['replace', 'pop', 'popitem', 'clear', 'finish']
)
def test_membership_tracking_never_calls_bar_hash(operation: str) -> None:
    class HashBar(progressbar.ProgressBar):
        armed: bool = False

        def __hash__(self) -> int:
            if self.armed:
                raise AssertionError('bar hash callback')
            return object.__hash__(self)

    multibar: progressbar.MultiBar = progressbar.MultiBar(fd=io.StringIO())
    progress: HashBar = HashBar(fd=io.StringIO())
    multibar['task'] = progress
    multibar._finished_at[progress] = 0
    multibar._labeled.add(progress)
    progress.armed = True
    if operation == 'replace':
        multibar['task'] = progressbar.ProgressBar(fd=io.StringIO())
    elif operation == 'pop':
        multibar.pop('task')
    elif operation == 'popitem':
        multibar.popitem()
    elif operation == 'clear':
        multibar.clear()
    else:
        list(
            multibar._render_finished_bar(
                progress, 10, None, lambda **kwargs: ''
            )
        )
    progress.armed = False


def test_multibar_membership_lock_resets_after_fork() -> None:
    import os
    import subprocess
    import sys
    import textwrap

    if not hasattr(os, 'fork'):
        pytest.skip('fork requires POSIX')
    code: str = textwrap.dedent("""
        import io
        import os
        import signal
        import threading
        import progressbar

        multibar = progressbar.MultiBar(fd=io.StringIO())
        held = threading.Event()
        release = threading.Event()
        def holder():
            with multibar._membership_lock:
                held.set()
                release.wait(5)
        thread = threading.Thread(target=holder, daemon=True)
        thread.start()
        assert held.wait(2)
        pid = os.fork()
        if pid == 0:
            signal.alarm(2)
            multibar['child'] = progressbar.ProgressBar(fd=io.StringIO())
            os._exit(0)
        _, status = os.waitpid(pid, 0)
        release.set()
        thread.join(2)
        assert os.waitstatus_to_exitcode(status) == 0
    """)
    result: subprocess.CompletedProcess[str] = subprocess.run(
        [sys.executable, '-c', code],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


def test_tracking_distinguishes_equal_bars_by_identity() -> None:
    class EqualBar(progressbar.ProgressBar):
        def __hash__(self) -> int:
            raise AssertionError('tracking called hash')

        def __eq__(self, other: object) -> bool:
            raise AssertionError('tracking called equality')

    multibar: progressbar.MultiBar = progressbar.MultiBar(fd=io.StringIO())
    first: EqualBar = EqualBar(fd=io.StringIO())
    second: EqualBar = EqualBar(fd=io.StringIO())
    multibar['first'] = first
    multibar['second'] = second
    multibar._finished_at[first] = 1
    multibar._finished_at[second] = 2
    multibar._labeled.add(first)
    multibar._labeled.add(second)
    assert len(multibar._finished_at) == len(multibar._labeled) == 2
    assert multibar._finished_at[first] == 1
    assert multibar._finished_at[second] == 2
    assert next(iter(multibar._finished_at)) is first
    assert list(multibar._labeled)[1] is second
    del multibar['first']
    assert first not in multibar._finished_at
    assert first not in multibar._labeled
    assert second in multibar._finished_at
    assert second in multibar._labeled
    multibar.clear()
    assert not multibar._finished_at
    assert not multibar._labeled


class _IdentityTracked:
    def __init__(self) -> None:
        self.owner: object = None

    def __hash__(self) -> int:
        raise AssertionError('hash callback')

    def __eq__(self, other: object) -> bool:
        raise AssertionError('equality callback')


@pytest.mark.parametrize('method', ['deepcopy', 'pickle'])
@pytest.mark.parametrize('kind', ['mapping', 'set'])
def test_identity_tracking_copy_rebuilds_ids_and_cycles(
    method: str, kind: str
) -> None:
    import copy
    import pickle
    import typing

    from progressbar import _identity

    tracked: _IdentityTracked = _IdentityTracked()
    collection: typing.Any
    if kind == 'mapping':
        collection = _identity.IdentityMap()
        collection[tracked] = 'value'
    else:
        collection = _identity.IdentitySet()
        collection.add(tracked)
    tracked.owner = collection
    restored: typing.Any = (
        copy.deepcopy(collection)
        if method == 'deepcopy'
        else pickle.loads(pickle.dumps(collection))
    )
    copied: _IdentityTracked = next(iter(restored))
    assert copied is not tracked
    assert copied.owner is restored
    assert copied in restored
    assert tracked not in restored
    if kind == 'mapping':
        assert restored[copied] == 'value'
        del restored[copied]
    else:
        restored.discard(copied)
    assert not restored


@pytest.mark.parametrize('operation', ['replace', 'clear', 'pop', 'popitem'])
def test_removed_bar_finalizer_runs_outside_membership_guard(
    operation: str,
) -> None:
    observed: list[bool] = []
    multibar: progressbar.MultiBar = progressbar.MultiBar(fd=io.StringIO())

    class FinalBar(progressbar.ProgressBar):
        def __del__(self) -> None:
            def observer() -> None:
                acquired: bool = multibar._membership_lock.acquire(timeout=1)
                observed.append(acquired)
                if acquired:
                    multibar._membership_lock.release()

            thread: threading.Thread = threading.Thread(target=observer)
            thread.start()
            thread.join(2)
            super().__del__()

    multibar['task'] = FinalBar(fd=io.StringIO())
    multibar._finished_at[multibar['task']] = 0
    multibar._labeled.add(multibar['task'])
    if operation == 'replace':
        multibar['task'] = progressbar.ProgressBar(fd=io.StringIO())
    elif operation == 'clear':
        multibar.clear()
    elif operation == 'pop':
        multibar.pop('task')
    else:
        multibar.popitem()
    assert observed == [True]


def test_render_does_not_relabel_replaced_bar() -> None:
    import inspect
    import sys
    import types
    import typing

    from progressbar import multi

    multibar: progressbar.MultiBar = progressbar.MultiBar(fd=io.StringIO())
    old: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO(), widgets=['old'], max_value=1
    )
    replacement: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO()
    )
    multibar['task'] = old
    old.start()
    old.finish()
    lines, first = inspect.getsourcelines(multi.MultiBar._render_bar)
    pause_line: int = first + next(
        i for i, line in enumerate(lines) if 'self._label_bar(bar_' in line
    )
    reached: threading.Event = threading.Event()
    resume: threading.Event = threading.Event()
    errors: list[BaseException] = []

    def trace(
        frame: types.FrameType, event: str, arg: typing.Any
    ) -> typing.Any:
        if (
            event == 'line'
            and frame.f_code.co_filename == multi.__file__
            and frame.f_lineno == pause_line
        ):
            reached.set()
            assert resume.wait(2)
        return trace

    def render() -> None:
        sys.settrace(trace)
        try:
            list(multibar._render_bar(old, now=10, expired=None))
        except BaseException as error:
            errors.append(error)
        finally:
            sys.settrace(None)

    thread: threading.Thread = threading.Thread(target=render)
    thread.start()
    try:
        assert reached.wait(2)
        multibar['task'] = replacement
    finally:
        resume.set()
        thread.join(2)
    assert not thread.is_alive()
    assert errors == []
    assert multibar.get('task') is replacement
    assert old not in multibar._finished_at
    assert old not in multibar._labeled


def test_expiry_rechecks_membership_after_custom_interval_callback() -> None:
    multibar: progressbar.MultiBar = progressbar.MultiBar(fd=io.StringIO())
    old: progressbar.ProgressBar = multibar['task']
    replacement: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO()
    )
    multibar._finished_at[old] = 0

    class Interval(float):
        def __bool__(self) -> bool:
            multibar['task'] = replacement
            return True

    multibar.remove_finished = Interval(1)
    assert (
        list(multibar._render_finished_bar(old, 10, 9, lambda **kwargs: ''))
        == []
    )
    assert multibar.get('task') is replacement


def test_label_reservation_skips_removed_bars_and_disabled_labels() -> None:
    multibar: progressbar.MultiBar = progressbar.MultiBar(
        fd=io.StringIO(), prepend_label=False, append_label=False
    )
    progress: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO(), widgets=['value']
    )
    multibar['task'] = progress
    assert multibar._label_bar(progress, require_member=True)
    assert progress.widgets == ['value']
    assert progress not in multibar._labeled
    del multibar['task']
    assert not multibar._label_bar(progress, require_member=True)
    assert progress not in multibar._labeled


def _observe_membership_lock(
    multibar: progressbar.MultiBar, observed: list[bool]
) -> None:
    def acquire() -> None:
        acquired: bool = multibar._membership_lock.acquire(timeout=0.1)
        observed.append(acquired)
        if acquired:
            multibar._membership_lock.release()

    thread: threading.Thread = threading.Thread(target=acquire)
    thread.start()
    thread.join(2)
    assert not thread.is_alive()


@pytest.mark.parametrize(
    'operation', ['assign', 'lookup', 'pop', 'setdefault', 'label', 'expire']
)
@pytest.mark.parametrize('callback', ['hash', 'equal'])
def test_custom_label_callbacks_run_outside_membership_guard(
    operation: str, callback: str
) -> None:
    multibar: progressbar.MultiBar = progressbar.MultiBar(
        fd=io.StringIO(), remove_finished=1
    )
    observed: list[bool] = []
    armed: bool = False

    class Label(str):
        def __hash__(self) -> int:
            if armed and callback == 'hash':
                _observe_membership_lock(multibar, observed)
            return str.__hash__(self)

        def __eq__(self, other: object) -> bool:
            if armed and callback == 'equal':
                _observe_membership_lock(multibar, observed)
            return str.__eq__(self, other)

    label: Label = Label('task')
    progress: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO(), widgets=['x']
    )
    multibar[label] = progress
    assert next(iter(multibar)) is label
    # Exact-str queries still call equality on the retained custom key.
    key: str = label if callback == 'hash' else 'task'
    armed = True
    if operation == 'assign':
        multibar[key] = progressbar.ProgressBar(fd=io.StringIO())
        assert next(iter(multibar)) is label
    elif operation == 'lookup':
        assert multibar[key] is progress
    elif operation == 'pop':
        assert multibar.pop(key) is progress
    elif operation == 'setdefault':
        assert multibar.setdefault(key) is progress
    elif operation == 'label':
        progress.label = key
        multibar._label_bar(progress, require_member=True)
    else:
        progress.label = key
        multibar._finished_at[progress] = 0
        list(
            multibar._render_finished_bar(progress, 10, 9, lambda **kwargs: '')
        )
    assert observed and all(observed)


def test_waiting_native_lookup_rechecks_custom_mode() -> None:
    multibar: progressbar.MultiBar = progressbar.MultiBar(fd=io.StringIO())
    observed: list[bool] = []
    started: threading.Event = threading.Event()
    errors: list[BaseException] = []
    armed: bool = False

    class Label(str):
        __hash__ = str.__hash__

        def __eq__(self, other: object) -> bool:
            if armed:

                def acquire() -> None:
                    acquired: bool = multibar._membership_lock.acquire(
                        timeout=0.2
                    )
                    observed.append(acquired)
                    if acquired:
                        multibar._membership_lock.release()

                observer: threading.Thread = threading.Thread(target=acquire)
                observer.start()
                observer.join(2)
            return str.__eq__(self, other)

    progress: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO()
    )

    def lookup() -> None:
        started.set()
        try:
            assert multibar['task'] is progress
        except BaseException as error:
            errors.append(error)

    with multibar._membership_lock:
        thread: threading.Thread = threading.Thread(target=lookup)
        thread.start()
        assert started.wait(2)
        multibar[Label('task')] = progress
        armed = True
    thread.join(2)
    assert not thread.is_alive()
    assert errors == []
    assert observed and all(observed)


def test_clear_does_not_reenable_native_mode_during_custom_insert() -> None:
    multibar: progressbar.MultiBar = progressbar.MultiBar(fd=io.StringIO())
    hashing: threading.Event = threading.Event()
    resume: threading.Event = threading.Event()
    observed: list[bool] = []
    errors: list[BaseException] = []
    armed: bool = False

    class Label(str):
        def __hash__(self) -> int:
            if (
                threading.current_thread().name == 'custom-insert'
                and not hashing.is_set()
            ):
                hashing.set()
                assert resume.wait(3)
            return str.__hash__(self)

        def __eq__(self, other: object) -> bool:
            if armed:

                def acquire() -> None:
                    acquired: bool = multibar._membership_lock.acquire(
                        timeout=0.2
                    )
                    observed.append(acquired)
                    if acquired:
                        multibar._membership_lock.release()

                observer: threading.Thread = threading.Thread(target=acquire)
                observer.start()
                observer.join(2)
            return str.__eq__(self, other)

    label: Label = Label('task')
    progress: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO()
    )

    def insert() -> None:
        try:
            multibar[label] = progress
        except BaseException as error:
            errors.append(error)

    thread: threading.Thread = threading.Thread(
        target=insert, name='custom-insert'
    )
    thread.start()
    try:
        assert hashing.wait(2)
        # On the old code this lock remains held by the custom hash callback.
        acquired: bool = multibar._membership_lock.acquire(timeout=0.2)
        assert acquired
        multibar._membership_lock.release()
        multibar.clear()
    finally:
        resume.set()
        thread.join(3)
    assert errors == []
    armed = True
    assert multibar['task'] is progress
    assert next(iter(multibar)) is label
    assert observed and all(observed)
