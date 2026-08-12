=====================
AdaptiveTransferSpeed
=====================

``AdaptiveTransferSpeed`` averages transfer speed over a short window.

Reach for it when the transfer rate itself fluctuates and a plain
``FileTransferSpeed`` -- which averages over the whole run -- reacts too
slowly to those swings. The windowed average only fills in once several
updates have landed more than a fraction of a second apart, so this
example runs longer and sleeps longer per step than most in this set;
without that, it would render '0.0 B/s' the whole way through.

.. autoclass:: progressbar.widgets.AdaptiveTransferSpeed
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/adaptive-transfer-speed

See also
--------------------------------------------------------------------------------

* :doc:`file-transfer-speed` — the whole-run average this reacts faster than.
