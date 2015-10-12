import progressbar


def test_unknown_length():
    pb = progressbar.ProgressBar(widgets=[progressbar.AnimatedMarker()],
                                 max_value=progressbar.UnknownLength)
    assert pb.max_value is progressbar.UnknownLength
