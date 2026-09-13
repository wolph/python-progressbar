========
Tutorial
========

Build a progress bar that shows how much work is left and keeps printed
messages readable. These five steps add one change at a time. Each step
includes the complete Python source and an example you can run in your browser.

.. only:: html and not epub

   The recordings below show the output of each step. Scroll a recording
   horizontally if the terminal is wider than your screen.

.. container:: guide-card

   .. rubric:: :doc:`1. Turn a loop into a progress bar <step1>`

   See each item move the bar towards 100%, with an elapsed time and an
   estimate of the time remaining. Wrap your iterable with
   ``progressbar.progressbar()`` to let it track the loop for you.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/tutorial-step1.svg
            :target: step1.html
            :alt: A loop reaching 100%, with an elapsed time and an ETA.

.. container:: guide-card

   .. rubric:: :doc:`2. Decide when progress moves <step2>`

   Keep a visible activity indicator even when you don't know the total.
   Call ``bar.update()`` yourself whenever your work advances.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/tutorial-step2.svg
            :target: step2.html
            :alt: An activity indicator and elapsed time, without a percentage.

.. container:: guide-card

   .. rubric:: :doc:`3. Show how much work is left <step3>`

   Give the bar a ``max_value`` to replace the activity indicator with a
   percentage and an ETA. The same updates now show how close you are to
   finishing.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/tutorial-step3.svg
            :target: step3.html
            :alt: Progress measured against a known total, with a percentage and ETA.

.. container:: guide-card

   .. rubric:: :doc:`4. Choose what your bar shows <step4>`

   Build a shorter display with just a percentage, a bar and an ETA.
   A ``widgets`` list sets the details and their order, including the
   spaces between them.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/tutorial-step4.svg
            :target: step4.html
            :alt: A custom display containing only a percentage, a bar and an ETA.

.. container:: guide-card

   .. rubric:: :doc:`5. Print messages above the bar <step5>`

   Keep ``Reached step`` messages on their own lines while the bar updates
   underneath. Add ``redirect_stdout=True`` so your loop can print without
   overwriting the progress display.

   .. only:: html and not epub

      .. container:: guide-preview

         .. image:: /_static/demos/tutorial-step5.svg
            :target: step5.html
            :alt: Reached step messages printed above a separate progress bar.

After step 5, the :doc:`how-to guides </howto/index>` cover file transfers,
several jobs at once and other specific tasks.

.. toctree::
   :hidden:
   :maxdepth: 1

   step1
   step2
   step3
   step4
   step5
