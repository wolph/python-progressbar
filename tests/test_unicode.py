# -*- coding: utf-8 -*-

import time
import pytest
import progressbar

import six


def _to_str(value):
    if isinstance(value, six.binary_type):
        return value
    return value.encode('utf-8', 'replace')


@pytest.mark.parametrize('name,markers', [
    ('line arrows', u'←↖↑↗→↘↓↙'),
    ('block arrows', u'◢◣◤◥'),
    ('wheels', u'◐◓◑◒'),
])
@pytest.mark.parametrize('as_unicode', [True, False])
def test_markers(name, markers, as_unicode):
    if as_unicode:
        markers = progressbar.utils.to_unicode(markers)
    else:
        markers = _to_str(markers)

    widgets = [
        '%s: ' % name.capitalize(),
        progressbar.AnimatedMarker(markers=markers),
    ]
    bar = progressbar.ProgressBar(widgets=widgets)
    bar._MINIMUM_UPDATE_INTERVAL = 1e-12
    for i in bar((i for i in range(24))):
        time.sleep(0.001)

