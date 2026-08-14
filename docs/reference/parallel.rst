==================
Parallel execution
==================

The parallel verb family runs a callable over a batch of items -- on
threads, processes, or asyncio -- with a progress bar. The how-to
guide (:doc:`../howto/parallel-execution`) shows the idioms; this page
is the API reference.

The shared keywords
===================

Every verb accepts (where applicable):

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Keyword
     - What it does
   * - ``workers``
     - Pool size for the sync verbs. Default: the executor's own
       default (``min(32, cpus + 4)`` threads, ``cpus`` processes).
       Accepted as an alias for ``concurrency`` on the async verbs.
   * - ``concurrency``
     - Async verbs: maximum in-flight tasks. ``None`` (default)
       creates every task up front, like ``asyncio.gather``.
   * - ``pool``
     - ``'thread'`` (default), ``'process'``, ``'interpreter'``
       (Python 3.14+), or an existing
       :py:class:`concurrent.futures.Executor` instance (used as-is,
       never shut down for you).
   * - ``bar``
     - ``'plain'`` (one aggregate bar, default), ``'multi'`` (a
       :py:class:`~progressbar.multi.MultiBar` with one sub-bar per
       in-flight task), ``False`` (no output), or a configured
       ``ProgressBar``/``MultiBar`` instance to drive.
   * - ``on_error``
     - ``'raise'`` (default): first failure cancels pending work and
       re-raises. ``'return'``: exceptions appear in place of their
       results; ``KeyboardInterrupt``/``SystemExit`` still propagate.
   * - ``chunksize``
     - Items per task. Default: 1 on threads; automatic on process
       and interpreter pools (about 16 chunks per worker, capped at
       1000). The bar advances per chunk.
   * - ``buffersize``
     - Maximum unfinished submitted tasks (sync verbs). Default
       ``max(4 × workers, 16)``; keeps memory flat on huge or lazy
       inputs.
   * - ``timeout``
     - Overall deadline in seconds. Expiry cancels pending work and
       raises ``TimeoutError`` without waiting for running tasks.
   * - ``poll_interval``
     - Seconds between coordinator wakeups *and* no-progress bar
       redraws (default 0.1) -- one knob for both.
   * - ``initializer``, ``initargs``, ``mp_context``,
       ``max_tasks_per_child``, ``thread_name_prefix``
     - Forwarded verbatim to the executor constructor
       (``max_tasks_per_child`` needs Python 3.11+; each option is
       validated against the pool kind).
   * - ``**bar_kwargs``
     - Anything else goes to the bar: ``prefix=``/``desc=``,
       ``suffix=``, ``widgets=``, ``max_value=``, ... Unknown names
       raise ``TypeError``.

Sync verbs
==========

.. autofunction:: progressbar.map
   :no-index:
.. autofunction:: progressbar.imap
   :no-index:
.. autofunction:: progressbar.imap_unordered
   :no-index:
.. autofunction:: progressbar.starmap
   :no-index:
.. autofunction:: progressbar.thread_map
   :no-index:
.. autofunction:: progressbar.process_map
   :no-index:
.. autofunction:: progressbar.as_completed
   :no-index:
.. autofunction:: progressbar.run
   :no-index:

Async verbs
===========

.. autofunction:: progressbar.amap
   :no-index:
.. autofunction:: progressbar.aimap
   :no-index:
.. autofunction:: progressbar.aimap_unordered
   :no-index:
.. autofunction:: progressbar.gather
   :no-index:

Reusable layers
===============

.. autoclass:: progressbar.Pool
   :members:
   :member-order: bysource
   :no-index:

.. autoclass:: progressbar.AsyncPool
   :members:
   :member-order: bysource
   :no-index:

.. autofunction:: progressbar.parallel
   :no-index:
.. autofunction:: progressbar.current_task_bar
   :no-index:

.. autoclass:: progressbar.ParallelFunction
   :members:
   :no-index:
