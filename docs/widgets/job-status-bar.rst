============
JobStatusBar
============

``JobStatusBar`` marks each job as succeeded or failed on the bar.

Reach for it when a bar tracks discrete jobs rather than continuous
progress: each ``update()`` records one job's outcome as a colored
marker, and jobs not yet reported stay blank rather than showing a
fill. ``success_marker``/``failure_marker`` and their ``*_fg_color``
counterparts control the rendering per outcome.

.. autoclass:: progressbar.widgets.JobStatusBar
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/job-status-bar

See also
--------------------------------------------------------------------------------

* :doc:`bar`: the plain fill bar this repurposes for discrete outcomes.
* :doc:`multi-range-bar`: proportional category segments instead of
  per-job markers.
