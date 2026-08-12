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
one line per update on its own once it isn't. The demo above passes the
explicit override because it records inside a terminal. The explicit
``line_breaks=True`` is also worth passing when stdout genuinely is a
terminal but every line should stay on screen, such as a build log.
