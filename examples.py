#!/usr/bin/python
from __future__ import annotations

import contextlib
import functools
import os
import random
import sys
import time
import typing

import progressbar

examples: list[typing.Callable[[typing.Any], typing.Any]] = []


def example(fn):
    """Wrap the examples so they generate readable output"""

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            sys.stdout.write(f'Running: {fn.__name__}\n')
            fn(*args, **kwargs)
            sys.stdout.write('\n')
        except KeyboardInterrupt:
            sys.stdout.write('\nSkipping example.\n\n')
            # Sleep a bit to make killing the script easier
            time.sleep(0.2)

    examples.append(wrapped)
    return wrapped


@example
def fast_example() -> None:
    """Updates bar really quickly to cause flickering"""
    with progressbar.ProgressBar(widgets=[progressbar.Bar()]) as bar:
        for i in range(100):
            bar.update(int(i / 10), force=True)


@example
def shortcut_example() -> None:
    for _ in progressbar.progressbar(range(10)):
        time.sleep(0.1)


@example
def prefixed_shortcut_example() -> None:
    for _ in progressbar.progressbar(range(10), prefix='Hi: '):
        time.sleep(0.1)


@example
def parallel_bars_multibar_example() -> None:
    if os.name == 'nt':
        print(
            'Skipping multibar example on Windows due to threading '
            'incompatibilities with the example code.'
        )
        return

    BARS = 5
    N = 50

    def do_something(bar):
        for _ in bar(range(N)):
            # Sleep up to 0.1 seconds
            time.sleep(random.random() * 0.1)

    with progressbar.MultiBar() as multibar:
        bar_labels = []
        for i in range(BARS):
            # Get a progressbar
            bar_label = 'Bar #%d' % i
            bar_labels.append(bar_label)
            multibar[bar_label]

        for _ in range(N * BARS):
            time.sleep(0.005)

            bar_i = random.randrange(0, BARS)
            bar_label = bar_labels[bar_i]
            # Increment one of the progress bars at random
            multibar[bar_label].increment()


@example
def multiple_bars_line_offset_example() -> None:
    BARS = 5
    N = 100

    bars = [
        progressbar.ProgressBar(
            max_value=N,
            # We add 1 to the line offset to account for the `print_fd`
            line_offset=i + 1,
            max_error=False,
        )
        for i in range(BARS)
    ]
    # Create a file descriptor for regular printing as well
    print_fd = progressbar.LineOffsetStreamWrapper(lines=0, stream=sys.stdout)
    assert print_fd

    # The progress bar updates, normally you would do something useful here
    for _ in range(N * BARS):
        time.sleep(0.005)

        # Increment one of the progress bars at random
        bars[random.randrange(0, BARS)].increment()

    # Cleanup the bars
    for bar in bars:
        bar.finish()
        # Add a newline to make sure the next print starts on a new line
        print()


@example
def templated_shortcut_example() -> None:
    for _ in progressbar.progressbar(range(10), suffix='{seconds_elapsed:.1}'):
        time.sleep(0.1)


@example
def job_status_example() -> None:
    with progressbar.ProgressBar(
        redirect_stdout=True,
        widgets=[progressbar.widgets.JobStatusBar('status')],
    ) as bar:
        for _ in range(30):
            print('random', random.random())
            # Roughly 1/3 probability for each status ;)
            # Yes... probability is confusing at times
            if random.random() > 0.66:
                bar.increment(status=True)
            elif random.random() > 0.5:
                bar.increment(status=False)
            else:
                bar.increment(status=None)
            time.sleep(0.1)


@example
def with_example_stdout_redirection() -> None:
    with progressbar.ProgressBar(max_value=10, redirect_stdout=True) as p:
        for i in range(10):
            if i % 3 == 0:
                print('Some print statement %i' % i)
            # do something
            p.update(i)
            time.sleep(0.1)


@example
def basic_widget_example() -> None:
    widgets = [progressbar.Percentage(), progressbar.Bar()]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=10).start()
    for i in range(10):
        # do something
        time.sleep(0.1)
        bar.update(i + 1)
    bar.finish()


@example
def color_bar_example() -> None:
    widgets = [
        '\x1b[33mColorful example\x1b[39m',
        progressbar.Percentage(),
        progressbar.Bar(marker='\x1b[32m#\x1b[39m'),
    ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=10).start()
    for i in range(10):
        # do something
        time.sleep(0.1)
        bar.update(i + 1)
    bar.finish()


