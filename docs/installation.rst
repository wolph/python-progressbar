============
Installation
============

The package is named ``progressbar2`` on PyPI (the module you import is
``progressbar``) and requires Python 3.10 or later. Install it with pip:

.. code-block:: console

    $ pip install progressbar2

Or with uv:

.. code-block:: console

    $ uv add progressbar2

The optional ``fast`` extra installs the native iterator accelerator used
by the fast path (see :doc:`explanation/performance-and-the-fast-path`):

.. code-block:: console

    $ pip install 'progressbar2[fast]'

Confirm the install by printing the version:

.. code-block:: console

    $ python -c "import progressbar; print(progressbar.__version__)"

If that prints a version number such as ``4.6.0``, continue with
:doc:`tutorial/index`.
