##############################################################################
progressbar2
##############################################################################

A typed terminal progress bar library for Python. It handles custom
widgets, clean output around prints and logs, multiple concurrent bars,
unknown-length progress, and pipe-friendly CLI usage.

.. image:: https://github.com/WoLpH/python-progressbar/actions/workflows/main.yml/badge.svg
    :alt: python-progressbar test status
    :target: https://github.com/WoLpH/python-progressbar/actions

.. image:: https://coveralls.io/repos/WoLpH/python-progressbar/badge.svg?branch=master
    :alt: coverage status
    :target: https://coveralls.io/r/WoLpH/python-progressbar?branch=master

Install
==============================================================================

.. code:: sh

    pip install progressbar2

Quick start
==============================================================================

.. code:: python

    import time
    import progressbar

    for item in progressbar.progressbar(range(100), desc='Loading'):
        time.sleep(0.02)

Try it in your browser
==============================================================================

Every example in the `documentation <https://progressbar-2.readthedocs.io/en/latest/>`_
runs live in the page. Press **Run** on any code block, no install required.

Progress with clean logs
==============================================================================

.. image:: https://raw.githubusercontent.com/wolph/python-progressbar/develop/docs/_static/demos/readme-hero.svg
    :alt: progressbar2 showing clean progress output with logs

.. code:: python

    """A build log printing above a progress bar without corrupting it."""

    from __future__ import annotations

    import time

    import progressbar

    STEPS = 24


    def main() -> None:
        with progressbar.ProgressBar(
            max_value=STEPS,
            prefix='Build ',
            redirect_stdout=True,
        ) as bar:
            for step in range(STEPS):
                if step in {8, 16}:
                    print(f'log: completed step {step}')
                bar.update(step + 1)
                time.sleep(0.005)


    if __name__ == '__main__':
        main()

Multiple bars
==============================================================================

.. image:: https://raw.githubusercontent.com/wolph/python-progressbar/develop/docs/_static/demos/readme-multibar.svg
    :alt: multiple progress bars updating together

.. code:: python

    """Two named bars progressing at different rates in one terminal."""

    from __future__ import annotations

    import sys
    import time

    import progressbar

    STEPS = 24


    def main() -> None:
        with progressbar.MultiBar(fd=sys.stdout) as multibar:
            build = multibar['build']
            test = multibar['test']
            build.max_value = STEPS
            test.max_value = STEPS
            for step in range(STEPS):
                build.update(step + 1)
                test.update(min(STEPS, max(0, round((step - 3) * 1.2))))
                time.sleep(0.005)

            # Reaching max_value doesn't finish a bar -- only finish() does.
            # A MultiBar waits for every bar to report finished() before its
            # context manager can exit, so without these calls the block
            # above would hang forever on exit.
            build.finish()
            test.finish()


    if __name__ == '__main__':
        main()

Unknown length and animated bars
==============================================================================

.. image:: https://raw.githubusercontent.com/wolph/python-progressbar/develop/docs/_static/demos/readme-unknown-length.svg
    :alt: unknown length progress with an animated marker

.. code:: python

    """A bar for work whose total is not known up front."""

    from __future__ import annotations

    import time

    import progressbar


    def main() -> None:
        with progressbar.ProgressBar(
            max_value=progressbar.UnknownLength,
        ) as bar:
            for value in range(0, 120, 10):
                bar.update(value)
                time.sleep(0.005)


    if __name__ == '__main__':
        main()

CLI usage
==============================================================================

.. code:: sh

    progressbar --progress --timer --eta --rate --bytes input.bin -o output.bin

Known terminal caveats
==============================================================================

* JetBrains IDEs need "Enable terminal in output console" for advanced
  terminal behavior such as ``MultiBar``.
* IDLE does not support terminal progress bars.
* Jupyter buffers stdout; call ``sys.stdout.flush()`` when output appears late.

Project history
==============================================================================

progressbar2 is based on the old Python progressbar package that was published
on the now defunct Google Code. Since that project was completely abandoned by
its developer and the developer did not respond to email, I decided to fork the
package.

This package is still backwards compatible with the original progressbar
package so you can use it as a drop-in replacement for existing projects.

Links
==============================================================================

* Documentation: https://progressbar-2.readthedocs.org/en/latest/
* Source: https://github.com/WoLpH/python-progressbar
* Bug reports: https://github.com/WoLpH/python-progressbar/issues
* Package homepage: https://pypi.python.org/pypi/progressbar2
