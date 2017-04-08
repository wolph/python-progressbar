from progressbar import __about__


def test_about():
    assert __about__.__title__
    assert __about__.__package_name__
    assert __about__.__author__
    assert __about__.__description__
    assert __about__.__email__
    assert __about__.__version__
    assert __about__.__license__
    assert __about__.__copyright__
    assert __about__.__url__
