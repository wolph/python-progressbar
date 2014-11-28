import progressbar


def test_empty_progressbar():
    for x in progressbar.ProgressBar()([]):
        print(x)


def test_examples():
    from examples import examples
    for example in examples:
        example()
