#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys


try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

# To prevent importing about and thereby breaking the coverage info we use this
# exec hack
about = {}
with open("progressbar/__about__.py") as fp:
    exec(fp.read(), about)


install_reqs = []
tests_reqs = []

if sys.version_info < (2, 7):
    tests_reqs += ['unittest2']


def parse_requirements(filename):
    '''Read the requirements from the filename, supports includes'''
    requirements = []

    if os.path.isfile(filename):
        with open(filename) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith('-r'):
                    requirements += parse_requirements(
                        os.path.join(os.path.dirname(filename),
                                     line.split(' ', 1)[-1]))
                elif line and not line.startswith('#'):
                    requirements.append(line)

    return requirements

install_reqs += parse_requirements('requirements.txt')
tests_reqs += parse_requirements('tests/requirements.txt')

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
        install_requires=install_reqs,
        tests_require=tests_reqs,
        setup_requires=['setuptools', 'pytest-runner>=2.8'],
        zip_safe=False,
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Natural Language :: English',
            "Programming Language :: Python :: 2",
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: Implementation :: PyPy',
        ],
    )
