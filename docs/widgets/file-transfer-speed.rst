=================
FileTransferSpeed
=================

``FileTransferSpeed`` shows the transfer rate averaged over the run.

Reach for it whenever a bar tracks bytes moved rather than abstract
units -- a transfer rate, in a sensibly scaled unit, alongside the
count. For a rate that reacts to recent speed changes instead of the
whole-run average, see ``AdaptiveTransferSpeed``.

.. autoclass:: progressbar.widgets.FileTransferSpeed
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/file-transfer-speed

See also
--------------------------------------------------------------------------------

* :doc:`data-size` — a static scaled amount instead of a rate.
* :doc:`adaptive-transfer-speed` — the same rate averaged over a short recent window instead.
