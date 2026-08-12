========
MultiBar
========

``MultiBar`` is a ``dict[str, ProgressBar]`` that renders every bar it holds
from a background thread, so several bars can progress independently in the
same terminal without their redraws stepping on each other.

.. autoclass:: progressbar.multi.MultiBar
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :no-index:

Constructor arguments worth knowing
====================================

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Argument
     - What it does
   * - ``bars``
     - Seed the multibar with existing ``{label: ProgressBar}`` pairs (a
       mapping or an iterable of ``(label, bar)`` tuples). Usually left
       unset -- ``multibar['label']`` creates a bar on first access instead.
   * - ``fd``
     - The stream all child bars render to. Defaults to ``sys.stderr``,
       same reasoning as :py:class:`~progressbar.bar.ProgressBar`'s ``fd``.
   * - ``prepend_label``, ``append_label``, ``label_format``
     - Control whether each bar gets its dict key stitched onto the front
       and/or back of its rendered line, and the format string used to do
       it (default ``'{label:20.20} '``, prepended only).
   * - ``initial_format``
     - What a bar shows before it has been started. Defaults to
       ``'{label:20.20} Not yet started'``. Pass ``None`` to start the bar
       immediately instead of showing a placeholder.
   * - ``finished_format``
     - What a finished bar shows once it's done. Defaults to ``None``,
       which keeps rendering the bar's own widgets (so a finished bar still
       shows 100% and its final timer/rate) instead of switching to a fixed
       string.
   * - ``update_interval``
     - How often (seconds) the render thread redraws the whole multibar,
       independent of any individual bar's own ``poll_interval``. Defaults
       to ``1/60`` (60fps).
   * - ``show_initial``, ``show_finished``
     - Whether not-yet-started and finished bars are rendered at all, or
       skipped.
   * - ``remove_finished``
     - Seconds (or a ``timedelta``) after which a finished bar is dropped
       from the multibar entirely and stops being rendered. Defaults to one
       hour; pass ``None`` to keep finished bars forever.
   * - ``sort_key``, ``sort_reverse``, ``sort_keyfunc``
     - How child bars are ordered on screen. ``sort_key`` takes a
       :py:class:`~progressbar.multi.SortKey` (or the matching attribute
       name as a string); ``sort_keyfunc`` overrides the sort entirely with
       a custom callable when a single attribute isn't enough.
   * - ``join_timeout``
     - Seconds to wait for unfinished bars on a clean ``with`` block exit
       before giving up and abandoning them. ``None`` (the default) waits
       forever, matching the historical behaviour; a never-finished bar
       under the default will hang the program on exit.
   * - ``**progressbar_kwargs``
     - Any keyword not listed above is forwarded to
       :py:class:`~progressbar.bar.ProgressBar`'s constructor for every bar
       the multibar creates on first access (see :doc:`progressbar`).

Since ``MultiBar`` renders from a background thread, per-bar ``update()``
calls are cheap: they just record the new value, and the render thread
picks it up on its next tick rather than redrawing synchronously.

For the automodule listing (including module-level helpers not tied to the
class), see :doc:`../progressbar.multi`.
