==============
AnimatedMarker
==============

``AnimatedMarker`` cycles through characters to show a spinner.

Reach for it for indeterminate work where there is nothing to measure a
percentage against -- just a signal that the process is still alive.
Unlike ``Bar``, it does not grow or fill; it only replaces one character
each redraw.

.. autoclass:: progressbar.widgets.AnimatedMarker
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/animated-marker

See also
--------------------------------------------------------------------------------

* :doc:`bar` — a fill bar, for when a total is known.
* :doc:`bouncing-bar` — a full-width bouncing marker in the same indeterminate spirit.
* :doc:`rotating-marker` — the legacy name for this same widget.
