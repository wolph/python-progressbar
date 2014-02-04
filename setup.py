#!/usr/bin/python

import os
from setuptools import setup, find_packages
import progressbar

# TODO: I don't believe this should be in here. This should be done on package
#       creation only
try:
    readme = 'README.txt'
    info = 'progressbar/__init__.py'

    if (not os.path.exists(readme) or
            os.stat(info).st_mtime > os.stat(readme).st_mtime):

        open(readme, 'w').write(progressbar.__doc__)
except:
    pass

setup(
    name='progressbar2',
    version=progressbar.__version__,
    packages=find_packages(),

    description=progressbar.__doc__.split('\n')[0],
    long_description=progressbar.__doc__,

    author=progressbar.__author__,
    maintainer=progressbar.__author__,
    author_email=progressbar.__author_email__,
    maintainer_email=progressbar.__author_email__,

    url='https://github.com/WoLpH/python-progressbar',
    license='LICENSE.txt',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: '
            'GNU Library or Lesser General Public License (LGPL)',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Terminals'
    ],
)
