import time

import pytest

import progressbar


class CrazyFileTransferSpeed(progressbar.FileTransferSpeed):
    "It's bigger between 45 and 80 percent"

    def update(self, pbar):
        if 45 < pbar.percentage() < 80:
            value = progressbar.FileTransferSpeed.update(self, pbar)
            return f'Bigger Now {value}'
        else:
            return progressbar.FileTransferSpeed.update(self, pbar)


def test_crazy_file_transfer_speed_widget() -> None:
    widgets = [
        # CrazyFileTransferSpeed(),
        ' <<<',
        progressbar.Bar(),
        '>>> ',
        progressbar.Percentage(),
        ' ',
        progressbar.ETA(),
    ]

    p = progressbar.ProgressBar(widgets=widgets, max_value=1000)
    # maybe do something
    p.start()
    for i in range(0, 200, 5):
        # do something
        time.sleep(0.1)
        p.update(i + 1)
    p.finish()


def test_variable_widget_widget() -> None:
    widgets = [
        ' [',
        progressbar.Timer(),
        '] ',
        progressbar.Bar(),
        ' (',
        progressbar.ETA(),
        ') ',
        progressbar.Variable('loss'),
        progressbar.Variable('text'),
        progressbar.Variable('error', precision=None),
        progressbar.Variable('missing'),
        progressbar.Variable('predefined'),
    ]

    p = progressbar.ProgressBar(
        widgets=widgets,
        max_value=1000,
        variables=dict(predefined='predefined'),
    )
    p.start()
    print('time', time, time.sleep)
    for i in range(0, 200, 5):
        time.sleep(0.1)
        p.update(i + 1, loss=0.5, text='spam', error=1)

    i += 1
    p.update(i, text=None)
    i += 1
    p.update(i, text=False)
    i += 1
    p.update(i, text=True, error='a')
    with pytest.raises(TypeError):
        p.update(i, non_existing_variable='error!')
    p.finish()


def test_format_custom_text_widget() -> None:
    widget = progressbar.FormatCustomText(
        'Spam: %(spam).1f kg, eggs: %(eggs)d',
        dict(
            spam=0.25,
            eggs=3,
        ),
    )

    bar = progressbar.ProgressBar(
        widgets=[
            widget,
        ],
    )

    for i in bar(range(5)):
        widget.update_mapping(eggs=i * 2)
        assert widget.mapping['eggs'] == bar.widgets[0].mapping['eggs']


def test_format_custom_text_mapping_is_per_instance() -> None:
    # Regression: F2 - default-constructed FormatCustomText instances shared
    # the mutable class-level ``mapping`` dict, so update_mapping on one bled
    # into every other instance (and the class attribute).
    class_default = dict(progressbar.FormatCustomText.mapping)

    a = progressbar.FormatCustomText('%(spam)s')
    b = progressbar.FormatCustomText('%(spam)s')

    a.update_mapping(spam='eggs')

    assert a.mapping == {'spam': 'eggs'}
    assert b.mapping == {}
    assert a.mapping is not b.mapping
    assert progressbar.FormatCustomText.mapping == class_default


def test_format_custom_text_subclass_keeps_class_default_mapping() -> None:
    # A subclass may declare a class-level mapping default; instances
    # constructed without an explicit mapping must inherit it (per
    # instance, without aliasing the class dict).
    class Defaulted(progressbar.FormatCustomText):
        # The mutable class attribute is the point of this test: it mirrors
        # how third-party subclasses declare default mappings.
        mapping = {'spam': 'ham'}  # noqa: RUF012

    widget = Defaulted('%(spam)s')
    assert widget.mapping == {'spam': 'ham'}

    widget.update_mapping(spam='eggs')
    assert widget.mapping == {'spam': 'eggs'}
    # The class default stays untouched by instance mutation.
    assert Defaulted.mapping == {'spam': 'ham'}
    assert Defaulted('%(spam)s').mapping == {'spam': 'ham'}
