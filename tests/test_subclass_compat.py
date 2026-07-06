"""Third-party subclass compatibility characterization tests.

progressbar2 is subclassed in the wild in two styles:

1. *Old style* — explicit unbound parent ``__init__`` calls, copying the
   library's own historic pattern
   (``FormatWidgetMixin.__init__(self, ...)`` followed by
   ``WidgetBase.__init__(self, ...)``).
2. *Super style* — a single cooperative ``super().__init__(...)``.

Both styles must construct and render identically before and after the
cooperative-``super()`` migration; these tests characterize today's
behavior and act as the gate for that refactor. The golden-render tests
additionally pin the exact default rendering so any refactor that
changes output byte-for-byte fails loudly.
"""

from __future__ import annotations

import io
import typing

import pytest

import progressbar
import progressbar.widgets

# Alias (not a `from` import) so CodeQL doesn't flag `progressbar` as
# imported with both `import` and `import from`.
widgets = progressbar.widgets


def _render(
    widget_list: list[typing.Any],
    max_value: int = 10,
    term_width: int = 60,
) -> str:
    fd = io.StringIO()
    bar = progressbar.ProgressBar(
        fd=fd,
        max_value=max_value,
        widgets=widget_list,
        term_width=term_width,
    )
    bar.start()
    bar.update(5, force=True)
    bar.finish()
    return fd.getvalue()


# --- (a) old style: explicit unbound parent __init__ calls -----------------


class OldStyleWidget(widgets.FormatWidgetMixin, widgets.WidgetBase):
    def __init__(
        self,
        my_param: str = 'x',
        format: str = '%(value)d!',
        **kwargs: typing.Any,
    ):
        self.my_param = my_param
        widgets.FormatWidgetMixin.__init__(self, format=format, **kwargs)
        widgets.WidgetBase.__init__(self, **kwargs)

    def __call__(self, progress, data, format=None):
        return widgets.FormatWidgetMixin.__call__(self, progress, data)


class OldStyleCounterClone(widgets.FormatWidgetMixin, widgets.WidgetBase):
    """Copies the library's historic ``format=``-leak style verbatim."""

    def __init__(self, format: str = '%(value)d', **kwargs: typing.Any):
        widgets.FormatWidgetMixin.__init__(self, format=format, **kwargs)
        widgets.WidgetBase.__init__(self, format=format, **kwargs)

    def __call__(self, progress, data, format=None):
        return widgets.FormatWidgetMixin.__call__(self, progress, data)


class OldStyleSamplesWidget(widgets.SamplesMixin):
    def __init__(self, **kwargs: typing.Any):
        # samples accepts int per the class docstring/doctest; the
        # timedelta-only annotation is a known typing gap (PR 4).
        widgets.SamplesMixin.__init__(
            self,
            samples=3,  # pyright: ignore[reportArgumentType]
            **kwargs,
        )

    def __call__(self, progress, data):  # pragma: no cover - never rendered
        return str(widgets.SamplesMixin.__call__(self, progress, data))


def test_old_style_widget_constructs_and_renders() -> None:
    widget = OldStyleWidget(min_width=1, max_width=100)
    # kwargs must keep reaching WidthWidgetMixin through both parent calls
    assert widget.min_width == 1
    assert widget.max_width == 100
    assert widget.format == '%(value)d!'
    assert '5!' in _render([widget])


def test_old_style_format_leak_still_constructs() -> None:
    # Must never raise, before or after the super() migration.
    widget = OldStyleCounterClone(min_width=2)
    assert widget.min_width == 2
    assert '5' in _render([widget])


def test_old_style_samples_mixin() -> None:
    widget = OldStyleSamplesWidget()
    assert widget.samples == 3
    assert widget.key_prefix == 'OldStyleSamplesWidget_'


# --- (b) super style: single cooperative call -------------------------------


class SuperStyleWidget(widgets.FormatWidgetMixin, widgets.WidgetBase):
    def __init__(
        self,
        my_param: str = 'x',
        format: str = '%(value)d?',
        **kwargs: typing.Any,
    ):
        self.my_param = my_param
        super().__init__(format=format, **kwargs)

    def __call__(self, progress, data, format=None):
        return super().__call__(progress, data)


