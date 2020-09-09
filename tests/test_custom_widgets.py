import time
import progressbar


class CrazyFileTransferSpeed(progressbar.FileTransferSpeed):
    "It's bigger between 45 and 80 percent"

    def update(self, pbar):
        if 45 < pbar.percentage() < 80:
            return 'Bigger Now ' + progressbar.FileTransferSpeed.update(self,
                                                                        pbar)
        else:
            return progressbar.FileTransferSpeed.update(self, pbar)


def test_crazy_file_transfer_speed_widget():
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


def test_variable_widget_widget():
    widgets = [
        ' [', progressbar.Timer(), '] ',
        progressbar.Bar(),
        ' (', progressbar.ETA(), ') ',
        progressbar.Variable('loss'),
        progressbar.Variable('text'),
        progressbar.Variable('error', precision=None),
        progressbar.Variable('missing'),
        progressbar.Variable('predefined'),
    ]

    p = progressbar.ProgressBar(widgets=widgets, max_value=1000,
                                variables=dict(predefined='predefined'))
    p.start()
    print('time', time, time.sleep)
    for i in range(0, 200, 5):
        time.sleep(0.1)
        p.update(i + 1, loss=.5, text='spam', error=1)

    i += 1
    p.update(i, text=None)
    i += 1
    p.update(i, text=False)
    i += 1
    p.update(i, text=True, error='a')
    p.finish()


def test_format_custom_text_widget():
    widget = progressbar.FormatCustomText(
        'Spam: %(spam).1f kg, eggs: %(eggs)d',
        dict(
            spam=0.25,
            eggs=3,
        ),
    )

    bar = progressbar.ProgressBar(widgets=[
        widget,
    ])

    for i in bar(range(5)):
        widget.update_mapping(eggs=i * 2)
        assert widget.mapping['eggs'] == bar.widgets[0].mapping['eggs']

