"""The `concurrent.futures` engine behind the sync parallel verbs.

One generator -- `execute` -- owns the whole coordination pattern:
windowed submission, a done-queue that costs O(1) per completion, and
poll-timeout ticks that keep the bar animating while nothing finishes.
Every public sync verb (`map`, and its siblings) is a thin consumer of
`execute`'s completion stream.
"""

from __future__ import annotations

import concurrent.futures
import functools
import inspect
import queue
import sys
import time
import typing

from . import (
    _common,
    _display,
)

#: One completion event: (item index, argument tuple, ok, result/error).
Completion = tuple[int, _common.ItemArgs, bool, typing.Any]

#: `pool=` values that name an executor kind rather than an instance.
_POOL_KINDS: frozenset[str] = frozenset({'thread', 'process', 'interpreter'})

#: Default seconds between coordinator wakeups; doubles as the bar's
#: redraw interval (one knob -- see the keep-alive contract).
DEFAULT_POLL_INTERVAL: float = 0.1


def _pool_kind(pool: typing.Any) -> str:
    """Map a `pool=` argument to 'thread'/'process'/'interpreter'."""
    if isinstance(pool, str):
        return pool
    if isinstance(pool, concurrent.futures.ProcessPoolExecutor):
        return 'process'
    return 'thread'


def _adopt_executor(
    pool: concurrent.futures.Executor,
    workers: int | None,
    constructor_kwargs: dict[str, typing.Any],
) -> tuple[concurrent.futures.Executor, bool, int]:
    """Adopt a caller-owned executor; reject construction kwargs."""
    configured: list[str] = [
        name for name, value in constructor_kwargs.items() if value
    ]
    if configured:
        raise ValueError(
            f'{configured!r} configure a new executor and cannot be '
            f'combined with an existing executor instance'
        )
    return pool, False, _common.resolve_workers(workers, _pool_kind(pool))


def _thread_executor(
    workers: int,
    initializer: typing.Callable[..., None] | None,
    initargs: tuple[typing.Any, ...],
    thread_name_prefix: str,
) -> concurrent.futures.Executor:
    """Build the owned thread pool."""
    return concurrent.futures.ThreadPoolExecutor(
        max_workers=workers,
        thread_name_prefix=thread_name_prefix,
        initializer=initializer,
        initargs=initargs,
    )


def _process_executor(
    workers: int,
    initializer: typing.Callable[..., None] | None,
    initargs: tuple[typing.Any, ...],
    mp_context: typing.Any,
    max_tasks_per_child: int | None,
) -> concurrent.futures.Executor:
    """Build the owned process pool."""
    process_kwargs: dict[str, typing.Any] = {
        'max_workers': workers,
        'mp_context': mp_context,
        'initializer': initializer,
        'initargs': initargs,
    }
    if max_tasks_per_child is not None:
        # Assignment before the version gate so the line is reachable
        # (and measured) on every Python; on 3.10 the raise below
        # discards the dict anyway.
        process_kwargs['max_tasks_per_child'] = max_tasks_per_child
        if sys.version_info < (3, 11):  # pragma: no cover - version gate
            raise ValueError('max_tasks_per_child requires Python 3.11+')
    return concurrent.futures.ProcessPoolExecutor(**process_kwargs)


def _interpreter_executor(
    workers: int,
    initializer: typing.Callable[..., None] | None,
    initargs: tuple[typing.Any, ...],
) -> concurrent.futures.Executor:
    """Build the owned interpreter pool (Python 3.14+)."""
    try:
        # typed Any: the class only exists on 3.14+, so pyright has no
        # signature for it on the 3.10 floor.
        interpreter_pool: typing.Any = (
            concurrent.futures.InterpreterPoolExecutor  # type: ignore[attr-defined]
        )
    except AttributeError:  # pragma: no cover - version gate (<=3.13)
        raise ValueError('pool="interpreter" requires Python 3.14+') from None
    return interpreter_pool(  # pragma: no cover - reachable on 3.14+ only
        max_workers=workers,
        initializer=initializer,
        initargs=initargs,
    )


