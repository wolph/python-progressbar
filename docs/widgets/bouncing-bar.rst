===========
BouncingBar
===========

``BouncingBar`` slides a marker back and forth instead of filling.

Reach for it for indeterminate work: with no total to measure progress
against, it shows a marker bouncing across the full width to signal
that the process is still running. The marker moves on a wall-clock
timer, not per ``update()`` call, and the characters come from the same
``marker``/``left``/``right``/``fill`` arguments as ``Bar``.

.. autoclass:: progressbar.widgets.BouncingBar
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/bouncing-bar

See also
--------------------------------------------------------------------------------

* :doc:`animated-marker`: a single-character spinner, also indeterminate.
* :doc:`bar`: the determinate fill bar this stands in for.
