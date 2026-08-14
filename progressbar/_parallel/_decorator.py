"""`@parallel`: attach the batch verbs to a plain function.

Sugar over the module verbs::

    @progressbar.parallel(workers=4, pool='process')
    def crunch(path: str) -> Result: ...


    crunch(one_path)  # unchanged direct call
    crunch.map(paths)  # parallel + bar, decorator config applied

The decorator returns the *original function object* with bound verbs
attached as attributes. That shape is deliberate: pickling by
qualified name stays intact (``pool='process'`` needs it), and spawn's
re-import just re-runs the decoration.
"""

from __future__ import annotations

import functools
import inspect
import typing

from . import (
    _async,
    _sync,
)


class ParallelFunction(typing.Protocol):
    """A function enriched with the parallel batch verbs."""

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        """The original, undecorated call."""
        ...

    def map(  # noqa: A003 - mirrors the module verb
        self, *iterables: typing.Any, **kwargs: typing.Any
    ) -> list[typing.Any]:
        """Parallel ordered map over the iterables; see the module verb."""
        ...

    def imap(
        self, *iterables: typing.Any, **kwargs: typing.Any
    ) -> typing.Generator[typing.Any, None, None]:
        """Lazy ordered results; see the module verb."""
        ...

    def imap_unordered(
        self, *iterables: typing.Any, **kwargs: typing.Any
    ) -> typing.Generator[tuple[typing.Any, typing.Any], None, None]:
        """Completion-order pairs; see the module verb."""
        ...

    def starmap(
        self, iterable: typing.Any, **kwargs: typing.Any
    ) -> list[typing.Any]:
        """Parallel map over pre-tupled arguments; see the module verb."""
        ...

    def amap(
        self, *iterables: typing.Any, **kwargs: typing.Any
    ) -> typing.Coroutine[typing.Any, typing.Any, list[typing.Any]]:
        """Async ordered map; see the module verb."""
        ...

    def aimap(
        self, *iterables: typing.Any, **kwargs: typing.Any
    ) -> typing.AsyncIterator[typing.Any]:
        """Async lazy ordered results; see the module verb."""
        ...

    def aimap_unordered(
        self, *iterables: typing.Any, **kwargs: typing.Any
    ) -> typing.AsyncIterator[tuple[typing.Any, typing.Any]]:
        """Async completion-order pairs; see the module verb."""
        ...


#: Verb name -> module implementation bound by the decorator.
_VERBS: dict[str, typing.Callable[..., typing.Any]] = {
    'map': _sync.map,
    'imap': _sync.imap,
    'imap_unordered': _sync.imap_unordered,
    'starmap': _sync.starmap,
    'amap': _async.amap,
    'aimap': _async.aimap,
    'aimap_unordered': _async.aimap_unordered,
}


def _bind(
    verb: typing.Callable[..., typing.Any],
    fn: typing.Callable[..., typing.Any],
    config: dict[str, typing.Any],
) -> typing.Callable[..., typing.Any]:
    """Close `verb` over `fn` and the decorator config."""

    @functools.wraps(verb, assigned=('__doc__',), updated=())
    def bound(*iterables: typing.Any, **kwargs: typing.Any) -> typing.Any:
        return verb(fn, *iterables, **{**config, **kwargs})

    return bound


def parallel(
    **config: typing.Any,
) -> typing.Callable[[typing.Callable[..., typing.Any]], ParallelFunction]:
    """Attach the parallel batch verbs to a function.

    Args:
        **config: Default keywords for every attached verb (`workers`,
            `pool`, `bar`, `on_error`, ...); individual calls override
            them.

    Returns:
        A decorator returning the same function object with `.map`,
        `.imap`, `.imap_unordered`, `.starmap`, `.amap`, `.aimap` and
        `.aimap_unordered` attached.

    Raises:
        TypeError: The target is not a plain named function. Lambdas
            and bound methods are rejected because ``pool='process'``
            pickles the function by qualified name.
    """

    def decorate(fn: typing.Callable[..., typing.Any]) -> ParallelFunction:
        if not inspect.isfunction(fn) or fn.__name__ == '<lambda>':
            raise TypeError(
                f'parallel() requires a plain named function, got '
                f'{fn!r} (needed so pool="process" can pickle it by '
                f'qualified name)'
            )
        for name, verb in _VERBS.items():
            setattr(fn, name, _bind(verb, fn, config))
        return typing.cast(ParallelFunction, fn)

    return decorate
