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
