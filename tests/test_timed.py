import datetime
import time

import progressbar


def test_timer() -> None:
    """Testing (Adaptive)ETA when the value doesn't actually change"""
    widgets = [
        progressbar.Timer(),
    ]
    p = progressbar.ProgressBar(
        max_value=2,
        widgets=widgets,
        poll_interval=0.0001,
    )

    p.start()
    p.update()
    p.update(1)
    p._needs_update()
    time.sleep(0.001)
    p.update(1)
    p.finish()


def test_eta() -> None:
    """Testing (Adaptive)ETA when the value doesn't actually change"""
    widgets = [
        progressbar.ETA(),
    ]
    p = progressbar.ProgressBar(
        min_value=0,
        max_value=2,
        widgets=widgets,
        poll_interval=0.0001,
    )

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


def test_adaptive_eta() -> None:
    """Testing (Adaptive)ETA when the value doesn't actually change"""
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
    for _i in range(20):
        p.update(1)
        time.sleep(0.001)
    p.finish()


def test_adaptive_transfer_speed() -> None:
    """Testing (Adaptive)ETA when the value doesn't actually change"""
    widgets = [
        progressbar.AdaptiveTransferSpeed(),
    ]
    p = progressbar.ProgressBar(
        max_value=2,
        widgets=widgets,
        poll_interval=0.0001,
    )

    p.start()
    p.update(1)
    time.sleep(0.001)
    p.update(1)
    p.finish()


def test_etas(monkeypatch) -> None:
    """Compare file transfer speed to adaptive transfer speed"""
    n = 10
    interval = datetime.timedelta(seconds=1)
    widgets = [
        progressbar.FileTransferSpeed(),
        progressbar.AdaptiveTransferSpeed(samples=n / 2),
    ]

    datas = []

    # Capture the output sent towards the `_speed` method
    def calculate_eta(self, value, elapsed):
        """Capture the widget output"""
        data = dict(
            value=value,
            elapsed=int(elapsed),
        )
        datas.append(data)
        return 0, 0

    monkeypatch.setattr(progressbar.FileTransferSpeed, '_speed', calculate_eta)
    monkeypatch.setattr(
        progressbar.AdaptiveTransferSpeed,
        '_speed',
        calculate_eta,
    )

    for widget in widgets:
        widget.INTERVAL = interval

    p = progressbar.ProgressBar(
        max_value=n,
        widgets=widgets,
        poll_interval=interval,
    )

    # Run the first few samples at a low speed and speed up later so we can
    # compare the results from both widgets
    for i in range(n):
        p.update(i)
        if i > n / 2:
            time.sleep(1)
        else:
            time.sleep(10)
    p.finish()

    # Due to weird travis issues, the actual testing is disabled for now
    # import pprint
    # pprint.pprint(datas[::2])
    # pprint.pprint(datas[1::2])

    # for i, (a, b) in enumerate(zip(datas[::2], datas[1::2])):
    #     # Because the speed is identical initially, the results should be the
    #     # same for adaptive and regular transfer speed. Only when the speed
    #     # changes we should start see a lot of differences between the two
    #     if i < (n / 2 - 1):
    #         assert a['elapsed'] == b['elapsed']
    #     if i > (n / 2 + 1):
    #         assert a['elapsed'] > b['elapsed']


def test_non_changing_eta() -> None:
    """Testing (Adaptive)ETA when the value doesn't actually change"""
    widgets = [
        progressbar.AdaptiveETA(),
        progressbar.ETA(),
        progressbar.AdaptiveTransferSpeed(),
    ]
    p = progressbar.ProgressBar(
        max_value=2,
        widgets=widgets,
        poll_interval=0.0001,
    )

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
        yield from range(200)

    widgets = [progressbar.AdaptiveETA(), progressbar.ETA()]

    bar = progressbar.ProgressBar(widgets=widgets)
    for _i in bar(gen()):
        pass
