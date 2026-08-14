"""Display backends for the parallel verbs.

One small protocol so both execution engines can drive any of four
rendering modes -- ``'plain'`` (one aggregate bar), ``'multi'``
(a MultiBar with per-task sub-bars), ``False`` (silent), or a
caller-configured bar instance -- through the same six calls.

The keep-alive contract lives here: `PlainDisplay` constructs its bar
with ``poll_interval`` set, because `ProgressBar.update()` without a
new value only redraws timers/animations when the bar's own
``poll_interval`` says a redraw is due. A default-configured bar
no-ops, which would freeze ETA/spinners during long tasks.
"""

from __future__ import annotations

import os
import sys
import typing

from .. import (
    bar as bar_module,
    base,
    fast as fast_module,
)
from . import _common

if typing.TYPE_CHECKING:
    from .. import multi as multi_module


@typing.runtime_checkable
class Display(typing.Protocol):
    """What the execution engines require from a rendering backend."""

    def start(self, total: typing.Any) -> None:
        """Begin rendering a run of `total` items (or `UnknownLength`)."""
        ...

    def task_started(
        self, seq: int, label: str
    ) -> bar_module.ProgressBar | None:
        """Register in-flight task `seq`; return its own bar, if any."""
        ...

    def task_finished(self, seq: int, ok: bool) -> None:
        """Retire task `seq` from the in-flight set."""
        ...

    def advance(self, n: int = 1) -> None:
        """Count `n` more items as completed."""
        ...

    def tick(self) -> None:
        """Keep time widgets moving when nothing completed this poll."""
        ...

    def finish(self, *, success: bool = True) -> None:
        """Stop rendering; a failed run must not jump the bar to 100%."""
        ...


class NullDisplay:
    """The ``bar=False`` backend: the machinery runs, nothing renders."""

    def start(self, total: typing.Any) -> None:
        """Ignore the run start."""

    def task_started(
        self, seq: int, label: str
    ) -> bar_module.ProgressBar | None:
        """Report no per-task bar."""
        return None

    def task_finished(self, seq: int, ok: bool) -> None:
        """Ignore the task end."""

    def advance(self, n: int = 1) -> None:
        """Ignore progress."""

    def tick(self) -> None:
        """Ignore the poll."""

    def finish(self, *, success: bool = True) -> None:
        """Ignore the run end."""


def _select_bar_class(
    bar_kwargs: dict[str, typing.Any],
) -> type[bar_module.ProgressBar]:
    """Pick the lean fast bar unless a kwarg needs the widget machinery.

    Mirrors the dispatch rule of `progressbar.shortcuts.progressbar`:
    anything widget-shaped (custom widgets, variables, units, postfix)
    forces the full bar; the plain percentage/ETA case takes the cheap
    renderer.
    """
    needs_full: bool = bool(
        bar_kwargs.get('widgets')
        or bar_kwargs.get('variables')
        or bar_kwargs.get('unit_scale')
        or bar_kwargs.get('postfix')
        or bar_kwargs.get('unit', 'it') != 'it'
        or os.environ.get('PROGRESSBAR_DISABLE_FASTPATH')
    )
    return (
        bar_module.ProgressBar if needs_full else fast_module.FastProgressBar
    )


class PlainDisplay:
    """One aggregate bar counting completed items."""

    _bar: bar_module.ProgressBar
    _owned: bool
    _started_by_us: bool
    _value: int

    def __init__(
        self,
        *,
        total: typing.Any,
        poll_interval: float,
        bar_kwargs: dict[str, typing.Any],
        instance: bar_module.ProgressBar | None = None,
    ) -> None:
        """Create the bar (or adopt `instance` without reconfiguring it)."""
        self._owned = instance is None
        self._started_by_us = False
        self._value = 0
        if instance is not None:
            self._bar = instance
        else:
            # poll_interval is what makes no-progress ticks redraw; a
            # caller-supplied value in bar_kwargs wins (same knob).
            kwargs: dict[str, typing.Any] = dict(bar_kwargs)
            kwargs.setdefault('poll_interval', poll_interval)
            kwargs.setdefault('max_value', total)
            bar_class: type[bar_module.ProgressBar] = _select_bar_class(kwargs)
            self._bar = bar_class(**kwargs)

    def start(self, total: typing.Any) -> None:
        """Start the bar unless the caller already started it."""
        if not self._bar.started():
            self._bar.start()
            self._started_by_us = True

    def task_started(
        self, seq: int, label: str
    ) -> bar_module.ProgressBar | None:
        """Report no per-task bar (plain mode has only the aggregate)."""
        return None

    def task_finished(self, seq: int, ok: bool) -> None:
        """Nothing tracked per task in plain mode."""

    def advance(self, n: int = 1) -> None:
        """Add `n` completions and redraw."""
        self._value += n
        self._bar.update(self._value)

    def tick(self) -> None:
        """Redraw with no new value so time widgets stay alive."""
        self._bar.update()

    def finish(self, *, success: bool = True) -> None:
        """Finish the bar; only if this display started it."""
        if self._started_by_us:
            # dirty=True on failure: keep the last real value on screen
            # instead of forcing the bar to max.
            self._bar.finish(dirty=not success)


