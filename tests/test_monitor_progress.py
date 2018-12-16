import pprint

pytest_plugins = 'pytester'


def test_list_example(testdir):
    ''' Run the simple example code in a python subprocess and then compare its
        stderr to what we expect to see from it.  We run it in a subprocess to
        best capture its stderr. We expect to see match_lines in order in the
        output.  This test is just a sanity check to ensure that the progress
        bar progresses from 1 to 10, it does not make sure that the '''

    v = testdir.makepyfile('''
    import time
    import timeit
    import freezegun
    import progressbar

    with freezegun.freeze_time() as fake_time:
        timeit.default_timer = time.time
        bar = progressbar.ProgressBar(term_width=65)
        bar._MINIMUM_UPDATE_INTERVAL = 1e-9
        for i in bar(list(range(9))):
            fake_time.tick(1)
    ''')
    result = testdir.runpython(v)
    result.stderr.lines = [l.rstrip() for l in result.stderr.lines
                           if l.strip()]
    pprint.pprint(result.stderr.lines, width=70)
    result.stderr.fnmatch_lines([
        'N/A% (0 of 9) |            | Elapsed Time: ?:00:00 ETA:  --:--:--',
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


def test_generator_example(testdir):
    ''' Run the simple example code in a python subprocess and then compare its
        stderr to what we expect to see from it.  We run it in a subprocess to
        best capture its stderr. We expect to see match_lines in order in the
        output.  This test is just a sanity check to ensure that the progress
        bar progresses from 1 to 10, it does not make sure that the '''

    v = testdir.makepyfile('''
    import time
    import timeit
    import freezegun
    import progressbar

    with freezegun.freeze_time() as fake_time:
        timeit.default_timer = time.time
        bar = progressbar.ProgressBar(term_width=60)
        bar._MINIMUM_UPDATE_INTERVAL = 1e-9
        for i in bar(iter(range(9))):
            fake_time.tick(1)
    ''')
    result = testdir.runpython(v)
    result.stderr.lines = [l for l in result.stderr.lines if l.strip()]
    pprint.pprint(result.stderr.lines, width=70)

    lines = []
    for i in range(9):
        lines.append(
            r'[/\\|\-]\s+\|\s*#\s*\| %(i)d Elapsed Time: \d:00:%(i)02d' %
            dict(i=i))

    result.stderr.re_match_lines(lines)


def test_rapid_updates(testdir):
    ''' Run some example code that updates 10 times, then sleeps .1 seconds,
        this is meant to test that the progressbar progresses normally with
        this sample code, since there were issues with it in the past '''

    v = testdir.makepyfile('''
    import time
    import timeit
    import freezegun
    import progressbar

    with freezegun.freeze_time() as fake_time:
        timeit.default_timer = time.time
        bar = progressbar.ProgressBar(term_width=60)
        bar._MINIMUM_UPDATE_INTERVAL = 1e-9
        for i in bar(range(10)):
            if i < 5:
                fake_time.tick(1)
            else:
                fake_time.tick(2)
    ''')
    result = testdir.runpython(v)
    result.stderr.lines = [l for l in result.stderr.lines if l.strip()]
    pprint.pprint(result.stderr.lines, width=70)
    result.stderr.fnmatch_lines([
        'N/A% (0 of 10) |      | Elapsed Time: ?:00:00 ETA:  --:--:--',
        ' 10% (1 of 10) |      | Elapsed Time: ?:00:01 ETA:   ?:00:09',
        ' 20% (2 of 10) |#     | Elapsed Time: ?:00:02 ETA:   ?:00:08',
        ' 30% (3 of 10) |#     | Elapsed Time: ?:00:03 ETA:   ?:00:07',
        ' 40% (4 of 10) |##    | Elapsed Time: ?:00:04 ETA:   ?:00:06',
        ' 50% (5 of 10) |###   | Elapsed Time: ?:00:05 ETA:   ?:00:05',
        ' 60% (6 of 10) |###   | Elapsed Time: ?:00:07 ETA:   ?:00:06',
        ' 70% (7 of 10) |####  | Elapsed Time: ?:00:09 ETA:   ?:00:06',
        ' 80% (8 of 10) |####  | Elapsed Time: ?:00:11 ETA:   ?:00:04',
        ' 90% (9 of 10) |##### | Elapsed Time: ?:00:13 ETA:   ?:00:02',
        '100% (10 of 10) |#####| Elapsed Time: ?:00:15 Time:  ?:00:15'
    ])


def test_context_wrapper(testdir):
    v = testdir.makepyfile('''
    import time
    import timeit
    import freezegun
    import progressbar

    with freezegun.freeze_time() as fake_time:
        timeit.default_timer = time.time
        with progressbar.ProgressBar(term_width=60) as bar:
            bar._MINIMUM_UPDATE_INTERVAL = 1e-9
            for _ in bar(list(range(5))):
                fake_time.tick(1)
    ''')

    result = testdir.runpython(v)
    result.stderr.lines = [l for l in result.stderr.lines if l.strip()]
    pprint.pprint(result.stderr.lines, width=70)
    result.stderr.fnmatch_lines([
        'N/A% (0 of 5) |       | Elapsed Time: ?:00:00 ETA:  --:--:--',
        ' 20% (1 of 5) |#      | Elapsed Time: ?:00:01 ETA:   ?:00:04',
        ' 40% (2 of 5) |##     | Elapsed Time: ?:00:02 ETA:   ?:00:03',
        ' 60% (3 of 5) |####   | Elapsed Time: ?:00:03 ETA:   ?:00:02',
        ' 80% (4 of 5) |#####  | Elapsed Time: ?:00:04 ETA:   ?:00:01',
        '100% (5 of 5) |#######| Elapsed Time: ?:00:05 Time:  ?:00:05',
    ])
