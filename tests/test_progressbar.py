
def test_examples():
    from examples import examples
    for example in examples:
        example()


def test_examples_nullbar(monkeypatch):
    # Patch progressbar to use null bar instead of regular progress bar
    import progressbar
    monkeypatch.setattr(progressbar, 'ProgressBar', progressbar.NullBar)
    assert progressbar.ProgressBar._MINIMUM_UPDATE_INTERVAL < 0.0001
    import examples
    examples.non_interactive_sleep_factor = 10000
    for example in examples.examples:
        example()


def test_reuse():
    import progressbar

    bar = progressbar.ProgressBar()
    bar.start()
    for i in range(10):
        bar.update(i)
    bar.finish()

    bar.start(init=True)
    for i in range(10):
        bar.update(i)
    bar.finish()

    bar.start(init=False)
    for i in range(10):
        bar.update(i)
    bar.finish()
