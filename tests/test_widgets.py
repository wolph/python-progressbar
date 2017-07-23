import time
import progressbar


def test_widgets_small_values():
    widgets = [
        'Test: ',
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(marker=progressbar.RotatingMarker()),
        ' ',
        progressbar.ETA(),
        ' ',
        progressbar.AbsoluteETA(),
        ' ',
        progressbar.FileTransferSpeed(),
    ]
    p = progressbar.ProgressBar(widgets=widgets, max_value=10).start()
    p.update(0)
    for i in range(10):
        time.sleep(0.001)
        p.update(i + 1)
    p.finish()


def test_widgets_large_values():
    widgets = [
        'Test: ',
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(marker=progressbar.RotatingMarker()),
        ' ',
        progressbar.ETA(),
        ' ',
        progressbar.AbsoluteETA(),
        ' ',
        progressbar.FileTransferSpeed(),
    ]
    p = progressbar.ProgressBar(widgets=widgets, max_value=10 ** 6).start()
    for i in range(0, 10 ** 6, 10 ** 4):
        time.sleep(0.001)
        p.update(i + 1)
    p.finish()


def test_format_widget():
    widgets = []
    for mapping in progressbar.FormatLabel.mapping:
        widgets.append(progressbar.FormatLabel('%%(%s)r' % mapping))

    p = progressbar.ProgressBar(widgets=widgets)
    for i in p(range(10)):
        time.sleep(0.001)


def test_all_widgets_small_values():
    widgets = [
        progressbar.Timer(),
        progressbar.ETA(),
        progressbar.AdaptiveETA(),
        progressbar.AbsoluteETA(),
        progressbar.DataSize(),
        progressbar.FileTransferSpeed(),
        progressbar.AdaptiveTransferSpeed(),
        progressbar.AnimatedMarker(),
        progressbar.Counter(),
        progressbar.Percentage(),
        progressbar.FormatLabel('%(value)d/%(max_value)d'),
        progressbar.SimpleProgress(),
        progressbar.Bar(),
        progressbar.ReverseBar(),
        progressbar.BouncingBar(),
        progressbar.CurrentTime(),
        progressbar.CurrentTime(microseconds=False),
        progressbar.CurrentTime(microseconds=True),
    ]
    p = progressbar.ProgressBar(widgets=widgets, max_value=10)
    for i in range(10):
        time.sleep(0.001)
        p.update(i + 1)
    p.finish()


def test_all_widgets_large_values():
    widgets = [
        progressbar.Timer(),
        progressbar.ETA(),
        progressbar.AdaptiveETA(),
        progressbar.AbsoluteETA(),
        progressbar.DataSize(),
        progressbar.FileTransferSpeed(),
        progressbar.AdaptiveTransferSpeed(),
        progressbar.AnimatedMarker(),
        progressbar.Counter(),
        progressbar.Percentage(),
        progressbar.FormatLabel('%(value)d/%(max_value)d'),
        progressbar.SimpleProgress(),
        progressbar.Bar(fill=lambda progress, data, width: '#'),
        progressbar.ReverseBar(),
        progressbar.BouncingBar(),
    ]
    p = progressbar.ProgressBar(widgets=widgets, max_value=10 ** 6)
    for i in range(0, 10 ** 6, 10 ** 4):
        time.sleep(0.001)
        p.update(i + 1)
    p.finish()

