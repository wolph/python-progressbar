========
Variable
========

``Variable`` displays a live, named value with custom formatting.

Reach for it to track a value that is not the bar's own progress (a
loss, a learning rate, a username) updated via
``bar.update(name=value)``. ``format``, ``width``, and ``precision``
control the rendering.

.. autoclass:: progressbar.widgets.Variable
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/variable

See also
--------------------------------------------------------------------------------

* :doc:`postfix`: several values rendered together as one compact suffix.
* :doc:`dynamic-message`: the original name for this same widget.
