#!/usr/bin/python

import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
from progressbar import metadata


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

if __name__ == '__main__':
    setup(
        name=metadata.__package_name__,
        version=metadata.__version__,
        packages=find_packages(),
        description=metadata.__doc__.split('\n')[0],
        long_description=metadata.__doc__,
        author=metadata.__author__,
        maintainer=metadata.__author__,
        author_email=metadata.__author_email__,
        maintainer_email=metadata.__author_email__,
        url=metadata.__url__,
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
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Topic :: Software Development :: Libraries',
            'Topic :: Software Development :: User Interfaces',
            'Topic :: Terminals'
        ],
    )
