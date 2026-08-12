===
Bar
===

``Bar`` draws a classic fill-style progress bar.

The default choice for a determinate task with a known total: a marker
fills the line from left to right as ``value`` approaches ``max_value``.
See ``ReverseBar`` for the mirrored direction, ``GranularBar`` for
sub-character precision, and ``BouncingBar`` for indeterminate work.

.. autoclass:: progressbar.widgets.Bar
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/bar

See also
--------------------------------------------------------------------------------

* :doc:`reverse-bar` — the same bar filling right to left.
* :doc:`granular-bar` — sub-character resolution.
