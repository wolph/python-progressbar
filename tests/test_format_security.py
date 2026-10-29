"""Format templates must not walk private attributes or crash on desc."""

from __future__ import annotations

import io

import pytest

import progressbar


def _render(**kwargs: object) -> str:
    fd: io.StringIO = io.StringIO()
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=fd,
        max_value=10,
        term_width=200,
        **kwargs,  # type: ignore[arg-type]
    )
    bar.start()
    bar.update(5)
    bar.finish()
    return fd.getvalue()


def test_desc_attribute_walk_renders_literally() -> None:
    desc: str = (
        '{variables.__class__.__getattr__.__globals__[os].environ[HOME]}'
    )
    output: str = _render(desc=desc)
    assert desc + ': ' in output


def test_desc_with_braces_renders_literally() -> None:
    output: str = _render(desc='report{2024}.txt')
    assert 'report{2024}.txt: ' in output


def test_prefix_private_attribute_raises() -> None:
    with pytest.raises(ValueError, match='__class__'):
        _render(prefix='{variables.__class__}')


def test_prefix_value_template_still_renders() -> None:
    output: str = _render(prefix='{value} ')
    assert '10 ' in output


def test_prefix_variable_template_still_renders() -> None:
    output: str = _render(
        prefix='{variables.name} ',
        variables={'name': 'spam'},
    )
    assert 'spam ' in output


def test_variable_format_private_attribute_raises() -> None:
    widget: progressbar.Variable = progressbar.Variable(
        'name',
        format='{formatted_value.__class__}',
    )
    with pytest.raises(ValueError, match='__class__'):
        _render(widgets=[widget], variables={'name': 'eggs'})


def test_format_error_logs_keys_not_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with pytest.raises(KeyError):
        _render(prefix='{missing} ', variables={'secret': 'hunter2'})
    assert 'hunter2' not in caplog.text


@pytest.mark.parametrize('raw', ['', 'inf', 'nan', 'spam', '-1'])
def test_bad_minimum_update_interval_env_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
) -> None:
    monkeypatch.setenv('PROGRESSBAR_MINIMUM_UPDATE_INTERVAL', raw)
    from progressbar import bar as bar_module

    assert bar_module._env_minimum_update_interval() == 0.0
    output: str = _render()
    assert output


def test_valid_minimum_update_interval_env_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('PROGRESSBAR_MINIMUM_UPDATE_INTERVAL', '0.5')
    from progressbar import bar as bar_module

    assert bar_module._env_minimum_update_interval() == 0.5


# ---- round-3 take-backs -------------------------------------------------


class _LazyStr:
    """A translation proxy shape: not a str, but has format() and __str__."""

    def __init__(self, text: str) -> None:
        self.text: str = text

    def format(self, *args: object, **kwargs: object) -> str:
        return self.text.format(*args, **kwargs)

    def __str__(self) -> str:
        return self.text


def _label_data() -> tuple[progressbar.ProgressBar, dict[str, object]]:
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=io.StringIO(), max_value=10, variables={'_x': 'v1', 'x': 1}
    )
    bar.start()
    bar.update(3, _x='v2')
    return bar, dict(bar.data())


def test_lazy_template_object_renders() -> None:
    bar, data = _label_data()
    label = progressbar.FormatLabel(
        _LazyStr('{value} of {max_value}'),  # type: ignore[arg-type]
        new_style=True,
    )
    assert label(bar, data) == '3 of 10'


def test_single_underscore_variable_renders() -> None:
    bar, data = _label_data()
    label = progressbar.FormatLabel('{variables._x}', new_style=True)
    assert label(bar, data) == 'v2'


def test_dunder_attribute_still_refused() -> None:
    bar, data = _label_data()
    label = progressbar.FormatLabel('{variables.x.__class__}', new_style=True)
    with pytest.raises(ValueError, match='__class__'):
        label(bar, data)


def test_prefix_reassigned_after_desc_is_a_template() -> None:
    fd: io.StringIO = io.StringIO()
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=fd, max_value=10, desc='d', widgets=[progressbar.SimpleProgress()]
    )
    bar.prefix = 'late {value} '
    bar.start()
    bar.update(4, force=True)
    assert 'late 4 4 of 10' in fd.getvalue()
    assert '{value}' not in fd.getvalue()


def test_format_error_with_non_str_keys_raises_the_template_error() -> None:
    bar, data = _label_data()
    data[0] = 'zero'  # type: ignore[index]
    label = progressbar.FormatLabel('{nope}', new_style=True)
    with pytest.raises(KeyError, match='nope'):
        label(bar, data)


def test_bad_minimum_update_interval_env_logs_a_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    from progressbar import bar as bar_module

    bar_module._reset_bad_interval_warnings()
    monkeypatch.setenv('PROGRESSBAR_MINIMUM_UPDATE_INTERVAL', 'spam')
    with caplog.at_level(logging.WARNING, logger='progressbar.bar'):
        progressbar.ProgressBar(fd=io.StringIO(), max_value=10)
    assert any(
        'PROGRESSBAR_MINIMUM_UPDATE_INTERVAL' in record.getMessage()
        and 'spam' in record.getMessage()
        for record in caplog.records
    )


def test_non_text_template_without_format_raises() -> None:
    bar, data = _label_data()

    class NotCallableFormat:
        format = 'text'

    for template in (None, ['{value}'], 42, NotCallableFormat()):
        label = progressbar.FormatLabel(template, new_style=True)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            label(bar, data)


