import time
import sys
import pytest

if sys.platform.startswith('win'):
    import win32console  # "pip install pypiwin32" to get this
else:
    pytest.skip('skipping windows-only tests', allow_module_level=True)


import progressbar

_WIDGETS = [progressbar.Percentage(), ' ',
            progressbar.Bar(), ' ',
            progressbar.FileTransferSpeed(), ' ',
            progressbar.ETA()]
_MB = 1024 * 1024


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
def runprogress():
    print('***BEGIN***')
    b = progressbar.ProgressBar(widgets=['example.m4v: '] + _WIDGETS,
                                max_value=10 * _MB)
    for i in range(10):
        b.update((i + 1) * _MB)
        time.sleep(0.25)
    b.finish()
    print('***END***')
    return 0


# ---------------------------------------------------------------------------
def find(L, x):
    try:
        return L.index(x)
    except ValueError:
        return -sys.maxsize


# ---------------------------------------------------------------------------
def test_windows():
    runprogress()

    scraped_lines = scrape_console(100)
    scraped_lines.reverse()  # reverse lines so we find the LAST instances of output.
    index_begin = find(scraped_lines, '***BEGIN***')
    index_end = find(scraped_lines, '***END***')

    if index_end + 2 != index_begin:
        print('ERROR: Unexpected multi-line output from progressbar')
        print(f'{index_begin=} {index_end=}')
        return 1
    return 0