@example
def color_bar_animated_marker_example() -> None:
    widgets = [
        # Colored animated marker with colored fill:
        progressbar.Bar(
            marker=progressbar.AnimatedMarker(
                fill='x',
                # fill='█',
                fill_wrap='\x1b[32m{}\x1b[39m',
                marker_wrap='\x1b[31m{}\x1b[39m',
            )
        ),
    ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=10).start()
    for i in range(10):
        # do something
        time.sleep(0.1)
        bar.update(i + 1)
    bar.finish()


@example
def multi_range_bar_example() -> None:
    markers = [
        '\x1b[32m█\x1b[39m',  # Done
        '\x1b[33m#\x1b[39m',  # Processing
        '\x1b[31m.\x1b[39m',  # Scheduling
        ' ',  # Not started
    ]
    widgets = [progressbar.MultiRangeBar('amounts', markers=markers)]
    amounts = [0] * (len(markers) - 1) + [25]

    with progressbar.ProgressBar(widgets=widgets, max_value=10).start() as bar:
        while True:
            incomplete_items = [
                idx
                for idx, amount in enumerate(amounts)
                for _ in range(amount)
                if idx != 0
            ]
            if not incomplete_items:
                break
            which = random.choice(incomplete_items)
            amounts[which] -= 1
            amounts[which - 1] += 1

            bar.update(amounts=amounts, force=True)
            time.sleep(0.02)


@example
def multi_progress_bar_example(left: bool = True) -> None:
    jobs = [
        # Each job takes between 1 and 10 steps to complete
        [0, random.randint(1, 10)]
        for _ in range(25)  # 25 jobs total
    ]

    widgets = [
        progressbar.Percentage(),
        ' ',
        progressbar.MultiProgressBar('jobs', fill_left=left),
    ]

    max_value = sum([total for progress, total in jobs])
    with progressbar.ProgressBar(widgets=widgets, max_value=max_value) as bar:
        while True:
            incomplete_jobs = [
                idx
                for idx, (progress, total) in enumerate(jobs)
                if progress < total
            ]
            if not incomplete_jobs:
                break
            which = random.choice(incomplete_jobs)
            jobs[which][0] += 1
            progress = sum([progress for progress, total in jobs])

            bar.update(progress, jobs=jobs, force=True)
            time.sleep(0.02)


@example
def granular_progress_example() -> None:
    widgets = [
        progressbar.GranularBar(markers=' ▏▎▍▌▋▊▉█', left='', right='|'),
        progressbar.GranularBar(markers=' ▁▂▃▄▅▆▇█', left='', right='|'),
        progressbar.GranularBar(markers=' ▖▌▛█', left='', right='|'),
        progressbar.GranularBar(markers=' ░▒▓█', left='', right='|'),
        progressbar.GranularBar(markers=' ⡀⡄⡆⡇⣇⣧⣷⣿', left='', right='|'),
        progressbar.GranularBar(markers=' .oO', left='', right=''),
    ]
    for _ in progressbar.progressbar(list(range(100)), widgets=widgets):
        time.sleep(0.03)

    for _ in progressbar.progressbar(iter(range(100)), widgets=widgets):
        time.sleep(0.03)


@example
def percentage_label_bar_example() -> None:
    widgets = [progressbar.PercentageLabelBar()]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=10).start()
    for i in range(10):
        # do something
        time.sleep(0.1)
        bar.update(i + 1)
    bar.finish()


@example
def file_transfer_example() -> None:
    widgets = [
        'Test: ',
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(marker=progressbar.RotatingMarker()),
        ' ',
        progressbar.ETA(),
        ' ',
        progressbar.FileTransferSpeed(),
    ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=1000).start()
    for i in range(100):
        # do something
        time.sleep(0.01)
        bar.update(10 * i + 1)
    bar.finish()


@example
def custom_file_transfer_example() -> None:
    class CrazyFileTransferSpeed(progressbar.FileTransferSpeed):
        """
        It's bigger between 45 and 80 percent
        """

        def update(self, bar):
            if 45 < bar.percentage() < 80:
                return 'Bigger Now ' + progressbar.FileTransferSpeed.update(
                    self, bar
                )
            else:
                return progressbar.FileTransferSpeed.update(self, bar)

    widgets = [
        CrazyFileTransferSpeed(),
        ' <<<',
        progressbar.Bar(),
        '>>> ',
        progressbar.Percentage(),
        ' ',
        progressbar.ETA(),
    ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=1000)
    # maybe do something
    bar.start()
    for i in range(200):
        # do something
        time.sleep(0.01)
        bar.update(5 * i + 1)
    bar.finish()


