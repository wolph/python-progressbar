from __future__ import annotations

# fmt: off
import os
import pprint

import progressbar

pytest_plugins = 'pytester'

SCRIPT = """
import sys
sys.path.append({progressbar_path!r})
import time
import timeit
import freezegun
import progressbar


with freezegun.freeze_time() as fake_time:
    timeit.default_timer = time.time
    with progressbar.ProgressBar(widgets={widgets}, **{kwargs!r}) as bar:
        bar._MINIMUM_UPDATE_INTERVAL = 1e-9
        for i in bar({items}):
            {loop_code}
"""


def _non_empty_lines(lines):
    return [line for line in lines if line.strip()]


def _create_script(
    widgets=None,
    items: list[int] | None=None,
    loop_code: str='fake_time.tick(1)',
    term_width: int=60,
    **kwargs,
) -> str:
    if items is None:
        items = list(range(9))
    kwargs['term_width'] = term_width

    # Reindent the loop code
    indent = '\n            '
    loop_code = loop_code.strip('\n').split('\n')
    dedent = len(loop_code[0]) - len(loop_code[0].lstrip())
    for i, line in enumerate(loop_code):
        loop_code[i] = line[dedent:]

    script = SCRIPT.format(
        items=items,
        widgets=widgets,
        kwargs=kwargs,
        loop_code=indent.join(loop_code),
        progressbar_path=os.path.dirname(
            os.path.dirname(progressbar.__file__),
        ),
    )
    print('# Script:')
    print('#' * 78)
    print(script)
    print('#' * 78)

    return script


def test_list_example(testdir) -> None:
    """Run the simple example code in a python subprocess and then compare its
    stderr to what we expect to see from it.  We run it in a subprocess to
    best capture its stderr. We expect to see match_lines in order in the
    output.  This test is just a sanity check to ensure that the progress
    bar progresses from 1 to 10, it does not make sure that the"""

    result = testdir.runpython(
        testdir.makepyfile(
            _create_script(
                term_width=65,
            ),
        ),
    )
    result.stderr.lines = [
        line.rstrip() for line in _non_empty_lines(result.stderr.lines)
    ]
    pprint.pprint(result.stderr.lines, width=70)
    result.stderr.fnmatch_lines([
        '  0% (0 of 9) |            | Elapsed Time: ?:00:00 ETA:  --:--:--',
        ' 11% (1 of 9) |#           | Elapsed Time: ?:00:01 ETA:   ?:00:08',
        ' 22% (2 of 9) |##          | Elapsed Time: ?:00:02 ETA:   ?:00:07',
        ' 33% (3 of 9) |####        | Elapsed Time: ?:00:03 ETA:   ?:00:06',
        ' 44% (4 of 9) |#####       | Elapsed Time: ?:00:04 ETA:   ?:00:05',
        ' 55% (5 of 9) |######      | Elapsed Time: ?:00:05 ETA:   ?:00:04',
        ' 66% (6 of 9) |########    | Elapsed Time: ?:00:06 ETA:   ?:00:03',
        ' 77% (7 of 9) |#########   | Elapsed Time: ?:00:07 ETA:   ?:00:02',
        ' 88% (8 of 9) |##########  | Elapsed Time: ?:00:08 ETA:   ?:00:01',
        '100% (9 of 9) |############| Elapsed Time: ?:00:09 Time:  ?:00:09',
    ])


def test_generator_example(testdir) -> None:
    """Run the simple example code in a python subprocess and then compare its
    stderr to what we expect to see from it.  We run it in a subprocess to
    best capture its stderr. We expect to see match_lines in order in the
    output.  This test is just a sanity check to ensure that the progress
    bar progresses from 1 to 10, it does not make sure that the"""
    result = testdir.runpython(
        testdir.makepyfile(
            _create_script(
                items='iter(range(9))',
            ),
        ),
    )
    result.stderr.lines = _non_empty_lines(result.stderr.lines)
    pprint.pprint(result.stderr.lines, width=70)

    lines = [
        r'[/\\|\-]\s+\|\s*#\s*\| %(i)d Elapsed Time: \d:00:%(i)02d' % dict(i=i)
        for i in range(9)
    ]
    result.stderr.re_match_lines(lines)


