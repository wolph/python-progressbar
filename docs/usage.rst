========
Usage
========

There are many ways to use Python Progressbar, you can see a few basic examples
here but there are many more in the :doc:`examples` file.

Wrapping an iterable
------------------------------------------------------------------------------
::

   import time
   import progressbar

   bar = progressbar.ProgressBar()
   for i in bar(range(100)):
       time.sleep(0.02)

Context wrapper
------------------------------------------------------------------------------
::

   import time
   import progressbar

   with progressbar.ProgressBar(max_value=10) as bar:
       for i in range(10):
           time.sleep(0.1)
           bar.update(i)

Combining progressbars with print output
------------------------------------------------------------------------------
::

    import time
    import progressbar

    bar = progressbar.ProgressBar(redirect_stdout=True)
    for i in range(100):
        print 'Some text', i
        time.sleep(0.1)
        bar.update(i)

Progressbar with unknown length
------------------------------------------------------------------------------
::

    import time
    import progressbar

    bar = progressbar.ProgressBar(max_value=progressbar.UnknownLength)
    for i in range(20):
        time.sleep(0.1)
        bar.update(i)

Bar with custom widgets
------------------------------------------------------------------------------
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

