=======
Postfix
=======

``Postfix`` renders a live key-value mapping (or string) after the bar.

Reach for it to show a snapshot of several live values at once -- like
tqdm's postfix -- as one compact ``key=value, key=value`` suffix,
sourced from a bar variable. Compare ``Variable`` for a single formatted
value and ``FormatCustomText`` for text that is not tied to the bar's
variables at all.

.. autoclass:: progressbar.widgets.Postfix
   :members:
   :show-inheritance:
   :no-index:

Example
--------------------------------------------------------------------------------

.. demo:: widgets/postfix

See also
--------------------------------------------------------------------------------

* :doc:`variable` — a single formatted value instead of several combined.
* :doc:`format-custom-text` — text that is not tied to the bar's variables at all.
