=====
Timer
=====

``Timer`` displays the elapsed time since the bar started.

Reach for it whenever "how long has this taken so far" matters more
than an estimate of what remains -- unlike the ``ETA`` family, it needs
no ``max_value`` and works just as well for indeterminate work. Compare
``CurrentTime`` for the wall-clock time of day instead of a duration.

This example runs longer than most in this set: elapsed time is only shown
to whole-second resolution, so a bar that finishes in a few milliseconds
would read "Elapsed Time: 0:00:00" for its entire run -- the one thing this
widget exists to show would never move.

.. autoclass:: progressbar.widgets.Timer
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/timer

See also
--------------------------------------------------------------------------------

* :doc:`eta` — a remaining-time estimate, which does need a known max_value.
* :doc:`current-time` — the time of day instead of a duration.
