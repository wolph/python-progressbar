"""A build log printing above a progress bar without corrupting it."""

import time

import progressbar

STEPS = 24


def main() -> None:
    with progressbar.ProgressBar(
        max_value=STEPS,
        prefix='Build ',
        redirect_stdout=True,
    ) as bar:
        for step in range(STEPS):
            if step in {8, 16}:
                print(f'log: completed step {step}')
            bar.update(step + 1)
            # Longer than the bar's 0.05s update gate, so every step
            # lands as a visible redraw.
            time.sleep(0.1)


if __name__ == '__main__':
    main()
