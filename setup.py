#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import setup, find_packages

# To prevent importing about and thereby breaking the coverage info we use this
# exec hack
about = {}
with open('progressbar/__about__.py', encoding='utf8') as fp:
    exec(fp.read(), about)


install_reqs = []
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
        name='progressbar2',
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
            'python-utils>=3.0.0',
        ],
        setup_requires=['setuptools'],
        zip_safe=False,
        extras_require={
            'docs': [
                'sphinx>=1.8.5',
            ],
            'tests': [
                'flake8>=3.7.7',
                'pytest>=4.6.9',
                'pytest-cov>=2.6.1',
                'pytest-mypy',
                'freezegun>=0.3.11',
                'sphinx>=1.8.5',
            ],
        },
        python_requires='>=3.7.0',
        classifiers=[
            'Development Status :: 6 - Mature',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Natural Language :: English',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            'Programming Language :: Python :: Implementation :: PyPy',
        ],
    )