def resolve_executor(
    pool: typing.Any,
    workers: int | None,
    *,
    initializer: typing.Callable[..., None] | None,
    initargs: tuple[typing.Any, ...],
    mp_context: typing.Any,
    max_tasks_per_child: int | None,
    thread_name_prefix: str,
) -> tuple[concurrent.futures.Executor, bool, int]:
    """Create (or adopt) the executor for one run.

    Args:
        pool: ``'thread'`` | ``'process'`` | ``'interpreter'`` (3.14+)
            or an existing `concurrent.futures.Executor` instance.
        workers: Pool size; `None` uses the executor defaults.
        initializer: Per-worker setup callable, forwarded verbatim.
        initargs: Arguments for `initializer`.
        mp_context: `multiprocessing` context for process pools.
        max_tasks_per_child: Worker recycling limit (3.11+).
        thread_name_prefix: Thread pool naming, forwarded verbatim.

    Returns:
        ``(executor, owned, effective_workers)`` -- `owned` is whether
        this run created (and must shut down) the executor.

    Raises:
        ValueError: Unknown `pool` string, construction kwargs combined
            with an executor instance or the wrong pool kind, or a
            version-gated option on an unsupported Python.
    """
    if isinstance(pool, concurrent.futures.Executor):
        return _adopt_executor(
            pool,
            workers,
            {
                'initializer': initializer,
                'initargs': initargs,
                'mp_context': mp_context,
                'max_tasks_per_child': max_tasks_per_child,
                'thread_name_prefix': thread_name_prefix,
            },
        )
    if pool not in _POOL_KINDS:
        raise ValueError(
            f'pool={pool!r} is not valid: expected "thread", "process", '
            f'"interpreter" or a concurrent.futures.Executor instance'
        )
    if pool != 'process' and (
        mp_context is not None or max_tasks_per_child is not None
    ):
        raise ValueError(
            'mp_context/max_tasks_per_child only apply to process pools'
        )
    if pool != 'thread' and thread_name_prefix:
        raise ValueError('thread_name_prefix only applies to thread pools')

    effective_workers: int = _common.resolve_workers(workers, pool)
    executor: concurrent.futures.Executor
    if pool == 'thread':
        executor = _thread_executor(
            effective_workers, initializer, initargs, thread_name_prefix
        )
    elif pool == 'interpreter':
        executor = _interpreter_executor(
            effective_workers, initializer, initargs
        )
    else:
        executor = _process_executor(
            effective_workers,
            initializer,
            initargs,
            mp_context,
            max_tasks_per_child,
        )
    return executor, True, effective_workers


def _indexed_chunks(
    iterables: tuple[typing.Iterable[typing.Any], ...],
    chunksize: int,
) -> typing.Iterator[tuple[int, list[_common.ItemArgs]]]:
    """Yield ``(first item index, chunk)`` pairs, consuming lazily."""
    index: int = 0
    for chunk in _common.iter_chunks(iterables, chunksize):
        yield index, chunk
        index += len(chunk)