def test_rapid_updates(testdir) -> None:
    """Run some example code that updates 10 times, then sleeps .1 seconds,
    this is meant to test that the progressbar progresses normally with
    this sample code, since there were issues with it in the past"""

    result = testdir.runpython(
        testdir.makepyfile(
            _create_script(
                term_width=60,
                items=list(range(10)),
                loop_code="""
        if i < 5:
            fake_time.tick(1)
        else:
            fake_time.tick(2)
        """,
            ),
        ),
    )
    result.stderr.lines = _non_empty_lines(result.stderr.lines)
    pprint.pprint(result.stderr.lines, width=70)
    result.stderr.fnmatch_lines(
        [
            '  0% (0 of 10) |      | Elapsed Time: 0:00:00 ETA:  --:--:--',
            ' 10% (1 of 10) |      | Elapsed Time: 0:00:01 ETA:   0:00:09',
            ' 20% (2 of 10) |#     | Elapsed Time: 0:00:02 ETA:   0:00:08',
            ' 30% (3 of 10) |#     | Elapsed Time: 0:00:03 ETA:   0:00:07',
            ' 40% (4 of 10) |##    | Elapsed Time: 0:00:04 ETA:   0:00:06',
            ' 50% (5 of 10) |###   | Elapsed Time: 0:00:05 ETA:   0:00:05',
            ' 60% (6 of 10) |###   | Elapsed Time: 0:00:07 ETA:   0:00:04',
            ' 70% (7 of 10) |####  | Elapsed Time: 0:00:09 ETA:   0:00:03',
            ' 80% (8 of 10) |####  | Elapsed Time: 0:00:11 ETA:   0:00:02',
            ' 90% (9 of 10) |##### | Elapsed Time: 0:00:13 ETA:   0:00:01',
            '100% (10 of 10) |#####| Elapsed Time: 0:00:15 Time:  0:00:15',
        ],
    )


def test_non_timed(testdir) -> None:
    result = testdir.runpython(
        testdir.makepyfile(
            _create_script(
                widgets='[progressbar.Percentage(), progressbar.Bar()]',
                items=list(range(5)),
            ),
        ),
    )
    result.stderr.lines = _non_empty_lines(result.stderr.lines)
    pprint.pprint(result.stderr.lines, width=70)
    result.stderr.fnmatch_lines(
        [
            '  0%|                                                      |',
            ' 20%|##########                                            |',
            ' 40%|#####################                                 |',
            ' 60%|################################                      |',
            ' 80%|###########################################           |',
            '100%|######################################################|',
        ],
    )


def test_line_breaks(testdir) -> None:
    result = testdir.runpython(
        testdir.makepyfile(
            _create_script(
                widgets='[progressbar.Percentage(), progressbar.Bar()]',
                line_breaks=True,
                items=list(range(5)),
            ),
        ),
    )
    pprint.pprint(result.stderr.str(), width=70)
    assert result.stderr.str() == '\n'.join(
        (
            '  0%|                                                      |',
            ' 20%|##########                                            |',
            ' 40%|#####################                                 |',
            ' 60%|################################                      |',
            ' 80%|###########################################           |',
            '100%|######################################################|',
            '100%|######################################################|',
        ),
    )


def test_no_line_breaks(testdir) -> None:
    result = testdir.runpython(
        testdir.makepyfile(
            _create_script(
                widgets='[progressbar.Percentage(), progressbar.Bar()]',
                line_breaks=False,
                items=list(range(5)),
            ),
        ),
    )
    pprint.pprint(result.stderr.lines, width=70)
    assert result.stderr.lines == [
        '',
        '  0%|                                                      |',
        ' 20%|##########                                            |',
        ' 40%|#####################                                 |',
        ' 60%|################################                      |',
        ' 80%|###########################################           |',
        '100%|######################################################|',
        '',
        '100%|######################################################|',
    ]


def test_percentage_label_bar(testdir) -> None:
    result = testdir.runpython(
        testdir.makepyfile(
            _create_script(
                widgets='[progressbar.PercentageLabelBar()]',
                line_breaks=False,
                items=list(range(5)),
            ),
        ),
    )
    pprint.pprint(result.stderr.lines, width=70)
    assert result.stderr.lines == [
        '',
        '|                            0%                            |',
        '|###########                20%                            |',
        '|#######################    40%                            |',
        '|###########################60%####                        |',
        '|###########################80%################            |',
        '|###########################100%###########################|',
        '',
        '|###########################100%###########################|',
    ]


def test_granular_bar(testdir) -> None:
    result = testdir.runpython(
        testdir.makepyfile(
            _create_script(
                widgets='[progressbar.GranularBar(markers=" .oO")]',
                line_breaks=False,
                items=list(range(5)),
            ),
        ),
    )
    pprint.pprint(result.stderr.lines, width=70)
    assert result.stderr.lines == [
        '',
        '|                                                          |',
        '|OOOOOOOOOOO.                                              |',
        '|OOOOOOOOOOOOOOOOOOOOOOO                                   |',
        '|OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOo                       |',
        '|OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO.           |',
        '|OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO|',
        '',
        '|OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO|',
    ]


def test_colors(testdir) -> None:
    kwargs = dict(
        items=range(1),
        widgets=['\033[92mgreen\033[0m'],
    )

    result = testdir.runpython(
        testdir.makepyfile(_create_script(enable_colors=True, **kwargs)),
    )
    pprint.pprint(result.stderr.lines, width=70)
    assert result.stderr.lines == ['\x1b[92mgreen\x1b[0m'] * 3

    result = testdir.runpython(
        testdir.makepyfile(_create_script(enable_colors=False, **kwargs)),
    )
    pprint.pprint(result.stderr.lines, width=70)
    assert result.stderr.lines == ['green'] * 3
