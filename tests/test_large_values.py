import time
import progressbar


def test_large_max_value():
    with progressbar.ProgressBar(max_value=1e10) as bar:
        for i in range(10):
            bar.update(i)
            time.sleep(0.1)


def test_value_beyond_max_value():
    with progressbar.ProgressBar(max_value=10, max_error=False) as bar:
        for i in range(20):
            bar.update(i)
            time.sleep(0.01)
