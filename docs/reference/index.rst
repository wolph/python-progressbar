=========
Reference
=========

Find constructor arguments, methods and command-line options for the part
of progressbar2 you are using. Each reference explains the available controls
and links to the corresponding classes and functions.

Bars and parallel work
======================

.. container:: guide-card

   .. rubric:: :doc:`Configure a ProgressBar <progressbar>`

   Set the value range, widgets, output stream and redraw intervals.
   Look up ``ProgressBar`` methods and the related ``DataTransferBar``,
   ``NullBar`` and ``FastProgressBar`` classes.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/tutorial-step4.svg
            :target: progressbar.html
            :alt: A ProgressBar configured with a percentage, a bar and an ETA.

.. container:: guide-card

   .. rubric:: :doc:`Manage rows with MultiBar <multibar>`

   Control labels, row ordering and the display of waiting and finished
   jobs. ``MultiBar`` keeps the child bars together and redraws them from
   its background thread.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-multibar.svg
            :target: multibar.html
            :alt: MultiBar displaying several jobs as they advance and finish.

.. container:: guide-card

   .. rubric:: :doc:`Choose a parallel execution API <parallel>`

   Look up ``map``, ``imap``, ``amap`` and the other batch helpers.
   Compare worker pools, result ordering, concurrency limits and error
   handling, including reusable ``Pool`` and ``AsyncPool`` objects.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/howto-parallel-execution.svg
            :target: parallel.html
            :alt: Parallel tasks with individual progress bars and an overall count.

Widgets, commands and modules
=============================

.. container:: guide-card

   .. rubric:: :doc:`Find the widget for your display <../widgets/index>`

   Choose a percentage, timer, transfer speed or live value by what you need
   to show. The widget table identifies which displays need a known total,
   with a runnable example for each widget.

   ``Percentage``, ``Bar``, ``ETA``, ``Variable``

.. container:: guide-card

   .. rubric:: :doc:`Look up command-line options <cli>`

   Track bytes or lines moving through a pipe or between files with the
   ``progressbar`` command. Check size, rate and output options, including
   the compatibility flags that are accepted but have no effect.

   ``progressbar`` and ``bar`` name the same command.

.. container:: guide-card

   .. rubric:: :doc:`Browse the full module listing <../progressbar>`

   Find classes, functions and modules in the generated API documentation,
   including helpers beyond the focused reference pages above.

   ``progressbar.bar``, ``progressbar.multi``, ``progressbar.widgets``

.. toctree::
   :hidden:
   :maxdepth: 1

   progressbar
   multibar
   parallel
   cli
   Full module autodoc <../progressbar>
