=================
FileTransferSpeed
=================

``FileTransferSpeed`` shows the transfer rate averaged over the run.

Reach for it whenever a bar tracks bytes moved rather than abstract
units: a transfer rate, in a sensibly scaled unit, alongside the count.
For very slow transfers it flips to ``inverse_format`` and renders
seconds per unit instead.

.. autoclass:: progressbar.widgets.FileTransferSpeed
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/file-transfer-speed

See also
--------------------------------------------------------------------------------

* :doc:`data-size`: a static scaled amount instead of a rate.
* :doc:`adaptive-transfer-speed`: the same rate over a short recent window.
