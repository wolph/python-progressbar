=========
Changelog
=========

Unreleased
----------

The ``progressbar`` and ``bar`` commands, and ``python -m progressbar``,
now exit with status 130 after Ctrl-C interrupts a transfer. Previously
they exited with status 0. Scripts that check the exit status can now
distinguish an interrupted transfer from a completed copy.

Captured output now survives a drain failure on the other stream, and
unwrapping restores the original stream even when its capture buffer is
closed. Built-in ``StringIO`` capture writes and drains remain atomic.
Caller-replaced buffers keep their method overrides, which run without
stream locks. As in 4.6.0, callers synchronise concurrent writes and drains
on those custom buffers.

Specialised format templates retain their escaping and result types.
Their field paths, including nested format specifications, are checked
before calling the application's formatter.

MultiBar expiry keeps a replacement registered under the same label.
Assignment, update, in-place union and ordinary removal methods share its
membership guard. Lifecycle tracking uses bar identity without calling
application hash or equality methods, and the guard resets after fork.
Direct calls to ``dict`` base-class mutation methods
bypass that guard and are not supported during concurrent rendering.

For the most recent changes to the Python Progressbar please look at the Git
releases or the commit log:

 - https://github.com/WoLpH/python-progressbar/releases
 - https://github.com/WoLpH/python-progressbar/commits/develop

Hint: the ``...`` button on a commit shows the full change message.
