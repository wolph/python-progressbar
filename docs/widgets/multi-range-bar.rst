=============
MultiRangeBar
=============

``MultiRangeBar`` shows several named ranges as segments of one bar.

Reach for it to visualize a whole made of distinct categories (done,
processing, scheduled, not started) as proportional segments of a
single bar, rather than a single fill fraction. ``markers`` gives one
character per category, and the segment sizes come from the bar
variable named by ``name``. In the demo, units migrate between
segments until every one is "done".

.. autoclass:: progressbar.widgets.MultiRangeBar
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/multi-range-bar

See also
--------------------------------------------------------------------------------

* :doc:`multi-progress-bar`: independent per-job progress instead of
  categories of one whole.
* :doc:`job-status-bar`: per-job success/failure markers instead of
  proportional segments.
