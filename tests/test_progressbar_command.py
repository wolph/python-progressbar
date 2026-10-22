import io
import pathlib

import pytest

import progressbar
import progressbar.__main__ as main


def test_size_to_bytes() -> None:
    assert main.size_to_bytes('1') == 1
    assert main.size_to_bytes('1k') == 1024
    assert main.size_to_bytes('1m') == 1048576
    assert main.size_to_bytes('1g') == 1073741824
    assert main.size_to_bytes('1p') == 1125899906842624

    assert main.size_to_bytes('1024') == 1024
    assert main.size_to_bytes('1024k') == 1048576
    assert main.size_to_bytes('1024m') == 1073741824
    assert main.size_to_bytes('1024g') == 1099511627776
    assert main.size_to_bytes('1024p') == 1152921504606846976


def test_sleep_for_rate_limit_skips_when_unset(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(main.time, 'sleep', calls.append)
    main._sleep_for_rate_limit(None, transferred=1024, started_at=0, now=1)
    assert calls == []


def test_sleep_for_rate_limit_sleeps_when_ahead(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(main.time, 'sleep', calls.append)
    main._sleep_for_rate_limit(1024, transferred=2048, started_at=0, now=1)
    assert calls == [1]


def test_sleep_for_rate_limit_skips_when_on_schedule(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(main.time, 'sleep', calls.append)
    main._sleep_for_rate_limit(1024, transferred=1024, started_at=0, now=1)
    assert calls == []


def test_main_passes_rate_limit(tmp_path, monkeypatch) -> None:
    sleeps = []
    monkeypatch.setattr(main.time, 'sleep', sleeps.append)
    monkeypatch.setattr(main.time, 'monotonic', lambda: 0)
    file = tmp_path / 'data.bin'
    file.write_bytes(b'x' * 2048)
    main.main(
        ['--rate-limit', '1k', str(file), '-o', str(tmp_path / 'out.bin')],
    )
    assert sleeps


def test_filename_to_bytes(tmp_path) -> None:
    file = tmp_path / 'test'
    file.write_text('test')
    assert main.size_to_bytes(f'@{file}') == 4

    with pytest.raises(FileNotFoundError):
        main.size_to_bytes(f'@{tmp_path / "nonexistent"}')


def test_create_argument_parser() -> None:
    parser = main.create_argument_parser()
    args = parser.parse_args(
        [
            '-p',
            '-t',
            '-e',
            '-r',
            '-a',
            '-b',
            '-8',
            '-T',
            '-n',
            '-q',
            'input',
            '-o',
            'output',
        ]
    )
    assert args.progress is True
    assert args.timer is True
    assert args.eta is True
    assert args.rate is True
    assert args.average_rate is True
    assert args.bytes is True
    assert args.bits is True
    assert args.buffer_percent is True
    assert args.last_written is None
    assert args.format is None
    assert args.numeric is True
    assert args.quiet is True
    assert args.input == ['input']
    assert args.output == 'output'


def test_main_binary(capsys) -> None:
    # Call the main function with different command line arguments
    main.main(
        [
            '-p',
            '-t',
            '-e',
            '-r',
            '-a',
            '-b',
            '-8',
            '-T',
            '-n',
            '-q',
            __file__,
        ]
    )

    captured = capsys.readouterr()
    assert 'test_main(capsys):' in captured.out


def test_main_lines(capsys) -> None:
    # Call the main function with different command line arguments
    main.main(
        [
            '-p',
            '-t',
            '-e',
            '-r',
            '-a',
            '-b',
            '-8',
            '-T',
            '-n',
            '-q',
            '-l',
            '-s',
            f'@{__file__}',
            __file__,
        ]
    )

    captured = capsys.readouterr()
    assert 'test_main(capsys):' in captured.out


class Input(io.StringIO):
    buffer: io.BytesIO

    @classmethod
    def create(cls, text: str) -> 'Input':
        instance = cls(text)
        instance.buffer = io.BytesIO(text.encode())
        return instance


def test_main_lines_output(monkeypatch, tmp_path) -> None:
    text = 'my input'
    monkeypatch.setattr('sys.stdin', Input.create(text))
    output_filename = tmp_path / 'output'
    main.main(['-l', '-o', str(output_filename)])

    assert output_filename.read_text() == text


def test_main_bytes_output(monkeypatch, tmp_path) -> None:
    text = 'my input'

    monkeypatch.setattr('sys.stdin', Input.create(text))
    output_filename = tmp_path / 'output'
    main.main(['-o', str(output_filename)])

    assert output_filename.read_text() == f'{text}'


def test_missing_input(tmp_path) -> None:
    with pytest.raises(SystemExit):
        main.main([str(tmp_path / 'output')])


@pytest.fixture
def recorded_bars(monkeypatch):
    created = []

    class RecordingProgressBar(progressbar.ProgressBar):
        def __init__(self, **kwargs) -> None:
            created.append(self)
            self.init_kwargs = kwargs
            super().__init__(**kwargs)

    class RecordingNullBar(progressbar.NullBar):
        def __init__(self, **kwargs) -> None:
            created.append(self)
            self.init_kwargs = kwargs
            super().__init__(**kwargs)

    monkeypatch.setattr(main.progressbar, 'ProgressBar', RecordingProgressBar)
    monkeypatch.setattr(main.progressbar, 'NullBar', RecordingNullBar)
    return created


def test_build_widgets_honors_display_flags() -> None:
    parser = main.create_argument_parser()
    args = parser.parse_args(
        ['--progress', '--timer', '--eta', '--rate', '--bytes']
    )
    widgets = main._build_widgets(args, filesize_available=True)
    widget_types = tuple(
        type(widget) for widget in widgets if not isinstance(widget, str)
    )
    assert progressbar.Percentage in widget_types
    assert progressbar.Bar in widget_types
    assert progressbar.Timer in widget_types
    assert progressbar.AdaptiveETA in widget_types
    assert progressbar.FileTransferSpeed in widget_types
    assert progressbar.DataSize in widget_types


def test_build_widgets_quiet_is_empty() -> None:
    parser = main.create_argument_parser()
    args = parser.parse_args(['--quiet'])
    assert main._build_widgets(args, filesize_available=True) == []


def test_main_quiet_uses_null_bar(tmp_path, recorded_bars) -> None:
    file = tmp_path / 'data.bin'
    file.write_bytes(b'x' * 16)
    main.main(['--quiet', str(file), '-o', str(tmp_path / 'out.bin')])

    assert isinstance(recorded_bars[0], progressbar.NullBar)


def test_numeric_output_uses_line_breaks(tmp_path, recorded_bars) -> None:
    file = tmp_path / 'data.bin'
    file.write_bytes(b'x' * 16)
    main.main(['--numeric', str(file), '-o', str(tmp_path / 'out.bin')])
    assert recorded_bars[0].init_kwargs['line_breaks'] is True
    assert any(
        isinstance(widget, progressbar.Percentage)
        for widget in recorded_bars[0].init_kwargs['widgets']
    )


def test_main_passes_widgets(tmp_path, recorded_bars) -> None:
    # Regression: E2 - the configured widgets were built but never passed
    # to the progress bar.
    file = tmp_path / 'data.bin'
    file.write_bytes(b'x' * 1024)
    main.main([str(file), '-o', str(tmp_path / 'out.bin')])

    assert recorded_bars
    assert recorded_bars[0].init_kwargs.get('widgets')


def test_main_line_mode_counts_bytes(tmp_path, recorded_bars) -> None:
    # Regression: E1 - line mode counted characters while the maximum was
    # measured in bytes, so multi-byte content never reached 100%.
    file = tmp_path / 'data.txt'
    file.write_text(('é' * 99 + '\n') * 5, encoding='utf-8')
    size = file.stat().st_size

    main.main(['-l', str(file), '-o', str(tmp_path / 'out.txt')])

    assert recorded_bars[0].value == size


def test_main_broken_pipe(tmp_path, monkeypatch) -> None:
    # Regression: E3 - an early-closing downstream pipe raised an
    # unhandled BrokenPipeError.
    file = tmp_path / 'data.bin'
    file.write_bytes(b'x' * 1024)

    class BrokenPipeIO(io.BytesIO):
        def write(self, data) -> int:
            raise BrokenPipeError

    monkeypatch.setattr(
        main, '_get_output_stream', lambda *args: BrokenPipeIO()
    )
    main.main([str(file)])  # must not raise, and must not exit non-zero


def test_main_empty_file_has_known_size(tmp_path, recorded_bars) -> None:
    # Regression: E8 - a zero-byte input flipped the bar into
    # unknown-length mode although the file size was known.
    file = tmp_path / 'empty.bin'
    file.write_bytes(b'')
    main.main([str(file), '-o', str(tmp_path / 'out.bin')])

    assert recorded_bars[0].init_kwargs.get('max_value') == 0


def test_console_scripts_include_the_bar_shorthand() -> None:
    # Both the canonical `progressbar` command and its `bar` shorthand
    # must point at the same entry point: the shorthand exists purely
    # for shorter pipelines (`bar data.bin -o copy.bin`).
    pyproject = (
        pathlib.Path(__file__).parents[1] / 'pyproject.toml'
    ).read_text(encoding='utf-8')

    assert "progressbar = 'progressbar.__main__:main'" in pyproject
    assert "bar = 'progressbar.__main__:main'" in pyproject


def test_missing_input_keeps_existing_output(tmp_path: pathlib.Path) -> None:
    output: pathlib.Path = tmp_path / 'out.bin'
    output.write_bytes(b'precious')
    with pytest.raises(SystemExit) as excinfo:
        main.main([str(tmp_path / 'missing'), '-o', str(output)])
    assert excinfo.value.code == 2
    assert output.read_bytes() == b'precious'


def test_directory_input_is_rejected(tmp_path: pathlib.Path) -> None:
    output: pathlib.Path = tmp_path / 'out.bin'
    output.write_bytes(b'precious')
    with pytest.raises(SystemExit) as excinfo:
        main.main([str(tmp_path), '-o', str(output)])
    assert excinfo.value.code == 2
    assert output.read_bytes() == b'precious'


def test_output_same_as_input_is_rejected(tmp_path: pathlib.Path) -> None:
    file: pathlib.Path = tmp_path / 'data.bin'
    file.write_bytes(b'precious')
    with pytest.raises(SystemExit) as excinfo:
        main.main([str(file), '-o', str(file)])
    assert excinfo.value.code == 2
    assert file.read_bytes() == b'precious'


@pytest.mark.parametrize(
    'option', [['-B', '0'], ['-B', 'abc'], ['-s', 'x'], ['-L', 'abc']]
)
def test_invalid_size_options_are_rejected(
    tmp_path: pathlib.Path, option: list[str]
) -> None:
    file: pathlib.Path = tmp_path / 'data.bin'
    file.write_bytes(b'x' * 16)
    output: pathlib.Path = tmp_path / 'out.bin'
    output.write_bytes(b'precious')
    with pytest.raises(SystemExit) as excinfo:
        main.main([*option, str(file), '-o', str(output)])
    assert excinfo.value.code == 2
    assert output.read_bytes() == b'precious'


def test_keyboard_interrupt_exits_130(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file: pathlib.Path = tmp_path / 'data.bin'
    file.write_bytes(b'x' * 4096)

    class InterruptingIO(io.BytesIO):
        def write(self, data: object) -> int:
            raise KeyboardInterrupt

    monkeypatch.setattr(
        main, '_get_output_stream', lambda *args: InterruptingIO()
    )
    with pytest.raises(SystemExit) as excinfo:
        main.main([str(file)])
    assert excinfo.value.code == main.EXIT_INTERRUPTED


def test_inputs_are_closed_after_their_copy(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files: list[pathlib.Path] = []
    for index in range(3):
        file: pathlib.Path = tmp_path / f'data{index}.bin'
        file.write_bytes(b'x' * 8)
        files.append(file)

    opened: list[io.BufferedReader] = []
    open_counts: list[int] = []
    original_open = pathlib.Path.open

    def recording_open(self: pathlib.Path, *args: object, **kwargs: object):
        open_counts.append(sum(not stream.closed for stream in opened))
        stream = original_open(self, *args, **kwargs)  # type: ignore[arg-type]
        opened.append(stream)
        return stream

    monkeypatch.setattr(pathlib.Path, 'open', recording_open)
    main.main([*map(str, files), '-o', str(tmp_path / 'out.bin')])
    assert open_counts == [0, 0, 0]
    assert all(stream.closed for stream in opened)
    assert (tmp_path / 'out.bin').read_bytes() == b'x' * 24


def test_output_directory_is_rejected(tmp_path: pathlib.Path) -> None:
    source: pathlib.Path = tmp_path / 'in.bin'
    source.write_bytes(b'data')
    with pytest.raises(SystemExit) as excinfo:
        main.main([str(source), '-o', str(tmp_path)])
    assert excinfo.value.code == 2


def test_existing_output_distinct_from_inputs_is_overwritten(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source: pathlib.Path = tmp_path / 'in.bin'
    source.write_bytes(b'new')
    output: pathlib.Path = tmp_path / 'out.bin'
    output.write_bytes(b'old contents')
    monkeypatch.setattr('sys.stdin', io.TextIOWrapper(io.BytesIO(b'')))
    main.main([str(source), '-', '-o', str(output)])
    assert output.read_bytes() == b'new'


def test_empty_size_option_means_not_given(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source: pathlib.Path = tmp_path / 'in.bin'
    source.write_bytes(b'data')
    output: pathlib.Path = tmp_path / 'out.bin'
    monkeypatch.setattr('sys.stdin', io.TextIOWrapper(io.BytesIO(b'')))
    main.main(
        ['-q', '-s', '', '-B', '', '-L', '', str(source), '-o', str(output)]
    )
    assert output.read_bytes() == b'data'


def test_output_on_a_device_shared_with_an_input_is_allowed() -> None:
    if not pathlib.Path('/dev/null').exists():
        pytest.skip('no /dev/null on this platform')
    main.main(['-q', '/dev/null', '-o', '/dev/null'])  # must not exit 2


@pytest.mark.parametrize('mode', [[], ['-l']])
def test_pipeline_reader_closing_early_exits_zero(
    tmp_path: pathlib.Path, mode: list[str]
) -> None:
    import os
    import subprocess
    import sys

    if not hasattr(os, 'fork'):
        pytest.skip('needs a POSIX pipe')
    source: pathlib.Path = tmp_path / 'big.bin'
    source.write_bytes(b'line of text\n' * 200_000)
    env: dict[str, str] = dict(os.environ)
    env['PYTHONPATH'] = str(pathlib.Path(progressbar.__file__).parents[1])
    proc = subprocess.Popen(
        [sys.executable, '-m', 'progressbar', '-q', *mode, str(source)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert proc.stdout is not None
    proc.stdout.read(1)
    proc.stdout.close()  # the reader goes away, as `| head -c 1` does
    _, stderr = proc.communicate(timeout=60)
    assert proc.returncode == 0, stderr.decode()
    assert b'Exception ignored' not in stderr


def test_broken_pipe_on_stdout_discards_the_descriptor(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    file: pathlib.Path = tmp_path / 'data.bin'
    file.write_bytes(b'x' * 1024)

    class BrokenStdout(io.BytesIO):
        def write(self, data) -> int:
            raise BrokenPipeError

    broken: BrokenStdout = BrokenStdout()
    discarded: list[bool] = []
    monkeypatch.setattr(main, '_get_output_stream', lambda *args: broken)
    monkeypatch.setattr(main.sys, 'stdout', broken)
    monkeypatch.setattr(
        main, '_discard_broken_stdout', lambda: discarded.append(True)
    )
    main.main([str(file)])
    assert discarded == [True]


def test_discard_broken_stdout_points_fd_at_devnull(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os

    read_end, write_end = os.pipe()
    os.close(read_end)  # the reader is gone
    saved_stdout: int = os.dup(1)
    os.dup2(write_end, 1)

    class FakeStdout:
        def fileno(self) -> int:
            return 1

    monkeypatch.setattr(main.sys, 'stdout', FakeStdout())
    try:
        main._discard_broken_stdout()
        os.write(1, b'late output')  # would raise EPIPE before
        assert os.fstat(1).st_ino == os.stat(os.devnull).st_ino
    finally:
        os.dup2(saved_stdout, 1)
        os.close(saved_stdout)
        os.close(write_end)


def test_discard_broken_stdout_leaves_other_descriptors_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import io
    import os

    read_end, write_end = os.pipe()

    class PipeStdout:  # an application's own pager pipe installed as stdout
        def fileno(self) -> int:
            return write_end

    monkeypatch.setattr(main.sys, 'stdout', PipeStdout())
    try:
        main._discard_broken_stdout()
        os.write(write_end, b'XYZ')
        assert os.read(read_end, 3) == b'XYZ'  # still the pipe, not devnull
    finally:
        os.close(read_end)
        os.close(write_end)

    monkeypatch.setattr(main.sys, 'stdout', io.StringIO())
    main._discard_broken_stdout()  # no fileno(): nothing to do, no raise
