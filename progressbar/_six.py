'''Library to make differences between Python 2 and 3 transparent'''
import sys

PY3 = sys.version_info[0] == 3

if PY3:  # pragma: no cover
    long_int = int
else:  # pragma: no cover
    long_int = long  # NOQA
