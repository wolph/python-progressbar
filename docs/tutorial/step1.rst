========================================
Step 1: Wrap a loop with ``progressbar``
========================================

A loop that takes a while to run gives no feedback while it works. This
step wraps a plain ``for`` loop so it prints a live progress bar instead,
without changing anything else about the loop.

.. demo:: tutorial/step1

First, check the install. ``pip install progressbar2`` (see
:doc:`/installation`) puts a ``progressbar`` package on your path; confirm
it with:

.. code-block:: console

   $ python -c "import progressbar; print(progressbar.__version__)"

If that prints a version number instead of an ``ImportError``, you are
ready.

The example wraps ``range(100)`` in ``progressbar.progressbar(...)`` and
iterates the result exactly as it would iterate ``range(100)`` on its own.
``progressbar.progressbar()`` is a function, not the bar itself: it takes
an iterable, hands back an iterator over the same values, and starts,
updates and finishes a bar behind the scenes as that iterator is consumed.
There is no separate call to make the bar advance or to mark it done.

That convenience comes from hiding the bar object entirely. The library
also exposes that object directly as the ``ProgressBar`` class, which you
construct yourself and update by calling a method whenever you decide
progress has changed. ``progressbar.progressbar()`` is built on top of
``ProgressBar`` for the common case of running a loop over an iterable and
showing a bar for it; when progress does not come from iterating something,
you reach for ``ProgressBar`` directly, which the next step shows.

Next: :doc:`step2`.
