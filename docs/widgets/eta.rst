===
ETA
===

``ETA`` estimates time remaining from the average rate since start.

It divides the elapsed time by the work done so far and extrapolates --
the plain, whole-run average. That average reacts slowly to a rate that
changes mid-run -- see ``AdaptiveETA`` (recent window) and
``SmoothingETA`` (exponential average) for estimates that track recent
speed instead, and ``AbsoluteETA`` for a clock time instead of a
countdown. Note that ``ProgressBar``'s own default widget set uses
``SmoothingETA``, not this widget.

This example runs longer than most in this set: the ETA is only shown to
whole-second resolution, so a bar that finishes in a few milliseconds would
show a countdown stuck at ``0:00:00`` -- the estimate this widget exists to
compute would never visibly move.

.. autoclass:: progressbar.widgets.ETA
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/eta

See also
--------------------------------------------------------------------------------

* :doc:`adaptive-eta` — a recent-window estimate that reacts to pace changes.
* :doc:`smoothing-eta` — an exponential-moving-average estimate; the library default.
* :doc:`absolute-eta` — a clock time instead of a countdown.
* :doc:`timer` — the elapsed-time widget this estimates against, no max_value required.
