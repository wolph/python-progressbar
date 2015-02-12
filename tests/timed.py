import time
import progressbar


def test_non_changing_eta():
    '''Testing (Adaptive)ETA when the value doesn't actually change'''
    widgets = [
        progressbar.AdaptiveETA(),
        progressbar.ETA(),
        progressbar.AdaptiveTransferSpeed(),
    ]
    p = progressbar.ProgressBar(maxval=2, widgets=widgets, poll=0.0001)

    p.start()
    p.update(1)
    time.sleep(0.001)
    p.update(1)
    p.finish()

