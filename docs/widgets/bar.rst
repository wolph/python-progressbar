===
Bar
===

``Bar`` draws a classic fill-style progress bar.

The default choice for a determinate task with a known total: a marker
fills the line from left to right as ``value`` approaches ``max_value``.
``marker``, ``left``, ``right``, and ``fill`` set the characters drawn,
and ``fill_left`` picks the side the padding sits on.

.. autoclass:: progressbar.widgets.Bar
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/bar

See also
--------------------------------------------------------------------------------

* :doc:`reverse-bar`: the same bar filling right to left.
* :doc:`granular-bar`: sub-character resolution.
* :doc:`bouncing-bar`: an indeterminate variant for unknown totals.
