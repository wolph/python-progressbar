from datetime import timedelta
import progressbar
from progressbar import widgets


def test_samples():
    samples = widgets.SamplesMixin(samples=10)
    bar = progressbar.ProgressBar(widgets=[samples])

    # Force updates in all cases
    samples.INTERVAL = - timedelta(1)

    bar.update(0)
    assert samples(bar, None)[1] == [0, 0, 0]
    bar.update(1)
    assert samples(bar, None)[1] == [0, 0, 0, 1, 1]
    bar.update(2)
    assert samples(bar, None)[1] == [0, 0, 0, 1, 1, 2, 2]

    assert samples(bar, None, delta=True)[1] == 2
