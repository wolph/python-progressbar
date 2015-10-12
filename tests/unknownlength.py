import progressbar
from progressbar import ProgressBar, UnknownLength


def test_unknown_length():
    pb = ProgressBar(widgets=[progressbar.AnimatedMarker()],
                     max_value=UnknownLength)
    assert pb.max_value is UnknownLength


def test_unknown_length_default_widgets():
    # The default widgets picked should work without a known max_value
    pb = ProgressBar(max_value=UnknownLength).start()
    for i in range(60):
        pb.update(i)
    pb.finish()


def test_unknown_length_at_start():
    # The default widgets should be picked after we call .start()
    pb = ProgressBar().start(max_value=UnknownLength)
    for i in range(60):
        pb.update(i)
    pb.finish()

    pb2 = ProgressBar().start(max_value=UnknownLength)
    assert any([isinstance(w, progressbar.Bar) for w in pb2.widgets])
