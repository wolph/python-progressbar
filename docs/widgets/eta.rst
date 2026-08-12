===
ETA
===

``ETA`` estimates time remaining from the average rate since start.

It divides the elapsed time by the work done so far and extrapolates:
the plain, whole-run average, so it reacts slowly to a rate that
changes mid-run. ``ProgressBar``'s own default widget set uses
``SmoothingETA``, not this widget.

.. autoclass:: progressbar.widgets.ETA
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/eta

See also
--------------------------------------------------------------------------------

* :doc:`adaptive-eta`: a recent-window estimate that reacts to pace changes.
* :doc:`smoothing-eta`: an exponential-moving-average estimate, the
  library default.
* :doc:`absolute-eta`: a clock time instead of a countdown.
* :doc:`timer`: elapsed time only, no max_value required.
