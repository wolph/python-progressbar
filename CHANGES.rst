=========
Changelog
=========

4.7.0 - 2026-11-05
------------------

Widgets are coloured by default: a bar on a colour terminal shows the
default palette without ``enable_colors=True``, spinners cycle through
colours, and the ``Bar`` fill colours are constructor arguments (``fg``,
``bg``) instead of the ``Bar.fg`` and ``Bar.bg`` class attributes. A
widget called directly returns the escape codes, and
``progressbar.utils.no_color`` strips them. Output to a file or pipe is
unchanged.

A parallel execution API: ``progressbar.map``, ``imap``,
``imap_unordered``, ``starmap``, ``thread_map``, ``process_map``,
``as_completed``, the asyncio variants ``amap``, ``aimap``,
``aimap_unordered`` and ``gather``, ``run`` for shell commands, and the
``progressbar.parallel`` decorator, with ``bar='multi'`` for an overall
bar plus a bar per task (PR #327).

A forced redraw of the default widgets is 20 percent faster than in
4.6.0 and the fast path, the iterator overhead and the import time are
at or below their 4.6.0 cost, with colours on. Rendered colour escapes
are remembered per gradient and per colour, new-style templates are
validated once per template text, and captured writes take a cheaper
lock (PR #333).

New-style format templates such as ``FormatLabel('{value.__class__}')``
or ``prefix='{value.__doc__} '`` now raise ``ValueError``: a template
walking dunder or frame attributes could reach interpreter internals.
Index access and ordinary attributes keep working, and a positional
field still raises ``IndexError`` as it did.

``desc`` is still the ``prefix`` alias and renders as a template, as it
did in 4.6.0. A literal brace in a description has to be doubled.

The fast bar reserves the width of ``prefix``, ``desc`` and ``suffix``
before sizing the filler, so a labelled bar no longer overflows the
terminal (contributed by @rupayon123 in PR #331). Labels that are not
strings and an uncallable ``custom_len`` render as before.

The ``progressbar`` and ``bar`` commands exit with status 2 and a usage
line on an invalid option value, such as ``--size abc``, where they
printed a traceback before, and validate every argument before the
output file is opened. A pipeline whose reader goes away ends the copy
quietly with status 0.

``PROGRESSBAR_MINIMUM_UPDATE_INTERVAL`` set to a value that is not a
non-negative finite number is logged once and ignored instead of raising
at the first ``ProgressBar()``.

Deprecation warnings for ``maxval``, ``poll`` and ``currval`` name the
caller's file and line. A warnings filter by module ``progressbar`` no
longer matches them, a filter by category or message does.

``StreamWrapper.lock`` and ``listeners_lock`` are read-only properties
shared with the wrapped streams and reset after ``fork``. A subclass
that assigned its own lock raises ``AttributeError`` at construction.
``update_capturing()`` calls ``flush()`` once the last capture stops, as
in 4.6.0. ``wrapped_excepthook`` is a ``bool``.


The ``progressbar`` and ``bar`` commands, and ``python -m progressbar``,
now exit with status 130 after Ctrl-C interrupts a transfer. Previously
they exited with status 0. Scripts that check the exit status can now
distinguish an interrupted transfer from a completed copy.

The ``python-utils`` dependency now requires 4.1.4 or newer, up from
3.8.1. Older releases render a negative ``scale_1024`` power as
``0.1 YiB`` instead of the byte count. An environment that pins
``python-utils<4`` has to lift that pin before upgrading.

Captured output now survives a drain failure on the other stream, and
unwrapping restores the original stream even when its capture buffer is
closed. Built-in ``StringIO`` capture writes and drains remain atomic.
Caller-replaced buffers keep their method overrides, which run without
stream locks. As in 4.6.0, callers synchronise concurrent writes and drains
on those custom buffers. A capture-hook failure now retains the other
stream's exception in the primary failure's context chain.

Specialised format templates retain their escaping and result types.
Their field paths, including nested format specifications, are checked
before calling the application's formatter.

MultiBar expiry keeps a replacement registered under the same exact
``str`` label. Assignment, update, in-place union and ordinary removal
methods share its membership guard. Lifecycle tracking uses bar identity
without calling application hash or equality methods, and the guard resets
after fork.
Custom label objects retain their hash and equality hooks and their
identity as dictionary keys. Using one for mutation or indexing switches
that MultiBar instance permanently to the 4.6.0 concurrency contract:
callers synchronise concurrent mutation and rendering, including expiry.
These hooks run without the membership guard, even for later exact
``str`` lookups. Clearing the instance does not reset this mode. Direct
calls to ``dict`` base-class mutation methods bypass this protocol.

For the most recent changes to the Python Progressbar please look at the Git
releases or the commit log:

 - https://github.com/WoLpH/python-progressbar/releases
 - https://github.com/WoLpH/python-progressbar/commits/develop

Hint: the ``...`` button on a commit shows the full change message.
