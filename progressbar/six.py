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
    basestring = str
else:  # pragma: no cover
    import __builtin__
    basestring = __builtin__.basestring
