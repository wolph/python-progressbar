==================================================
Wrap an iterable without managing the bar yourself
==================================================

Most loops don't need explicit ``start()``/``update()``/``finish()``
calls -- they just need the bar to track a ``for`` loop over something
with a known length.

.. demo:: howto/iterable-wrapper

``progressbar.progressbar(iterable)`` wraps any iterable and returns an
iterator that updates a fresh bar on every step, sized from
``len(iterable)`` when available. If you already built a ``ProgressBar``
instance for its own widgets, prefix, or other configuration, call it
directly as ``bar(iterable)`` instead of building a second bar just to
iterate -- it wraps the same way, reusing the instance you already
configured.
