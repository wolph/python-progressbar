pytest_plugins = "pytester"


def test_simple_example(testdir):
    """ Run the simple example code in a python subprocess and then compare its
        stderr to what we expect to see from it.  We run it in a subprocess to
        best capture its stderr. We expect to see match_lines in order in the
        output.  This test is just a sanity check to ensure that the progress
        bar progresses from 1 to 10, it does not make sure that the """
    v = testdir.makepyfile("""
        import time
        import progressbar

        bar = progressbar.ProgressBar()
        for i in bar(range(10)):
            time.sleep(0.1)

    """)
    result = testdir.runpython(v)
    result.stderr.re_match_lines([
        " 10% \(1 of 10\)",
        " 20% \(2 of 10\)",
        " 30% \(3 of 10\)",
        " 40% \(4 of 10\)",
        " 50% \(5 of 10\)",
        " 60% \(6 of 10\)",
        " 70% \(7 of 10\)",
        " 80% \(8 of 10\)",
        " 90% \(9 of 10\)",
        "100% \(10 of 10\)"
    ])


def test_rapid_updates(testdir):
    """ Run some example code that updates 10 times, then sleeps .1 seconds,
        this is meant to test that the progressbar progresses normally with
        this sample code, since there were issues with it in the past """
    v = testdir.makepyfile("""
        import time
        import progressbar

        bar = progressbar.ProgressBar()
        for i in bar(range(100)):
            if i % 10 == 0:
                time.sleep(0.1)

    """)
    result = testdir.runpython(v)
    result.stderr.re_match_lines([
        "  1% \(1 of 100\)",
        " 11% \(11 of 100\)",
        " 21% \(21 of 100\)",
        " 31% \(31 of 100\)",
        " 41% \(41 of 100\)",
        " 51% \(51 of 100\)",
        " 61% \(61 of 100\)",
        " 71% \(71 of 100\)",
        " 81% \(81 of 100\)",
        " 91% \(91 of 100\)",
        "100% \(100 of 100\)"
    ])