class _Run:
    """State and coordination for one `execute` invocation.

    Split from `execute` so each concern -- submission, completion
    handling, deadline, shutdown -- stays a small method; `execute`
    itself only owns the generator's try/finally lifecycle.
    """

    fn: typing.Callable[..., typing.Any]
    kind: str
    total: typing.Any
    on_error: str
    catch: bool
    single: bool
    window: int
    timeout: float | None
    poll_interval: float
    deadline: float | None
    executor: concurrent.futures.Executor
    owned: bool
    display: _display.Display
    done: queue.SimpleQueue[concurrent.futures.Future[typing.Any]]
    in_flight: dict[
        concurrent.futures.Future[typing.Any],
        tuple[int, list[_common.ItemArgs], int],
    ]
    chunk_source: typing.Iterator[tuple[int, list[_common.ItemArgs]]]
    seq: int

    def __init__(
        self,
        fn: typing.Callable[..., typing.Any],
        iterables: tuple[typing.Iterable[typing.Any], ...],
        *,
        workers: int | None,
        pool: typing.Any,
        bar: typing.Any,
        on_error: str,
        chunksize: int | None,
        buffersize: int | None,
        timeout: float | None,
        poll_interval: float,
        initializer: typing.Callable[..., None] | None,
        initargs: tuple[typing.Any, ...],
        mp_context: typing.Any,
        max_tasks_per_child: int | None,
        thread_name_prefix: str,
        bar_kwargs: dict[str, typing.Any],
    ) -> None:
        """Validate the configuration and set up executor and display."""
        if inspect.iscoroutinefunction(fn):
            raise TypeError(
                f'{fn!r} is a coroutine function; use progressbar.amap() '
                f'-- the sync verbs cannot await it'
            )
        if on_error not in ('raise', 'return'):
            raise ValueError(
                f"on_error={on_error!r} is not valid: expected 'raise' "
                f"or 'return'"
            )
        _common.validate_bar_kwargs(bar_kwargs)

        self.fn = fn
        self.kind = _pool_kind(pool)
        self.total = _common.detect_total(iterables)
        self.on_error = on_error
        self.catch = on_error == 'return'
        self.single = len(iterables) == 1
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.deadline = None if timeout is None else time.monotonic() + timeout
        self.executor, self.owned, effective_workers = resolve_executor(
            pool,
            workers,
            initializer=initializer,
            initargs=initargs,
            mp_context=mp_context,
            max_tasks_per_child=max_tasks_per_child,
            thread_name_prefix=thread_name_prefix,
        )
        if chunksize is None:
            chunksize = (
                _common.auto_chunksize(self.total, effective_workers)
                if self.kind in ('process', 'interpreter')
                else 1
            )
        self.window = (
            buffersize
            if buffersize is not None
            else _common.default_buffersize(effective_workers)
        )
        self.display = _display.make_display(
            bar,
            total=self.total,
            poll_interval=poll_interval,
            bar_kwargs=bar_kwargs,
        )
        self.done = queue.SimpleQueue()
        self.in_flight = {}
        self.chunk_source = _indexed_chunks(iterables, chunksize)
        self.seq = 0

    def completions(self) -> typing.Iterator[Completion]:
        """Drive the run, yielding per-item events in completion order."""
        self.display.start(self.total)
        while len(self.in_flight) < self.window and self._submit_one():
            pass
        while self.in_flight:
            self._check_deadline()
            future = self._next_done()
            if future is not None:
                yield from self._handle(future)

    def _submit_one(self) -> bool:
        """Submit the next chunk; `False` when the input is exhausted."""
        indexed: tuple[int, list[_common.ItemArgs]] | None = next(
            self.chunk_source, None
        )
        if indexed is None:
            return False
        start_index, chunk = indexed
        self.seq += 1
        label: str = str(_common.item_of(chunk[0], self.single))
        task_bar = self.display.task_started(self.seq, label)
        inner: typing.Callable[[], list[tuple[bool, typing.Any]]] = (
            functools.partial(_common.run_chunk, self.fn, chunk, self.catch)
        )
        if task_bar is not None and self.kind == 'thread':
            # Threads share our address space, so the worker can update
            # its sub-bar through `current_task_bar()`. Process (and
            # interpreter) workers cannot -- the bar object does not
            # survive pickling; see the phase-2 note in the docs.
            inner = _common.with_task_bar(task_bar, inner)
        future: concurrent.futures.Future[typing.Any] = self.executor.submit(
            inner
        )
        self.in_flight[future] = (start_index, chunk, self.seq)
        future.add_done_callback(self.done.put)
        return True

    def _next_done(
        self,
    ) -> concurrent.futures.Future[typing.Any] | None:
        """Wait one poll for a completion; tick the display on none."""
        try:
            return self.done.get(timeout=self.poll_interval)
        except queue.Empty:
            self.display.tick()
            return None

    def _check_deadline(self) -> None:
        """Raise once the overall `timeout` budget is spent."""
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise concurrent.futures.TimeoutError(
                f'parallel execution exceeded timeout={self.timeout}'
            )

    def _handle(
        self, future: concurrent.futures.Future[typing.Any]
    ) -> typing.Iterator[Completion]:
        """Turn one finished future into per-item completion events."""
        start_index, chunk, chunk_seq = self.in_flight.pop(future)
        error: BaseException | None = future.exception()
        if error is not None:
            # Fail-fast fn errors (catch=False), machinery errors (e.g.
            # BrokenProcessPool, unpicklable results) and
            # KeyboardInterrupt/SystemExit escaping run_chunk all land
            # here: never silently, always raised.
            self.display.task_finished(chunk_seq, ok=False)
            raise error
        outcomes: list[tuple[bool, typing.Any]] = future.result()
        self.display.task_finished(chunk_seq, ok=all(ok for ok, _ in outcomes))
        self.display.advance(len(chunk))
        self._submit_one()
        for offset, (ok, value) in enumerate(outcomes):
            yield start_index + offset, chunk[offset], ok, value

    def close(self, *, interrupted: bool, success: bool) -> None:
        """Cancel leftovers and release executor and display."""
        for future in self.in_flight:
            future.cancel()
        if self.owned:
            self.executor.shutdown(wait=not interrupted, cancel_futures=True)
        self.display.finish(success=success)


