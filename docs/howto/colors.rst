==============================
Color a bar, solid or gradient
==============================

Bars use a progress gradient by default, and spinners cycle through
colours as they animate. Choose your own gradient or keep a spinner
one colour when that better suits the surrounding output:

.. demo:: howto/colors

Pass ``gradient_colors=TGradientColors(fg=ColorGradient(...), bg=None)``
to ``Bar()`` to change the foreground colour as its percentage moves
from 0 to 100. The first bar follows that gradient. The spinner uses
``gradient_colors=TGradientColors(fg=colors.blue, bg=None)``. A single
colour keeps it blue while its characters continue to rotate.

For an unknown-length ``Bar`` or ``BouncingBar``, use
``fixed_colors=TFixedColors(fg_none=..., bg_none=None)`` to choose its
colour. ``AnimatedMarker`` follows its animation cycle instead of a
percentage, so its ``gradient_colors`` works with or without a total.

Caveats
-------

Whether either actually renders in color depends on what the terminal
reports it supports -- detected from ``COLORTERM``/``TERM``, or forced
with the ``PROGRESSBAR_ENABLE_COLORS`` environment variable (``24bit``,
``256``, or ``16``) when detection guesses wrong, such as under CI or
when output is piped through something that strips the terminal type.

Pass ``enable_colors=False`` to ``ProgressBar`` to disable colours for
the whole bar.