def test_super_style_widget_sets_format() -> None:
    # FormatWidgetMixin is first in the MRO, so this works even today.
    widget = SuperStyleWidget()
    assert widget.format == '%(value)d?'


def test_super_style_widget_constructs_and_renders() -> None:
    widget = SuperStyleWidget(min_width=1)
    assert widget.min_width == 1
    assert widget.format == '%(value)d?'
    assert '5?' in _render([widget])


def test_super_style_diamond_subclass() -> None:
    class MyETA(widgets.AdaptiveETA):
        def __init__(self, **kwargs: typing.Any):
            super().__init__(samples=7, **kwargs)

    widget = MyETA()
    assert widget.samples == 7
    _render([widget])


# --- library widgets: constructor kwargs must land where they belong -------


@pytest.mark.parametrize(
    'widget_class, args',
    [
        (widgets.FormatLabel, ('%(value)s',)),
        (widgets.Timer, ()),
        (widgets.ETA, ()),
        (widgets.AdaptiveETA, ()),
        (widgets.Counter, ()),
        (widgets.Percentage, ()),
        (widgets.SimpleProgress, ()),
        (widgets.PercentageLabelBar, ()),
        (widgets.FormatLabelBar, ('%(value)s',)),
    ],
)
def test_width_kwargs_reach_width_mixin(widget_class, args) -> None:
    widget = widget_class(*args, min_width=3, max_width=90)
    assert widget.min_width == 3
    assert widget.max_width == 90


def test_variable_name_reaches_variable_mixin() -> None:
    assert widgets.MultiRangeBar('jobs', markers=[' ', '#']).name == 'jobs'
    assert widgets.JobStatusBar('status').name == 'status'
    assert widgets.Variable('speed', precision=2).name == 'speed'


# --- ProgressBar subclasses, both styles ------------------------------------


class OldStyleBar(progressbar.ProgressBar):
    """Copies the library's current explicit-parent-call style."""

    def __init__(self, *args: typing.Any, **kwargs: typing.Any):
        progressbar.ProgressBar.__init__(self, *args, **kwargs)
        self.custom = True


class SuperStyleBar(progressbar.ProgressBar):
    def __init__(
        self,
        *args: typing.Any,
        my_option: str | None = None,
        **kwargs: typing.Any,
    ):
        self.my_option = my_option
        super().__init__(*args, **kwargs)

    def start(self, *args: typing.Any, **kwargs: typing.Any):
        self.start_hook = True
        return super().start(*args, **kwargs)

    def update(self, value=None, force=False, **kwargs: typing.Any):
        self.update_hook = getattr(self, 'update_hook', 0) + 1
        super().update(value, force=force, **kwargs)


@pytest.mark.parametrize(
    'bar_class',
    [OldStyleBar, SuperStyleBar, progressbar.ProgressBar],
)
def test_bar_subclass_lifecycle(bar_class) -> None:
    fd = io.StringIO()
    with bar_class(fd=fd, max_value=5, term_width=60) as bar:
        for i in range(5):
            bar.update(i + 1, force=True)
    assert bar.finished()
    assert '100%' in fd.getvalue()


def test_index_consumed_once_per_bar() -> None:
    first = progressbar.ProgressBar(
        fd=io.StringIO(), max_value=1, term_width=60
    )
    second = OldStyleBar(fd=io.StringIO(), max_value=1, term_width=60)
    # Bar indexes must stay monotonic, exactly one per instance; the
    # cooperative migration must not make subclasses consume extra ones.
    assert second.index == first.index + 1


# --- golden rendering --------------------------------------------------------


def test_default_widgets_render_identically() -> None:
    fd = io.StringIO()
    bar = progressbar.ProgressBar(
        fd=fd,
        min_value=0,
        max_value=10,
        term_width=80,
        enable_colors=False,
        line_breaks=True,
    )
    bar.start()
    for i in (3, 7, 10):
        bar.update(i, force=True)
    bar.finish()
    out = fd.getvalue()
    assert '100%' in out
    assert '10 of 10' in out
    assert 'Elapsed Time' in out


