import os
import sys
import time

import pytest

if os.name == 'nt':
    import win32console  # "pip install pypiwin32" to get this
else:
    pytest.skip('skipping windows-only tests', allow_module_level=True)

import progressbar

pytest_plugins = 'pytester'
_WIDGETS = [
    progressbar.Percentage(),
    ' ',
    progressbar.Bar(),
    ' ',
    progressbar.FileTransferSpeed(),
    ' ',
    progressbar.ETA(),
]
_MB: int = 1024 * 1024


# ---------------------------------------------------------------------------
def scrape_console(line_count):
    pcsb = win32console.GetStdHandle(win32console.STD_OUTPUT_HANDLE)
    csbi = pcsb.GetConsoleScreenBufferInfo()
    col_max = csbi['Size'].X
    row_max = csbi['CursorPosition'].Y

    line_count = min(line_count, row_max)
    lines = []
    for row in range(line_count):
        pct = win32console.PyCOORDType(0, row + row_max - line_count)
        line = pcsb.ReadConsoleOutputCharacter(col_max, pct)
        lines.append(line.rstrip())
    return lines


# ---------------------------------------------------------------------------
def runprogress() -> int:
    print('***BEGIN***')
    b = progressbar.ProgressBar(
        widgets=['example.m4v: ', *_WIDGETS],
        max_value=10 * _MB,
    )
    for i in range(10):
        b.update((i + 1) * _MB)
        time.sleep(0.25)
    b.finish()
    print('***END***')
    return 0


# ---------------------------------------------------------------------------
def find(lines, x):
    try:
        return lines.index(x)
    except ValueError:
        return -sys.maxsize


# ---------------------------------------------------------------------------
def test_windows(testdir: pytest.Testdir) -> None:
    testdir.run(
        sys.executable, '-c', 'import progressbar; print(progressbar.__file__)'
    )


def main() -> int:
    runprogress()

    scraped_lines = scrape_console(100)
    # reverse lines so we find the LAST instances of output.
    scraped_lines.reverse()
    index_begin = find(scraped_lines, '***BEGIN***')
    index_end = find(scraped_lines, '***END***')

    if index_end + 2 != index_begin:
        print('ERROR: Unexpected multi-line output from progressbar')
        print(f'{index_begin=} {index_end=}')
        return 1
    return 0


if __name__ == '__main__':
    main()


def test_kernel32_argtypes() -> None:
    # Regression: E4 - missing argtypes silently truncated 64-bit HANDLE
    # values to 32-bit C ints.
    from progressbar.terminal.os_specific import windows

    assert windows._GetConsoleMode.argtypes is not None
    assert windows._SetConsoleMode.argtypes is not None
    assert windows._GetStdHandle.argtypes is not None
    assert windows._ReadConsoleInput.argtypes is not None


def test_getch_reads_first_event(monkeypatch) -> None:
    # Regression: E5 - getch() unconditionally decoded the second buffer
    # entry, ignoring how many events were actually read.
    from progressbar.terminal.os_specific import windows

    def fake_read_console_input(handle, buffer, length, events_read):
        buffer[0].Event.KeyEvent.uChar.AsciiChar = b'a'
        events_read._obj.value = 1
        return 1

    monkeypatch.setattr(
        windows, '_ReadConsoleInput', fake_read_console_input
    )
    assert windows.getch() == 'a'
