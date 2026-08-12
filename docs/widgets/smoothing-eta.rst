============
SmoothingETA
============

``SmoothingETA`` estimates remaining time via a recency-weighted rate.

Reach for it when per-item timing is noisy but you still want a stable
estimate without the fixed sample window ``AdaptiveETA`` uses. The
exponential moving average weights recent updates more than old ones
without discarding history outright, and ``smoothing_algorithm`` with
``smoothing_parameters`` picks the algorithm. In the demo, each step's
timing carries random jitter, yet the countdown moves smoothly.

.. autoclass:: progressbar.widgets.SmoothingETA
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/smoothing-eta

See also
--------------------------------------------------------------------------------

* :doc:`adaptive-eta`: a fixed sample window instead of an exponential
  average.
* :doc:`eta`: the plain whole-run-average estimate this smooths.
* :doc:`absolute-eta`: a clock time instead of a countdown.
