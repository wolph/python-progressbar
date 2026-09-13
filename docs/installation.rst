============
Installation
============

Install the ``progressbar2`` package, then import it as ``progressbar``.
You need Python 3.10 or later.

1. Install the package
======================

Choose the command that matches how you manage your Python environment:

.. container:: install-options

   .. container:: install-option

      .. rubric:: Install with pip

      Use the Python environment where you will run your script:

      .. code-block:: console

         $ python -m pip install progressbar2

   .. container:: install-option

      .. rubric:: Add to a uv project

      From an existing uv project, add the package as a dependency:

      .. code-block:: console

         $ uv add progressbar2

2. Check the import
===================

Print the installed version from the same Python environment:

.. code-block:: console

    $ python -c "import progressbar; print(progressbar.__version__)"

In a uv project, run the check through uv:

.. code-block:: console

    $ uv run python -c "import progressbar; print(progressbar.__version__)"

A version number confirms that Python can import the installed package.

3. Run your first bar
=====================

Wrap a loop to track its progress:

.. demo:: tutorial/step1

The loop processes 100 steps. ``progressbar.progressbar()`` starts the bar,
advances it as the loop runs and finishes it when the loop ends. The short
sleep makes the movement visible. Replace it with your own work.

Optional native iterator
========================

The standard installation includes the update gate and automatic fast
renderer. The optional ``fast`` extra adds a native iterator for counting
items in large loops:

.. code-block:: console

    $ python -m pip install 'progressbar2[fast]'

For a uv project:

.. code-block:: console

    $ uv add 'progressbar2[fast]'

The examples work without this extra. The
:doc:`fast-path explanation <explanation/performance-and-the-fast-path>`
describes when the native iterator is used.

Keep building
=============

.. container:: guide-card

   .. rubric:: :doc:`Build a bar in five steps <tutorial/index>`

   Start with the loop above, then control updates, set a total, choose
   widgets and print messages above the display.

.. container:: guide-card

   .. rubric:: :doc:`Find a guide for your task <howto/index>`

   Track file transfers, show several jobs together or add live values and
   colour to your progress display.
