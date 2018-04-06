import pytest
import progressbar


@pytest.fixture(autouse=True)
def large_interval(monkeypatch):
    # Remove the update limit for tests by default
    monkeypatch.setattr(
        progressbar.ProgressBar, '_MINIMUM_UPDATE_INTERVAL', 0.1)


def test_end():
    m = 24514315
    p = progressbar.ProgressBar(
        widgets=[progressbar.Percentage(), progressbar.Bar()],
        max_value=m
    )

    for x in range(0, m, 8192):
        p.update(x)

    data = p.data()
    assert data['percentage'] < 100.

    p.finish()

    data = p.data()
    assert data['percentage'] >= 100.

    assert p.value == m


def test_end_100(monkeypatch):
    assert progressbar.ProgressBar._MINIMUM_UPDATE_INTERVAL == 0.1
    p = progressbar.ProgressBar(
        widgets=[progressbar.Percentage(), progressbar.Bar()],
        max_value=103,
    )

    for x in range(0, 102):
        p.update(x)

    data = p.data()
    import pprint
    pprint.pprint(data)
    assert data['percentage'] < 100.

    p.finish()

    data = p.data()
    assert data['percentage'] >= 100.
