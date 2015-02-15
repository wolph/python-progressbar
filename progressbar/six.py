'''Library to make differences between Python 2 and 3 transparent'''

__all__ = [
    'StringIO',
]

try:
    from cStringIO import StringIO
except ImportError:  # pragma: no cover
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO

