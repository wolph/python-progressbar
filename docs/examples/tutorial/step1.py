"""Wrap an iterable to show its progress."""

import time

import progressbar


def main() -> None:
    for _ in progressbar.progressbar(range(100)):
        time.sleep(0.01)


if __name__ == '__main__':
    main()