def test_known_length_render_golden() -> None:
    fd = io.StringIO()
    bar = progressbar.ProgressBar(
        fd=fd,
        max_value=10,
        term_width=40,
        enable_colors=False,
        widgets=[
            widgets.Percentage(),
            ' ',
            widgets.SimpleProgress(),
            ' ',
            widgets.Bar(),
        ],
    )
    bar.start()
    bar.update(5, force=True)
    bar.finish()
    assert _final_line(fd) == GOLDEN_KNOWN_LENGTH_FINAL


def test_unknown_length_render_golden() -> None:
    fd = io.StringIO()
    bar = progressbar.ProgressBar(
        fd=fd,
        max_value=progressbar.UnknownLength,
        term_width=40,
        enable_colors=False,
        widgets=[widgets.Counter(), ' ', widgets.Timer()],
    )
    bar.start()
    bar.update(5, force=True)
    bar.finish()
    assert _final_line(fd) == GOLDEN_UNKNOWN_LENGTH_FINAL


def _final_line(fd: io.StringIO) -> str:
    lines = [
        line.strip('\r') for line in fd.getvalue().splitlines() if line.strip()
    ]
    return lines[-1]


# Exact expected final lines, captured from the current release behavior
# under the deterministic test clock (frozen time -> zero elapsed).
GOLDEN_KNOWN_LENGTH_FINAL: str = '100% 10 of 10 |########################|'
GOLDEN_UNKNOWN_LENGTH_FINAL: str = '5 Elapsed Time: 0:00:00'


# --- post-migration guarantees ----------------------------------------------


def test_no_double_width_mixin_init(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cooperative chain must init each base exactly once.

    Pre-migration, ``Timer`` reached ``WidthWidgetMixin.__init__`` twice
    (once via ``FormatLabel``/``WidgetBase`` and again via
    ``TimeSensitiveWidgetBase``/``WidgetBase``). The single cooperative
    chain must run it exactly once.
    """
    calls = 0
    original = widgets.WidthWidgetMixin.__init__

    def counting_init(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        nonlocal calls
        calls += 1
        original(self, *args, **kwargs)

    monkeypatch.setattr(widgets.WidthWidgetMixin, '__init__', counting_init)
    widgets.Timer()
    assert calls == 1


class OldStyleTwoPhaseColorWidget(
    widgets.FormatWidgetMixin, widgets.WidgetBase
):
    """Old-style widget that reaches ``WidgetBase.__init__`` twice.

    The first parent call carries no color kwargs; the second supplies
    ``fixed_colors=``. ``uses_colors`` must reflect the *final* state, not
    the stale ``False`` cached during the first pass.
    """

    def __init__(self, format: str = '%(value)d', **kwargs: typing.Any):
        # First parent call: no color kwargs (would cache uses_colors=False).
        widgets.FormatWidgetMixin.__init__(self, format=format)
        # Second parent call: colors arrive now.
        widgets.WidgetBase.__init__(
            self,
            fixed_colors=dict(fg_none=widgets.colors.red),
            **kwargs,
        )

    def __call__(self, progress, data, format=None):
        return widgets.FormatWidgetMixin.__call__(self, progress, data)


def test_old_style_two_phase_color_kwargs() -> None:
    # Regression: the cached ``uses_colors`` must be dropped between passes
    # so late-arriving fixed_colors still enable color rendering.
    widget = OldStyleTwoPhaseColorWidget()
    assert widget.uses_colors is True
    assert widget._len is widgets.utils.len_color


def test_super_style_color_kwargs_reach_widget_base() -> None:
    # The cooperative path must also route fixed_colors to WidgetBase.
    widget = SuperStyleWidget(
        fixed_colors=dict(fg_none=widgets.colors.red),
    )
    assert widget.uses_colors is True
    assert widget._len is widgets.utils.len_color
