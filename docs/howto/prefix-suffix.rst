=======================================
Put live values in the prefix or suffix
=======================================

A fixed string works for a label that never changes, but a prefix that
names the file currently being processed, or a suffix that shows the
running count, needs to be re-evaluated on every redraw.

.. demo:: howto/prefix-suffix

Both ``prefix=`` and ``suffix=`` accept a ``str.format()`` template
evaluated against the bar's data on every redraw, not just a plain
string: use ``{value}``, ``{max_value}``, or any other key the built-in
widgets read. A custom entry works the same way as in
:doc:`dynamic-messages` -- seed it through ``variables=`` (or let it
default), then reach it in the template as ``{variables.<name>}``, and
update it by name through ``bar.update(step, <name>=...)``.
