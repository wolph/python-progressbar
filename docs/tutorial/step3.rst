====================================
Step 3: Give the bar a ``max_value``
====================================

Without knowing how much work there is, a ``ProgressBar`` has nothing to
divide the current value by, so it cannot show a percentage or estimate how
long is left. This step tells it the total up front so it can show both.

.. demo:: tutorial/step3

The previous step's ``ProgressBar()`` call took no arguments, so the bar
rendered as an indeterminate display -- there was no way to know how far
through the work it was. Here the constructor gains a ``max_value=100``
argument: ``progressbar.ProgressBar(max_value=100)``. Nothing else about
the loop changes -- ``bar.update(i + 1)`` is called exactly as before -- but
knowing the total lets the bar compute a percentage and an ETA from each
update instead of just showing that something is happening.

Next: :doc:`step4`.
