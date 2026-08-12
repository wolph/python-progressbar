============
progressbar2
============

A quick taste
=============

After ``pip install progressbar2`` (:doc:`installation`), wrapping any
iterable shows a live bar:

.. code:: python

    import time
    import progressbar

    for item in progressbar.progressbar(range(100)):
        time.sleep(0.02)

That is the whole API for the common case. From there:

* :doc:`tutorial/index` builds up from that one line to custom widgets in
  five steps.
* :doc:`howto/index` answers specific questions: printing while a bar is
  running, several bars at once, unknown-length work, colors.
* :doc:`widgets/index` has a page per widget, each with an animation you
  can run in your browser.
* :doc:`explanation/index` covers why the bar redraws when it does, how
  terminal detection works, and what the fast path costs.

Every example on this site is a tested, runnable module. In an HTML
browser each one carries a **Run** button that executes it in place with
real CPython compiled to WebAssembly, nothing installed.

.. Deliberately not ``.. include:: ../README.rst``: its remote SVG badges
   break the LaTeX/PDF/ePub builds under ``fail_on_warning``, and the site
   documents everything the README covers.

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
