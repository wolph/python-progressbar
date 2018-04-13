##############################################################################
Text progress bar library for Python.
##############################################################################

Travis status:

.. image:: https://travis-ci.org/WoLpH/python-progressbar.svg?branch=master
  :target: https://travis-ci.org/WoLpH/python-progressbar

Coverage:

.. image:: https://coveralls.io/repos/WoLpH/python-progressbar/badge.svg?branch=master
  :target: https://coveralls.io/r/WoLpH/python-progressbar?branch=master

******************************************************************************
Install
******************************************************************************

The package can be installed through `pip` (this is the recommended method):

    pip install progressbar2
    
Or if `pip` is not available, `easy_install` should work as well:

    easy_install progressbar2
    
Or download the latest release from Pypi (https://pypi.python.org/pypi/progressbar2) or Github.

Note that the releases on Pypi are signed with my GPG key (https://pgp.mit.edu/pks/lookup?op=vindex&search=0xE81444E9CE1F695D) and can be checked using GPG:

     gpg --verify progressbar2-<version>.tar.gz.asc progressbar2-<version>.tar.gz

******************************************************************************
Introduction
******************************************************************************

A text progress bar is typically used to display the progress of a long
running operation, providing a visual cue that processing is underway.

The ProgressBar class manages the current progress, and the format of the line
is given by a number of widgets. A widget is an object that may display
differently depending on the state of the progress bar. There are many types
of widgets:

 - `AbsoluteETA <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#AbsoluteETA>`_
 - `AdaptiveETA <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#AdaptiveETA>`_
 - `AdaptiveTransferSpeed <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#AdaptiveTransferSpeed>`_
 - `AnimatedMarker <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#AnimatedMarker>`_
 - `Bar <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#Bar>`_
 - `BouncingBar <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#BouncingBar>`_
 - `Counter <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#Counter>`_
 - `CurrentTime <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#CurrentTime>`_
 - `DataSize <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#DataSize>`_
 - `DynamicMessage <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#DynamicMessage>`_
 - `ETA <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#ETA>`_
 - `FileTransferSpeed <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#FileTransferSpeed>`_
 - `FormatCustomText <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#FormatCustomText>`_
 - `FormatLabel <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#FormatLabel>`_
 - `Percentage <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#Percentage>`_
 - `ReverseBar <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#ReverseBar>`_
 - `RotatingMarker <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#RotatingMarker>`_
 - `SimpleProgress <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#SimpleProgress>`_
 - `Timer <http://progressbar-2.readthedocs.io/en/latest/_modules/progressbar/widgets.html#Timer>`_

The progressbar module is very easy to use, yet very powerful. It will also
automatically enable features like auto-resizing when the system supports it.

******************************************************************************
Known issues
******************************************************************************

Due to limitations in both the IDLE shell and the Jetbrains (Pycharm) shells this progressbar cannot function properly within those.

- The IDLE editor doesn't support these types of progress bars at all: https://bugs.python.org/issue23220
- The Jetbrains (Pycharm) editors partially work but break with fast output. As a workaround make sure you only write to either `sys.stdout` (regular print) or `sys.stderr` at the same time. If you do plan to use both, make sure you wait about ~200 milliseconds for the next output or it will break regularly. Linked issue: https://github.com/WoLpH/python-progressbar/issues/115

******************************************************************************
Links
******************************************************************************

* Documentation
    - https://progressbar-2.readthedocs.org/en/latest/
* Source
    - https://github.com/WoLpH/python-progressbar
* Bug reports 
    - https://github.com/WoLpH/python-progressbar/issues
* Package homepage
    - https://pypi.python.org/pypi/progressbar2
* My blog
    - https://w.wol.ph/

******************************************************************************
Usage
******************************************************************************

There are many ways to use Python Progressbar, you can see a few basic examples
here but there are many more in the examples file.

Wrapping an iterable
==============================================================================
.. code:: python

    import time
    import progressbar
 
    for i in progressbar.progressbar(range(100)):
        time.sleep(0.02)

Progressbars with logging
==============================================================================

Progressbars with logging require `stderr` redirection _before_ the
`StreamHandler` is initialized. To make sure the `stderr` stream has been
redirected on time make sure to call `progressbar.streams.wrap_stderr()` before
you initialize the `logger`.

One option to force early initialization is by using the `WRAP_STDERR`
environment variable, on Linux/Unix systems this can be done through:

.. code:: sh
   
    # WRAP_STDERR=true python your_script.py

If you need to flush manually while wrapping, you can do so using:

.. code:: python

    import progressbar

    progressbar.streams.flush()

In most cases the following will work as well, as long as you initialize the
`StreamHandler` after the wrapping has taken place.

.. code:: python

    import time
    import logging
    import progressbar

    progressbar.streams.wrap_stderr()
    logging.basicConfig()

    for i in progressbar.ProgressBar(range(10)):
        logging.error('Got %d', i)
        time.sleep(0.2)

Context wrapper
==============================================================================
.. code:: python

   import time
   import progressbar

   with progressbar.ProgressBar(max_value=10) as bar:
       for i in range(10):
           time.sleep(0.1)
           bar.update(i)

Combining progressbars with print output
==============================================================================
.. code:: python

    import time
    import progressbar

    for i in progressbar.ProgressBar(range(100), redirect_stdout=True):
        print('Some text', i)
        time.sleep(0.1)

Progressbar with unknown length
==============================================================================
.. code:: python

    import time
    import progressbar

    bar = progressbar.ProgressBar(max_value=progressbar.UnknownLength)
    for i in range(20):
        time.sleep(0.1)
        bar.update(i)

Bar with custom widgets
==============================================================================
.. code:: python

    import time
    import progressbar

    widgets=[
        ' [', progressbar.Timer(), '] ',
        progressbar.Bar(),
        ' (', progressbar.ETA(), ') ',
    ]
    for i in progressbar.ProgressBar(range(20), widgets=widgets):
        time.sleep(0.1)

Bar with wide Chinese (or other multibyte) characters
==============================================================================

.. code:: python

    # vim: fileencoding=utf-8
    import time
    import progressbar


    def custom_len(value):
        # These characters take up more space
        characters = {
            '进': 2,
            '度': 2,
        }

        total = 0
        for c in value:
            total += characters.get(c, 1)

        return total


    bar = progressbar.ProgressBar(
        widgets=[
            '进度: ',
            progressbar.Bar(),
            ' ',
            progressbar.Counter(format='%(value)02d/%(max_value)d'),
        ],
        len_func=custom_len,
    )
    for i in bar(range(10)):
        time.sleep(0.1)
