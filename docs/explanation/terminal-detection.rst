=====================
Terminal detection
=====================

A ``ProgressBar`` answers two separate questions about its output stream,
using different logic for each: *is this a terminal at all* (``is_terminal``,
controlling whether it overwrites one line or prints a new line per update),
and *how many colors can it show* (``enable_colors``). Both can be overridden
explicitly by constructor argument; left alone, both fall back to
environment inspection in :py:mod:`progressbar.env` and
:py:mod:`progressbar.bar`. This page traces exactly what each check does and
in what order, since getting the order wrong when reasoning about "why isn't
my bar colored" is easy.

``is_terminal``: is this a terminal?
=========================================

:py:func:`progressbar.env.is_terminal` resolves in this order, stopping at
the first step that produces a non-``None`` result:

1. The ``is_terminal`` constructor argument, if you passed one explicitly.
2. :py:func:`progressbar.env.is_ansi_terminal`, which itself checks, in
   order: whether this looks like a Jupyter kernel (``JUPYTER_COLUMNS``,
   ``JUPYTER_LINES`` or ``JPY_PARENT_PID`` set) or a modern-enough PyCharm
   terminal (``PYCHARM_HOSTED=1`` and not under pytest); then, if neither
   matched, whether the stream's own ``fd.isatty()`` is true *and* ``TERM``
   matches a known ANSI-terminal pattern, or ``ANSICON`` is set, or (on
   Windows) the console mode reports processed output.
3. The ``PROGRESSBAR_IS_TERMINAL`` environment variable (``y``/``n``,
   ``1``/``0``, ``true``/``false``, etc. -- see
   :py:func:`progressbar.env.env_flag`), as an explicit override for
   situations auto-detection can't cover.
4. A bare ``fd.isatty()`` call, falling back to ``False`` if the stream
   doesn't support it (closed, detached, or not a real file object).

The default for ``line_breaks`` is derived from this: it defaults to
``not is_terminal`` (via the ``PROGRESSBAR_LINE_BREAKS`` environment
variable, which itself defaults to that), so a bar piped to a file or ``tee``
switches to one line per update automatically, without needing
``--numeric``/``line_breaks=True`` set explicitly.

.. demo:: howto/non-tty

Color depth: two separate layers
=====================================

Color support is resolved by two different pieces of logic that run at
different times, and -- this is the part worth reading carefully -- they
scan the *same two* environment variables in *opposite order*.

Layer 1 -- the module-level ceiling
--------------------------------------

When :py:mod:`progressbar.env` is first imported, it computes
``COLOR_SUPPORT``, a :py:class:`~progressbar.env.ColorSupport` value, once,
via :py:meth:`ColorSupport.from_env() <progressbar.env.ColorSupport.from_env>`.
This is the *ceiling*: the best color depth this environment could support,
independent of any particular bar.

* If this looks like a Jupyter kernel, the answer is immediately
  ``XTERM_TRUECOLOR``.
* Otherwise, on Windows, the console mode is probed instead of the
  environment variables below.
* Otherwise, four variables are scanned **in this order**: ``FORCE_COLOR``,
  ``PROGRESSBAR_ENABLE_COLORS``, ``COLORTERM``, ``TERM``. For each one that
  is set: a literal ``truecolor``/``24bit`` value wins immediately and stops
  the scan; a value naming a terminal that is always truecolor-capable
  (``xterm-kitty``, ``xterm-ghostty``) raises the running maximum to
  truecolor; a value containing ``256`` raises it to 256-color; a value
  matching a known ANSI terminal pattern raises it to 16-color; and a
  generic truthy flag (``1``, ``yes``, ``true``, ...) wins immediately with
  truecolor, the same way a literal ``truecolor`` value does. Otherwise the
  variable is ignored and the scan continues. The result is the *highest*
  depth implied by any of the four -- so, per the source docstring,
  "``COLORTERM=truecolor`` will override ``TERM=xterm-256color``" even
  though ``COLORTERM`` and ``TERM`` are just two entries scanned in order,
  not a simple first-match-wins.

Layer 2 -- the per-bar on/off decision
-------------------------------------------

Separately, when a ``ProgressBar`` is constructed, ``enable_colors=None``
(the default) triggers
:py:meth:`DefaultFdMixin._determine_enable_colors() <progressbar.bar.DefaultFdMixin._determine_enable_colors>`,
which decides whether *this bar* uses color at all, and does so by scanning
three signals **in this order**: ``PROGRESSBAR_ENABLE_COLORS``,
``FORCE_COLOR``, then ``is_ansi_terminal`` (see above). The first of the
three that is not ``None`` wins: if truthy, the bar uses the Layer 1
ceiling (``COLOR_SUPPORT``); if falsy, it uses no color at all
(``ColorSupport.NONE``). If none of the three produced an answer, the
default is also no color.

Note the reversal: Layer 1 checks ``FORCE_COLOR`` before
``PROGRESSBAR_ENABLE_COLORS``; Layer 2 checks ``PROGRESSBAR_ENABLE_COLORS``
before ``FORCE_COLOR``. In practice this rarely matters -- both variables
being set to conflicting *boolean* values (one truthy, one falsy) is the
only case where the order changes the outcome, since Layer 1's ordering only
controls which *depth* wins when both are set to color-naming values (not
plain booleans), while Layer 2's ordering only controls which *on/off
verdict* wins when both are set to plain booleans.

Passing ``enable_colors`` explicitly (``True``, ``False``, or a specific
:py:class:`~progressbar.env.ColorSupport` member) to the ``ProgressBar``
constructor skips both layers for that bar.

``COLUMNS``: a different mechanism entirely
================================================

``COLUMNS`` is not part of either color check above -- it plays no role in
:py:mod:`progressbar.env` at all. It affects the terminal *width*
(``term_width``), through a completely separate path: when a bar is created
without an explicit ``term_width``, or on a resize signal,
:py:meth:`ResizableMixin._handle_resize() <progressbar.bar.ResizableMixin._handle_resize>`
calls :py:func:`progressbar.utils.get_terminal_size` (re-exported from
`python-utils <https://pypi.org/project/python-utils/>`_). That function
tries, in order, an IPython-specific check, then Python's
:py:func:`shutil.get_terminal_size`, then its own explicit ``COLUMNS``/
``LINES`` read, then a few further platform-specific fallbacks, ending in a
hard-coded ``79, 24``.

The practical effect: since :py:func:`shutil.get_terminal_size` itself
checks the ``COLUMNS``/``LINES`` environment variables *before* querying the
real terminal, a valid positive ``COLUMNS`` value takes priority over the
actual terminal width whenever it's set -- which is exactly the mechanism
scripts use to pin a bar's width in a non-interactive or resized-oddly
environment.
