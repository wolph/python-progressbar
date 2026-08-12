====================
``progressbar`` CLI
====================

Installing ``progressbar2`` installs a ``progressbar`` console script
(:py:func:`progressbar.__main__.main`). It reads from stdin (or one or more
files), writes the same bytes through to stdout (or a file), and draws a
progress bar on stderr while it does -- a small, Python-native reimplementation
of the ``pv`` ("pipe viewer") command. Per its own ``--help`` text it is
"functional but not yet feature complete": most flags below are wired up,
but a block of ``pv``-compatible flags is accepted for compatibility and
currently has no effect. Each is marked in the tables below.

Worked example
================

.. code:: sh

    curl -sL https://example.com/bigfile.iso | progressbar --progress --bytes --rate > bigfile.iso

Reading from stdin means the total size isn't known up front, so the bar
falls back to a count-only display (no percentage, no bar fill) until it
finishes. If you know the size in advance -- from a ``Content-Length``
header, for instance -- pass it explicitly so the bar can show a real
percentage and ETA:

.. code:: sh

    curl -sL https://example.com/bigfile.iso | progressbar --progress --bytes --eta --size 128m > bigfile.iso

The bar itself always writes to stderr, so it never ends up mixed into the
piped stdout data; the equivalent file-based invocation from the project
README is:

.. code:: sh

    progressbar --progress --timer --eta --rate --bytes input.bin -o output.bin

Positional and I/O arguments
=============================

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - What it does
   * - ``input``
     - One or more input file paths. Omitted or ``-`` reads stdin (the
       default). Multiple files are concatenated in order.
   * - ``-o``, ``--output OUTPUT``
     - Output file path. Defaults to ``-`` (stdout).
   * - ``-s``, ``--size SIZE``
     - Assume the total input size is ``SIZE`` instead of ``stat()``-ing the
       input files (the only way to get a percentage/ETA when reading from
       a pipe). Accepts a plain byte count or a ``k``/``m``/``g``/``t``/``p``
       suffix (powers of 1024), or ``@path`` to read another file's size.
   * - ``-l``, ``--line-mode``
     - Count and transfer lines instead of bytes; input is read and written
       as text rather than binary.
   * - ``-B``, ``--buffer-size BYTES``
     - Read/write in chunks of ``BYTES`` instead of the 1024-byte default.
       Accepts the same size suffixes as ``--size``.

Display switches
==================

Toggle which widgets appear. With none of these given, the bar falls back
to a built-in default set (percentage/bar/timer/speed when the size is
known, count/size/timer otherwise).

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Flag
     - What it does
   * - ``-p``, ``--progress``
     - Show the percentage and bar widgets.
   * - ``-t``, ``--timer``
     - Show elapsed time.
   * - ``-e``, ``--eta``
     - Show an adaptive ETA (:py:class:`~progressbar.widgets.AdaptiveETA`).
   * - ``-I``, ``--fineta``
     - Show the ETA as an absolute local time of arrival instead of a
       countdown.
   * - ``-r``, ``--rate``
     - Show a transfer-speed widget.
   * - ``-a``, ``--average-rate``
     - Also shows the transfer-speed widget. It currently selects the exact
       same widget as ``--rate`` -- there is no separate averaging window
       applied yet; ``--average-rate-window`` (below) is accepted but not
       currently wired to it.
   * - ``-b``, ``--bytes``
     - Show the running byte/line count.
   * - ``-n``, ``--numeric``
     - Print one line per update instead of overwriting the current line
       (equivalent to ``ProgressBar(line_breaks=True)`` -- see
       :doc:`../explanation/terminal-detection`).
   * - ``-q``, ``--quiet``
     - Suppress all progress output (uses
       :py:class:`~progressbar.bar.NullBar` internally).

Accepted, not yet wired up
----------------------------

These parse without error but have no observable effect today: ``-8``/
``--bits``, ``-T``/``--buffer-percent``, ``-A``/``--last-written``, ``-F``/
``--format``.

Output modifiers
===================

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Flag
     - What it does
   * - ``-f``, ``--force``
     - Accepted, not yet wired up.
   * - ``-c``, ``--cursor``
     - Accepted, not yet wired up.
   * - ``-W``, ``--wait``
     - Accepted, not yet wired up.
   * - ``-D``, ``--delay-start DELAY_START``
     - Accepted, not yet wired up.
   * - ``-0``, ``--null``
     - Accepted, not yet wired up.
   * - ``-i``, ``--interval INTERVAL``
     - Accepted, not yet wired up.
   * - ``-m``, ``--average-rate-window AVERAGE_RATE_WINDOW``
     - Accepted, not yet wired up (see ``--average-rate`` above).
   * - ``-w``, ``--width WIDTH``
     - Accepted, not yet wired up.
   * - ``-H``, ``--height HEIGHT``
     - Accepted, not yet wired up.
   * - ``-N``, ``--name NAME``
     - Accepted, not yet wired up.

Data transfer modifiers
==========================

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Flag
     - What it does
   * - ``-L``, ``--rate-limit RATE``
     - Throttle transfer to ``RATE`` bytes per second (same size suffixes
       as ``--size``). Implemented by sleeping between chunks based on
       elapsed time vs. expected time at the target rate.
   * - ``-C``, ``--no-splice``
     - Accepted, not yet wired up.
   * - ``-E``, ``--skip-errors``
     - Accepted, not yet wired up.
   * - ``-Z``, ``--error-skip-block SIZE``
     - Accepted, not yet wired up.
   * - ``-S``, ``--stop-at-size``
     - Accepted, not yet wired up.
   * - ``-Y``, ``--sync``
     - Accepted, not yet wired up.
   * - ``-K``, ``--direct-io``
     - Accepted, not yet wired up.
   * - ``-X``, ``--discard``
     - Accepted, not yet wired up.
   * - ``-d``, ``--watchfd FD``
     - Accepted, not yet wired up.
   * - ``-R``, ``--remote PID``
     - Accepted, not yet wired up.

General options
==================

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Flag
     - What it does
   * - ``-P``, ``--pidfile FILE``
     - Accepted, not yet wired up.
   * - ``-h``, ``--help``
     - Show the built-in ``argparse`` help and exit.
