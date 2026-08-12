=======================================
Send logging output above a running bar
=======================================

``redirect_stdout``/``redirect_stderr`` catch ``print()`` and raw writes,
but calls through the stdlib ``logging`` module go via a
``StreamHandler`` that writes directly to whatever stream it was bound
to -- redirecting the raw stream alone doesn't touch it.

.. demo:: howto/logging-integration

``streams.wrap_stderr()`` redirects raw writes, the same way
``redirect_stderr=True`` does on a single bar. ``streams.wrap_logging()``
additionally retargets ``StreamHandler`` instances already attached to a
logger: it walks every logger's handlers once, and any handler currently
writing to the real stdout/stderr (or to whatever stdout/stderr already
is) gets pointed at the wrapped stream instead, so ``logging.info(...)``
lands above the bar the same way ``print()`` does. Construction order does
not matter here: a bar defaulting to ``sys.stderr`` resolves that to the
*unwrapped* stream either way, which is what keeps its own redraws from
recursing back through the capture. Unwind both in a ``finally``: ``unwrap_logging()``
restores each handler's original stream, then ``unwrap_stderr()``
restores ``sys.stderr`` -- both mutate process-global state, so a leaked
wrapper affects every bar built afterward in the same process.

Caveats
-------

``wrap_logging()`` only touches handlers it can already see: it matches
each handler's current stream against the process's real stdout/stderr
(captured once, when ``progressbar`` first loads) and whatever
stdout/stderr are right now. A handler already pointed at some other
stream object -- because another tool had already substituted
``sys.stderr`` before this one ran, or because the handler was built with
an explicit file argument -- isn't one ``wrap_logging()`` recognizes, and
is left untouched, still writing wherever it already was.
