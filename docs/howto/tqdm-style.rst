===============================================
Switch from tqdm without renaming your keywords
===============================================

Porting a loop from ``tqdm`` means either rewriting every call site's
keyword arguments, or finding the ones that already mean the same thing
here.

.. demo:: howto/tqdm-style

``desc`` and ``total`` work on any ``ProgressBar``: ``desc`` becomes the
prefix (rendered as ``f'{desc}: '``), and ``total`` becomes ``max_value``
when ``max_value`` isn't given explicitly. ``unit=``/``unit_scale=``
don't render anything by themselves -- they only show up through a
widget that reads them, such as ``UnitProgress()`` -- so pass a widget
list that includes one if you want them visible, as this demo does
alongside ``Postfix()`` for the live per-file status.

Caveats
-------

Not every tqdm keyword carries over. An unrecognized one, such as
``ncols``, is silently accepted rather than raising -- it has no effect
and nothing warns you it was ignored, so a typo in a keyword name fails
quietly instead of loudly.
