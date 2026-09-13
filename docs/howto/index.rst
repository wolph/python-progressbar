=============
How-to guides
=============

Pick the task you need to solve, from tracking a download to keeping several
jobs visible at once. For a first progress bar, start with the
:doc:`tutorial <../tutorial/index>`.

.. only:: html and not epub

   Each recording shows the output you can build with its guide. Scroll a
   recording horizontally if the terminal is wider than your screen.

Track your work
===============

.. container:: guide-card

   .. rubric:: :doc:`Add progress to a loop <iterable-wrapper>`

   See how far your loop has got without managing the bar's lifecycle.
   Wrap an iterable directly, or reuse a bar you have already configured.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-iterable-wrapper.svg
            :target: iterable-wrapper.html
            :alt: A progress bar tracking items from an iterable.

.. container:: guide-card

   .. rubric:: :doc:`Track a transfer's size and speed <file-transfer>`

   Show how many bytes have moved, the average transfer speed and the recent
   rate. Combine three widgets to see both progress and changes in speed.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-file-transfer.svg
            :target: file-transfer.html
            :alt: Transferred data size alongside average and recent transfer speeds.

.. container:: guide-card

   .. rubric:: :doc:`Show activity without a known total <unknown-length>`

   Keep a moving marker and a count of completed items when you can't calculate
   a percentage. Use it for streams, scans and other open-ended work.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-unknown-length.svg
            :target: unknown-length.html
            :alt: An animated marker and item counter for work with no known total.

.. container:: guide-card

   .. rubric:: :doc:`Bring your tqdm-style arguments <tqdm-style>`

   Keep familiar ``desc`` and ``total`` arguments when moving a loop to
   progressbar2. See how widgets display units and live status, and which
   tqdm arguments don't carry over.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-tqdm-style.svg
            :target: tqdm-style.html
            :alt: A labelled progress bar with units and live per-file status.

Manage several jobs
===================

.. container:: guide-card

   .. rubric:: :doc:`Give each job its own bar <multibar>`

   Watch jobs advance and finish independently in one display. ``MultiBar``
   manages their rows and redraws them together. Run the example locally,
   since its background thread isn't available in the browser.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-multibar.svg
            :target: multibar.html
            :alt: Several labelled jobs progressing and finishing independently.

.. container:: guide-card

   .. rubric:: :doc:`Place independent bars on fixed rows <multibar-line-offset>`

   Assign each bar a ``line_offset`` when you want to manage the rows yourself.
   The guide also covers keeping other output out of those rows.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-multibar-line-offset.svg
            :target: multibar-line-offset.html
            :alt: Independent progress bars updating on separate terminal rows.

.. container:: guide-card

   .. rubric:: :doc:`Run a batch in parallel <parallel-execution>`

   Watch three files advance at different speeds with ``progressbar.map``.
   Each worker reports its own progress, while the overall bar counts finished
   files. Run this example locally.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-parallel-execution.svg
            :target: parallel-execution.html
            :alt: progressbar.map running a batch with a separate bar for each active task.

Keep output readable
====================

.. container:: guide-card

   .. rubric:: :doc:`Print messages above the bar <redirect-stdout>`

   Keep ordinary ``print()`` messages on their own lines while progress updates
   underneath. Enable ``redirect_stdout`` and keep printing from your loop.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-redirect-stdout.svg
            :target: redirect-stdout.html
            :alt: Printed messages appearing above a progress bar.

.. container:: guide-card

   .. rubric:: :doc:`Keep logging output above the bar <logging-integration>`

   Route messages from Python's ``logging`` handlers above the progress display.
   Wrap existing handlers, then restore their streams when the work finishes.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-logging-integration.svg
            :target: logging-integration.html
            :alt: Logging messages appearing above a running progress bar.

.. container:: guide-card

   .. rubric:: :doc:`Keep every update in a log <non-tty>`

   Print a fresh line for each update when output goes to a file or log
   collector. Use ``line_breaks`` to control the behaviour explicitly.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-non-tty.svg
            :target: non-tty.html
            :alt: Progress updates printed on separate lines instead of overwriting.

Customise the display
=====================

.. container:: guide-card

   .. rubric:: :doc:`Add colour and gradients <colors>`

   Change a bar's colour as it approaches completion, or give a marker a fixed
   colour. The guide covers terminal colour support as well as the widgets.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-colors.svg
            :target: colors.html
            :alt: A progress bar with a colour gradient and a marker with a fixed colour.

.. container:: guide-card

   .. rubric:: :doc:`Display your own widget <custom-widget>`

   Show ``Phase: preparing``, ``processing`` and ``finishing`` as the job
   advances. Write a callable that supplies that text and place it before
   the bar.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-custom-widget.svg
            :target: custom-widget.html
            :alt: A custom widget showing the current phase of a job.

.. container:: guide-card

   .. rubric:: :doc:`Show a value from your loop <dynamic-messages>`

   Count errors while scanning log records. ``Errors`` increases only when a
   record contains an error, while the bar tracks every record scanned.
   A ``Variable`` widget reads that count from ``bar.update()``.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-dynamic-messages.svg
            :target: dynamic-messages.html
            :alt: An error count increasing separately from the percentage of records scanned.

.. container:: guide-card

   .. rubric:: :doc:`Put live values in labels <prefix-suffix>`

   Show the current filename and file number before the bar, with the processed
   block count after it. Each file advances in twenty small steps, so you can
   watch the labels change as the work moves from one file to the next.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-prefix-suffix.svg
            :target: prefix-suffix.html
            :alt: Prefix and suffix labels updating with values from the running bar.

.. toctree::
   :hidden:
   :maxdepth: 1

   iterable-wrapper
   redirect-stdout
   logging-integration
   non-tty
   colors
   custom-widget
   dynamic-messages
   prefix-suffix
   tqdm-style
   file-transfer
   unknown-length
   multibar
   multibar-line-offset
   parallel-execution
