# -*- coding: utf-8 -*-

import time
import pytest
import progressbar
from python_utils import converters


@pytest.mark.parametrize('name,markers', [
    ('line arrows', u'←↖↑↗→↘↓↙'),
    ('block arrows', u'◢◣◤◥'),
    ('wheels', u'◐◓◑◒'),
])
@pytest.mark.parametrize('as_unicode', [True, False])
def test_markers(name, markers, as_unicode):
    if as_unicode:
        markers = converters.to_unicode(markers)
    else:
        markers = converters.to_str(markers)

    widgets = [
        '%s: ' % name.capitalize(),
        progressbar.AnimatedMarker(markers=markers),
    ]
    bar = progressbar.ProgressBar(widgets=widgets)
    bar._MINIMUM_UPDATE_INTERVAL = 1e-12
    for i in bar((i for i in range(24))):
        time.sleep(0.001)

