#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys


try:
    from setuptools import setup, find_packages
    from setuptools.command.test import test as TestCommand
except ImportError:
    from distutils.core import setup, find_packages, Command as TestCommand

about = {}
with open("progressbar/__about__.py") as fp:
    exec(fp.read(), about)


install_reqs = []
tests_reqs = []

if sys.version_info < (2, 7):
    install_reqs += ['argparse']
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

with open('README.rst') as fh:
    readme = fh.read()


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)

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
    zip_safe=False,
    cmdclass={'test': PyTest},
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
