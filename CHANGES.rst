=========
Changelog
=========

Unreleased
----------

The ``progressbar`` and ``bar`` commands, and ``python -m progressbar``,
now exit with status 130 after Ctrl-C interrupts a transfer. Previously
they exited with status 0. Scripts that check the exit status can now
distinguish an interrupted transfer from a completed copy.

For the most recent changes to the Python Progressbar please look at the Git
releases or the commit log:

 - https://github.com/WoLpH/python-progressbar/releases
 - https://github.com/WoLpH/python-progressbar/commits/develop

Hint: the ``...`` button on a commit shows the full change message.
