"""The one-call entry point: `progressbar(iterable)`.

Most users never touch anything else in this package.
"""

from __future__ import annotations

import collections.abc
import os
import typing

from . import (
    bar,
    fast as fast_module,
)

if typing.TYPE_CHECKING:
    from . import widgets as widgets_module

T = typing.TypeVar('T')


def progressbar(
    iterator: collections.abc.Iterable[T],
    min_value: bar.NumberT = 0,
    max_value: bar.ValueT = None,
    widgets: collections.abc.Sequence[widgets_module.WidgetBase | str]
    | None = None,
    prefix: str | None = None,
    suffix: str | None = None,
    fast: bool | None = None,
    desc: str | None = None,
    total: bar.ValueT = None,
    unit: str = 'it',
    unit_scale: bool = False,
    postfix: typing.Any = None,
    **kwargs: typing.Any,
) -> collections.abc.Iterator[T]:
    """Wrap an iterable so iterating it renders a progress bar.

    The common case needs nothing but the iterable::

        for item in progressbar(items):
            ...

    Args:
        iterator: The iterable to wrap. Its length is used as the
            total when it has one; otherwise pass `max_value`, or
            accept a bar with no percentage or ETA.
        min_value: Value the bar starts from. Only worth changing
            when progress does not begin at zero.
        max_value: Value counted as complete. Defaults to the
            iterable's length, or `UnknownLength` when it has none.
        widgets: Replaces the default bar layout entirely. Passing
            this forces the full widget machinery; see the widget
            reference for what can go in it.
        prefix: Text before the bar. `desc` is the tqdm-style alias.
        suffix: Text after the bar.
        fast: Force the lean fast path on or off instead of letting
            it be chosen. `False` always uses the full widget bar.
            Mainly useful for benchmarking; the automatic choice is
            usually right.
        desc: tqdm-compatible alias for `prefix`.
        total: tqdm-compatible alias for `max_value`.
        unit: Noun for one item, shown in the rate. Anything other
            than the default forces the full widget bar.
        unit_scale: Scale counts to SI prefixes (1200 becomes 1.2K).
            Forces the full widget bar.
        postfix: Values rendered after the bar and refreshed as it
            advances. Forces the full widget bar.
        **kwargs: Passed through to the underlying bar. Note that
            supplying `variables` forces the full widget bar.

    Returns:
        An iterator yielding the same items, advancing the bar as it
        goes.
    """
    # Auto-dispatch to the lean FastProgressBar for the simple, common case;
    # anything that needs the full widget machinery uses ProgressBar. The
    # tqdm-style `desc` (a prefix) and `total` (a max_value) render fine on
    # the fast path, but units and postfixes are widgets and need the full
    # bar.
    use_fast = (
        widgets is None
        and fast is not False
        and not kwargs.get('variables')
        and unit == 'it'
        and not unit_scale
        and postfix is None
        and not os.environ.get('PROGRESSBAR_DISABLE_FASTPATH')
    )
    cls = fast_module.FastProgressBar if use_fast else bar.ProgressBar
    progressbar_ = cls(
        min_value=min_value,
        max_value=max_value,
        widgets=widgets,
        prefix=prefix,
        suffix=suffix,
        desc=desc,
        total=total,
        unit=unit,
        unit_scale=unit_scale,
        postfix=postfix,
        **kwargs,
    )
    return iter(progressbar_(iterator))
