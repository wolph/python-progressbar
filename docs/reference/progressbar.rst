===========
ProgressBar
===========

``ProgressBar`` is the class behind ``progressbar.progressbar()`` and every
bar you construct directly. It combines several mixins (stream redirection,
terminal resizing, color/terminal detection) but they are all reachable
through this one class and its constructor.

.. autoclass:: progressbar.bar.ProgressBar
   :members:
   :undoc-members:
   :show-inheritance:
   :member-order: bysource
   :no-index:

Constructor arguments worth knowing
====================================

The table below covers the constructor arguments most scripts actually
set.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Argument
     - What it does
   * - ``max_value``, ``min_value``
     - The value range. Leave ``max_value`` unset (or pass
       ``progressbar.UnknownLength``) for a spinner-style bar when the total
       is not known up front. ``total`` is a tqdm-style alias for
       ``max_value``.
   * - ``widgets``
     - Overrides the default widget list entirely. Leave unset to get
       :py:meth:`~progressbar.bar.ProgressBar.default_widgets`, which differs
       depending on whether ``max_value`` is known.
   * - ``prefix``, ``suffix``
     - Plain strings stitched onto the rendered line. ``desc`` is a
       tqdm-style alias that sets ``prefix`` to ``f'{desc}: '``.
   * - ``unit``, ``unit_scale``, ``postfix``
     - tqdm-style extras: ``unit`` labels counted items, ``unit_scale``
       scales the count with IEC binary prefixes (KiB/MiB, base 1024), and
       ``postfix`` seeds a trailing key-value widget. Any of the three routes
       through the full widget machinery even when the fast-path dispatch
       in :py:func:`progressbar.progressbar` would otherwise apply -- see
       :doc:`../explanation/performance-and-the-fast-path`.
   * - ``fd``
     - The stream to draw on. Defaults to ``sys.stderr`` so a piped
       ``stdout`` is never corrupted by the bar itself.
   * - ``redirect_stdout``, ``redirect_stderr``
     - Capture the named stream and print it above the bar instead of
       letting it interleave with (and corrupt) the redraw.
   * - ``line_breaks``
     - ``True`` prints a new line per update (log-friendly), ``False``
       overwrites the current line with ``\r``. Defaults to the opposite of
       terminal detection (see :doc:`../explanation/terminal-detection`).
   * - ``enable_colors``, ``is_terminal``
     - Override color and terminal auto-detection explicitly instead of
       relying on the environment. See
       :doc:`../explanation/terminal-detection` for exactly how the
       automatic values are derived.
   * - ``poll_interval``, ``min_poll_interval``
     - Tune how often the bar is allowed (``min_poll_interval``) or forced
       (``poll_interval``) to redraw. See
       :doc:`../explanation/rendering-and-the-update-gate`.
   * - ``max_error``
     - When ``True`` (the default), calling ``update()`` past ``max_value``
       raises ``ValueError``. Set to ``False`` to clamp instead -- the
       ``progressbar`` console script does this since a piped size estimate
       can be wrong (see :doc:`cli`).
   * - ``term_width``
     - Pin the rendered width instead of auto-detecting it. See
       :doc:`../explanation/terminal-detection` for how auto-detection
       works and what ``COLUMNS`` does.
   * - ``left_justify``
     - Justify the rendered line left (``True``, the default) or right
       (``False``) within ``term_width``.
   * - ``variables``
     - Seeds the dictionary backing :py:class:`~progressbar.widgets.Variable`
       widgets, so a formatted label can start with a value before the
       first ``update(my_var=...)`` call.

Related classes
================

``DataTransferBar`` and ``NullBar`` are small ``ProgressBar`` subclasses
that only override ``default_widgets()`` (or, for ``NullBar``, turn every
lifecycle method into a no-op). Every constructor argument above still
applies.

.. autoclass:: progressbar.bar.DataTransferBar
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:

.. autoclass:: progressbar.bar.NullBar
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:

``FastProgressBar`` is also a ``ProgressBar`` subclass, accepting the same
constructor arguments, but it replaces the widget system with a single fixed
formatter. It is what ``progressbar.progressbar()`` constructs automatically
for the common case. :doc:`../explanation/performance-and-the-fast-path`
covers when that happens and why.

.. autoclass:: progressbar.fast.FastProgressBar
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:

For the full generated listing of every class, function and module in the
package -- including ones not covered on this page -- see
:doc:`../progressbar`.