class MultiDisplay:
    """A MultiBar: one overall bar plus one bar per in-flight task.

    Per-task bars are keyed ``'{seq}: {label}'`` -- ``seq`` is unique
    per run, so two items with the same ``str()`` can never collide on
    a key (a plain-label key would silently merge them and corrupt the
    display). Finished task bars are deleted immediately: MultiBar's
    own default keeps them around for an hour, which would stack
    thousands of dead lines on a big batch.

    Rendering is done by MultiBar's daemon thread at
    ``update_interval=poll_interval``, so `tick` needs no work here.
    Best suited to modest worker counts: the block occupies one
    terminal row per in-flight task plus one for the total.
    """

    #: Overall bar's key in the multibar (also its visible label).
    _TOTAL_KEY: typing.ClassVar[str] = 'Total'
    #: Bounded wait for the render thread; it wakes every
    #: `update_interval` seconds, so this is generous.
    _STOP_TIMEOUT: typing.ClassVar[float] = 5.0

    multibar: multi_module.MultiBar
    _keys: dict[int, str]
    _owned: bool
    _started_thread: bool
    _value: int
    _poll_interval: float

    def __init__(
        self,
        *,
        total: typing.Any,
        poll_interval: float,
        bar_kwargs: dict[str, typing.Any],
        instance: multi_module.MultiBar | None = None,
    ) -> None:
        """Create (or adopt) the multibar and its overall bar."""
        # Deferred import: keeps `import progressbar` + plain-mode use
        # from paying for the multibar/widget machinery.
        from .. import multi as multi_module

        self._keys = {}
        self._value = 0
        self._started_thread = False
        self._poll_interval = poll_interval
        self._owned = instance is None
        kwargs: dict[str, typing.Any] = dict(bar_kwargs)
        if instance is not None:
            self.multibar = instance
        else:
            self.multibar = multi_module.MultiBar(
                fd=kwargs.pop('fd', sys.stderr),
                update_interval=poll_interval,
                show_finished=False,
                remove_finished=0,
                sort_reverse=False,
            )
        # Remaining bar kwargs style the overall bar.
        kwargs.setdefault('poll_interval', poll_interval)
        kwargs.setdefault('max_value', total)
        self._overall: bar_module.ProgressBar = bar_module.ProgressBar(
            **kwargs
        )

    def start(self, total: typing.Any) -> None:
        """Add and start the overall bar, then the render thread."""
        self.multibar[self._TOTAL_KEY] = self._overall
        self._overall.start()
        # `_thread` is the only handle MultiBar exposes for "already
        # running"; an adopted, already-started instance must not be
        # started twice (MultiBar asserts on that).
        if self.multibar._thread is None:  # noqa: SLF001
            self.multibar.start()
            self._started_thread = True

    def task_started(
        self, seq: int, label: str
    ) -> bar_module.ProgressBar | None:
        """Add a per-task bar and hand it out for `current_task_bar`."""
        key: str = f'{seq}: {label}'
        self._keys[seq] = key
        task_bar: bar_module.ProgressBar = bar_module.ProgressBar(
            max_value=base.UnknownLength,
        )
        self.multibar[key] = task_bar
        task_bar.start()
        return task_bar

    def task_finished(self, seq: int, ok: bool) -> None:
        """Drop the task's bar -- finished bars must not pile up."""
        key: str | None = self._keys.pop(seq, None)
        if key is not None and key in self.multibar:
            del self.multibar[key]

    def advance(self, n: int = 1) -> None:
        """Count completions on the overall bar.

        The overall bar is `paused` (MultiBar contract), so `update`
        only records the value; the render thread draws it.
        """
        self._value += n
        self._overall.update(self._value)

    def tick(self) -> None:
        """No-op: the render thread redraws every `poll_interval`."""

    def finish(self, *, success: bool = True) -> None:
        """Finish the overall bar and wind down the render thread."""
        for seq in list(self._keys):
            self.task_finished(seq, ok=success)
        self._overall.finish(dirty=not success)
        if self._started_thread:
            # One last frame so the final state is on screen even if
            # the render thread never woke between finish and stop.
            self.multibar.render(force=True)
            self.multibar.stop(timeout=self._STOP_TIMEOUT)


def make_display(
    bar_mode: typing.Any,
    *,
    total: typing.Any,
    poll_interval: float,
    bar_kwargs: dict[str, typing.Any],
) -> Display:
    """Build the display backend for one run.

    Args:
        bar_mode: ``'plain'`` | ``'multi'`` | ``False`` | a
            `ProgressBar` or `MultiBar` instance to drive.
        total: Item count or `base.UnknownLength`.
        poll_interval: Redraw cadence; also the engines' wake interval.
        bar_kwargs: Validated passthrough for the constructed bar.

    Raises:
        TypeError: For unknown or unvalidated bar kwargs, or an
            unrecognized `bar_mode`.
    """
    _common.validate_bar_kwargs(bar_kwargs)
    if bar_mode is False or bar_mode is None:
        return NullDisplay()
    if bar_mode == 'plain':
        return PlainDisplay(
            total=total, poll_interval=poll_interval, bar_kwargs=bar_kwargs
        )
    if bar_mode == 'multi':
        return MultiDisplay(
            total=total, poll_interval=poll_interval, bar_kwargs=bar_kwargs
        )
    if isinstance(bar_mode, bar_module.ProgressBar):
        return PlainDisplay(
            total=total,
            poll_interval=poll_interval,
            bar_kwargs=bar_kwargs,
            instance=bar_mode,
        )
    # Deferred import mirrors MultiDisplay's: only pay for the multibar
    # machinery when a MultiBar is actually in play.
    from .. import multi as multi_module

    if isinstance(bar_mode, multi_module.MultiBar):
        return MultiDisplay(
            total=total,
            poll_interval=poll_interval,
            bar_kwargs=bar_kwargs,
            instance=bar_mode,
        )
    raise TypeError(
        f'bar={bar_mode!r} is not a valid mode: expected "plain", '
        f'"multi", False, a ProgressBar or a MultiBar'
    )
