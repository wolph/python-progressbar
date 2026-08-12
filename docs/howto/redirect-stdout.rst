============================
Print while a bar is running
============================

A plain ``print()`` call while a bar is redrawing collides with it on
the same line -- the two fight over the same carriage return, and
neither comes out readable.

.. demo:: howto/redirect-stdout

Pass ``redirect_stdout=True`` and call ``print()`` normally from inside
the loop. The bar holds the line back and flushes it above the moving
bar on its next redraw. This only catches writes to ``sys.stdout``:
``print()`` and anything else writing there directly. To route the
stdlib ``logging`` module the same way, see
:doc:`Send logging output above a running bar <logging-integration>`.
