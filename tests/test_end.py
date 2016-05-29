import progressbar


def test_end():
    m = 24514315
    p = progressbar.ProgressBar(
        widgets=[progressbar.Percentage(), progressbar.Bar()],
        max_value=m
    )

    for x in range(0, m, 8192):
        p.update(x)

    p.finish()
    data = p.data()
    assert data['percentage'] >= 100.
    assert p.value == m


def test_end_100():
    p = progressbar.ProgressBar(
        widgets=[progressbar.Percentage(), progressbar.Bar()],
        max_value=101,
    )

    for x in range(0, 102):
        p.update(x)

    data = p.data()
    assert data['percentage'] >= 100.
    p.finish()
    assert data['percentage'] >= 100.

