======================================
Run a batch in parallel with progress
======================================

One call runs a function over a batch of items -- on threads,
processes, or asyncio -- and renders a live progress bar while it
happens:

.. code-block:: python

    import progressbar

    results = progressbar.map(fetch, urls, workers=8)

``progressbar.map`` mirrors the builtin ``map``: results come back in
input order, multiple iterables zip (``progressbar.map(pow, bases,
exps)``), and the bar counts completed items. The bar keeps animating
-- ETA, timers, spinners -- even while long tasks are running with
nothing finishing.

Choosing where the work runs
============================

.. code-block:: python

    # Threads (default): I/O-bound work, no pickling requirements.
    progressbar.map(fetch, urls, workers=8)

    # Processes: CPU-bound work; fn and items must be picklable and
    # fn must be a module-level function.
    progressbar.map(crunch, files, pool='process')

    # tqdm-style spellings of the same two calls:
    progressbar.thread_map(fetch, urls)
    progressbar.process_map(crunch, files)

    # An executor you already have (never shut down for you):
    progressbar.map(fetch, urls, pool=my_executor)

Process pools accept the executor construction keywords you would pass
to ``ProcessPoolExecutor`` -- ``initializer``/``initargs`` for
per-worker setup (database connections, loaded models),
``mp_context``, and ``max_tasks_per_child`` (Python 3.11+). Thread
pools accept ``thread_name_prefix``. On Python 3.14+,
``pool='interpreter'`` runs on an ``InterpreterPoolExecutor``.

For many small items on a process pool, items are automatically
submitted in chunks to amortize the per-task overhead (the bar then
advances a chunk at a time); pass ``chunksize=`` to tune it.

Streaming results as they arrive
================================

.. code-block:: python

    # Input order, lazily -- multiprocessing.Pool.imap semantics:
    for result in progressbar.imap(fetch, urls, workers=8):
        handle(result)

    # Completion order, as (item, result) pairs -- the pair restores
    # the correspondence that completion order loses:
    for url, result in progressbar.imap_unordered(fetch, urls):
        print(f'{url} done')

Breaking out of either loop cancels the not-yet-submitted work and
shuts the run down. For deterministic cleanup wrap the iterator in
``contextlib.closing`` (``contextlib.aclosing`` for the async
variants).

Async code
==========

.. code-block:: python

    # fn may be async -- or plain sync, which runs via asyncio.to_thread:
    results = await progressbar.amap(fetch, urls, concurrency=8)

    # Lazy variants, mirroring the sync pair:
    async for result in progressbar.aimap(fetch, urls, concurrency=8):
        ...
    async for url, result in progressbar.aimap_unordered(fetch, urls):
        ...

    # A drop-in asyncio.gather with a bar (same signature, same
    # ordering, same return_exceptions keyword):
    results = await progressbar.gather(*coroutines)

``concurrency=None`` (the default) creates every task up front, exactly
like ``asyncio.gather``; pass a limit for large batches so tasks are
created lazily in a window of that size.

Shell commands: a progress-bar'd ``xargs -P``
=============================================

.. code-block:: python

    # {} (or {item}) is replaced per item; no placeholder appends the
    # item as the last argument, like xargs:
    procs = progressbar.run('gzip -k {}', files, workers=4)

    # List and callable templates for full control:
    progressbar.run(['ffmpeg', '-i', '{}', '{}.mp4'], videos)
    progressbar.run(lambda p: ['convert', p, p.with_suffix('.png')], images)

Substitution replaces only the exact placeholder tokens -- never
``str.format`` -- so commands containing literal braces (``awk '{print
$1}'``) work, and an item containing spaces stays a single argument.
Each command's output is captured into its
:py:class:`subprocess.CompletedProcess` (so child output can't corrupt
the bar), and a non-zero exit raises
:py:class:`subprocess.CalledProcessError` by default (``check=False``
to collect exit codes instead). ``shell=True`` is available for the
string form but substitutes items into a shell command line -- only
use it with items you trust.

Sub-task bars with ``bar='multi'``
==================================

.. code-block:: python

    progressbar.map(crunch, files, workers=4, bar='multi')

