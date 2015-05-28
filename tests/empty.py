import progressbar


def test_empty_list():
    for x in progressbar.ProgressBar()([]):
        print(x)


def test_empty_iterator():
    for x in progressbar.ProgressBar(max_value=0)(iter([])):
        print(x)

