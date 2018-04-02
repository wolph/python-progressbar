from . import bar


def progressbar(iterator, min_value=0, max_value=None,
                widgets=None, **kwargs):
    progressbar = bar.ProgressBar(
        min_value=min_value, max_value=max_value,
        widgets=widgets, **kwargs)

    for result in progressbar(iterator):
        yield result
