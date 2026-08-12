===================================
Step 4: Choose your own ``widgets``
===================================

The bar's built-in display won't always be what you want on screen. This
step replaces it entirely with a hand-picked, explicit list of widgets.

.. demo:: tutorial/step4

The previous step let ``ProgressBar`` pick its own display based on
``max_value``. Here the constructor gains a ``widgets=widgets`` argument,
where ``widgets`` is a plain list built before the call:
``[progressbar.Percentage(), ' ', progressbar.Bar(), ' ',
progressbar.ETA()]``. Passing ``widgets`` overrides everything
``ProgressBar`` would otherwise have picked -- only what is listed is
shown, in the order listed, including the plain ``' '`` strings used here
to space the widgets apart.

Next: :doc:`step5`.
