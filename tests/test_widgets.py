import time
import pytest
import progressbar


max_values = [None, 10, progressbar.UnknownLength]


def test_create_wrapper():
    with pytest.raises(AssertionError):
        progressbar.widgets.create_wrapper('ab')

    with pytest.raises(RuntimeError):
        progressbar.widgets.create_wrapper(123)


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
        time.sleep(1)
        p.update(i + 1)
    p.finish()


@pytest.mark.parametrize('max_value', [10 ** 6, 10 ** 8])
def test_widgets_large_values(max_value):
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
    p = progressbar.ProgressBar(widgets=widgets, max_value=max_value).start()
    for i in range(0, 10 ** 6, 10 ** 4):
        time.sleep(1)
        p.update(i + 1)
    p.finish()


def test_format_widget():
    widgets = []
    for mapping in progressbar.FormatLabel.mapping:
        widgets.append(progressbar.FormatLabel('%%(%s)r' % mapping))

    p = progressbar.ProgressBar(widgets=widgets)
    for i in p(range(10)):
        time.sleep(1)


@pytest.mark.parametrize('max_value', [None, 10])
def test_all_widgets_small_values(max_value):
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
        progressbar.FormatLabel('%(value)d'),
        progressbar.SimpleProgress(),
        progressbar.Bar(),
        progressbar.ReverseBar(),
        progressbar.BouncingBar(),
        progressbar.CurrentTime(),
        progressbar.CurrentTime(microseconds=False),
        progressbar.CurrentTime(microseconds=True),
    ]
    p = progressbar.ProgressBar(widgets=widgets, max_value=max_value)
    for i in range(10):
        time.sleep(1)
        p.update(i + 1)
    p.finish()


@pytest.mark.parametrize('max_value', [10 ** 6, 10 ** 7])
def test_all_widgets_large_values(max_value):
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
        progressbar.FormatCustomText('Custom %(text)s', dict(text='text')),
    ]
    p = progressbar.ProgressBar(widgets=widgets, max_value=max_value)
    p.update()
    time.sleep(1)
    p.update()

    for i in range(0, 10 ** 6, 10 ** 4):
        time.sleep(1)
        p.update(i)


@pytest.mark.parametrize('min_width', [None, 1, 2, 80, 120])
@pytest.mark.parametrize('term_width', [1, 2, 80, 120])
def test_all_widgets_min_width(min_width, term_width):
    widgets = [
        progressbar.Timer(min_width=min_width),
        progressbar.ETA(min_width=min_width),
        progressbar.AdaptiveETA(min_width=min_width),
        progressbar.AbsoluteETA(min_width=min_width),
        progressbar.DataSize(min_width=min_width),
        progressbar.FileTransferSpeed(min_width=min_width),
        progressbar.AdaptiveTransferSpeed(min_width=min_width),
        progressbar.AnimatedMarker(min_width=min_width),
        progressbar.Counter(min_width=min_width),
        progressbar.Percentage(min_width=min_width),
        progressbar.FormatLabel('%(value)d', min_width=min_width),
        progressbar.SimpleProgress(min_width=min_width),
        progressbar.Bar(min_width=min_width),
        progressbar.ReverseBar(min_width=min_width),
        progressbar.BouncingBar(min_width=min_width),
        progressbar.FormatCustomText('Custom %(text)s', dict(text='text'),
                                     min_width=min_width),
        progressbar.DynamicMessage('custom', min_width=min_width),
        progressbar.CurrentTime(min_width=min_width),
    ]
    p = progressbar.ProgressBar(widgets=widgets, term_width=term_width)
    p.update(0)
    p.update()
    for widget in p._format_widgets():
        if min_width and min_width > term_width:
            assert widget == ''
        else:
            assert widget != ''


@pytest.mark.parametrize('max_width', [None, 1, 2, 80, 120])
@pytest.mark.parametrize('term_width', [1, 2, 80, 120])
def test_all_widgets_max_width(max_width, term_width):
    widgets = [
        progressbar.Timer(max_width=max_width),
        progressbar.ETA(max_width=max_width),
        progressbar.AdaptiveETA(max_width=max_width),
        progressbar.AbsoluteETA(max_width=max_width),
        progressbar.DataSize(max_width=max_width),
        progressbar.FileTransferSpeed(max_width=max_width),
        progressbar.AdaptiveTransferSpeed(max_width=max_width),
        progressbar.AnimatedMarker(max_width=max_width),
        progressbar.Counter(max_width=max_width),
        progressbar.Percentage(max_width=max_width),
        progressbar.FormatLabel('%(value)d', max_width=max_width),
        progressbar.SimpleProgress(max_width=max_width),
        progressbar.Bar(max_width=max_width),
        progressbar.ReverseBar(max_width=max_width),
        progressbar.BouncingBar(max_width=max_width),
        progressbar.FormatCustomText('Custom %(text)s', dict(text='text'),
                                     max_width=max_width),
        progressbar.DynamicMessage('custom', max_width=max_width),
        progressbar.CurrentTime(max_width=max_width),
    ]
    p = progressbar.ProgressBar(widgets=widgets, term_width=term_width)
    p.update(0)
    p.update()
    for widget in p._format_widgets():
        if max_width and max_width < term_width:
            assert widget == ''
        else:
            assert widget != ''
