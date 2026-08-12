=================================
Rendering and the update gate
=================================

``bar.update(value)`` does not redraw the line every time you call it. If it
did, a tight loop over a million items would spend most of its time writing
to the terminal instead of doing the work the bar is measuring. Instead,
every ``ProgressBar`` (and everything built on it, including
``FastProgressBar``) sits behind two independent checks, described below,
that decide whether a given ``update()`` call actually produces output.
Both live in :py:mod:`progressbar.bar`.

The integer gate: deciding whether to even look
==================================================

The cheapest possible check is one integer comparison, and that is what runs
on every iteration of ``progressbar.progressbar(iterable)`` and every
explicit ``update()`` call. Internally, each bar tracks a threshold,
``_next_update``: while ``value`` is still below it, ``update()`` records the
new value and returns immediately, without touching ``_needs_update()`` or
any widget at all.

The threshold is not a fixed step. After each real redraw, it is recalibrated
from how much ``value`` changed and how much wall-clock time that took, aimed
at roughly one redraw per ``min_poll_interval`` window (see below). A loop
that turns out to run faster than expected -- the threshold was reached but
no redraw was actually due -- causes the step to double instead of shrink,
backing off further. The gate starts at a step of ``1`` (redraw every call)
so a slow loop, where real time passes between iterations, is never skipped
before a timing measurement has had a chance to grow it.

This is what "the integer gate keeps the common iteration to an increment +
compare + store" (the comment above
:py:meth:`~progressbar.bar.ProgressBar._iter_python` in the source) refers
to, and it is also why :doc:`the fast path <performance-and-the-fast-path>`
can claim single-digit-nanosecond overhead per iteration in the common case:
most iterations never reach the more expensive check described next.

``_needs_update()``: deciding whether to actually redraw
============================================================

Once the integer gate lets a call through, ``_needs_update()`` makes the
real decision, in this order:

1. If the bar is paused, never redraw.
2. If less than ``min_poll_interval`` seconds have passed since the last
   redraw, don't redraw -- this is the hard rate limit.
3. If ``poll_interval`` is set and more than that many seconds have passed,
   redraw unconditionally, even if the value hasn't changed. This exists for
   widgets that depend on elapsed time alone, such as a ``Timer`` or an
   animated marker, which need to keep moving even while ``value`` is
   static.
4. If ``max_value`` is unknown, redraw whenever ``value`` has changed at all
   (still subject to the rate limit above).
5. Otherwise, redraw only if the value crossed a threshold large enough to
   move the rendered bar by at least one terminal column, computed from
   ``max_value`` and the current ``term_width``. A bar with a huge
   ``max_value`` on a normal-width terminal redraws far less often, per unit
   of ``value``, than one where each unit is visually significant.

``force=True``
================

``update(value, force=True)`` bypasses both checks unconditionally: the
integer gate never skips a forced call, and ``_needs_update()``'s answer is
discarded rather than skipped -- it is the leftmost operand of
``if self._needs_update() or variables_changed or force:``, so it still runs,
but ``force`` makes the result irrelevant. Either way the line is redrawn
regardless of timing or value movement.
``start()`` and ``finish()`` both call ``update(..., force=True)``
internally, which is why a bar always shows 0% on start and 100% (or its
final state) on finish even if the gate would otherwise have skipped that
exact value. :doc:`MultiBar <../reference/multibar>` also renders its child
bars with ``force=True`` on every tick of its own render loop, since it
manages the redraw cadence itself.

``min_poll_interval`` vs. ``poll_interval``
================================================

These are opposites: one is a floor, the other is a ceiling.

* ``min_poll_interval`` is the *minimum* time between redraws -- a rate
  limit. It defaults to ``0.050`` seconds (20 redraws/second), and cannot go
  lower: the effective floor is the largest of the constructor argument, the
  hard-coded ``0.050`` minimum, and the ``PROGRESSBAR_MINIMUM_UPDATE_INTERVAL``
  environment variable. That environment variable can only raise the floor
  above whatever the code already requested, never lower it.
* ``poll_interval`` is the *maximum* time between redraws -- a forced
  refresh. It has no default (``None``, meaning "never force a redraw on
  time alone"); set it when your widgets show elapsed time or an animation
  and should keep visibly moving even while the tracked value sits still.

Both are seconds (or anything :py:func:`progressbar.utils.deltas_to_seconds`
accepts, such as a ``datetime.timedelta``), and both are documented as
constructor arguments on :doc:`ProgressBar <../reference/progressbar>`.

Why this matters for piped output
======================================

Because the rate limit applies regardless of how fast ``value`` changes,
redirecting a bar's output through ``tee`` or into a log file (see
:doc:`terminal-detection`) still produces a bounded number of lines rather
than one per unit of progress -- the gate throttles it the same way it
throttles a fast interactive redraw.
