# -*- coding: utf-8 -*-

import time
import progressbar


def test_empty_arrows():
    # You may need python 3.x to see this correctly
    widgets = ['Arrows: ', progressbar.AnimatedMarker(markers=u'←↖↑↗→↘↓↙')]
    pbar = progressbar.ProgressBar(widgets=widgets)
    for i in pbar((i for i in range(24))):
        time.sleep(0.001)


def test_filled_arrows():
    # You may need python 3.x to see this correctly
    widgets = ['Arrows: ', progressbar.AnimatedMarker(markers=u'◢◣◤◥')]
    pbar = progressbar.ProgressBar(widgets=widgets)
    for i in pbar((i for i in range(24))):
        time.sleep(0.001)


def test_wheels():
    # You may need python 3.x to see this correctly
    widgets = ['Wheels: ', progressbar.AnimatedMarker(markers=u'◐◓◑◒')]
    pbar = progressbar.ProgressBar(widgets=widgets)
    for i in pbar((i for i in range(24))):
        time.sleep(0.001)


