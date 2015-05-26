import time
import progressbar


def test_timer():
    '''Testing (Adaptive)ETA when the value doesn't actually change'''
    widgets = [
        progressbar.Timer(),
    ]
    p = progressbar.ProgressBar(maxval=2, widgets=widgets, poll=0.0001)

    p.start()
    p.update(1)
    time.sleep(0.001)
    p.update(1)
    p.finish()


def test_eta():
    '''Testing (Adaptive)ETA when the value doesn't actually change'''
    widgets = [
        progressbar.ETA(),
    ]
    p = progressbar.ProgressBar(maxval=2, widgets=widgets, poll=0.0001)

    p.start()
    p.update(1)
    time.sleep(0.001)
    p.update(1)
    p.finish()



def test_adaptive_eta():
    '''Testing (Adaptive)ETA when the value doesn't actually change'''
    widgets = [
        progressbar.AdaptiveETA(),
    ]
    p = progressbar.ProgressBar(maxval=2, widgets=widgets, poll=0.0001)

    p.start()
    p.update(1)
    time.sleep(0.001)
    p.update(1)
    p.finish()


def test_adaptive_transfer_speed():
    '''Testing (Adaptive)ETA when the value doesn't actually change'''
    widgets = [
        progressbar.AdaptiveTransferSpeed(),
    ]
    p = progressbar.ProgressBar(maxval=2, widgets=widgets, poll=0.0001)

    p.start()
    p.update(1)
    time.sleep(0.001)
    p.update(1)
    p.finish()


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
