"""Text progress bar library for Python.

A text progress bar is typically used to display the progress of a long
running operation, providing a visual cue that processing is underway.

The ProgressBar class manages the current progress, and the format of the line
is given by a number of widgets. A widget is an object that may display
differently depending on the state of the progress bar.

The progressbar module is very easy to use, yet very powerful. It will also
automatically enable features like auto-resizing when the system supports it.
"""

__title__ = 'Python Progressbar'
__package_name__ = 'progressbar2'
__author__ = 'Rick van Hattem (Wolph)'
__description__: str = ' '.join(
    """
A Python Progressbar library to provide visual (yet text based) progress to
long running operations.
""".strip().split(),
)
__email__ = 'wolph@wol.ph'
__version__ = '4.6.0'
#: Release date of ``__version__`` as a static string. Bump on each release.
__date__ = '2026-08-13'
__license__ = 'BSD'
__copyright__ = 'Copyright 2015-2026 Rick van Hattem (Wolph)'
__url__ = 'https://github.com/wolph/python-progressbar'
