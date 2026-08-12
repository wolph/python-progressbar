==============================
Color a bar, solid or gradient
==============================

A plain bar is monochrome, but sometimes color carries information: a
gradient that shifts from red through yellow to green as work completes
gives an at-a-glance health signal, and a solid color still helps a
spinner stand out from surrounding log output.

.. demo:: howto/colors

Pass ``gradient_colors=TGradientColors(fg=ColorGradient(...), bg=None)``
to ``Bar()`` to interpolate the foreground color as ``percentage`` moves
from 0 to 100 -- this only makes sense once ``max_value`` gives the bar a
percentage to compute in the first place. For a bar with no ``max_value``
(an indeterminate spinner, here built from ``AnimatedMarker``), there is
no percentage to key off, so use ``fixed_colors=TFixedColors(fg_none=...,
bg_none=None)`` instead: a single unchanging color rather than a
gradient. Both accept colors from ``progressbar.terminal.colors``.

Caveats
-------

Whether either actually renders in color depends on what the terminal
reports it supports -- detected from ``COLORTERM``/``TERM``, or forced
with the ``PROGRESSBAR_ENABLE_COLORS`` environment variable (``24bit``,
``256``, or ``16``) when detection guesses wrong, such as under CI or
when output is piped through something that strips the terminal type.