Instead of one aggregate bar, a ``MultiBar`` shows an overall bar plus
one line per in-flight task, labeled with the item. Inside a worker
(threads and asyncio), ``progressbar.current_task_bar()`` returns that
task's own bar for sub-progress:

.. code-block:: python

    def crunch(path):
        bar = progressbar.current_task_bar()
        for i, block in enumerate(read_blocks(path)):
            process(block)
            if bar is not None:
                bar.update(i)

``'multi'`` suits modest worker counts -- the display occupies one
terminal row per in-flight task plus one for the total. Process
workers can't reach their bar this way yet
(``current_task_bar()`` returns ``None`` there): the bar object cannot
cross the process boundary in this release.

Errors, timeouts and Ctrl-C
===========================

.. code-block:: python

    # Default: fail fast. First exception cancels the pending work and
    # re-raises; running tasks finish first.
    progressbar.map(crunch, files)

    # Collect instead: exceptions come back in place of results.
    results = progressbar.map(crunch, files, on_error='return')
    for item, result in zip(files, results):
        if isinstance(result, Exception):
            print(f'{item} failed: {result}')

    # An overall deadline; expiry cancels pending work and raises
    # TimeoutError without waiting for stragglers.
    progressbar.map(crunch, files, timeout=60)

On ``KeyboardInterrupt`` the pending work is cancelled, the bar's
final state is left on its own line, and the interrupt re-raises --
no garbled terminal. One honest limitation applies everywhere:
*running* tasks cannot be killed. A cancelled process task runs to
completion in the background, and a sync function inside ``amap`` is
abandoned in its thread, not interrupted.

Reusing a pool across batches
=============================

.. code-block:: python

    with progressbar.Pool(8) as pool:            # Pool(8, 'process') for processes
        thumbnails = pool.map(thumbnail, images)
        uploads = pool.map(upload, thumbnails)
        pool.run('touch {}', markers)

    async with progressbar.AsyncPool(8) as pool:
        results = await pool.map(fetch, urls)

Constructor keywords (``bar=``, ``on_error=``, ...) become per-call
defaults; the executor is created lazily on first use and
``pool.executor`` exposes it for direct ``submit()`` calls.

The decorator spelling
======================

.. code-block:: python

    @progressbar.parallel(workers=4, pool='process')
    def crunch(path): ...

    crunch(one_path)      # still an ordinary call
    crunch.map(paths)     # parallel + bar, decorator config applied
    await crunch.amap(paths)

The decorator needs a plain module-level function (that's what
``pool='process'`` can pickle); it returns the same function object
with ``.map``/``.imap``/``.imap_unordered``/``.starmap``/``.amap``/
``.aimap``/``.aimap_unordered`` attached.

Progress for futures you already have
=====================================

.. code-block:: python

    futures = [executor.submit(work, item) for item in items]
    for future in progressbar.as_completed(futures):
        handle(future.result())

A superset of :py:func:`concurrent.futures.as_completed` -- same
yield order and ``timeout`` behavior, plus the bar.

Semantics worth knowing
=======================

- **Bar options pass through.** Every verb forwards unknown keywords
  to the bar: ``prefix=``/``desc=``, ``widgets=``, ``max_value=``, ...
  A typo raises ``TypeError`` instead of being silently ignored.
- **Bar modes.** ``bar='plain'`` (default), ``bar='multi'``,
  ``bar=False`` (run silently), or pass your own configured
  ``ProgressBar``/``MultiBar`` instance to be driven.
- **One poll knob.** ``poll_interval`` (default 0.1s) is both how
  often the coordinator wakes and how often the bar redraws with no
  progress -- the keep-alive cadence.
- **Bounded memory.** Items are pulled from the input lazily and at
  most ``buffersize`` tasks (default ``4 × workers``) are unfinished
  at once, so million-item and generator inputs run in flat memory.
  This deviates deliberately from ``Executor.map(buffersize=None)``
  on Python 3.14, where ``None`` means unbounded.
- **imap_unordered yields pairs.** ``multiprocessing.Pool``'s version
  yields bare results; ours yields ``(item, result)`` because
  completion order loses the correspondence.
- **Totals.** ``len()`` where available, ``operator.length_hint``
  otherwise; without either the bar runs in unknown-length mode.