def execute(
    fn: typing.Callable[..., typing.Any],
    iterables: tuple[typing.Iterable[typing.Any], ...],
    *,
    workers: int | None = None,
    pool: typing.Any = 'thread',
    bar: typing.Any = 'plain',
    on_error: str = 'raise',
    chunksize: int | None = None,
    buffersize: int | None = None,
    timeout: float | None = None,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    initializer: typing.Callable[..., None] | None = None,
    initargs: tuple[typing.Any, ...] = (),
    mp_context: typing.Any = None,
    max_tasks_per_child: int | None = None,
    thread_name_prefix: str = '',
    **bar_kwargs: typing.Any,
) -> typing.Iterator[Completion]:
    """Run `fn` over zipped `iterables`, yielding completion events.

    The single sync coordination loop. Yields one ``(index, args, ok,
    value)`` tuple per item in *completion order*; consumers impose
    their own ordering (`map` collects by index, `imap` holds back,
    `imap_unordered` passes through).

    Cleanup is the generator's ``finally``: closing this generator (an
    early ``break`` in a consumer) cancels unsubmitted work and shuts
    down an owned executor. Running tasks cannot be interrupted -- they
    finish in the background of the shutdown; on `KeyboardInterrupt`
    the shutdown does not wait for them.

    Raises:
        TypeError: `fn` is a coroutine function (belongs to `amap`), or
            an unknown bar keyword was passed.
        ValueError: `on_error` is not ``'raise'``/``'return'``, or the
            executor configuration is invalid.
        concurrent.futures.TimeoutError: The overall `timeout` expired;
            pending work is cancelled first.
    """
    run: _Run = _Run(
        fn,
        iterables,
        workers=workers,
        pool=pool,
        bar=bar,
        on_error=on_error,
        chunksize=chunksize,
        buffersize=buffersize,
        timeout=timeout,
        poll_interval=poll_interval,
        initializer=initializer,
        initargs=initargs,
        mp_context=mp_context,
        max_tasks_per_child=max_tasks_per_child,
        thread_name_prefix=thread_name_prefix,
        bar_kwargs=bar_kwargs,
    )
    interrupted: bool = False
    success: bool = False
    try:
        yield from run.completions()
        success = True
    except BaseException as error:
        # Ctrl-C means "stop now" and a timeout is a promise about
        # wall-clock time -- neither may block on running tasks. Plain
        # fail-fast still waits so results/streams aren't torn down
        # under a worker mid-write.
        interrupted = isinstance(
            error,
            (KeyboardInterrupt, TimeoutError, concurrent.futures.TimeoutError),
        )
        raise
    finally:
        run.close(interrupted=interrupted, success=success)


