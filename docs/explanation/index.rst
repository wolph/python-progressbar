===========
Explanation
===========

If a bar redraws less often than your loop runs, changes its output when
piped to a file, or selects a different renderer, these guides explain why.

From an update to a line
========================

A progress update usually follows these three steps. Forced updates can
bypass the redraw checks, including the updates made when a bar starts
and finishes.

.. container:: render-flow

   1. **Record progress**

      Keep the current value when your loop advances or you call
      ``bar.update(value)``.

   2. **Check whether a redraw is due**

      An integer threshold skips most of the work in a fast loop.
      Calls that pass it are checked against timing and visible progress.

   3. **Format and write the line**

      When a redraw is due, build the display from widgets or the fast
      renderer's fixed format and write it to the output stream.

Understand the behaviour
========================

.. container:: guide-card

   .. rubric:: :doc:`Why doesn't every update redraw? <rendering-and-the-update-gate>`

   Follow the integer threshold and timing checks that decide when a value
   change produces output. See how ``min_poll_interval``, ``poll_interval``
   and ``force=True`` affect the result.

.. container:: guide-card

   .. rubric:: :doc:`Why does output change between terminals and logs? <terminal-detection>`

   Trace terminal detection, colour support and width selection separately.
   Find which constructor arguments and environment variables control
   overwriting a line, using colour and sizing the bar.

.. container:: guide-card

   .. rubric:: :doc:`What work does the fast path skip? <performance-and-the-fast-path>`

   Separate the update gate, the automatically selected ``FastProgressBar``
   renderer and the optional native iterator. Learn when custom widgets
   need the full renderer and what the ``fast`` extra changes.

.. container:: guide-card

   .. rubric:: :doc:`What carries over from the original progressbar? <backwards-compatibility>`

   Check the shared import name and bar lifecycle, then find the modern
   names for deprecated arguments and attributes. See where compatibility
   ends, including Python version support and newer APIs.

.. toctree::
   :hidden:
   :maxdepth: 1

   rendering-and-the-update-gate
   terminal-detection
   performance-and-the-fast-path
   backwards-compatibility
