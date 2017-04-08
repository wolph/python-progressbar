import time
import datetime
import progressbar


def test_timer():
    '''Testing (Adaptive)ETA when the value doesn't actually change'''
    widgets = [
        progressbar.Timer(),
    ]
    p = progressbar.ProgressBar(max_value=2, widgets=widgets,
                                poll_interval=0.0001)

    p.start()
    p.update()
    p.update(1)
    p._needs_update()
    time.sleep(0.001)
    p.update(1)
    p.finish()


def test_eta():
    '''Testing (Adaptive)ETA when the value doesn't actually change'''
    widgets = [
        progressbar.ETA(),
    ]
    p = progressbar.ProgressBar(min_value=0, max_value=2, widgets=widgets,
                                poll_interval=0.0001)

    p.start()
    time.sleep(0.001)
    p.update(0)
    time.sleep(0.001)
    p.update(1)
    time.sleep(0.001)
    p.update(1)
    time.sleep(0.001)
    p.update(2)
    time.sleep(0.001)
    p.finish()
    time.sleep(0.001)
    p.update(2)


def test_adaptive_eta():
    '''Testing (Adaptive)ETA when the value doesn't actually change'''
    widgets = [
        progressbar.AdaptiveETA(),
    ]
    widgets[0].INTERVAL = datetime.timedelta(microseconds=1)
    p = progressbar.ProgressBar(
        max_value=2,
        samples=2,
        widgets=widgets,
        poll_interval=0.0001,
    )

    p.start()
    for i in range(20):
        p.update(1)
        time.sleep(0.001)
    p.finish()


def test_adaptive_transfer_speed():
    '''Testing (Adaptive)ETA when the value doesn't actually change'''
    widgets = [
        progressbar.AdaptiveTransferSpeed(),
    ]
    p = progressbar.ProgressBar(max_value=2, widgets=widgets,
                                poll_interval=0.0001)

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
    p = progressbar.ProgressBar(max_value=2, widgets=widgets,
                                poll_interval=0.0001)

    p.start()
    p.update(1)
    time.sleep(0.001)
    p.update(1)
    p.finish()


def test_eta_not_available():
    """
     When ETA is not available (data coming from a generator),
     ETAs should not raise exceptions.
    """
    def gen():
        for x in range(200):
            yield x

    widgets = [progressbar.AdaptiveETA(), progressbar.ETA()]

    bar = progressbar.ProgressBar(widgets=widgets)
    for i in bar(gen()):
        pass
