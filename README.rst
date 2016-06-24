##############################################################################
Text progress bar library for Python.
##############################################################################

Travis status:

.. image:: https://travis-ci.org/WoLpH/python-progressbar.png?branch=master
  :target: https://travis-ci.org/WoLpH/python-progressbar

Coverage:

.. image:: https://coveralls.io/repos/WoLpH/python-progressbar/badge.png?branch=master
  :target: https://coveralls.io/r/WoLpH/python-progressbar?branch=master

******************************************************************************
Introduction
******************************************************************************

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

******************************************************************************
Links
******************************************************************************

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

******************************************************************************
Usage
******************************************************************************

There are many ways to use Python Progressbar, you can see a few basic examples
here but there are many more in the :doc:`examples` file.

Wrapping an iterable
==============================================================================
::

   import time
   import progressbar

   bar = progressbar.ProgressBar()
   for i in bar(range(100)):
       time.sleep(0.02)

Context wrapper
==============================================================================
::

   import time
   import progressbar

   with progressbar.ProgressBar(max_value=10) as bar:
       for i in range(10):
           time.sleep(0.1)
           bar.update(i)

Combining progressbars with print output
==============================================================================
::

    import time
    import progressbar

    bar = progressbar.ProgressBar(redirect_stdout=True)
    for i in range(100):
        print 'Some text', i
        time.sleep(0.1)
        bar.update(i)

Progressbar with unknown length
==============================================================================
::

    import time
    import progressbar

    bar = progressbar.ProgressBar(max_value=progressbar.UnknownLength)
    for i in range(20):
        time.sleep(0.1)
        bar.update(i)

Bar with custom widgets
==============================================================================
::

    import time
    import progressbar

    bar = progressbar.ProgressBar(widgets=[
        ' [', progressbar.Timer(), '] ',
        progressbar.Bar(),
        ' (', progressbar.ETA(), ') ',
    ])
    for i in bar(range(20)):
        time.sleep(0.1)

