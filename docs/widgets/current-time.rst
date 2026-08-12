===========
CurrentTime
===========

``CurrentTime`` displays the current date and time, updated live.

Reach for it to stamp log-like output with a wall clock, independent of
the bar's own progress -- unlike ``Timer``, which reports time elapsed
*since the bar started* rather than the actual time of day.

This example runs longer than most in this set: the clock is only shown
to whole-second resolution, so a bar that finishes in a fraction of a
second would show the same, unmoving reading for its entire run --
"updated live" would never actually be visible.

.. autoclass:: progressbar.widgets.CurrentTime
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/current-time

See also
--------------------------------------------------------------------------------

* :doc:`timer` — elapsed time since the bar started, instead of the time of day.
