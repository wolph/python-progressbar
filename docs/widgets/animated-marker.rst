==============
AnimatedMarker
==============

``AnimatedMarker`` cycles through characters and colours to show a spinner.

Reach for it for indeterminate work where there is nothing to measure a
percentage against, just a signal that the process is still alive.
Unlike ``Bar``, it does not grow or fill: it replaces one character each
redraw. ``markers`` sets the cycle of characters (default ``|/-\``).

.. autoclass:: progressbar.widgets.AnimatedMarker
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/animated-marker

The default spinner changes both its character and colour on redraws.
No colour configuration is needed.

See also
--------------------------------------------------------------------------------

* :doc:`bar`: a fill bar, for when a total is known.
* :doc:`bouncing-bar`: a full-width bouncing marker, also indeterminate.
* :doc:`rotating-marker`: the legacy name for this same widget.
