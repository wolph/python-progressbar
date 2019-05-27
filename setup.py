#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys


try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages


# Not all systems use utf8 encoding by default, this works around that issue
if sys.version_info > (3,):
    from functools import partial
    open = partial(open, encoding='utf8')


# To prevent importing about and thereby breaking the coverage info we use this
# exec hack
about = {}
with open("progressbar/__about__.py") as fp:
    exec(fp.read(), about)


install_reqs = []
needs_pytest = set(['ptr', 'pytest', 'test']).intersection(sys.argv)
pytest_runner = ['pytest-runner>=2.8'] if needs_pytest else []
tests_reqs = []

if sys.version_info < (2, 7):
    tests_reqs += ['unittest2']


if sys.argv[-1] == 'info':
    for k, v in about.items():
        print('%s: %s' % (k, v))
    sys.exit()

if os.path.isfile('README.rst'):
    with open('README.rst') as fh:
        readme = fh.read()
else:
    readme = \
        'See http://pypi.python.org/pypi/%(__package_name__)s/' % about


if __name__ == '__main__':
    setup(
        name=about['__package_name__'],
        version=about['__version__'],
        author=about['__author__'],
        author_email=about['__email__'],
        description=about['__description__'],
        url=about['__url__'],
        license=about['__license__'],
        keywords=about['__title__'],
        packages=find_packages(exclude=['docs']),
        long_description=readme,
        include_package_data=True,
        install_requires=[
            'python-utils>=2.3.0',
            'six',
        ],
        tests_require=tests_reqs,
        setup_requires=['setuptools'] + pytest_runner,
        zip_safe=False,
        extras_require={
            'docs': [
                'sphinx>=1.7.4',
            ],
            'tests': [
                'flake8>=3.7.7',
                'pytest>=4.3.1',
                'pytest-cov>=2.6.1',
                'pytest-flakes>=4.0.0',
                'pytest-pep8>=1.0.6',
                'freezegun>=0.3.11',
                'sphinx>=1.8.5',
            ],
        },
        classifiers=[
            'Development Status :: 6 - Mature',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Natural Language :: English',
            "Programming Language :: Python :: 2",
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: Implementation :: PyPy',
        ],
    )
