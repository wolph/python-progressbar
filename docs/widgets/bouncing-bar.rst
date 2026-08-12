===========
BouncingBar
===========

``BouncingBar`` slides a marker back and forth instead of filling.

Reach for it for indeterminate work -- there is no total to measure
progress against, so instead of a percentage it shows a bouncing marker
to signal that the process is still running, similar in spirit to
``AnimatedMarker`` but shaped like a full-width bar. The marker moves on
a wall-clock timer, not per ``update()`` call, so this example runs
longer than most in this set -- otherwise it barely twitches before the
run ends.

.. autoclass:: progressbar.widgets.BouncingBar
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/bouncing-bar

See also
--------------------------------------------------------------------------------

* :doc:`animated-marker` — a narrower spinner in the same indeterminate spirit.
* :doc:`bar` — the determinate fill bar this stands in for when no total is known.
