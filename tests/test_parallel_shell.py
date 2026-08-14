"""The `run()` shell helper and its brace-safe template engine."""

from __future__ import annotations

import subprocess
import sys
import typing

import pytest

from progressbar._parallel import (
    _shell,
    _sync,
)

#: A tiny portable command: exit with the given code.
_EXIT: list[str] = [sys.executable, '-c', 'import sys; sys.exit(0)']


class TestBuildArgv:
    def test_str_template_placeholder(self) -> None:
        assert _shell.build_argv('gzip -k {}', 'a.txt', shell=False) == [
            'gzip',
            '-k',
            'a.txt',
        ]

    def test_item_with_spaces_stays_one_argument(self) -> None:
        assert _shell.build_argv('gzip -k {}', 'a file.txt', shell=False) == [
            'gzip',
            '-k',
            'a file.txt',
        ]

    def test_literal_braces_survive(self) -> None:
        # str.format would blow up on awk's braces; replacement of the
        # exact placeholder token must not.
        argv = _shell.build_argv(
            "awk '{print $1}' {}", 'data.csv', shell=False
        )
        assert argv == ['awk', '{print $1}', 'data.csv']

    def test_item_placeholder_synonym(self) -> None:
        assert _shell.build_argv(
            'convert {item} out-{item}.png', 'x', shell=False
        ) == ['convert', 'x', 'out-x.png']

    def test_no_placeholder_appends_item(self) -> None:
        assert _shell.build_argv('gzip -k', 'a.txt', shell=False) == [
            'gzip',
            '-k',
            'a.txt',
        ]

    def test_list_template(self) -> None:
        assert _shell.build_argv(
            ['ffmpeg', '-i', '{}', '{}.mp4'], 'in.avi', shell=False
        ) == ['ffmpeg', '-i', 'in.avi', 'in.avi.mp4']

    def test_list_without_placeholder_appends(self) -> None:
        assert _shell.build_argv(['echo'], 'hi', shell=False) == [
            'echo',
            'hi',
        ]

    def test_callable_template(self) -> None:
        assert _shell.build_argv(
            lambda item: ['echo', str(item).upper()], 'hi', shell=False
        ) == ['echo', 'HI']

    def test_shell_string_replacement(self) -> None:
        command = _shell.build_argv(
            'gzip -k {} > /dev/null', 'a.txt', shell=True
        )
        assert command == 'gzip -k a.txt > /dev/null'

    def test_shell_string_appends_quoted(self) -> None:
        command = _shell.build_argv('gzip -k', 'a file.txt', shell=True)
        assert command == "gzip -k 'a file.txt'"


class TestRun:
    @pytest.mark.no_freezegun
    def test_runs_commands_and_returns_completed_processes(self) -> None:
        results: list[subprocess.CompletedProcess[str]] = _shell.run(
            [sys.executable, '-c', 'print({})'],
            [1, 2, 3],
            workers=2,
            bar=False,
        )
        assert [proc.stdout.strip() for proc in results] == ['1', '2', '3']
        assert all(proc.returncode == 0 for proc in results)

    @pytest.mark.no_freezegun
    def test_check_raises_called_process_error(self) -> None:
        with pytest.raises(subprocess.CalledProcessError):
            _shell.run(
                [sys.executable, '-c', 'import sys; sys.exit({})'],
                [0, 1],
                workers=1,
                bar=False,
            )

    @pytest.mark.no_freezegun
    def test_check_false_returns_failures(self) -> None:
        results = _shell.run(
            [sys.executable, '-c', 'import sys; sys.exit({})'],
            [0, 1],
            check=False,
            workers=1,
            bar=False,
        )
        assert [proc.returncode for proc in results] == [0, 1]

    @pytest.mark.no_freezegun
    def test_on_error_return_embeds_the_error(self) -> None:
        results: list[typing.Any] = _shell.run(
            [sys.executable, '-c', 'import sys; sys.exit({})'],
            [0, 1],
            on_error='return',
            workers=1,
            bar=False,
        )
        assert results[0].returncode == 0
        assert isinstance(results[1], subprocess.CalledProcessError)

    def test_pool_kwarg_rejected(self) -> None:
        with pytest.raises(TypeError, match=r'Pool\.run'):
            _shell.run(_EXIT, [1], pool='process', bar=False)

    @pytest.mark.no_freezegun
    def test_pool_run_method(self) -> None:
        with _sync.Pool(2) as pool:
            results = pool.run(_EXIT, range(2), bar=False)
        assert all(proc.returncode == 0 for proc in results)
