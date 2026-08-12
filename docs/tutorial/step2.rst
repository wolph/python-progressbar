=======================================
Step 2: Update a ProgressBar explicitly
=======================================

Not every loop hands you a clean iterable to wrap -- sometimes you need to
decide for yourself when and where progress has moved on. This step drops
the wrapper from the previous step and drives a ``ProgressBar`` by hand.

.. demo:: tutorial/step2

The previous step gave ``range(100)`` to ``progressbar.progressbar()`` and
let it manage everything. Here, the loop opens the bar as a context
manager with ``with progressbar.ProgressBar() as bar:`` and, on each pass
through its own ``for`` loop, calls ``bar.update(i + 1)`` to report the
new value itself. The ``with`` block starts the bar on entry and finishes
it on exit, just as ``progressbar.progressbar()`` did implicitly in step
1. The difference is that *this* code decides when ``update()`` is called,
so it works just as well when progress doesn't come from iterating a
sequence at all.

Next: :doc:`step3`.
