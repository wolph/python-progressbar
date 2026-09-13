=====================
Write a custom widget
=====================

The built-in widgets cover percentages, timers, and transfer speeds, but
a job may also need a named phase. The custom widget below shows
"preparing", "processing", and "finishing" as the work advances.

.. demo:: howto/custom-widget

The phase appears before the bar. ``Stage`` returns a label padded to
ten characters, so switching from "preparing" to "processing" keeps
the percentage and bar aligned.

A widget is any callable matching ``WidgetBase.__call__(self, progress,
data)``, returning the text to render for one redraw. Subclass
``WidgetBase`` and implement ``__call__``: ``progress`` is the bar itself
(read from it, don't mutate it), and ``data`` is the same snapshot dict
the built-in widgets read -- ``data['value']``, ``data['percentage']``,
and so on. Drop the instance straight into a ``widgets=`` list alongside
the built-ins. Nothing distinguishes a custom widget from a shipped one
at that point.
