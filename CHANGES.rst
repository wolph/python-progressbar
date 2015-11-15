=========
Changelog
=========

Here you can find the recent changes to Python Progressbar..

.. changelog::
    :version: dev
    :released: Ongoing

    .. change::
        :tags:  docs

        Updated CHANGES.

.. changelog::
    :version: 3.5
    :released: 2015-11-15

    .. change::
        Added support for size-dependent widgets

    .. change::
        Fixed inheritance issues

.. changelog::
    :version: 3.4
    :released: 2015-11-11

    .. change::
        Added usage documentation

    .. change::
        Fixed several bugs including default widths and output redirection

    :version: 3.3
    :released: 2015-10-12

    .. change::
        :tags: unknown-length

        Fixed `UnknownLength` handling. Thanks to @takluyver

.. changelog::
    :version: 3.2
    :released: 2015-10-11

    .. change::
        :tags: packaging

        Cookiecutter package

.. changelog::
    :version: 3.1
    :released: 2015-07-11

    .. change::
        :tags: python 3

        Python 3 support

2011-05-15:
  - Removed parse errors for Python2.4 (no, people *should not* be using it
    but it is only 3 years old and it does not have that many differences)

  - split up progressbar.py into logical units while maintaining backwards
    compatability

  - Removed MANIFEST.in because it is no longer needed and it was causing
    distribute to show warnings


2011-05-14:
  - Changes to directory structure so pip can install from Google Code
  - Python 3.x related fixes (all examples work on Python 3.1.3)
  - Added counters, timers, and action bars for iterators with unknown length

2010-08-29:
  - Refactored some code and made it possible to use a ProgressBar as
    an iterator (actually as an iterator that is a proxy to another iterator).
    This simplifies showing a progress bar in a number of cases.

2010-08-15:
  - Did some minor changes to make it compatible with python 3.

2009-05-31:
  - Included check for calling start before update.

2009-03-21:
  - Improved FileTransferSpeed widget, which now supports an unit parameter,
    defaulting to 'B' for bytes. It will also show B/s, MB/s, etc instead of
    B/s, M/s, etc.

2009-02-24:
  - Updated licensing.
  - Moved examples to separated file.
  - Improved _need_update() method, which is now as fast as it can be. IOW,
    no wasted cycles when an update is not needed.

2008-12-22:
  - Added SimpleProgress widget contributed by Sando Tosi
    <matrixhasu at gmail.com>.

2006-05-07:
  - Fixed bug with terminal width in Windows.
  - Released version 2.2.

2005-12-04:
  - Autodetection of terminal width.
  - Added start method.
  - Released version 2.1.

2005-12-04:
  - Everything is a widget now!
  - Released version 2.0.

2005-12-03:
  - Rewrite using widgets.
  - Released version 1.0.

2005-06-02:
  - Rewrite.
  - Released version 0.5.

2004-06-15:
  - First version.
  - Released version 0.1.

.. todo:: vim: set filetype=rst:
