===================================
Show a custom value next to the bar
===================================

When you scan a log, the number of errors matters alongside the number
of records inspected. A ``Variable`` widget displays the error count
while the percentage tracks the scan:

.. demo:: howto/dynamic-messages

``Variable('errors')`` reads the ``errors=`` keyword passed to
``bar.update()``. The example increments that count only when a record
starts with ``ERROR``. The scan finishes at 100% with 20 errors found
among 100 records. Placing the count first keeps it beside the scan
percentage as the bar stretches to fill the remaining width.

``variables={'errors': 0}`` supplies the initial reading. Without an
initial value, the bar registers a placeholder for each ``Variable``
in its widget list and displays dashes until the first update.

Older code may import ``DynamicMessage``. It is a plain subclass of
``Variable``, kept for compatibility, and behaves identically. Use
``Variable`` in new code.
