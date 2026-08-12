=====================
AdaptiveTransferSpeed
=====================

``AdaptiveTransferSpeed`` averages transfer speed over a short window.

Reach for it when the transfer rate fluctuates and ``FileTransferSpeed``,
which averages over the whole run, reacts too slowly to the swings. The
windowed average only fills in once several updates have landed more
than a fraction of a second apart. Until then it renders "0.0 B/s".

.. autoclass:: progressbar.widgets.AdaptiveTransferSpeed
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/adaptive-transfer-speed

See also
--------------------------------------------------------------------------------

* :doc:`file-transfer-speed`: the whole-run average this reacts faster than.
