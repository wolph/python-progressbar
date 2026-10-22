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

    bar_module._warn_bad_minimum_update_interval.cache_clear()
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

    bar_module._warn_bad_minimum_update_interval.cache_clear()
    monkeypatch.setenv('PROGRESSBAR_MINIMUM_UPDATE_INTERVAL', 'eggs')
    with caplog.at_level(logging.WARNING, logger='progressbar.bar'):
        for _ in range(3):
            progressbar.ProgressBar(fd=io.StringIO(), max_value=10)
    records = [r for r in caplog.records if 'eggs' in r.getMessage()]
    assert len(records) == 1