@example
def double_bar_example() -> None:
    widgets = [
        progressbar.Bar('>'),
        ' ',
        progressbar.ETA(),
        ' ',
        progressbar.ReverseBar('<'),
    ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=1000).start()
    for i in range(100):
        # do something
        time.sleep(0.01)
        bar.update(10 * i + 1)
    bar.finish()


@example
def basic_file_transfer() -> None:
    widgets = [
        'Test: ',
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(marker='0', left='[', right=']'),
        ' ',
        progressbar.ETA(),
        ' ',
        progressbar.FileTransferSpeed(),
    ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=500)
    bar.start()
    # Go beyond the max_value
    for i in range(100, 501, 50):
        time.sleep(0.1)
        bar.update(i)
    bar.finish()


@example
def simple_progress() -> None:
    bar = progressbar.ProgressBar(
        widgets=[progressbar.SimpleProgress()],
        max_value=17,
    ).start()
    for i in range(17):
        time.sleep(0.1)
        bar.update(i + 1)
    bar.finish()


@example
def basic_progress() -> None:
    bar = progressbar.ProgressBar().start()
    for i in range(10):
        time.sleep(0.1)
        bar.update(i + 1)
    bar.finish()


@example
def progress_with_automatic_max() -> None:
    # Progressbar can guess max_value automatically.
    bar = progressbar.ProgressBar()
    for _ in bar(range(8)):
        time.sleep(0.1)


@example
def progress_with_unavailable_max() -> None:
    # Progressbar can't guess max_value.
    bar = progressbar.ProgressBar(max_value=8)
    for _ in bar(i for i in range(8)):
        time.sleep(0.1)


@example
def animated_marker() -> None:
    bar = progressbar.ProgressBar(
        widgets=['Working: ', progressbar.AnimatedMarker()]
    )
    for _ in bar(i for i in range(5)):
        time.sleep(0.1)


@example
def filling_bar_animated_marker() -> None:
    bar = progressbar.ProgressBar(
        widgets=[
            progressbar.Bar(
                marker=progressbar.AnimatedMarker(fill='#'),
            ),
        ]
    )
    for _ in bar(range(15)):
        time.sleep(0.1)


@example
def counter_and_timer() -> None:
    widgets = [
        'Processed: ',
        progressbar.Counter('Counter: %(value)05d'),
        ' lines (',
        progressbar.Timer(),
        ')',
    ]
    bar = progressbar.ProgressBar(widgets=widgets)
    for _ in bar(i for i in range(15)):
        time.sleep(0.1)


@example
def format_label() -> None:
    widgets = [
        progressbar.FormatLabel('Processed: %(value)d lines (in: %(elapsed)s)')
    ]
    bar = progressbar.ProgressBar(widgets=widgets)
    for _ in bar(i for i in range(15)):
        time.sleep(0.1)


@example
def animated_balloons() -> None:
    widgets = ['Balloon: ', progressbar.AnimatedMarker(markers='.oO@* ')]
    bar = progressbar.ProgressBar(widgets=widgets)
    for _ in bar(i for i in range(24)):
        time.sleep(0.1)


@example
def animated_arrows() -> None:
    # You may need python 3.x to see this correctly
    try:
        widgets = ['Arrows: ', progressbar.AnimatedMarker(markers='←↖↑↗→↘↓↙')]
        bar = progressbar.ProgressBar(widgets=widgets)
        for _ in bar(i for i in range(24)):
            time.sleep(0.1)
    except UnicodeError:
        sys.stdout.write('Unicode error: skipping example')


@example
def animated_filled_arrows() -> None:
    # You may need python 3.x to see this correctly
    try:
        widgets = ['Arrows: ', progressbar.AnimatedMarker(markers='◢◣◤◥')]
        bar = progressbar.ProgressBar(widgets=widgets)
        for _ in bar(i for i in range(24)):
            time.sleep(0.1)
    except UnicodeError:
        sys.stdout.write('Unicode error: skipping example')


@example
def animated_wheels() -> None:
    # You may need python 3.x to see this correctly
    try:
        widgets = ['Wheels: ', progressbar.AnimatedMarker(markers='◐◓◑◒')]
        bar = progressbar.ProgressBar(widgets=widgets)
        for _ in bar(i for i in range(24)):
            time.sleep(0.1)
    except UnicodeError:
        sys.stdout.write('Unicode error: skipping example')


