========================================
Welcome to Progress Bar's documentation!
========================================

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   installation
   tutorial/index
   howto/index
   widgets/index
   reference/index
   explanation/index

.. toctree::
   :maxdepth: 1
   :caption: Project

   contributing
   history

.. Deliberately not ``.. include:: ../README.rst``. The README carries
   remote SVG badges and demo animations, and LaTeX cannot render SVG at
   all -- including it here emitted warnings no ``suppress_warnings``
   category could target, which under ``fail_on_warning`` broke the PDF
   and ePub builds. The site has its own full documentation now, so
   duplicating the README on the landing page was redundant anyway.

A quick taste
=============

.. code:: python

    import time
    import progressbar

    for item in progressbar.progressbar(range(100)):
        time.sleep(0.02)

That is the whole API for the common case. From there:

* :doc:`tutorial/index` builds up from that one line to custom widgets in
  five steps.
* :doc:`howto/index` answers specific questions -- printing while a bar is
  running, several bars at once, unknown-length work, colours.
* :doc:`widgets/index` has a page per widget, each with an animation you
  can run in your browser.
* :doc:`explanation/index` covers why the bar redraws when it does, how
  terminal detection works, and what the fast path costs.

Every example on this site is a real, tested module. In an HTML browser
each one carries a **Run** button that executes it in place -- real
CPython, compiled to WebAssembly, with nothing installed.

Install
=======

.. code:: sh

    pip install progressbar2

******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
