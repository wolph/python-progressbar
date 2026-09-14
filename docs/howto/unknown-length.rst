========================================
Show progress when the total isn't known
========================================

A percentage and an ETA both need a total to measure against -- neither
means anything for a job whose length you can't compute in advance,
such as scanning a filesystem or reading a stream.

.. demo:: howto/unknown-length

Pass ``max_value=progressbar.UnknownLength`` and include an
``AnimatedMarker`` (or another marker-style widget) so there is still
something visibly moving even without a percentage to report. A
``Counter()`` widget still works normally here, since it just echoes
``value`` rather than computing a fraction of ``max_value``.
