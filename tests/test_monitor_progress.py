pytest_plugins = 'pytester'


def test_list_example(testdir):
    ''' Run the simple example code in a python subprocess and then compare its
        stderr to what we expect to see from it.  We run it in a subprocess to
        best capture its stderr. We expect to see match_lines in order in the
        output.  This test is just a sanity check to ensure that the progress
        bar progresses from 1 to 10, it does not make sure that the '''
    v = testdir.makepyfile('''
        import time
        import progressbar

        bar = progressbar.ProgressBar(term_width=60)
        for i in bar(list(range(10))):
            time.sleep(0.05)

    ''')
    result = testdir.runpython(v)
    result.stderr.lines = [l for l in result.stderr.lines if l.strip()]
    result.stderr.re_match_lines([
        r'N/A% \(0 of 10\) \|\s+\| Elapsed Time: 0:00:00 ETA:  --:--:--',
        r' 10% \(1 of 10\) \|\s+\| Elapsed Time: 0:00:00 ETA:  0:00:00',
        r' 20% \(2 of 10\) \|#+\s+\| Elapsed Time: 0:00:00 ETA:  0:00:00',
        r' 30% \(3 of 10\) \|#+\s+\| Elapsed Time: 0:00:00 ETA:  0:00:00',
        r' 40% \(4 of 10\) \|#+\s+\| Elapsed Time: 0:00:00 ETA:  0:00:00',
        r' 50% \(5 of 10\) \|#+\s+\| Elapsed Time: 0:00:00 ETA:  0:00:00',
        r' 60% \(6 of 10\) \|#+\s+\| Elapsed Time: 0:00:00 ETA:  0:00:00',
        r' 70% \(7 of 10\) \|#+\s+\| Elapsed Time: 0:00:00 ETA:  0:00:00',
        r' 80% \(8 of 10\) \|#+\s+\| Elapsed Time: 0:00:00 ETA:  0:00:00',
        r' 90% \(9 of 10\) \|#+\s+\| Elapsed Time: 0:00:00 ETA:  0:00:00',
        r'100% \(10 of 10\) \|#+\| Elapsed Time: 0:00:00 Time: 0:00:00',
    ])


def test_generator_example(testdir):
    ''' Run the simple example code in a python subprocess and then compare its
        stderr to what we expect to see from it.  We run it in a subprocess to
        best capture its stderr. We expect to see match_lines in order in the
        output.  This test is just a sanity check to ensure that the progress
        bar progresses from 1 to 10, it does not make sure that the '''
    v = testdir.makepyfile('''
        import time
        import progressbar

        bar = progressbar.ProgressBar(term_width=60)
        for i in bar(iter(range(10))):
            time.sleep(0.05)

    ''')
    result = testdir.runpython(v)
    print('##################')
    import pprint
    pprint.pprint([l.strip() for l in result.stderr.lines if l.strip()])
    print('##################')
    result.stderr.re_match_lines([
        r'/ 0 Elapsed Time: 0:00:00',
        r'- 1 Elapsed Time: 0:00:00',
        r'\\ 2 Elapsed Time: 0:00:00',
        r'\| 3 Elapsed Time: 0:00:00',
        r'/ 4 Elapsed Time: 0:00:00',
        r'- 5 Elapsed Time: 0:00:00',
        r'\\ 6 Elapsed Time: 0:00:00',
        r'\| 7 Elapsed Time: 0:00:00',
        r'/ 8 Elapsed Time: 0:00:00',
        r'- 9 Elapsed Time: 0:00:00',
        r'\| 9 Elapsed Time: 0:00:00',
    ])


def test_rapid_updates(testdir):
    ''' Run some example code that updates 10 times, then sleeps .1 seconds,
        this is meant to test that the progressbar progresses normally with
        this sample code, since there were issues with it in the past '''
    v = testdir.makepyfile('''
        import time
        import progressbar

        bar = progressbar.ProgressBar(term_width=60)
        for i in bar(range(100)):
            if i % 10 == 0:
                time.sleep(0.05)

    ''')
    result = testdir.runpython(v)
    result.stderr.re_match_lines([
        r'  1% \(1 of 100\)',
        r' 11% \(11 of 100\)',
        r' 21% \(21 of 100\)',
        r' 31% \(31 of 100\)',
        r' 41% \(41 of 100\)',
        r' 51% \(51 of 100\)',
        r' 61% \(61 of 100\)',
        r' 71% \(71 of 100\)',
        r' 81% \(81 of 100\)',
        r' 91% \(91 of 100\)',
        r'100% \(100 of 100\)'
    ])
