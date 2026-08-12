=======
Counter
=======

``Counter`` displays the current value as a running count.

Reach for it when there is no meaningful total to show a percentage or
fraction against -- just the raw count so far. Compare ``SimpleProgress``
("5 of 47") when a total is known, and ``UnitProgress`` when the count
should carry a unit label.

.. autoclass:: progressbar.widgets.Counter
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/counter

See also
--------------------------------------------------------------------------------

* :doc:`simple-progress` — the same count shown against a known total.
* :doc:`unit-progress` — the same count with a unit label attached.
