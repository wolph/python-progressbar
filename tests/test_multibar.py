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


def test_multibar_print() -> None:
    bars = 5
    n = 10

    def print_sometimes(bar, probability):
        for i in bar(range(n)):
            # Sleep up to 0.1 seconds
            time.sleep(random.random() * 0.1)

            # print messages at random intervals to show how extra output works
            if random.random() < probability:
                bar.print('random message for bar', bar, i)

    with progressbar.MultiBar() as multibar:
        for i in range(bars):
            # Get a progressbar
            bar = multibar[f'Thread label here {i}']
            bar.max_error = False
            # Create a thread and pass the progressbar
            # Print never, sometimes and always
            threading.Thread(target=print_sometimes, args=(bar, 0)).start()
            threading.Thread(target=print_sometimes, args=(bar, 0.5)).start()
            threading.Thread(target=print_sometimes, args=(bar, 1)).start()

        for i in range(5):
            multibar.print(f'{i}', flush=False)

        multibar.update(force=True, flush=False)
        multibar.update(force=True, flush=True)


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
    multibar.join()
    bar.finish()
    multibar.join()
    multibar.render(force=True)
