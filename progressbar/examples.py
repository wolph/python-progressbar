#!/usr/bin/python

import time

from progressbar import ProgressBar, Percentage, Bar, ETA, FileTransferSpeed, \
     RotatingMarker, ReverseBar, SimpleProgress

def example0():
    pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=300).start()
    for i in range(300):
        time.sleep(0.01)
        pbar.update(i+1)
    pbar.finish()
    print

def example1():
    widgets = ['Test: ', Percentage(), ' ', Bar(marker=RotatingMarker()),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
    for i in range(1000000):
        # do something
        pbar.update(10*i+1)
    pbar.finish()
    print

def example2():
    class CrazyFileTransferSpeed(FileTransferSpeed):
        "It's bigger between 45 and 80 percent"
        def update(self, pbar):
            if 45 < pbar.percentage() < 80:
                return 'Bigger Now ' + FileTransferSpeed.update(self,pbar)
            else:
                return FileTransferSpeed.update(self,pbar)

    widgets = [CrazyFileTransferSpeed(),' <<<', Bar(), '>>> ', Percentage(),' ', ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=10000000)
    # maybe do something
    pbar.start()
    for i in range(2000000):
        # do something
        pbar.update(5*i+1)
    pbar.finish()
    print

def example3():
    widgets = [Bar('>'), ' ', ETA(), ' ', ReverseBar('<')]
    pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
    for i in range(1000000):
        # do something
        pbar.update(10*i+1)
    pbar.finish()
    print

def example4():
    widgets = ['Test: ', Percentage(), ' ',
               Bar(marker='0',left='[',right=']'),
               ' ', ETA(), ' ', FileTransferSpeed()]
    pbar = ProgressBar(widgets=widgets, maxval=500)
    pbar.start()
    for i in range(100,500+1,50):
        time.sleep(0.2)
        pbar.update(i)
    pbar.finish()
    print

def example5():
  pbar = ProgressBar(widgets=[SimpleProgress()], maxval=17).start()
  for i in range(17):
    time.sleep(0.2)
    pbar.update(i + 1)
  pbar.finish()
  print

example0()
example1()
example2()
example3()
example4()
example5()
