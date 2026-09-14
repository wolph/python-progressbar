"""Show a percentage and a bar that changes colour as work progresses."""

import time

import progressbar


def main() -> None:
    for _ in progressbar.progressbar(
        range(100),
        widgets=[progressbar.Percentage(), ' ', progressbar.Bar()],
    ):
        time.sleep(0.03)


if __name__ == '__main__':
    main()
