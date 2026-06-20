import io

import progressbar


def test_with() -> None:
    with progressbar.ProgressBar(max_value=10) as p:
        for i in range(10):
            p.update(i)


def test_with_stdout_redirection() -> None:
    with progressbar.ProgressBar(max_value=10, redirect_stdout=True) as p:
        for i in range(10):
            p.update(i)


def test_with_extra_start() -> None:
    with progressbar.ProgressBar(max_value=10) as p:
        p.start()
        p.start()


def test_context_manager_and_iterable_no_duplicate() -> None:
    # Regression #301: using a bar as BOTH a context manager and an iterable
    # wrapper finished it twice and drew the bar twice.
    fd = io.StringIO()
    with progressbar.ProgressBar(
        max_value=10, fd=fd, is_terminal=True, term_width=40
    ) as bar:
        for _ in bar(range(10)):
            pass
    # The completed bar must be rendered exactly once; the bug finished the
    # bar twice (StopIteration and then __exit__), drawing it a second time.
    assert fd.getvalue().count('100% (10 of 10)') == 1, repr(fd.getvalue())
