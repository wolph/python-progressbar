from __future__ import print_function

import time
import progressbar


def test_flush():
    '''Left justify using the terminal width'''
    p = progressbar.ProgressBar(poll_interval=0.001)

    for i in range(10):
        print('pre-updates', p.updates)
        p.update(i)
        print('need update?', p._needs_update())
        if i > 5:
            time.sleep(0.1)
        print('post-updates', p.updates)

