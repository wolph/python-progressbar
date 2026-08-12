=============
MultiRangeBar
=============

``MultiRangeBar`` shows several named ranges as segments of one bar.

Reach for it to visualize a whole made of distinct categories -- done,
processing, scheduled, not started -- as proportional segments of a
single bar, rather than a single fill fraction. Compare
``MultiProgressBar``, which shows independent per-job progress instead
of categories of one whole. Its loop runs until every unit reaches the
"done" range rather than a fixed ``STEPS`` count, since that is what the
widget is for.

.. autoclass:: progressbar.widgets.MultiRangeBar
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/multi-range-bar

See also
--------------------------------------------------------------------------------

* :doc:`multi-progress-bar` — independent per-job progress instead of categories of one whole.
* :doc:`job-status-bar` — per-job success/failure markers instead of proportional segments.
