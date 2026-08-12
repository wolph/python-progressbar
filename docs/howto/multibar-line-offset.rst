=======================================
Stack independent bars without MultiBar
=======================================

Not every group of concurrent bars is a single managed job set --
sometimes each bar only needs to know its own row in a fixed stack, with
no shared start/stop lifecycle tying them together. Reach for
``line_offset`` on plain ``ProgressBar`` instances instead of
:doc:`multibar` when that's the shape of the problem.

.. demo:: howto/multibar-line-offset

Each bar gets its own ``line_offset=`` (counting rows up from the
current cursor position) and renders independently -- there is no shared
container or background thread. Print the blank lines the bars will
occupy *before* creating them, since every redraw moves the cursor up by
``line_offset``, writes, then moves back down by the same amount,
relative to wherever the cursor already is.

Caveats
-------

That relative cursor movement means anything else that writes to the
same stream while these bars are active -- a stray ``print()``, a log
line, another bar's redraw landing at the wrong moment -- shifts the
baseline every bar measures its offset from, and throws off every row
after that point. Keep the region these bars occupy free of unrelated
output for as long as they're active.

Because independent bars don't coordinate a shared target the way
``MultiBar`` jobs do, a single call site incrementing a random bar past
its own ``max_value`` is easy to trigger by accident. Pass
``max_error=False`` so an over-target update clamps at ``max_value``
instead of raising.
