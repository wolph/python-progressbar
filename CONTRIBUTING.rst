============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/WoLpH/python-progressbar/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "feature"
is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

Python Progressbar could always use more documentation, whether as part of the
official Python Progressbar docs, in docstrings, or even on the web in blog posts,
articles, and such.

Regenerating the API reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``docs/progressbar*.rst`` pages are generated once with ``sphinx-apidoc`` and then
committed and hand-maintained, not regenerated on every build. Never pass ``-f``/``--force``
when running it again — that silently discards hand-added options, such as
``docs/progressbar.bar.rst``'s ``:member-order: bysource``. If you add a new module under
``progressbar/``, generate its page the same way the rest were generated and link it into
``docs/progressbar.rst``'s ``Submodules`` toctree yourself::

    $ sphinx-apidoc -e -o docs/ progressbar */os_specific/* */six.py

The docs build runs with ``-W`` (warnings fail the build), so a page that exists but isn't
linked into a toctree fails immediately with "document isn't included in any toctree" —
you'll know right away if you forgot this step.

Regenerating demo animations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``python scripts/render_demos.py`` captures each example attached to a pty, so
it requires a POSIX system. The generated SVGs are committed, and CI regenerates
and diffs them on Linux, so Windows contributors do not need to run it.

Two demos -- ``howto/multibar`` and ``readme/multibar`` -- are excluded from
that diff (``Demo.drift_check = False`` in ``docs/examples/_registry.py``):
``MultiBar`` renders from a background thread that races the main thread's
updates, so how many redraws land before both bars finish is a real OS
thread-scheduling outcome, not something this script can pin down. ``--check``
prints exactly which demos it skipped and why on every run rather than
silently passing over them. If you change either demo, regenerate its SVG
(``python scripts/render_demos.py --only readme/multibar``, for instance) and
hand-verify the result instead of relying on ``--check``.

Adding an example
~~~~~~~~~~~~~~~~~~

1. Write ``docs/examples/<section>/<name>.py`` with a module docstring, a
   ``main()`` function, and no terminal-forcing arguments.
2. Register it in ``docs/examples/_registry.py``.
3. Run ``python scripts/render_demos.py --only <section>/<name>``.
4. Reference it from a page with ``.. demo:: <section>/<name>``.

``tests/test_docs_examples.py`` fails if an example exists without a registry
entry or vice versa, and ``tox -e docs-demos`` fails if a committed animation is
stale.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/WoLpH/python-progressbar/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `python-progressbar` for local development.

1. Fork the `python-progressbar` repo on GitHub.
2. Clone your fork locally::

    $ git clone --branch develop git@github.com:your_name_here/python-progressbar.git

3. Install your local copy into a virtualenv. Assuming you have `uv` installed, this is how you set up your fork for local development::

    $ cd progressbar/
    $ uv sync

4. Create a branch for local development with `git-flow-avh`_::

    $ git-flow feature start name-of-your-bugfix-or-feature

   Or without git-flow:

    $ git checkout -b feature/name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass flake8 and the tests, including testing other Python versions with tox::

    $ flake8 progressbar tests
    $ py.test
    $ tox

   To get flake8 and tox, just pip install them into your virtualenv using the requirements file.

    $ pip install -r tests/requirements.txt

6. Commit your changes and push your branch to GitHub with `git-flow-avh`_::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git-flow feature publish

   Or without git-flow:

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push -u origin feature/name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 2.7, 3.3, and for PyPy. Check
   https://travis-ci.org/WoLpH/python-progressbar/pull_requests
   and make sure that the tests pass for all supported Python versions.

Tips
----

To run a subset of tests::

	$ py.test tests/some_test.py

.. _git-flow-avh: https://github.com/petervanderdoes/gitflow
