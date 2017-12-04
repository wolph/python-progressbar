# -*- mode: python; coding: utf-8 -*-
import six
import pytest
import progressbar.utils


@pytest.mark.parametrize('val,expected', [('abc', u'abc'),
                                          (u'←', u'←'),
                                          (u'◢', u'◢'),
                                          (b'abc', u'abc'),
                                          (r'c:\dir', u'c:\\dir'),
                                          (None, u"None")])
def test_to_unicode(val, expected):
    result = progressbar.utils.to_unicode(val)
    assert result == expected, result
    assert isinstance(result, six.text_type), type(result)
