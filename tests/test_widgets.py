from __future__ import annotations

import io
import time
from datetime import timedelta

import pytest

import progressbar

def test_create_wrapper() -> None:
    # F4: user-facing validation must raise ValueError (not a bare assert that
    # vanishes under ``python -O``).
    with pytest.raises(ValueError):
        progressbar.widgets.create_wrapper('ab')

    with pytest.raises(RuntimeError):
        progressbar.widgets.create_wrapper(123)


def test_create_marker_rejects_multichar_marker() -> None:
    # F4: markers must be a single visible character.
    with pytest.raises(ValueError):
        progressbar.widgets.create_marker('ab')


def test_multi_range_bar_rejects_multichar_marker() -> None:
    # F4: the render path validates marker width; a 2-char marker must raise
    # ValueError rather than a stripped-under-O assert.
    widget = progressbar.MultiRangeBar('amounts', markers=['ab', ' '])
    bar = progressbar.ProgressBar(
        widgets=[widget],
        variables={'amounts': []},
        max_value=10,
        fd=io.StringIO(),
        term_width=60,
    )
    bar.start()
    data = bar.data()
    data['variables'] = {'amounts': [1, 0]}
    with pytest.raises(ValueError):
        widget(bar, data, width=20)
    bar.finish(dirty=True)


def test_multi_range_bar_rejects_multichar_fill() -> None:
    # Item 4: the fill path validates the fill width; a 2-char fill must raise
    # ValueError rather than a stripped-under-O assert. Non-empty amounts keep
    # the initial render on the marker branch; emptying them forces the
    # zero-sum ``else`` (fill) branch on the direct call.
    widget = progressbar.MultiRangeBar(
        'amounts', markers=[' ', '#'], fill='xx'
    )
    bar = progressbar.ProgressBar(
        widgets=[widget],
        variables={'amounts': [1, 0]},
        max_value=10,
        fd=io.StringIO(),
        term_width=60,
    )
    bar.start()
    data = bar.data()
    data['variables'] = {'amounts': []}
    with pytest.raises(ValueError):
        widget(bar, data, width=20)
    bar.finish(dirty=True)


def test_widgets_small_values() -> None:
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


@pytest.mark.parametrize('max_value', [10**6, 10**8])
def test_widgets_large_values(max_value) -> None:
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
    for i in range(0, 10**6, 10**4):
        time.sleep(1)
        p.update(i + 1)
    p.finish()


def test_postfix_widget_renders_mapping_sorted() -> None:
    bar = progressbar.ProgressBar(
        widgets=[progressbar.Postfix()],
        variables={'postfix': {'z': 2, 'a': 1}},
        fd=io.StringIO(),
        term_width=80,
    )
    bar.start()
    output = ''.join(bar._format_widgets())
    assert output == ' a=1, z=2'


def test_postfix_widget_renders_string() -> None:
    bar = progressbar.ProgressBar(
        widgets=[progressbar.Postfix()],
        variables={'postfix': 'loss=0.25'},
        fd=io.StringIO(),
        term_width=80,
    )
    bar.start()
    output = ''.join(bar._format_widgets())
    assert output == ' loss=0.25'


def test_postfix_widget_renders_other_values() -> None:
    bar = progressbar.ProgressBar(
        widgets=[progressbar.Postfix()],
        variables={'postfix': 3},
        fd=io.StringIO(),
        term_width=80,
    )
    bar.start()
    output = ''.join(bar._format_widgets())
    assert output == ' 3'


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (0, ' 0'),
        (0.0, ' 0.0'),
        (False, ' False'),
    ],
)
def test_postfix_widget_renders_falsy_values(value, expected) -> None:
    bar = progressbar.ProgressBar(
        widgets=[progressbar.Postfix()],
        variables={'postfix': value},
        fd=io.StringIO(),
        term_width=80,
    )
    bar.start()
    output = ''.join(bar._format_widgets())
    assert output == expected


def test_postfix_widget_omits_empty_values() -> None:
    bar = progressbar.ProgressBar(
        widgets=[progressbar.Postfix()],
        variables={'postfix': None},
        fd=io.StringIO(),
        term_width=80,
    )
    bar.start()
    output = ''.join(bar._format_widgets())
    assert output == ''


def test_format_unit_value_special_cases() -> None:
    assert progressbar.widgets.format_unit_value(None) == 'N/A'
    unknown_value = progressbar.widgets.format_unit_value(
        progressbar.UnknownLength,
    )
    assert unknown_value == 'N/A'
    assert progressbar.widgets.format_unit_value(1.5, unit='B') == '1.5 B'
    assert progressbar.widgets.format_unit_value(2, unit='B') == '2 B'


