==============================================
Step 5: Print safely with ``redirect_stdout``
==============================================

A bar redraws its own line in place using a carriage return. A plain
``print()`` from inside the same loop writes a newline into that same
spot and tears the display apart. This step adds an option that keeps the
two apart.

.. demo:: tutorial/step5

Watch the animation: every 25 iterations the loop prints
``Reached step N``, and that line appears above the bar as ordinary
scrolled text, while the bar itself keeps redrawing cleanly on its own
line underneath. Nothing is lost and nothing overwrites the bar mid-line.

The change from the previous step is one keyword argument on the
constructor: ``redirect_stdout=True``, alongside the same ``max_value``
and ``widgets`` as before --
``progressbar.ProgressBar(max_value=100, widgets=widgets,
redirect_stdout=True)``. With it set, anything written to standard output
while the bar is active -- here, the loop's own ``print(f'Reached step
{i}')`` -- is held back and flushed above the bar on its next redraw,
instead of colliding with the bar's carriage return.

That's the whole tutorial. From here, the :doc:`how-to guides
</howto/index>` cover specific tasks and the :doc:`widget pages
</widgets/index>` document every widget.
