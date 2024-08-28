import io

import pytest

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