def test_bad_minimum_update_interval_env_warns_once_per_value(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    from progressbar import bar as bar_module

    bar_module._reset_bad_interval_warnings()
    monkeypatch.setenv('PROGRESSBAR_MINIMUM_UPDATE_INTERVAL', 'eggs')
    with caplog.at_level(logging.WARNING, logger='progressbar.bar'):
        for _ in range(3):
            progressbar.ProgressBar(fd=io.StringIO(), max_value=10)
    records = [r for r in caplog.records if 'eggs' in r.getMessage()]
    assert len(records) == 1


def test_bad_interval_warning_is_once_per_value_beyond_sixteen_and_threadsafe(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import logging
    import threading

    from progressbar import bar as bar_module

    bar_module._reset_bad_interval_warnings()
    with caplog.at_level(logging.WARNING, logger='progressbar.bar'):
        for i in range(17):
            bar_module._warn_bad_minimum_update_interval(f'bad-{i}')
        bar_module._warn_bad_minimum_update_interval('bad-0')
        barrier: threading.Barrier = threading.Barrier(4)

        def warn() -> None:
            barrier.wait()
            bar_module._warn_bad_minimum_update_interval('concurrent')

        threads: list[threading.Thread] = [
            threading.Thread(target=warn) for _ in range(4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    messages: list[str] = [r.getMessage() for r in caplog.records]
    assert sum("'bad-0'" in m for m in messages) == 1
    assert sum("'concurrent'" in m for m in messages) == 1
    assert len(messages) == 18


def test_desc_prefix_is_a_format_label_that_renders_literally() -> None:
    fd: io.StringIO = io.StringIO()
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=fd,
        max_value=10,
        desc='{files}',
        widgets=[progressbar.SimpleProgress()],
    )
    assert bar.prefix == '{files}: '  # read back unescaped, as in 4.6.0
    bar.start()
    assert isinstance(bar.widgets[0], progressbar.FormatLabel)  # as in 4.6.0
    bar.update(4, force=True)
    assert '{files}: 4 of 10' in fd.getvalue()


def test_desc_with_braces_renders_literally_on_the_fast_path() -> None:
    fd: io.StringIO = io.StringIO()
    bar: progressbar.ProgressBar = progressbar.ProgressBar(
        fd=fd, max_value=10, desc='{files}'
    )
    bar.start()
    bar.update(4, force=True)
    assert '{files}: ' in fd.getvalue()
    assert '{{files}}' not in fd.getvalue()
    fast: progressbar.FastProgressBar = progressbar.FastProgressBar(
        fd=io.StringIO(), max_value=10, desc='{files}'
    )
    assert fast.prefix == '{files}: '
    from progressbar import fast as fast_module

    line: str = fast_module._pure_format_fast_line(fast)
    assert line.startswith('{files}: ')


def test_frame_walks_are_refused_like_dunders() -> None:
    import sys
    import types

    bar, data = _label_data()
    frame: types.FrameType = sys._getframe()
    data['variables'] = progressbar.utils.AttributeDict(frame=frame)
    for template in (
        '{variables.frame.f_globals}',
        '{variables.frame.f_locals}',
        '{variables.frame.f_back}',
    ):
        label = progressbar.FormatLabel(template, new_style=True)
        with pytest.raises(ValueError, match='not allowed'):
            label(bar, data)


def test_specialised_template_preserves_markup_escaping_and_type() -> None:
    from markupsafe import Markup

    bar, data = _label_data()
    data['value'] = '<tag>'
    label: progressbar.FormatLabel = progressbar.FormatLabel(
        Markup('{value}'), new_style=True
    )
    result: str = label(bar, data)
    assert result == '&lt;tag&gt;'
    assert isinstance(result, Markup)


@pytest.mark.parametrize(
    'template',
    [
        '{value.__class__!s}',
        '{value:{width.__class__}}',
        '{value:{width.f_globals}}',
        '{value!z}',
        '{value:{width:{precision}}}',
    ],
)
def test_specialised_template_validates_before_delegation(
    template: str,
) -> None:
    calls: list[str] = []

    class Template(str):
        def format(self, *args: object, **kwargs: object) -> str:
            calls.append(self)
            return 'specialised'

    bar, data = _label_data()
    label: progressbar.FormatLabel = progressbar.FormatLabel(
        Template(template), new_style=True
    )
    with pytest.raises(ValueError):
        label(bar, data)
    assert calls == []


def test_specialised_proxy_preserves_format_method() -> None:
    class Template(_LazyStr):
        def format(self, *args: object, **kwargs: object) -> str:
            return 'specialised:' + super().format(*args, **kwargs)

    bar, data = _label_data()
    label: progressbar.FormatLabel = progressbar.FormatLabel(
        Template('{value}'), new_style=True
    )  # type: ignore[arg-type]
    assert label(bar, data) == 'specialised:3'


def test_specialised_str_cannot_hide_field_paths_in_str_override() -> None:
    calls: list[str] = []

    class Template(str):
        def __str__(self) -> str:
            return '{value}'

        def format(self, *args: object, **kwargs: object) -> str:
            calls.append('called')
            return super().format(*args, **kwargs)

    bar, data = _label_data()
    label: progressbar.FormatLabel = progressbar.FormatLabel(
        Template('{value.__class__}'), new_style=True
    )
    with pytest.raises(ValueError, match='__class__'):
        label(bar, data)
    assert calls == []


def test_specialised_template_allows_literal_braces_and_nested_width() -> None:
    from markupsafe import Markup

    bar, data = _label_data()
    data['width'] = 3
    label: progressbar.FormatLabel = progressbar.FormatLabel(
        Markup('{{literal}} {value:0{width}d}'), new_style=True
    )
    assert label(bar, data) == '{literal} 003'
