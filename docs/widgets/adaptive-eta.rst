===========
AdaptiveETA
===========

``AdaptiveETA`` estimates time remaining from the last few seconds.

Reach for it when the processing rate can change mid-run (resuming a
paused job, or one that starts slow and speeds up) so the estimate
should track the *current* pace rather than the whole-run average that
plain ``ETA`` uses. The window size comes from ``SamplesMixin``'s
``samples`` argument: an update count or a time span. In the demo, the
run starts slow and speeds up partway through, and the countdown
visibly drops as the estimate catches on.

.. autoclass:: progressbar.widgets.AdaptiveETA
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/adaptive-eta

See also
--------------------------------------------------------------------------------

* :doc:`eta`: the plain whole-run-average estimate this reacts faster than.
* :doc:`smoothing-eta`: an exponential moving average instead of a fixed
  sample window.
* :doc:`absolute-eta`: a clock time instead of a countdown.