@example
def format_label_bouncer() -> None:
    widgets = [
        progressbar.FormatLabel('Bouncer: value %(value)d - '),
        progressbar.BouncingBar(),
    ]
    bar = progressbar.ProgressBar(widgets=widgets)
    for _ in bar(i for i in range(100)):
        time.sleep(0.01)


@example
def format_label_rotating_bouncer() -> None:
    widgets = [
        progressbar.FormatLabel('Animated Bouncer: value %(value)d - '),
        progressbar.BouncingBar(marker=progressbar.RotatingMarker()),
    ]

    bar = progressbar.ProgressBar(widgets=widgets)
    for _ in bar(i for i in range(18)):
        time.sleep(0.1)


@example
def with_right_justify() -> None:
    with progressbar.ProgressBar(
        max_value=10, term_width=20, left_justify=False
    ) as progress:
        assert progress.term_width is not None
        for i in range(10):
            progress.update(i)


@example
def exceeding_maximum() -> None:
    with progressbar.ProgressBar(max_value=1) as progress, contextlib.suppress(
        ValueError
    ):
        progress.update(2)


@example
def reaching_maximum() -> None:
    progress = progressbar.ProgressBar(max_value=1)
    with contextlib.suppress(RuntimeError):
        progress.update(1)


@example
def stdout_redirection() -> None:
    with progressbar.ProgressBar(redirect_stdout=True) as progress:
        print('', file=sys.stdout)
        progress.update(0)


@example
def stderr_redirection() -> None:
    with progressbar.ProgressBar(redirect_stderr=True) as progress:
        print('', file=sys.stderr)
        progress.update(0)


@example
def rotating_bouncing_marker() -> None:
    widgets = [progressbar.BouncingBar(marker=progressbar.RotatingMarker())]
    with progressbar.ProgressBar(
        widgets=widgets, max_value=20, term_width=10
    ) as progress:
        for i in range(20):
            time.sleep(0.1)
            progress.update(i)

    widgets = [
        progressbar.BouncingBar(
            marker=progressbar.RotatingMarker(), fill_left=False
        )
    ]
    with progressbar.ProgressBar(
        widgets=widgets, max_value=20, term_width=10
    ) as progress:
        for i in range(20):
            time.sleep(0.1)
            progress.update(i)


@example
def incrementing_bar() -> None:
    bar = progressbar.ProgressBar(
        widgets=[
            progressbar.Percentage(),
            progressbar.Bar(),
        ],
        max_value=10,
    ).start()
    for _ in range(10):
        # do something
        time.sleep(0.1)
        bar += 1
    bar.finish()


@example
def increment_bar_with_output_redirection() -> None:
    widgets = [
        'Test: ',
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(marker=progressbar.RotatingMarker()),
        ' ',
        progressbar.ETA(),
        ' ',
        progressbar.FileTransferSpeed(),
    ]
    bar = progressbar.ProgressBar(
        widgets=widgets, max_value=100, redirect_stdout=True
    ).start()
    for i in range(10):
        # do something
        time.sleep(0.01)
        bar += 10
        print('Got', i)
    bar.finish()


@example
def eta_types_demonstration() -> None:
    widgets = [
        progressbar.Percentage(),
        ' ETA: ',
        progressbar.ETA(),
        ' Adaptive : ',
        progressbar.AdaptiveETA(),
        ' Smoothing(a=0.1): ',
        progressbar.SmoothingETA(smoothing_parameters=dict(alpha=0.1)),
        ' Smoothing(a=0.9): ',
        progressbar.SmoothingETA(smoothing_parameters=dict(alpha=0.9)),
        ' Absolute: ',
        progressbar.AbsoluteETA(),
        ' Transfer: ',
        progressbar.FileTransferSpeed(),
        ' Adaptive T: ',
        progressbar.AdaptiveTransferSpeed(),
        ' ',
        progressbar.Bar(),
    ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=500)
    bar.start()
    for i in range(500):
        if i < 100:
            time.sleep(0.02)
        elif i > 400:
            time.sleep(0.1)
        else:
            time.sleep(0.01)
        bar.update(i + 1)
    bar.finish()


@example
def adaptive_eta_without_value_change() -> None:
    # Testing progressbar.AdaptiveETA when the value doesn't actually change
    bar = progressbar.ProgressBar(
        widgets=[
            progressbar.AdaptiveETA(),
            progressbar.AdaptiveTransferSpeed(),
        ],
        max_value=2,
        poll_interval=0.0001,
    )
    bar.start()
    for _ in range(100):
        bar.update(1)
        time.sleep(0.1)
    bar.finish()


