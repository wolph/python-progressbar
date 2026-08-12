================
MultiProgressBar
================

``MultiProgressBar`` renders many sub-jobs as stacked fill levels.

Reach for it to show the aggregate state of several jobs -- each with
its own progress toward its own total -- as one bar, rather than one
bar per job. Compare ``MultiRangeBar`` when the sub-ranges are simple
categories instead of independent job progress. Its loop runs until
every job finishes rather than a fixed ``STEPS`` count, since that is
what the widget is for.

.. autoclass:: progressbar.widgets.MultiProgressBar
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/multi-progress-bar

See also
--------------------------------------------------------------------------------

* :doc:`multi-range-bar` — categories of one whole instead of independent per-job progress.