#: Keywords that configure a `Pool`'s lazily created executor rather
#: than an individual run.
_EXECUTOR_KWARG_NAMES: frozenset[str] = frozenset(
    {
        'initializer',
        'initargs',
        'mp_context',
        'max_tasks_per_child',
        'thread_name_prefix',
    }
)


class Pool:
    """A reusable executor plus per-call defaults for the sync verbs.

    The flat verbs create and destroy an executor per call; a `Pool`
    keeps one alive across calls::

        with progressbar.Pool(8) as pool:
            first = pool.map(fetch, urls)
            second = pool.map(fetch, more_urls)

    Positional shorthand: ``Pool(8)`` is eight threads, ``Pool(8,
    'process')`` eight processes. ``Pool(executor=existing)`` adopts a
    caller-owned executor (never shut down here). Every other keyword
    becomes a per-call default that individual calls can override.

    The executor is created lazily on first use, so an unused
    ``Pool(kind='process')`` spawns nothing.
    """

    _workers: int | None
    _kind: str
    _external: concurrent.futures.Executor | None
    _executor: concurrent.futures.Executor | None
    _executor_kwargs: dict[str, typing.Any]
    _defaults: dict[str, typing.Any]

    def __init__(
        self,
        workers: int | None = None,
        kind: str = 'thread',
        *,
        executor: concurrent.futures.Executor | None = None,
        **defaults: typing.Any,
    ) -> None:
        """Validate eagerly (fail fast); create nothing yet."""
        executor_kwargs: dict[str, typing.Any] = {
            name: defaults.pop(name)
            for name in list(defaults)
            if name in _EXECUTOR_KWARG_NAMES
        }
        if executor is not None:
            if workers is not None or kind != 'thread' or executor_kwargs:
                raise ValueError(
                    'workers/kind/executor-construction options cannot '
                    'be combined with an existing executor instance'
                )
        elif kind not in _POOL_KINDS:
            raise ValueError(
                f'kind={kind!r} is not valid: expected "thread", '
                f'"process" or "interpreter"'
            )
        self._workers = workers
        self._kind = kind
        self._external = executor
        self._executor = None
        self._executor_kwargs = executor_kwargs
        self._defaults = defaults

    @property
    def executor(self) -> concurrent.futures.Executor:
        """The underlying executor, created on first access."""
        if self._external is not None:
            return self._external
        if self._executor is None:
            self._executor, _owned, _workers = resolve_executor(
                self._kind,
                self._workers,
                initializer=self._executor_kwargs.get('initializer'),
                initargs=self._executor_kwargs.get('initargs', ()),
                mp_context=self._executor_kwargs.get('mp_context'),
                max_tasks_per_child=self._executor_kwargs.get(
                    'max_tasks_per_child'
                ),
                thread_name_prefix=self._executor_kwargs.get(
                    'thread_name_prefix', ''
                ),
            )
        return self._executor

    def _merged(self, kwargs: dict[str, typing.Any]) -> dict[str, typing.Any]:
        """Per-call keywords override the pool's defaults."""
        return {**self._defaults, **kwargs, 'pool': self.executor}

    def map(  # noqa: A003 - mirrors the module verb
        self,
        fn: typing.Callable[..., typing.Any],
        /,
        *iterables: typing.Iterable[typing.Any],
        **kwargs: typing.Any,
    ) -> list[typing.Any]:
        """`map` on this pool's executor; see the module `map`."""
        return map(fn, *iterables, **self._merged(kwargs))

    def imap(
        self,
        fn: typing.Callable[..., typing.Any],
        /,
        *iterables: typing.Iterable[typing.Any],
        **kwargs: typing.Any,
    ) -> typing.Generator[typing.Any, None, None]:
        """`imap` on this pool's executor; see the module `imap`."""
        return imap(fn, *iterables, **self._merged(kwargs))

    def imap_unordered(
        self,
        fn: typing.Callable[..., typing.Any],
        /,
        *iterables: typing.Iterable[typing.Any],
        **kwargs: typing.Any,
    ) -> typing.Generator[tuple[typing.Any, typing.Any], None, None]:
        """`imap_unordered` on this pool's executor; see the module verb."""
        return imap_unordered(fn, *iterables, **self._merged(kwargs))

    def starmap(
        self,
        fn: typing.Callable[..., typing.Any],
        iterable: typing.Iterable[typing.Any],
        /,
        **kwargs: typing.Any,
    ) -> list[typing.Any]:
        """`starmap` on this pool's executor; see the module `starmap`."""
        return starmap(fn, iterable, **self._merged(kwargs))

    def run(
        self,
        command: typing.Any,
        items: typing.Iterable[typing.Any],
        /,
        **kwargs: typing.Any,
    ) -> list[typing.Any]:
        """`run` a shell command per item on this pool's executor."""
        # Deferred import: _shell imports this module.
        from . import _shell

        runner = _shell.make_runner(
            command,
            **{
                name: kwargs.pop(name)
                for name in (
                    'check',
                    'capture_output',
                    'text',
                    'shell',
                    'cwd',
                    'env',
                )
                if name in kwargs
            },
        )
        return self.map(runner, items, **kwargs)

    def shutdown(
        self, wait: bool = True, *, cancel_futures: bool = False
    ) -> None:
        """Shut down the owned executor; adopted executors are spared."""
        if self._executor is not None:
            self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    def __enter__(self) -> Pool:
        """Return the pool; the executor still waits for first use."""
        return self

    def __exit__(self, *exc_info: typing.Any) -> None:
        """Shut down the owned executor, waiting for running work."""
        self.shutdown(wait=True)


