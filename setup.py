#!/usr/bin/python

import os
from distutils.core import setup
import progressbar

if (not os.path.exists('README') or
    os.stat('progressbar.py').st_mtime > os.stat('README').st_mtime):
    file('README','w').write(progressbar.__doc__)

setup(
    name = 'progressbar',
    version = progressbar.__version__,
    description = progressbar.__doc__.splitlines()[0],
    long_description = progressbar.__doc__,
    maintainer = progressbar.__author__,
    maintainer_email = progressbar.__author_email__,
    url = 'http://code.google.com/p/python-progressbar',
    py_modules = [ 'progressbar' ],
    classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development :: User Interfaces',
    'Topic :: Terminals',
    ],
)
