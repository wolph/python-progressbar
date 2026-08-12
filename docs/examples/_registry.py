"""The single source of truth for which examples exist.

Every entry here is consumed four ways: rendered to an animated SVG by
``scripts/render_demos.py``, literal-included by the ``.. demo::``
directive, fetched verbatim by the browser console, and executed by
``tests/test_docs_examples.py``.
"""

from __future__ import annotations

import dataclasses
import pathlib

EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent
DEMOS_DIR = EXAMPLES_DIR.parent / '_static' / 'demos'


@dataclasses.dataclass(frozen=True)
class Demo:
    #: Path under ``docs/examples/`` without the suffix, hyphenated.
    name: str
    #: Shown in the SVG title bar.
    title: str
    #: Terminal columns the pty is sized to while capturing.
    term_width: int = 112
    #: How many preceding log lines to keep visible above the bar.
    log_lines: int = 0
    #: Upper bound on animation frames; excess frames are sampled evenly.
    max_frames: int = 24
    #: Whether ``scripts/render_demos.py --check`` compares this demo's
    #: committed SVG against a fresh render. ``False`` for demos whose
    #: capture is not byte-stable across runs for reasons this repository
    #: cannot fix from the capture side alone -- see the two ``False``
    #: entries below for the one known case. Everything else defaults to
    #: gated; flipping this off is the exception, not a shortcut, so any
    #: new ``False`` entry needs a comment naming the cause right next to
    #: it, the same way those two do.
    drift_check: bool = True

    @property
    def path(self) -> pathlib.Path:
        return EXAMPLES_DIR / f'{self.name.replace("-", "_")}.py'

    @property
    def svg_path(self) -> pathlib.Path:
        return DEMOS_DIR / f'{self.name.replace("/", "-")}.svg'


DEMOS: tuple[Demo, ...] = (
    Demo('howto/colors', 'Fixed and gradient bar colors'),
    Demo('howto/custom-widget', 'A hand-written widget'),
    Demo('howto/dynamic-messages', 'Variable and DynamicMessage'),
    Demo(
        'howto/file-transfer',
        'DataSize, FileTransferSpeed, AdaptiveTransferSpeed',
    ),
    Demo('howto/iterable-wrapper', 'Wrapping an iterable directly'),
    Demo('howto/logging-integration', 'Logging above the bar', log_lines=2),
    # drift_check=False: MultiBar renders from a background thread that
    # races the main thread's updates (progressbar/multi.py's `run`) --
    # real OS thread scheduling decides how many redraws land before both
    # bars report finished(), so the captured frame count (and so the SVG)
    # is not reproducible run to run. Confirmed empirically: capturing this
    # demo repeatedly produced distinct frame sequences even after
    # collapsing consecutive-duplicate frames, so the variation is in which
    # states get seen, not merely how many times a state repeats. Fixing it
    # would mean changing MultiBar's threaded render loop, which is outside
    # scripts/render_demos.py's reach. Hand-verify this SVG after
    # regenerating it instead of trusting --check.
    Demo(
        'howto/multibar',
        'MultiBar jobs finishing at different times',
        drift_check=False,
    ),
    Demo('howto/multibar-line-offset', 'Manual line-offset bars'),
    Demo('howto/non-tty', 'Forcing one line per update'),
    Demo('howto/prefix-suffix', 'Templated prefix and suffix'),
    Demo('howto/redirect-stdout', 'print() above the bar', log_lines=2),
    Demo('howto/tqdm-style', 'tqdm-style keyword arguments'),
    Demo('howto/unknown-length', 'UnknownLength with an animated marker'),
    Demo('readme/hero', 'Progress with clean logs', log_lines=2),
    # drift_check=False: same MultiBar background-thread race as
    # howto/multibar above.
    Demo('readme/multibar', 'Multiple active jobs', drift_check=False),
    Demo('readme/unknown-length', 'Unknown length'),
    Demo('tutorial/step1', 'Wrap an iterable'),
    Demo('tutorial/step2', 'Explicit update()'),
    Demo('tutorial/step3', 'A known max_value'),
    Demo('tutorial/step4', 'A custom widget list'),
    Demo('tutorial/step5', 'print() survives redirect_stdout', log_lines=2),
    Demo('widgets/absolute-eta', 'AbsoluteETA'),
    Demo('widgets/adaptive-eta', 'AdaptiveETA'),
    Demo('widgets/adaptive-transfer-speed', 'AdaptiveTransferSpeed'),
    Demo('widgets/animated-marker', 'AnimatedMarker'),
    Demo('widgets/bar', 'Bar'),
    Demo('widgets/bouncing-bar', 'BouncingBar', term_width=30),
    Demo('widgets/counter', 'Counter'),
    Demo('widgets/current-time', 'CurrentTime'),
    Demo('widgets/data-size', 'DataSize'),
    Demo('widgets/dynamic-message', 'DynamicMessage'),
    Demo('widgets/eta', 'ETA'),
    Demo('widgets/file-transfer-speed', 'FileTransferSpeed'),
    Demo('widgets/format-custom-text', 'FormatCustomText'),
    Demo('widgets/format-label', 'FormatLabel'),
    Demo('widgets/format-label-bar', 'FormatLabelBar'),
    Demo('widgets/granular-bar', 'GranularBar'),
    Demo('widgets/job-status-bar', 'JobStatusBar'),
    Demo('widgets/multi-progress-bar', 'MultiProgressBar'),
    Demo('widgets/multi-range-bar', 'MultiRangeBar'),
    Demo('widgets/percentage', 'Percentage'),
    Demo('widgets/percentage-label-bar', 'PercentageLabelBar'),
    Demo('widgets/postfix', 'Postfix'),
    Demo('widgets/reverse-bar', 'ReverseBar'),
    Demo('widgets/rotating-marker', 'RotatingMarker'),
    Demo('widgets/simple-progress', 'SimpleProgress'),
    Demo('widgets/smoothing-eta', 'SmoothingETA'),
    Demo('widgets/timer', 'Timer'),
    Demo('widgets/unit-progress', 'UnitProgress'),
    Demo('widgets/variable', 'Variable'),
)

DEMOS_BY_NAME: dict[str, Demo] = {demo.name: demo for demo in DEMOS}
