import threading
import time

import pytest

import progressbar


def test_multi_progress_bar_out_of_range():
    widgets = [
        progressbar.MultiProgressBar('multivalues'),
    ]

    bar = progressbar.ProgressBar(widgets=widgets, max_value=10)
    with pytest.raises(ValueError):
        bar.update(multivalues=[123])

    with pytest.raises(ValueError):
        bar.update(multivalues=[-1])


def test_multi_progress_bar_fill_left():
    import examples
    return examples.multi_progress_bar_example(False)


def test_multibar():
    bars = 3
    N = 10
    multibar = progressbar.MultiBar(sort_keyfunc=lambda bar: bar.label)
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

    multibar.append_label = True

    def do_something(bar):
        for j in bar(range(N)):
            time.sleep(0.01)
            bar.update(j)

    for i in range(bars):
        thread = threading.Thread(
            target=do_something,
            args=(multibar['bar {}'.format(i)],)
        )
        thread.start()

    for bar in multibar.values():
        for j in range(N):
            bar.update(j)
            time.sleep(0.002)

    multibar.join(0.1)
    multibar.stop(0.1)


@pytest.mark.parametrize(
    'sort_key', [
        None,
        'index',
        'label',
        'value',
        'percentage',
        progressbar.SortKey.CREATED,
        progressbar.SortKey.LABEL,
        progressbar.SortKey.VALUE,
        progressbar.SortKey.PERCENTAGE,
    ]
)
def test_multibar_sorting(sort_key):
    bars = 3
    N = 10

    with progressbar.MultiBar() as multibar:
        for i in range(bars):
            label = 'bar {}'.format(i)
            multibar[label] = progressbar.ProgressBar(max_value=N)

        for bar in multibar.values():
            for j in bar(range(N)):
                assert bar.started()
                time.sleep(0.002)

        for bar in multibar.values():
            assert bar.finished()


def test_offset_bar():
    with progressbar.ProgressBar(line_offset=2) as bar:
        for i in range(100):
            bar.update(i)