def _star_call(
    fn: typing.Callable[..., typing.Any], args: typing.Any
) -> typing.Any:
    """Unpack one `starmap` argument tuple into a call (picklable)."""
    return fn(*args)


def starmap(
    fn: typing.Callable[..., typing.Any],
    iterable: typing.Iterable[typing.Any],
    /,
    **kwargs: typing.Any,
) -> list[typing.Any]:
    """`map` over pre-tupled arguments (``multiprocessing.Pool.starmap``).

    ``starmap(fn, [(1, 2), (3, 4)])`` calls ``fn(1, 2)`` and
    ``fn(3, 4)`` in parallel. See `execute` for keywords.
    """
    return map(functools.partial(_star_call, fn), iterable, **kwargs)


def thread_map(
    fn: typing.Callable[..., typing.Any],
    /,
    *iterables: typing.Iterable[typing.Any],
    **kwargs: typing.Any,
) -> list[typing.Any]:
    """`map` pinned to a thread pool (tqdm-compatible spelling)."""
    if 'pool' in kwargs:
        raise TypeError(
            "thread_map() already sets pool='thread'; use map() to pick "
            'a pool explicitly'
        )
    return map(fn, *iterables, pool='thread', **kwargs)


def process_map(
    fn: typing.Callable[..., typing.Any],
    /,
    *iterables: typing.Iterable[typing.Any],
    **kwargs: typing.Any,
) -> list[typing.Any]:
    """`map` pinned to a process pool (tqdm-compatible spelling)."""
    if 'pool' in kwargs:
        raise TypeError(
            "process_map() already sets pool='process'; use map() to "
            'pick a pool explicitly'
        )
    return map(fn, *iterables, pool='process', **kwargs)


