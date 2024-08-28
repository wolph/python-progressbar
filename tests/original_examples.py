#!/usr/bin/python

import sys
import time

from progressbar import (
    ETA,
    AdaptiveETA,
    AnimatedMarker,
    Bar,
    BouncingBar,
    Counter,
    FileTransferSpeed,
    FormatLabel,
    Percentage,
    ProgressBar,
    ReverseBar,
    RotatingMarker,
    SimpleProgress,
    Timer,
    UnknownLength,
)

examples = []


def example(fn):
    try:
        name = 'Example %d' % int(fn.__name__[7:])
    except Exception:
        name = fn.__name__

    def wrapped():
        try:
            sys.stdout.write(f'Running: {name}\n')
            fn()
            sys.stdout.write('\n')
        except KeyboardInterrupt:
            sys.stdout.write('\nSkipping example.\n\n')

    examples.append(wrapped)
    return wrapped


@example
def example0() -> None:
    pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=300).start()
    for i in range(300):
        time.sleep(0.01)
        pbar.update(i + 1)
    pbar.finish()


@example
def example1() -> None:
    widgets = [
        'Test: ',
        Percentage(),
        ' ',
        Bar(marker=RotatingMarker()),
        ' ',
        ETA(),
        ' ',
        FileTransferSpeed(),
    ]
    pbar = ProgressBar(widgets=widgets, maxval=10000).start()
    for i in range(1000):
        # do something
        pbar.update(10 * i + 1)
    pbar.finish()


@example
def example2() -> None:
    class CrazyFileTransferSpeed(FileTransferSpeed):
        """It's bigger between 45 and 80 percent."""

        def update(self, pbar):
            if 45 < pbar.percentage() < 80:
                return 'Bigger Now ' + FileTransferSpeed.update(self, pbar)
            else:
                return FileTransferSpeed.update(self, pbar)

    widgets = [
        CrazyFileTransferSpeed(),
        ' <<<',
        Bar(),
        '>>> ',
        Percentage(),
        ' ',
        ETA(),
    ]
    pbar = ProgressBar(widgets=widgets, maxval=10000)
    # maybe do something
    pbar.start()
    for i in range(2000):
        # do something
        pbar.update(5 * i + 1)
    pbar.finish()


@example
def example3() -> None:
    widgets = [Bar('>'), ' ', ETA(), ' ', ReverseBar('<')]
    pbar = ProgressBar(widgets=widgets, maxval=10000).start()
    for i in range(1000):
        # do something
        pbar.update(10 * i + 1)
    pbar.finish()


@example
def example4() -> None:
    widgets = [
        'Test: ',
        Percentage(),
        ' ',
        Bar(marker='0', left='[', right=']'),
        ' ',
        ETA(),
        ' ',
        FileTransferSpeed(),
    ]
    pbar = ProgressBar(widgets=widgets, maxval=500)
    pbar.start()
    for i in range(100, 500 + 1, 50):
        time.sleep(0.2)
        pbar.update(i)
    pbar.finish()


@example
def example5() -> None:
    pbar = ProgressBar(widgets=[SimpleProgress()], maxval=17).start()
    for i in range(17):
        time.sleep(0.2)
        pbar.update(i + 1)
    pbar.finish()


@example
def example6() -> None:
    pbar = ProgressBar().start()
    for i in range(100):
        time.sleep(0.01)
        pbar.update(i + 1)
    pbar.finish()


@example
def example7() -> None:
    pbar = ProgressBar()  # Progressbar can guess maxval automatically.
    for _i in pbar(range(80)):
        time.sleep(0.01)


@example
def example8() -> None:
    pbar = ProgressBar(maxval=80)  # Progressbar can't guess maxval.
    for _i in pbar(i for i in range(80)):
        time.sleep(0.01)


@example
def example9() -> None:
    pbar = ProgressBar(widgets=['Working: ', AnimatedMarker()])
    for _i in pbar(i for i in range(50)):
        time.sleep(0.08)


@example
def example10() -> None:
    widgets = ['Processed: ', Counter(), ' lines (', Timer(), ')']
    pbar = ProgressBar(widgets=widgets)
    for _i in pbar(i for i in range(150)):
        time.sleep(0.1)


@example
def example11() -> None:
    widgets = [FormatLabel('Processed: %(value)d lines (in: %(elapsed)s)')]
    pbar = ProgressBar(widgets=widgets)
    for _i in pbar(i for i in range(150)):
        time.sleep(0.1)


@example
def example12() -> None:
    widgets = ['Balloon: ', AnimatedMarker(markers='.oO@* ')]
    pbar = ProgressBar(widgets=widgets)
    for _i in pbar(i for i in range(24)):
        time.sleep(0.3)


@example
def example13() -> None:
    # You may need python 3.x to see this correctly
    try:
        widgets = ['Arrows: ', AnimatedMarker(markers='←↖↑↗→↘↓↙')]
        pbar = ProgressBar(widgets=widgets)
        for _i in pbar(i for i in range(24)):
            time.sleep(0.3)
    except UnicodeError:
        sys.stdout.write('Unicode error: skipping example')


@example
def example14() -> None:
    # You may need python 3.x to see this correctly
    try:
        widgets = ['Arrows: ', AnimatedMarker(markers='◢◣◤◥')]
        pbar = ProgressBar(widgets=widgets)
        for _i in pbar(i for i in range(24)):
            time.sleep(0.3)
    except UnicodeError:
        sys.stdout.write('Unicode error: skipping example')


@example
def example15() -> None:
    # You may need python 3.x to see this correctly
    try:
        widgets = ['Wheels: ', AnimatedMarker(markers='◐◓◑◒')]
        pbar = ProgressBar(widgets=widgets)
        for _i in pbar(i for i in range(24)):
            time.sleep(0.3)
    except UnicodeError:
        sys.stdout.write('Unicode error: skipping example')


@example
def example16() -> None:
    widgets = [FormatLabel('Bouncer: value %(value)d - '), BouncingBar()]
    pbar = ProgressBar(widgets=widgets)
    for _i in pbar(i for i in range(180)):
        time.sleep(0.05)


@example
def example17() -> None:
    widgets = [
        FormatLabel('Animated Bouncer: value %(value)d - '),
        BouncingBar(marker=RotatingMarker()),
    ]

    pbar = ProgressBar(widgets=widgets)
    for _i in pbar(i for i in range(180)):
        time.sleep(0.05)


@example
def example18() -> None:
    widgets = [Percentage(), ' ', Bar(), ' ', ETA(), ' ', AdaptiveETA()]
    pbar = ProgressBar(widgets=widgets, maxval=500)
    pbar.start()
    for i in range(500):
        time.sleep(0.01 + (i < 100) * 0.01 + (i > 400) * 0.9)
        pbar.update(i + 1)
    pbar.finish()


@example
def example19() -> None:
    pbar = ProgressBar()
    for _i in pbar([]):
        pass
    pbar.finish()


@example
def example20() -> None:
    """Widgets that behave differently when length is unknown"""
    widgets = [
        '[When length is unknown at first]',
        ' Progress: ',
        SimpleProgress(),
        ', Percent: ',
        Percentage(),
        ' ',
        ETA(),
        ' ',
        AdaptiveETA(),
    ]
    pbar = ProgressBar(widgets=widgets, maxval=UnknownLength)
    pbar.start()
    for i in range(20):
        time.sleep(0.5)
        if i == 10:
            pbar.maxval = 20
        pbar.update(i + 1)
    pbar.finish()


if __name__ == '__main__':
    try:
        for example in examples:
            example()
    except KeyboardInterrupt:
        sys.stdout.write('\nQuitting examples.\n')
