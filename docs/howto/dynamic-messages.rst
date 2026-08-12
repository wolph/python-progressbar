===================================
Show a custom value next to the bar
===================================

Sometimes the bar's own progress isn't the only number worth showing --
a current filename, a running total, or any other value your loop
computes -- and that value doesn't come from ``value``/``max_value`` at
all.

.. demo:: howto/dynamic-messages

``Variable(name)`` renders a named entry from ``bar.update()``'s keyword
arguments: pass ``current=some_value`` to ``update()`` and a
``Variable('current')`` widget picks it up on the next redraw. You don't
need to seed it in advance -- the bar scans its widget list at
construction and registers a placeholder for every named variable that
isn't already supplied, so the first render shows dashes rather than
raising. Older code may import ``DynamicMessage`` instead: it is a plain
subclass of ``Variable``, kept only so existing imports keep working, and
behaves identically -- prefer ``Variable`` in anything new.
