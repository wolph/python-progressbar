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