def test_unit_progress_scales_values() -> None:
    bar = progressbar.ProgressBar(
        max_value=2048,
        widgets=[progressbar.UnitProgress(unit='B', unit_scale=True)],
        fd=io.StringIO(),
        term_width=80,
    )
    bar.start()
    bar.update(1024, force=True)
    output = ''.join(bar._format_widgets())
    assert output == '1.0 KiB of 2.0 KiB'


def test_unit_progress_uses_progress_units_by_default() -> None:
    bar = progressbar.ProgressBar(
        max_value=2048,
        widgets=[progressbar.UnitProgress()],
        unit='B',
        unit_scale=True,
        fd=io.StringIO(),
        term_width=80,
    )
    bar.start()
    bar.update(1024, force=True)
    output = ''.join(bar._format_widgets())
    assert output == '1.0 KiB of 2.0 KiB'


def test_format_widget() -> None:
    widgets = [
        progressbar.FormatLabel(f'%({mapping})r')
        for mapping in progressbar.FormatLabel.mapping
    ]
    p = progressbar.ProgressBar(widgets=widgets)
    for _ in p(range(10)):
        time.sleep(1)


@pytest.mark.parametrize('max_value', [None, 10])
def test_all_widgets_small_values(max_value) -> None:
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


@pytest.mark.parametrize('max_value', [10**6, 10**7])
def test_all_widgets_large_values(max_value) -> None:
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

    for i in range(0, 10**6, 10**4):
        time.sleep(1)
        p.update(i)


@pytest.mark.parametrize('min_width', [None, 1, 2, 80, 120])
@pytest.mark.parametrize('term_width', [1, 2, 80, 120])
def test_all_widgets_min_width(min_width, term_width) -> None:
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
        progressbar.FormatCustomText(
            'Custom %(text)s',
            dict(text='text'),
            min_width=min_width,
        ),
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
def test_all_widgets_max_width(max_width, term_width) -> None:
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
        progressbar.FormatCustomText(
            'Custom %(text)s',
            dict(text='text'),
            max_width=max_width,
        ),
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


def test_eta_respects_min_value() -> None:
    # Regression: B3 - the items/second rate divided by the raw value
    # instead of the progress relative to min_value.
    bar = progressbar.ProgressBar(
        min_value=50, max_value=100, fd=io.StringIO(), term_width=60
    )
    bar.start()
    bar.update(75)
    bar.start_time -= timedelta(seconds=30)
    data = bar.data()
    progressbar.ETA()(bar, data)

    # 25 of 50 items done in 30 seconds -> 30 seconds remaining
    assert data['eta_seconds'] == pytest.approx(30, rel=0.05)


def test_multi_progress_bar_zero_total() -> None:
    # Regression: B5 - a (value, 0) tuple raised ZeroDivisionError.
    widget = progressbar.MultiProgressBar('jobs')
    bar = progressbar.ProgressBar(
        widgets=[widget], max_value=10, fd=io.StringIO(), term_width=60
    )
    ranges = widget.get_values(bar, {'variables': {'jobs': [(3, 0)]}})
    assert sum(ranges) > 0


def test_bar_widget_respects_min_value() -> None:
    # Regression: B9 - the fill width was computed from the raw value, so
    # a bar at 0% progress with min_value > 0 rendered partially full.
    bar = progressbar.ProgressBar(
        min_value=50,
        max_value=100,
        widgets=[progressbar.Bar()],
        fd=io.StringIO(),
        term_width=60,
    )
    bar.start()
    assert '#' not in bar.fd.getvalue()
    bar.finish(dirty=True)


def test_animated_marker_fill_stays_full_when_finished() -> None:
    # Regression: a Bar filled by an AnimatedMarker(fill=...) collapsed to a
    # single marker character at finish() because the end_time branch
    # short-circuited before applying the fill. The finished bar must stay
    # full instead of emptying out at 100%.
    bar = progressbar.ProgressBar(
        widgets=[progressbar.Bar(marker=progressbar.AnimatedMarker(fill='#'))],
        max_value=10,
        fd=io.StringIO(),
        term_width=60,
    )
    bar.start()
    for i in range(11):
        bar.update(i)
    bar.finish()

    last_line = [
        line for line in bar.fd.getvalue().split('\n') if line.strip()
    ][-1]
    # term_width 60 leaves ~58 fill characters; the collapse bug left ~1
    assert last_line.count('#') > 40, repr(last_line)
