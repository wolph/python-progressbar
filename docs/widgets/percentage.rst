==========
Percentage
==========

``Percentage`` displays the current progress as ``N%``.

Reach for it as the simplest possible progress readout: just the
percentage, with no bar. When ``max_value`` is unknown it renders the
``na`` text instead (default ``N/A%``).

.. autoclass:: progressbar.widgets.Percentage
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/percentage

See also
--------------------------------------------------------------------------------

* :doc:`simple-progress`: the raw counts when the ratio alone is not enough.
* :doc:`percentage-label-bar`: the same percentage overlaid on a fill bar.
