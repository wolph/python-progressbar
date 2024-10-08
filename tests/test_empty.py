import progressbar


def test_empty_list() -> None:
    for x in progressbar.ProgressBar()([]):
        print(x)


def test_empty_iterator() -> None:
    for x in progressbar.ProgressBar(max_value=0)(iter([])):
        print(x)
