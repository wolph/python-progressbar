===========
CurrentTime
===========

``CurrentTime`` displays the current date and time, updated live.

Reach for it to stamp log-like output with a wall clock, independent of
the bar's own progress. Unlike ``Timer``, which reports time elapsed
*since the bar started*, it shows the actual time of day, updated each
redraw at whole-second resolution.

.. autoclass:: progressbar.widgets.CurrentTime
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/current-time

See also
--------------------------------------------------------------------------------

* :doc:`timer`: elapsed time since the bar started, instead of the time
  of day.
