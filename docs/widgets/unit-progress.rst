============
UnitProgress
============

``UnitProgress`` shows a count against its total with a unit label.

Reach for it when the count needs a unit: "12 of 24 files". ``unit``
sets the label and ``unit_scale`` enables 1024-based scaling for large
counts.

.. autoclass:: progressbar.widgets.UnitProgress
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/unit-progress

See also
--------------------------------------------------------------------------------

* :doc:`simple-progress`: the same idea without a unit label.
* :doc:`data-size`: a single scaled byte value, no total.
* :doc:`counter`: the same count with no total to compare against.
