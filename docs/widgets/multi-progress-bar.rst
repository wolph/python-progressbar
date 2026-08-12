================
MultiProgressBar
================

``MultiProgressBar`` renders many sub-jobs as stacked fill levels.

Reach for it to show the aggregate state of several jobs, each with its
own progress toward its own total, as one bar rather than one bar per
job. The bar variable named by ``name`` holds one progress fraction per
job, and ``markers`` sets the ascending-height histogram characters.

.. autoclass:: progressbar.widgets.MultiProgressBar
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/multi-progress-bar

See also
--------------------------------------------------------------------------------

* :doc:`multi-range-bar`: categories of one whole instead of independent
  per-job progress.
