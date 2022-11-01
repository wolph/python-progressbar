import time
import progressbar


def test_progressbar_1_widgets():
    widgets = [
        progressbar.AdaptiveETA(format="Time left: %s"),
        progressbar.Timer(format="Time passed: %s"),
        progressbar.Bar()
    ]

    bar = progressbar.ProgressBar(widgets=widgets, max_value=100).start()

    for i in range(1, 101):
        bar.update(i)
        time.sleep(0.1)
