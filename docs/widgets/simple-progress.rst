==============
SimpleProgress
==============

``SimpleProgress`` shows progress as a raw count, like "5 of 47".

Reach for it when the counts themselves are useful information, not
just their ratio -- compare ``Percentage`` for the ratio alone, and
``UnitProgress`` for the same count with a unit label attached.

.. autoclass:: progressbar.widgets.SimpleProgress
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/simple-progress

See also
--------------------------------------------------------------------------------

* :doc:`percentage` — the ratio alone, when the raw counts do not matter.
* :doc:`unit-progress` — the same count with a unit label attached.
* :doc:`counter` — the same count with no total to compare against.
