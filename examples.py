#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import time

from progressbar import AnimatedMarker, Bar, BouncingBar, Counter, ETA, \
    FileTransferSpeed, FormatLabel, Percentage, \
    ProgressBar, ReverseBar, RotatingMarker, \
    SimpleProgress, Timer, AdaptiveETA, AbsoluteETA, AdaptiveTransferSpeed

examples = []


def example(fn):
    def wrapped():
        try:
            sys.stdout.write('Running: %s\n' % fn.__name__)
            fn()
            sys.stdout.write('\n')
        except KeyboardInterrupt:
            sys.stdout.write('\nSkipping example.\n\n')

    examples.append(wrapped)
    return wrapped


@example
def with_example0():
    with ProgressBar(max_value=10) as progress:
        for i in range(10):
            # do something
            time.sleep(0.001)
            progress.update(i)


@example
def with_example1():
    with ProgressBar(max_value=10, redirect_stdout=True) as p:
        for i in range(10):
            # do something
            p.update(i)
            time.sleep(0.001)


@example
def example0():
    pbar = ProgressBar(widgets=[Percentage(), Bar()], max_value=10).start()
    for i in range(10):
        # do something
        time.sleep(0.001)
        pbar.update(i + 1)
    pbar.finish()


@example
def example1():
    widgets = ['Test: ', Percentage(), ' ', Bar(marker=RotatingMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, max_value=1000).start()
    for i in range(100):
        # do something
        pbar.update(10 * i + 1)
    pbar.finish()


@example
def example2():
    class CrazyFileTransferSpeed(FileTransferSpeed):

        "It's bigger between 45 and 80 percent"

        def update(self, pbar):
            if 45 < pbar.percentage() < 80:
                return 'Bigger Now ' + FileTransferSpeed.update(self, pbar)
            else:
                return FileTransferSpeed.update(self, pbar)

    widgets = [CrazyFileTransferSpeed(), ' <<<', Bar(), '>>> ',
               Percentage(), ' ', ETA()]
    pbar = ProgressBar(widgets=widgets, max_value=1000)
    # maybe do something
    pbar.start()
    for i in range(200):
        # do something
        pbar.update(5 * i + 1)
    pbar.finish()


@example
def example3():
    widgets = [Bar('>'), ' ', ETA(), ' ', ReverseBar('<')]
    pbar = ProgressBar(widgets=widgets, max_value=1000).start()
    for i in range(100):
        # do something
        pbar.update(10 * i + 1)
    pbar.finish()


@example
def example4():
    widgets = ['Test: ', Percentage(), ' ',
               Bar(marker='0', left='[', right=']'),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, max_value=500)
    pbar.start()
    for i in range(100, 500 + 1, 50):
        time.sleep(0.001)
        pbar.update(i)
    pbar.finish()


@example
def example5():
    pbar = ProgressBar(widgets=[SimpleProgress()], max_value=17).start()
    for i in range(17):
        time.sleep(0.001)
        pbar.update(i + 1)
    pbar.finish()


@example
def example6():
    pbar = ProgressBar().start()
    for i in range(10):
        time.sleep(0.001)
        pbar.update(i + 1)
    pbar.finish()


@example
def example7():
    pbar = ProgressBar()  # Progressbar can guess max_value automatically.
    for i in pbar(range(8)):
        time.sleep(0.001)


@example
def example8():
    pbar = ProgressBar(max_value=8)  # Progressbar can't guess max_value.
    for i in pbar((i for i in range(8))):
        time.sleep(0.001)


@example
def example9():
    pbar = ProgressBar(widgets=['Working: ', AnimatedMarker()])
    for i in pbar((i for i in range(5))):
        time.sleep(0.001)


@example
def example10():
    widgets = ['Processed: ', Counter(), ' lines (', Timer(), ')']
    pbar = ProgressBar(widgets=widgets)
    for i in pbar((i for i in range(15))):
        time.sleep(0.001)


@example
def example11():
    widgets = [FormatLabel('Processed: %(value)d lines (in: %(elapsed)s)')]
    pbar = ProgressBar(widgets=widgets)
    for i in pbar((i for i in range(15))):
        time.sleep(0.001)


@example
def example12():
    widgets = ['Balloon: ', AnimatedMarker(markers='.oO@* ')]
    pbar = ProgressBar(widgets=widgets)
    for i in pbar((i for i in range(24))):
        time.sleep(0.001)


@example
def example13():
    # You may need python 3.x to see this correctly
    try:
        widgets = ['Arrows: ', AnimatedMarker(markers='←↖↑↗→↘↓↙')]
        pbar = ProgressBar(widgets=widgets)
        for i in pbar((i for i in range(24))):
            time.sleep(0.001)
    except UnicodeError:
        sys.stdout.write('Unicode error: skipping example')


@example
def example14():
    # You may need python 3.x to see this correctly
    try:
        widgets = ['Arrows: ', AnimatedMarker(markers='◢◣◤◥')]
        pbar = ProgressBar(widgets=widgets)
        for i in pbar((i for i in range(24))):
            time.sleep(0.001)
    except UnicodeError:
        sys.stdout.write('Unicode error: skipping example')


@example
def example15():
    # You may need python 3.x to see this correctly
    try:
        widgets = ['Wheels: ', AnimatedMarker(markers='◐◓◑◒')]
        pbar = ProgressBar(widgets=widgets)
        for i in pbar((i for i in range(24))):
            time.sleep(0.001)
    except UnicodeError:
        sys.stdout.write('Unicode error: skipping example')


@example
def example16():
    widgets = [FormatLabel('Bouncer: value %(value)d - '), BouncingBar()]
    pbar = ProgressBar(widgets=widgets)
    for i in pbar((i for i in range(100))):
        time.sleep(0.001)


@example
def example17():
    widgets = [FormatLabel('Animated Bouncer: value %(value)d - '),
               BouncingBar(marker=RotatingMarker())]

    pbar = ProgressBar(widgets=widgets)
    for i in pbar((i for i in range(18))):
        time.sleep(0.001)


@example
def with_example18():
    with ProgressBar(max_value=10, term_width=20, left_justify=False) as \
            progress:
        assert progress._env_size() is not None
        for i in range(10):
            progress.update(i)


@example
def with_example19():
    with ProgressBar(max_value=1) as progress:
        try:
            progress.update(2)
        except ValueError:
            pass


@example
def with_example20():
    progress = ProgressBar(max_value=1)
    try:
        progress.update(1)
    except RuntimeError:
        pass


@example
def with_example21a():
    with ProgressBar(max_value=1, redirect_stdout=True) as progress:
        print('', file=sys.stdout)
        progress.update(0)


@example
def with_example21b():
    with ProgressBar(max_value=1, redirect_stderr=True) as progress:
        print('', file=sys.stderr)
        progress.update(0)


@example
def with_example22():
    try:
        with ProgressBar(max_value=-1) as progress:
            progress.start()
    except ValueError:
        pass


@example
def example23():
    widgets = [BouncingBar(marker=RotatingMarker())]
    with ProgressBar(widgets=widgets, max_value=20, term_width=10) as progress:
        for i in range(20):
            progress.update(i)

    widgets = [BouncingBar(marker=RotatingMarker(), fill_left=False)]
    with ProgressBar(widgets=widgets, max_value=20, term_width=10) as progress:
        for i in range(20):
            progress.update(i)


@example
def example24():
    pbar = ProgressBar(widgets=[Percentage(), Bar()], max_value=10).start()
    for i in range(10):
        # do something
        time.sleep(0.001)
        pbar += 1
    pbar.finish()


@example
def example25():
    widgets = ['Test: ', Percentage(), ' ', Bar(marker=RotatingMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, max_value=1000,
                       redirect_stdout=True).start()
    for i in range(100):
        # do something
        pbar += 10
    pbar.finish()


@example
def example26():
    widgets = [
        Percentage(),
        ' ', Bar(),
        ' ', ETA(),
        ' ', AdaptiveETA(),
        ' ', AdaptiveTransferSpeed(),
    ]
    pbar = ProgressBar(widgets=widgets, max_value=500)
    pbar.start()
    for i in range(500):
        time.sleep(0.001 + (i < 100) * 0.0001 + (i > 400) * 0.009)
        pbar.update(i + 1)
    pbar.finish()


@example
def example27():
    # Testing AdaptiveETA when the value doesn't actually change
    pbar = ProgressBar(widgets=[AdaptiveETA(), AdaptiveTransferSpeed()],
                       max_value=2, poll=0.0001)
    pbar.start()
    pbar.update(1)
    time.sleep(0.001)
    pbar.update(1)
    pbar.finish()


@example
def example28():
    # Testing using progressbar as an iterator with a max value
    pbar = ProgressBar()

    for n in pbar(iter(range(100)), 100):
        # iter range is a way to get an iterator in both python 2 and 3
        pass


@example
def example29():
    widgets = ['Test: ', Percentage(), ' | ', ETA(), ' | ', AbsoluteETA()]
    pbar = ProgressBar(widgets=widgets, maxval=500).start()
    for i in range(500):
        time.sleep(0.01)
        pbar.update(i+1)
    pbar.finish()


def test():
    for example in examples:
        example()

if __name__ == '__main__':
    try:
        test()
    except KeyboardInterrupt:
        sys.stdout('\nQuitting examples.\n')
