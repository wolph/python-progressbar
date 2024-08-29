from __future__ import annotations

import typing

from . import (
    bar,
    widgets as widgets_module,
)

T = typing.TypeVar('T')


def progressbar(
    iterator: typing.Iterator[T],
    min_value: bar.NumberT = 0,
    max_value: bar.ValueT = None,
    widgets: typing.Sequence[widgets_module.WidgetBase | str] | None = None,
    prefix: str | None = None,
    suffix: str | None = None,
    **kwargs: typing.Any,
) -> typing.Generator[T, None, None]:
    progressbar_ = bar.ProgressBar(
        min_value=min_value,
        max_value=max_value,
        widgets=widgets,
        prefix=prefix,
        suffix=suffix,
        **kwargs,
    )
    yield from progressbar_(iterator)