@example
def iterator_with_max_value() -> None:
    # Testing using progressbar as an iterator with a max value
    bar = progressbar.ProgressBar()

    for _ in bar(iter(range(100)), 100):
        # iter range is a way to get an iterator in both python 2 and 3
        time.sleep(0.01)


@example
def eta() -> None:
    widgets = [
        'Test: ',
        progressbar.Percentage(),
        ' | ETA: ',
        progressbar.ETA(),
        ' | AbsoluteETA: ',
        progressbar.AbsoluteETA(),
        ' | AdaptiveETA: ',
        progressbar.AdaptiveETA(),
    ]
    bar = progressbar.ProgressBar(widgets=widgets, max_value=50).start()
    for i in range(50):
        time.sleep(0.1)
        bar.update(i + 1)
    bar.finish()


@example
def variables() -> None:
    # Use progressbar.Variable to keep track of some parameter(s) during
    # your calculations
    widgets = [
        progressbar.Percentage(),
        progressbar.Bar(),
        progressbar.Variable('loss'),
        ', ',
        progressbar.Variable('username', width=12, precision=12),
    ]
    with progressbar.ProgressBar(max_value=100, widgets=widgets) as bar:
        min_so_far = 1
        for i in range(100):
            time.sleep(0.01)
            val = random.random()
            if val < min_so_far:
                min_so_far = val
            bar.update(i, loss=min_so_far, username='Some user')


@example
def user_variables() -> None:
    tasks = {
        'Download': [
            'SDK',
            'IDE',
            'Dependencies',
        ],
        'Build': [
            'Compile',
            'Link',
        ],
        'Test': [
            'Unit tests',
            'Integration tests',
            'Regression tests',
        ],
        'Deploy': [
            'Send to server',
            'Restart server',
        ],
    }
    num_subtasks = sum(len(x) for x in tasks.values())

    with progressbar.ProgressBar(
        prefix='{variables.task} >> {variables.subtask}',
        variables={'task': '--', 'subtask': '--'},
        max_value=10 * num_subtasks,
    ) as bar:
        for tasks_name, subtasks in tasks.items():
            for subtask_name in subtasks:
                for _ in range(10):
                    bar.update(
                        bar.value + 1, task=tasks_name, subtask=subtask_name
                    )
                    time.sleep(0.1)


@example
def format_custom_text() -> None:
    format_custom_text = progressbar.FormatCustomText(
        'Spam: %(spam).1f kg, eggs: %(eggs)d',
        dict(
            spam=0.25,
            eggs=3,
        ),
    )

    bar = progressbar.ProgressBar(
        widgets=[
            format_custom_text,
            ' :: ',
            progressbar.Percentage(),
        ]
    )
    for i in bar(range(25)):
        format_custom_text.update_mapping(eggs=i * 2)
        time.sleep(0.1)


@example
def simple_api_example() -> None:
    bar = progressbar.ProgressBar(widget_kwargs=dict(fill='█'))
    for _ in bar(range(200)):
        time.sleep(0.02)


@example
def eta_on_generators():
    def gen():
        for _ in range(200):
            yield None

    widgets = [
        progressbar.AdaptiveETA(),
        ' ',
        progressbar.ETA(),
        ' ',
        progressbar.Timer(),
    ]

    bar = progressbar.ProgressBar(widgets=widgets)
    for _ in bar(gen()):
        time.sleep(0.02)


@example
def percentage_on_generators():
    def gen():
        for _ in range(200):
            yield None

    widgets = [
        progressbar.Counter(),
        ' ',
        progressbar.Percentage(),
        ' ',
        progressbar.SimpleProgress(),
        ' ',
    ]

    bar = progressbar.ProgressBar(widgets=widgets)
    for _ in bar(gen()):
        time.sleep(0.02)


def test(*tests) -> None:
    if tests:
        no_tests = True
        for example in examples:
            for test in tests:
                if test in example.__name__:
                    example()
                    no_tests = False
                    break

        if no_tests:
            for example in examples:
                print('Skipping', example.__name__)
    else:
        for example in examples:
            example()


if __name__ == '__main__':
    try:
        test(*sys.argv[1:])
    except KeyboardInterrupt:
        sys.stdout.write('\nQuitting examples.\n')
