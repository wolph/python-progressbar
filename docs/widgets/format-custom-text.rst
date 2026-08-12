================
FormatCustomText
================

``FormatCustomText`` renders its own text, independent of the bar.

Reach for it to show auxiliary information that is not part of the
bar's progress or ``variables`` -- it keeps its own mapping, updated
directly with ``update_mapping()`` rather than through ``bar.update()``.

.. autoclass:: progressbar.widgets.FormatCustomText
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/format-custom-text

See also
--------------------------------------------------------------------------------

* :doc:`postfix`: a compact key=value summary sourced from a bar variable.
* :doc:`format-label`: a format string over the bar's own data snapshot.
