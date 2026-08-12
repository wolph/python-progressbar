========
DataSize
========

``DataSize`` shows a single byte count scaled with binary prefixes.

Reach for it to show an amount of data transferred or processed so far
-- "12.5 MiB" instead of a raw byte count -- as one value scaled to a
sensible unit. Compare ``FileTransferSpeed``, which shows a *rate*
instead of a static amount.

.. autoclass:: progressbar.widgets.DataSize
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/data-size

See also
--------------------------------------------------------------------------------

* :doc:`file-transfer-speed` — the same scaling applied to a rate instead of a static amount.
* :doc:`unit-progress` — a count against a total instead of a single scaled amount.
