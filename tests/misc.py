from progressbar import metadata


def test_metadata():
    assert metadata.__package_name__
    assert metadata.__author__
    assert metadata.__author_email__
    assert metadata.__url__
    assert metadata.__date__
    assert metadata.__version__
