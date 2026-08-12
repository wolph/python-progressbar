============
SmoothingETA
============

``SmoothingETA`` estimates remaining time via a recency-weighted rate.

Reach for it when per-item timing is noisy but you still want a stable
estimate without the fixed sample window ``AdaptiveETA`` uses -- the
exponential moving average weights recent updates more than old ones
without discarding history outright. This example adds seeded random
jitter to each step's timing over a longer run than most examples here,
since the smoothing only becomes visible across unevenly spaced
updates -- and since the ETA is only shown to whole-second resolution,
"longer" means several seconds, not merely more than a few milliseconds.

.. autoclass:: progressbar.widgets.SmoothingETA
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/smoothing-eta

See also
--------------------------------------------------------------------------------

* :doc:`adaptive-eta` — a fixed sample window instead of an exponential average.
* :doc:`eta` — the plain whole-run-average estimate this smooths.
* :doc:`absolute-eta` — a clock time instead of a countdown.
