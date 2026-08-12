===========
AdaptiveETA
===========

``AdaptiveETA`` estimates time remaining from the last few seconds.

Reach for it when the processing rate can change mid-run -- resuming a
paused job, or one that starts slow and speeds up -- so the estimate
should track the *current* pace rather than the whole-run average that
plain ``ETA`` uses. This example runs slower at first and speeds up
partway through so the adaptive estimate visibly reacts; a uniform run
like most examples in this set would look identical to ``ETA``.

It also runs longer than most in this set: the ETA is only shown to
whole-second resolution, so too short a run shows only a tick or two rather
than a real countdown reacting to the pace change.

.. autoclass:: progressbar.widgets.AdaptiveETA
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/adaptive-eta

See also
--------------------------------------------------------------------------------

* :doc:`eta` — the plain whole-run-average estimate this reacts faster than.
* :doc:`smoothing-eta` — an exponential moving average instead of a fixed sample window.
* :doc:`absolute-eta` — a clock time instead of a countdown.
