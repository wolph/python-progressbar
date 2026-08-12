===========================
Backwards compatibility
===========================

progressbar2 began as a fork of the original ``progressbar`` package, once
hosted on the now-defunct Google Code and abandoned by its author. The
project has said ever since that it is "backwards compatible with the
original progressbar package so you can safely use it as a drop-in
replacement for existing projects" (see the project README). This page is
about what that claim covers today, verified against the current source,
and -- just as importantly -- what it does not cover.

What "drop-in" covers
==========================

* **The import name.** ``import progressbar`` still works; only the PyPI
  distribution name changed, to ``progressbar2``, because the original
  ``progressbar`` name on PyPI belonged to the abandoned package.
* **The core object lifecycle.** Construct a ``ProgressBar``, call
  ``.start()``, ``.update(value)``, ``.finish()``, or iterate over it
  directly -- the shape of that usage is unchanged from the original
  package.
* **Legacy keyword and attribute names**, translated internally rather than
  rejected, with a ``DeprecationWarning`` pointing at the replacement:

  .. list-table::
     :header-rows: 1
     :widths: 30 30 40

     * - Legacy name
       - Modern name
       - Where
     * - ``maxval=`` (constructor)
       - ``max_value=``
       - :py:meth:`ProgressBar.__init__ <progressbar.bar.ProgressBar.__init__>`
     * - ``poll=`` (constructor)
       - ``poll_interval=``
       - same
     * - ``.currval`` (property)
       - ``.value``
       - :py:attr:`ProgressBar.currval <progressbar.bar.ProgressBar.currval>`

* **A couple of renamed widgets, kept as plain aliases** with no warning at
  all (yet -- both are commented in the source as staying until the next
  major version): ``RotatingMarker`` is an alias for
  :py:class:`~progressbar.widgets.AnimatedMarker`, and ``DynamicMessage`` is
  kept as a subclass of :py:class:`~progressbar.widgets.Variable`.
* **Old-style format strings.** ``Timer`` and ``ETA`` (and anything built on
  them) silently rewrite a legacy bare ``%s`` placeholder in a custom
  ``format=`` string to the named form they actually use internally
  (``%(elapsed)s``/``%(eta)s``), so a format string written against the
  original package still works.
* **Unknown widget constructor kwargs are tolerated, not rejected.** The
  cooperative ``__init__`` chain that widgets go through ends in a sink that
  silently absorbs any keyword argument no widget class consumed, "since
  third-party widgets have passed stray kwargs to their parents for years"
  (from the source comment).

What it does not cover
===========================

* **Python version support moves forward, not backward.** The currently
  supported floor is CPython 3.10 (see ``pyproject.toml``'s
  ``requires-python``); this is a live constraint, not a compatibility
  promise about older interpreters the original package may have targeted.
  Consult the project's GitHub releases for the history of exactly when that
  floor changed -- this repository's own ``CHANGES.rst`` points there rather
  than keeping an inline log, so this page does not restate specific past
  versions it cannot verify from the source tree.
* **Most of today's public surface is new, with no equivalent in the
  original package**: ``MultiBar``, ``FastProgressBar``, the native
  ``speedups`` accelerator (see
  :doc:`performance-and-the-fast-path`), the ``progressbar`` console script
  (see :doc:`../reference/cli`), automatic terminal/color detection (see
  :doc:`terminal-detection`), the tqdm-style ``desc``/``total``/``unit``
  aliases, and most of the widget catalog. "Drop-in replacement" describes
  upgrading a script that already used the original package, not that
  progressbar2 is a behavioral clone limited to what that package did.
* **The deprecated aliases are a migration aid, not a permanent guarantee.**
  ``maxval``, ``poll``, and ``currval`` all emit a ``DeprecationWarning`` on
  use (visible under ``python -W error`` or a test suite that turns warnings
  into failures), and nothing in the source commits to keeping them forever
  -- only the two silent widget aliases above are explicitly commented as
  staying "until the next major version." Treat all of them as due for
  removal eventually, and migrate off them when convenient rather than
  relying on them long-term.
* **The format-string compatibility shim is narrow.** It only rewrites a
  bare ``%s`` for ``Timer`` and ``ETA`` specifically; a custom widget outside
  that inheritance chain that expects the same old-style placeholder is not
  covered.
