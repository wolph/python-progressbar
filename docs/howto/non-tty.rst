================================================
Print one line per update instead of overwriting
================================================

``ProgressBar`` normally repaints one line in place, overwriting the
previous redraw -- the right behavior for an interactive terminal, but
the wrong one once output is piped to a file, ``tee``, or a log
collector, where overwriting means every redraw but the last is lost.

.. demo:: howto/non-tty

Pass ``line_breaks=True`` to print a full new line per update instead of
overwriting. Left to auto-detect (the default, ``line_breaks=None``),
the bar checks whether its output stream is a terminal and switches to
this same one-line-per-update behavior on its own once it isn't -- but
that auto-detection can't be demonstrated on this page, since the
harness that captures this demo's animation always presents itself as a
terminal. What you see above is the explicit override, not the
auto-detected behavior it stands in for. Reach for the same
``line_breaks=True`` even when stdout genuinely is a terminal, wherever
every line should stay on screen -- a build log, say.
