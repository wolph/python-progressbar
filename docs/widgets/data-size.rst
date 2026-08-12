========
DataSize
========

``DataSize`` shows a single byte count scaled with binary prefixes.

Reach for it to show an amount of data transferred or processed so far:
"12.5 MiB" instead of a raw byte count. ``variable`` picks which bar
value it renders, and ``unit``/``prefixes`` control the scaling labels.

.. autoclass:: progressbar.widgets.DataSize
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/data-size

See also
--------------------------------------------------------------------------------

* :doc:`file-transfer-speed`: the same scaling applied to a rate.
* :doc:`unit-progress`: a count against a total instead of one amount.
