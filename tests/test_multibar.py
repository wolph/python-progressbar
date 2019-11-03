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
