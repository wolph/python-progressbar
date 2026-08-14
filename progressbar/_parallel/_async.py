"""The asyncio engine behind `amap`, `aimap` and `gather`.

Mirrors the sync engine's coordination pattern -- windowed task
creation, a done-queue costing O(1) per completion, poll-timeout ticks
for the keep-alive guarantee -- with asyncio primitives. Sync callables
are welcome too: they run via `asyncio.to_thread`, so one async entry
point covers both worlds.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import time
import typing

from . import (
    _common,
    _display,
)

#: One completion event: (item index, argument tuple, ok, result/error).
Completion = tuple[int, _common.ItemArgs, bool, typing.Any]

#: Default seconds between coordinator wakeups; doubles as the bar's
#: redraw interval (one knob -- see the keep-alive contract).
DEFAULT_POLL_INTERVAL: float = 0.1


def _call_strategy(fn: typing.Callable[..., typing.Any]) -> str:
    """Classify `fn` as ``'async'`` or ``'sync'``.

    Unwraps `functools.partial` manually: on the 3.10 floor
    `inspect.iscoroutinefunction` does not look through partials, and
    `asyncio.iscoroutinefunction` (which does) is deprecated in 3.14.
    """
    target: typing.Any = fn
    while isinstance(target, functools.partial):
        target = target.func
    return 'async' if inspect.iscoroutinefunction(target) else 'sync'


async def _acall(
    fn: typing.Callable[..., typing.Any],
    args: _common.ItemArgs,
    strategy: str,
) -> typing.Any:
    """Await `fn(*args)` per the detected strategy.

    ``'async'`` awaits directly. ``'sync'`` runs in a thread via
    `asyncio.to_thread` -- note cancellation *abandons* such a thread
    rather than interrupting it -- and, if the call returned an
    awaitable (a sync factory of coroutines), awaits that too.
    """
    if strategy == 'async':
        return await fn(*args)
    value: typing.Any = await asyncio.to_thread(fn, *args)
    if inspect.isawaitable(value):
        value = await value
    return value


async def _await_it(awaitable: typing.Awaitable[typing.Any]) -> typing.Any:
    """Adapt a bare awaitable (the `gather` path) into a task coro."""
    return await awaitable


class _AsyncRun:
    """State and coordination for one `execute_async` invocation."""

    fn: typing.Callable[..., typing.Any] | None
    strategy: str
    awaitables: bool
    total: typing.Any
    on_error: str
    single: bool
    window: int | None
    timeout: float | None
    poll_interval: float
    deadline: float | None
    display: _display.Display
    done: asyncio.Queue[asyncio.Task[typing.Any]]
    in_flight: dict[
        asyncio.Task[typing.Any], tuple[int, _common.ItemArgs, int]
    ]
    item_source: typing.Iterator[tuple[int, _common.ItemArgs]]
    seq: int

    def __init__(
        self,
        fn: typing.Callable[..., typing.Any] | None,
        iterables: tuple[typing.Iterable[typing.Any], ...],
        *,
        concurrency: int | None,
        bar: typing.Any,
        on_error: str,
        timeout: float | None,
        poll_interval: float,
        awaitables: bool,
        bar_kwargs: dict[str, typing.Any],
    ) -> None:
        """Validate the configuration and set up the display."""
        if on_error not in ('raise', 'return'):
            raise ValueError(
                f"on_error={on_error!r} is not valid: expected 'raise' "
                f"or 'return'"
            )
        _common.validate_bar_kwargs(bar_kwargs)
        self.fn = fn
        self.strategy = '' if fn is None else _call_strategy(fn)
        self.awaitables = awaitables
        self.total = _common.detect_total(iterables)
        self.on_error = on_error
        self.single = len(iterables) == 1
        self.window = concurrency
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.deadline = None if timeout is None else time.monotonic() + timeout
        self.display = _display.make_display(
            bar,
            total=self.total,
            poll_interval=poll_interval,
            bar_kwargs=bar_kwargs,
        )
        self.done = asyncio.Queue()
        self.in_flight = {}
        self.item_source = enumerate(zip(*iterables, strict=False))
        self.seq = 0

    async def completions(self) -> typing.AsyncIterator[Completion]:
        """Drive the run, yielding per-item events in completion order."""
        self.display.start(self.total)
        if self.window is None:
            # gather semantics: everything in flight at once.
            while self._launch_one():
                pass
        else:
            while len(self.in_flight) < self.window and self._launch_one():
                pass
        while self.in_flight:
            self._check_deadline()
            task = await self._next_done()
            if task is None:
                continue
            event: Completion | None = self._handle(task)
            if event is not None:
                yield event

    def _launch_one(self) -> bool:
        """Create the next task; `False` when the input is exhausted."""
        indexed: tuple[int, _common.ItemArgs] | None = next(
            self.item_source, None
        )
        if indexed is None:
            return False
        index, args = indexed
        self.seq += 1
        label: str = str(_common.item_of(args, self.single))
        task_bar = self.display.task_started(self.seq, label)
        coroutine: typing.Coroutine[typing.Any, typing.Any, typing.Any]
        if self.awaitables:
            coroutine = _await_it(args[0])
        else:
            assert self.fn is not None
            coroutine = _acall(self.fn, args, self.strategy)
        if task_bar is None:
            task: asyncio.Task[typing.Any] = asyncio.ensure_future(coroutine)
        else:
            # Task creation snapshots the current context, so binding
            # the contextvar around it is what makes
            # `current_task_bar()` work inside the task.
            token = _common._task_bar_var.set(task_bar)  # noqa: SLF001
            try:
                task = asyncio.ensure_future(coroutine)
            finally:
                _common._task_bar_var.reset(token)  # noqa: SLF001
        self.in_flight[task] = (index, args, self.seq)
        task.add_done_callback(self.done.put_nowait)
        return True

    async def _next_done(self) -> asyncio.Task[typing.Any] | None:
        """Wait one poll for a completion; tick the display on none."""
        try:
            return await asyncio.wait_for(
                self.done.get(), timeout=self.poll_interval
            )
        except asyncio.TimeoutError:
            self.display.tick()
            return None

    def _check_deadline(self) -> None:
        """Raise once the overall `timeout` budget is spent."""
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise asyncio.TimeoutError(
                f'parallel execution exceeded timeout={self.timeout}'
            )

    def _handle(self, task: asyncio.Task[typing.Any]) -> Completion | None:
        """Turn one finished task into a completion event."""
        index, args, seq = self.in_flight.pop(task)
        if task.cancelled():
            # Something outside this run cancelled the task; surface it
            # rather than silently dropping the item.
            self.display.task_finished(seq, ok=False)
            raise asyncio.CancelledError
        error: BaseException | None = task.exception()
        if error is not None:
            self.display.task_finished(seq, ok=False)
            if self.on_error == 'raise' or isinstance(
                error, (KeyboardInterrupt, SystemExit)
            ):
                raise error
            self.display.advance()
            self._launch_one()
            return index, args, False, error
        self.display.task_finished(seq, ok=True)
        self.display.advance()
        self._launch_one()
        return index, args, True, task.result()

    async def close(self, *, success: bool) -> None:
        """Cancel outstanding tasks, await them, release the display."""
        for task in self.in_flight:
            task.cancel()
        if self.in_flight:
            # Awaiting the cancelled tasks prevents "Task exception was
            # never retrieved"/"Task was destroyed" noise on teardown.
            await asyncio.gather(*self.in_flight, return_exceptions=True)
        self.display.finish(success=success)


async def execute_async(
    fn: typing.Callable[..., typing.Any] | None,
    iterables: tuple[typing.Iterable[typing.Any], ...],
    *,
    concurrency: int | None = None,
    workers: int | None = None,
    bar: typing.Any = 'plain',
    on_error: str = 'raise',
    timeout: float | None = None,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    awaitables: bool = False,
    **bar_kwargs: typing.Any,
) -> typing.AsyncIterator[Completion]:
    """Run `fn` over zipped `iterables` on the event loop.

    The async twin of the sync `execute`: yields ``(index, args, ok,
    value)`` events in completion order. `workers` is accepted as an
    alias for `concurrency` (same concept, sync spelling).
    ``concurrency=None`` creates every task up front (`asyncio.gather`
    semantics -- pass a limit for large batches); with a limit, tasks
    are created lazily in a window of that size.

    With ``awaitables=True`` (the `gather` path) the single iterable
    contains awaitables to schedule directly and `fn` is ignored.

    Raises:
        ValueError: Invalid `on_error`.
        TypeError: Unknown bar keyword.
        asyncio.TimeoutError: The overall `timeout` expired; outstanding
            tasks are cancelled and awaited first.
    """
    if concurrency is None:
        concurrency = workers
    run: _AsyncRun = _AsyncRun(
        fn,
        iterables,
        concurrency=concurrency,
        bar=bar,
        on_error=on_error,
        timeout=timeout,
        poll_interval=poll_interval,
        awaitables=awaitables,
        bar_kwargs=bar_kwargs,
    )
    success: bool = False
    try:
        async for event in run.completions():
            yield event
        success = True
    finally:
        await run.close(success=success)


async def amap(
    fn: typing.Callable[..., typing.Any],
    /,
    *iterables: typing.Iterable[typing.Any],
    **kwargs: typing.Any,
) -> list[typing.Any]:
    """Apply `fn` to every zipped item on the event loop; ordered.

    The async counterpart of `progressbar.map`. `fn` may be an async
    *or* a plain sync callable -- sync callables run in a thread via
    `asyncio.to_thread`. Results come back in input order::

        results = await progressbar.amap(fetch, urls, concurrency=8)

    See `execute_async` for the keyword reference.
    """
    results: dict[int, typing.Any] = {
        index: value
        async for index, _args, _ok, value in execute_async(
            fn, iterables, **kwargs
        )
    }
    return [results[index] for index in range(len(results))]
