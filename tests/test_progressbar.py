
def test_examples():
    from examples import examples
    for example in examples:
        example()


def test_examples_nullbar(monkeypatch):
    # Patch progressbar to use null bar instead of regular progress bar
    import progressbar
    monkeypatch.setattr(progressbar, 'ProgressBar', progressbar.NullBar)
    from examples import examples
    for example in examples:
        example()