def as_completed(
    futures: typing.Iterable[concurrent.futures.Future[typing.Any]],
    timeout: float | None = None,
    *,
    bar: typing.Any = 'plain',
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    **bar_kwargs: typing.Any,
) -> typing.Generator[concurrent.futures.Future[typing.Any], None, None]:
    """`concurrent.futures.as_completed` with a progress bar.

    A superset of the stdlib function: same yield order and `timeout`
    semantics, plus a bar counting completions (total inferred from the
    futures). The caller owns the futures -- an early ``break`` or a
    timeout never cancels them.
    """
    futures_list: list[concurrent.futures.Future[typing.Any]] = list(futures)
    display: _display.Display = _display.make_display(
        bar,
        total=len(futures_list),
        poll_interval=poll_interval,
        bar_kwargs=bar_kwargs,
    )
    done: queue.SimpleQueue[concurrent.futures.Future[typing.Any]] = (
        queue.SimpleQueue()
    )
    pending: set[concurrent.futures.Future[typing.Any]] = set(futures_list)
    deadline: float | None = (
        None if timeout is None else time.monotonic() + timeout
    )
    success: bool = False
    for future in pending:
        future.add_done_callback(done.put)
    try:
        display.start(len(futures_list))
        while pending:
            if deadline is not None and time.monotonic() > deadline:
                raise concurrent.futures.TimeoutError(
                    f'{len(pending)} (of {len(futures_list)}) futures '
                    f'unfinished within timeout={timeout}'
                )
            try:
                future = done.get(timeout=poll_interval)
            except queue.Empty:
                display.tick()
                continue
            pending.discard(future)
            display.advance()
            yield future
        success = True
    finally:
        display.finish(success=success)


def imap(
    fn: typing.Callable[..., typing.Any],
    /,
    *iterables: typing.Iterable[typing.Any],
    **kwargs: typing.Any,
) -> typing.Generator[typing.Any, None, None]:
    """Lazily apply `fn` in parallel, yielding results in input order.

    The parallel counterpart of ``multiprocessing.Pool.imap``: same
    ordering, same laziness, same results-only element shape. Results
    completed out of order are held back until their turn; the held
    set stays bounded by the submission window (`buffersize`).

    Closing the generator early (``break``) cancels unsubmitted work
    and shuts down the run's executor; wrap in `contextlib.closing`
    for deterministic cleanup. See `execute` for keywords.
    """
    held: dict[int, typing.Any] = {}
    next_index: int = 0
    for index, _args, _ok, value in execute(fn, iterables, **kwargs):
        held[index] = value
        while next_index in held:
            yield held.pop(next_index)
            next_index += 1


def imap_unordered(
    fn: typing.Callable[..., typing.Any],
    /,
    *iterables: typing.Iterable[typing.Any],
    **kwargs: typing.Any,
) -> typing.Generator[tuple[typing.Any, typing.Any], None, None]:
    """Lazily apply `fn` in parallel, yielding as tasks complete.

    Yields ``(item, result)`` pairs in *completion* order -- the pair
    shape exists because completion order loses the input
    correspondence (a deliberate deviation from
    ``multiprocessing.Pool.imap_unordered``, which yields bare
    results). With multiple iterables, ``item`` is the argument tuple.

    Closing the generator early cancels unsubmitted work; see `imap`.
    """
    single: bool = len(iterables) == 1
    for _index, args, _ok, value in execute(fn, iterables, **kwargs):
        yield _common.item_of(args, single), value


def map(  # noqa: A001 - intentional builtin name, namespaced use only
    fn: typing.Callable[..., typing.Any],
    /,
    *iterables: typing.Iterable[typing.Any],
    **kwargs: typing.Any,
) -> list[typing.Any]:
    """Apply `fn` to every zipped item in parallel; results in order.

    The parallel counterpart of the builtin ``map``:
    ``progressbar.map(fn, items, workers=8)`` runs on a thread pool by
    default, renders a progress bar, and returns the results in input
    order once the batch completes. ``pool='process'`` switches to
    processes, ``bar='multi'`` shows per-task sub-bars, and
    ``on_error='return'`` swaps fail-fast for exceptions-in-place. See
    `execute` for the full keyword reference.
    """
    results: dict[int, typing.Any] = {
        index: value
        for index, _args, _ok, value in execute(fn, iterables, **kwargs)
    }
    return [results[index] for index in range(len(results))]
