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


def test_multibar_concurrent_mutation() -> None:
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
