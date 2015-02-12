import progressbar


def test_empty_list():
    for x in progressbar.ProgressBar()([]):
        print(x)


def test_empty_iterator():
    for x in progressbar.ProgressBar(maxval=0)(iter([])):
        print(x)

