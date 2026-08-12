==========
Percentage
==========

``Percentage`` displays the current progress as ``N%``.

Reach for it as the simplest possible progress readout -- just the
percentage, with no bar. Compare ``SimpleProgress`` ("5 of 47") when
the raw counts matter more than the ratio, and ``PercentageLabelBar``
to overlay the same percentage on a fill bar instead of beside it.

.. autoclass:: progressbar.widgets.Percentage
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/percentage

See also
--------------------------------------------------------------------------------

* :doc:`simple-progress` — the raw counts when the ratio alone is not enough.
* :doc:`percentage-label-bar` — the same percentage overlaid on a fill bar instead of beside it.
