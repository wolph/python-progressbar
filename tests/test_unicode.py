from __future__ import annotations

import time

import pytest
from python_utils import converters

import progressbar


@pytest.mark.parametrize(
    'name,markers',
    [
        ('line arrows', '←↖↑↗→↘↓↙'),
        ('block arrows', '◢◣◤◥'),
        ('wheels', '◐◓◑◒'),
    ],
)
@pytest.mark.parametrize('as_unicode', [True, False])
def test_markers(name, markers: bytes | str, as_unicode) -> None:
    if as_unicode:
        markers = converters.to_unicode(markers)
    else:
        markers = converters.to_str(markers)

    widgets = [
        f'{name.capitalize()}: ',
        progressbar.AnimatedMarker(markers=markers),
    ]
    bar = progressbar.ProgressBar(widgets=widgets)
    bar._MINIMUM_UPDATE_INTERVAL = 1e-12
    for _i in bar(iter(range(24))):
        time.sleep(0.001)
