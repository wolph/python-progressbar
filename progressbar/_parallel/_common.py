"""Shared plumbing for the parallel execution verbs.

Everything here is engine-agnostic: argument validation, total
detection, chunking, worker/window defaults, and the context variable
that gives workers access to their own sub-bar under ``bar='multi'``.
"""

from __future__ import annotations

import contextvars
import functools
import inspect
import itertools
import operator
import os
import typing

from .. import (
    bar as bar_module,
    base,
)

#: One zipped argument tuple, i.e. one call's positional arguments.
ItemArgs = tuple[typing.Any, ...]

T = typing.TypeVar('T')

#: Chunk sizing targets ~16 chunks per worker so completion events stay
#: frequent enough for a lively bar while amortizing per-task overhead.
_CHUNKS_PER_WORKER: int = 16
#: Hard cap so gigantic inputs still produce regular progress updates.
_MAX_AUTO_CHUNKSIZE: int = 1_000
#: Submission window per worker; the floor keeps tiny pools busy.
_WINDOWS_PER_WORKER: int = 4
_MIN_BUFFERSIZE: int = 16

#: The bar owned by the currently executing task, set by `with_task_bar`
#: around each worker invocation under ``bar='multi'``. Workers read it
#: through `current_task_bar`.
_task_bar_var: contextvars.ContextVar[bar_module.ProgressBar | None] = (
    contextvars.ContextVar('current_task_bar', default=None)
)


def current_task_bar() -> bar_module.ProgressBar | None:
    """Return the calling task's own progress bar, if it has one.

    Inside a function executed by `progressbar.map`/`amap` with
    ``bar='multi'`` this returns the per-task bar so the worker can
    report sub-progress (``current_task_bar().update(i)``). Anywhere
    else -- including process-pool workers, which cannot share a bar
    object with the parent in v1 -- it returns `None`.
    """
    return _task_bar_var.get()


def with_task_bar(
    task_bar: bar_module.ProgressBar,
    inner: typing.Callable[[], T],
) -> typing.Callable[[], T]:
    """Wrap `inner` so `current_task_bar` returns `task_bar` inside it."""

    def _bound() -> T:
        token: contextvars.Token[bar_module.ProgressBar | None] = (
            _task_bar_var.set(task_bar)
        )
        try:
            return inner()
        finally:
            _task_bar_var.reset(token)

    return _bound


def detect_total(
    iterables: tuple[typing.Iterable[typing.Any], ...],
) -> int | typing.Any:
    """Return the number of items `zip(*iterables)` will yield.

    Uses `len` where available, falling back to `operator.length_hint`;
    any iterable without either makes the total `base.UnknownLength`.
    Multiple iterables zip, so the total is their minimum.
    """
    totals: list[int] = []
    for iterable in iterables:
        try:
            totals.append(len(iterable))  # type: ignore[arg-type]
        except TypeError:
            hint: int = operator.length_hint(iterable, -1)
            if hint < 0:
                return base.UnknownLength
            totals.append(hint)
    return min(totals) if totals else 0


@functools.cache
def known_bar_kwargs(cls: type) -> frozenset[str]:
    """Collect every keyword parameter accepted along `cls`'s MRO."""
    names: set[str] = set()
    for klass in cls.__mro__:
        init: typing.Any = klass.__dict__.get('__init__')
        if init is None:
            continue
        for parameter in inspect.signature(init).parameters.values():
            if parameter.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                names.add(parameter.name)
    names.discard('self')
    return frozenset(names)


def validate_bar_kwargs(bar_kwargs: dict[str, typing.Any]) -> None:
    """Reject unknown bar keyword arguments loudly.

    `ProgressBarMixinBase.__init__` swallows unknown ``**kwargs``
    silently, so a typo like ``worker=8`` would otherwise run with
    defaults and no error -- exactly the failure this guard exists for.
    """
    # FastProgressBar subclasses ProgressBar, so its MRO covers both.
    allowed: frozenset[str] = known_bar_kwargs(bar_module.ProgressBar)
    unknown: set[str] = set(bar_kwargs) - allowed
    if unknown:
        raise TypeError(
            f'unknown progress bar argument(s): {sorted(unknown)!r}. '
            f'Not a bar option and not a parallel option either.'
        )


def resolve_workers(workers: int | None, kind: str) -> int:
    """Return the effective pool size, mirroring the executor defaults."""
    if workers is not None:
        return workers
    cpu_count: int = os.cpu_count() or 1
    if kind == 'thread':
        # ThreadPoolExecutor's documented default.
        return min(32, cpu_count + 4)
    return cpu_count


def default_buffersize(workers: int) -> int:
    """Return the default submission window (unfinished futures)."""
    return max(_WINDOWS_PER_WORKER * workers, _MIN_BUFFERSIZE)


def auto_chunksize(total: int | typing.Any, workers: int) -> int:
    """Pick a chunk size for process pools from the batch size.

    Targets `_CHUNKS_PER_WORKER` chunks per worker, capped at
    `_MAX_AUTO_CHUNKSIZE` so progress updates stay regular. Streaming
    inputs (unknown total) get 1: correctness first, tuning explicit.
    """
    if total is base.UnknownLength:
        return 1
    return max(
        1, min(total // (workers * _CHUNKS_PER_WORKER), _MAX_AUTO_CHUNKSIZE)
    )


def iter_chunks(
    iterables: tuple[typing.Iterable[typing.Any], ...],
    chunksize: int,
) -> typing.Iterator[list[ItemArgs]]:
    """Lazily zip `iterables` and batch the argument tuples."""
    zipped: typing.Iterator[ItemArgs] = zip(*iterables)
    while chunk := list(itertools.islice(zipped, chunksize)):
        yield chunk


def item_of(args: ItemArgs, single: bool) -> typing.Any:
    """Return the user-facing item: bare for one iterable, tuple else."""
    return args[0] if single else args


def run_chunk(
    fn: typing.Callable[..., typing.Any],
    chunk: list[ItemArgs],
    catch: bool,
) -> list[tuple[bool, typing.Any]]:
    """Run `fn` over a chunk of argument tuples in one task.

    Top-level and closed over nothing so process pools can pickle it.

    Args:
        fn: The callable applied per argument tuple.
        chunk: The argument tuples for this task.
        catch: Under ``on_error='return'`` each item's `Exception` is
            captured as a ``(False, exc)`` outcome so one failure loses
            no other results. `KeyboardInterrupt`/`SystemExit` always
            escape -- errors may be *returned*, never swallowed. With
            ``catch=False`` the first exception escapes, aborting the
            chunk's remainder (documented fail-fast semantics).

    Returns:
        One ``(ok, result_or_exception)`` pair per completed item.
    """
    outcomes: list[tuple[bool, typing.Any]] = []
    for args in chunk:
        if catch:
            try:
                outcomes.append((True, fn(*args)))
            except Exception as exc:  # noqa: BLE001 - returned, not silenced
                outcomes.append((False, exc))
        else:
            outcomes.append((True, fn(*args)))
    return outcomes
