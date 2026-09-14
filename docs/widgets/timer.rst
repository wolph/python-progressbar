=====
Timer
=====

``Timer`` displays the elapsed time since the bar started.

Reach for it whenever "how long has this taken so far" matters more
than an estimate of what remains. Unlike the ``ETA`` family, it needs
no ``max_value`` and works just as well for indeterminate work.
``format`` controls the text (default ``Elapsed Time: %(elapsed)s``)
and the readout has whole-second resolution.

.. autoclass:: progressbar.widgets.Timer
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/timer

See also
--------------------------------------------------------------------------------

* :doc:`eta`: a remaining-time estimate, which does need a known max_value.
* :doc:`current-time`: the time of day instead of a duration.
