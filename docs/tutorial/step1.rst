========================================
Step 1: Wrap a loop with ``progressbar``
========================================

A loop that takes a while to run gives no feedback while it works. This
step wraps a plain ``for`` loop so it prints a live progress bar instead,
without changing anything else about the loop.

.. demo:: tutorial/step1

Install the library first if you have not yet (:doc:`/installation`).

The example wraps ``range(100)`` in ``progressbar.progressbar(...)`` and
iterates the result exactly as it would iterate ``range(100)`` on its own.
``progressbar.progressbar()`` is a function, not the bar itself: it takes
an iterable, hands back an iterator over the same values, and starts,
updates and finishes a bar behind the scenes as that iterator is consumed.
There is no separate call to make the bar advance or to mark it done.

That convenience comes from hiding the bar object entirely. The library
also exposes it directly as the ``ProgressBar`` class, which you construct
and update yourself when progress does not come from iterating something.
The next step shows how.

Next: :doc:`step2`.
