===========
GranularBar
===========

``GranularBar`` renders sub-character progress using block glyphs.

Useful when the bar is narrow and whole-character steps would look like
the bar is stuck. ``markers`` sets the glyph ramp used for the partial
cell. In the demo, the bar's leading edge steps through the partial
glyphs instead of jumping a whole character at a time.

.. autoclass:: progressbar.widgets.GranularBar
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/granular-bar

See also
--------------------------------------------------------------------------------

* :doc:`bar`: the whole-character fill this refines.
