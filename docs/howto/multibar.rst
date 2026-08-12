========================================
Track several jobs at once with MultiBar
========================================

A download, an extraction, a build, and a test run -- four jobs, each
progressing at its own pace, finishing at different times -- need more
than one bar, laid out and cleaned up as a group rather than by hand.

.. demo:: howto/multibar

``MultiBar`` is a dict of label to ``ProgressBar``: subscripting it with
a new label -- ``multibar[name]`` -- creates that job's bar on first
access, so there's no separate registration step. A background thread
renders every job's bar together, redrawing whichever rows changed; the
``with`` block waits for that thread on exit. Each job calls its own
``finish()`` independently once it reaches its own target (as every job
here does), so its row freezes at its own finished state -- elapsed
time, final count -- while the others keep moving, rather than one
shared bar where everything completes in lockstep.

Caveats
-------

By default, exiting the ``with`` block waits forever for every job to
finish -- pass ``join_timeout=`` (seconds, or a ``datetime.timedelta``)
to ``MultiBar()`` to bound that wait; once it elapses, any still-running
jobs are abandoned and the render thread is left running as a daemon so
the program can still exit.

Rendering multiple bars in place relies on the terminal understanding
cursor-movement escapes. JetBrains IDEs (PyCharm, IntelliJ) need
"Enable terminal in output console" turned on in the run configuration
for this to render correctly; IDLE's output pane doesn't support this at
all.
