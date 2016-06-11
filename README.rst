Text progress bar library for Python.
=====================================

Travis status:

.. image:: https://travis-ci.org/WoLpH/python-progressbar.png?branch=master
  :target: https://travis-ci.org/WoLpH/python-progressbar

Coverage:

.. image:: https://coveralls.io/repos/WoLpH/python-progressbar/badge.png?branch=master
  :target: https://coveralls.io/r/WoLpH/python-progressbar?branch=master

Introduction
------------

.. highlights::

    **NOTE:** This version has been completely rewritten and might not be
    100% compatible with the old version. If you encounter any problems
    while using it please let me know:
    https://github.com/WoLpH/python-progressbar/issues

A text progress bar is typically used to display the progress of a long
running operation, providing a visual cue that processing is underway.

The ProgressBar class manages the current progress, and the format of the line
is given by a number of widgets. A widget is an object that may display
differently depending on the state of the progress bar. There are many types
of widgets:

 - `Timer`
 - `ETA`
 - `AdaptiveETA`
 - `FileTransferSpeed`
 - `AdaptiveTransferSpeed`
 - `AnimatedMarker`
 - `Counter`
 - `Percentage`
 - `FormatLabel`
 - `SimpleProgress`
 - `Bar`
 - `ReverseBar`
 - `BouncingBar`
 - `RotatingMarker`
 - `DynamicMessage`

The progressbar module is very easy to use, yet very powerful. It will also
automatically enable features like auto-resizing when the system supports it.

Links
-----

* Documentation
    - http://progressbar-2.readthedocs.org/en/latest/
* Source
    - https://github.com/WoLpH/python-progressbar
* Bug reports 
    - https://github.com/WoLpH/python-progressbar/issues
* Package homepage
    - https://pypi.python.org/pypi/progressbar2
* My blog
    - http://w.wol.ph/

