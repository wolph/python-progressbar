import progressbar


def test_unknown_length():
    pb = progressbar.ProgressBar(widgets=[progressbar.AnimatedMarker()],
                                 max_value=progressbar.UnknownLength)
    assert pb.max_value is progressbar.UnknownLength


def test_unknown_length_default_widgets():
    # The default widgets picked should work without a known max_value
    pb = progressbar.ProgressBar(max_value=progressbar.UnknownLength).start()
    for i in range(60):
        pb.update(i)
    pb.finish()


def test_unknown_length_at_start():
    # The default widgets should be picked after we call .start()
    pb = progressbar.ProgressBar().start(max_value=progressbar.UnknownLength)
    for i in range(60):
        pb.update(i)
    pb.finish()

    pb2 = progressbar.ProgressBar().start(max_value=progressbar.UnknownLength)
    for w in pb2.widgets:
        print(type(w), repr(w))
    assert any([isinstance(w, progressbar.Bar) for w in pb2.widgets])
