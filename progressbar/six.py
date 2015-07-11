'''Library to make differences between Python 2 and 3 transparent'''

__all__ = [
    'StringIO',
    'basestring',
]

import sys

try:
    from cStringIO import StringIO
except ImportError:  # pragma: no cover
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO

PY2 = sys.version[0] == 2

if PY2:
    basestring = basestring
else:
    basestring = str

