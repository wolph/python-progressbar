import time
import progressbar


def test_large_max_value():
    with progressbar.ProgressBar(max_value=1e10) as bar:
        for i in range(10):
            bar.update(i)
            time.sleep(0.1)
