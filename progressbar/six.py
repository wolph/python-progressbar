'''Library to make differences between Python 2 and 3 transparent'''
import sys

__all__ = [
    'StringIO',
    'basestring',
]

try:
    from cStringIO import StringIO
except ImportError:  # pragma: no cover
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO

PY3 = sys.version_info[0] == 3

if PY3:  # pragma: no cover
    basestring = str,
else:  # pragma: no cover
    basestring = str, unicode  # NOQA


if PY3:  # pragma: no cover
    numeric_types = int, float
else:  # pragma: no cover
    numeric_types = int, long, float  # NOQA


if PY3:  # pragma: no cover
    long_int = int
else:  # pragma: no cover
    long_int = long  # NOQA
