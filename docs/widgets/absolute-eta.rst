===========
AbsoluteETA
===========

``AbsoluteETA`` shows the wall-clock time the run is expected to finish.

Reach for it when the audience cares about *when* the job will finish
("done around 14:32:07") rather than a countdown duration -- every other
ETA widget in this reference reports a remaining-time span instead. This
example runs longer than most in this set: the estimate is only shown to
whole-second resolution, so a bar that finishes in a fraction of a second
never accumulates enough elapsed time for the projected finish time to
visibly move.

.. autoclass:: progressbar.widgets.AbsoluteETA
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/absolute-eta

See also
--------------------------------------------------------------------------------

* :doc:`eta` — the whole-run-average countdown this specializes into a clock time.
* :doc:`adaptive-eta` — a countdown that reacts to recent pace instead.
* :doc:`smoothing-eta` — a countdown smoothed with an exponential moving average.
