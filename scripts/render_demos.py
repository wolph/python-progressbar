from __future__ import annotations

import argparse
import errno
import fcntl
import html
import importlib.util
import os
import pty
import re
import select
import struct
import subprocess
import sys
import termios
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_docs_examples(repo_root: Path) -> types.ModuleType:
    """Import ``docs/examples`` by path, under a private module name.

    ``docs/examples`` cannot be imported as top-level ``examples`` -- e.g.
    via ``sys.path.insert(0, str(repo_root / 'docs'))`` followed by
    ``import examples`` -- because that name collides with the real
    top-level ``examples.py`` demo runner. Once Python caches the wrong
    module under ``sys.modules['examples']`` the collision is permanent
    for the rest of the process. Loading by file path under a private
    name sidesteps ``sys.path`` and the ``examples`` name entirely.
    """
    examples_dir = repo_root / 'docs' / 'examples'
    spec = importlib.util.spec_from_file_location(
        'docs_examples',
        examples_dir / '__init__.py',
        submodule_search_locations=[str(examples_dir)],
    )
    if spec is None or spec.loader is None:  # pragma: no cover - unreachable
        raise ImportError(
            f'cannot load docs examples package from {examples_dir}'
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_docs_examples = load_docs_examples(ROOT)
DEMOS = _docs_examples.DEMOS
DEMOS_BY_NAME = _docs_examples.DEMOS_BY_NAME
Demo = _docs_examples.Demo
load_example = _docs_examples.load_example

BAR_RE = re.compile(r'\|(?P<inner>(?:#+[\s#]*|))\|')
PERCENT_RE = re.compile(r'\b\d{1,3}%')
POSTFIX_RE = re.compile(r'\b[A-Za-z_][\w-]*=[^\s,]+')
LABEL_RE = re.compile(r'[A-Za-z][\w-]*:?')
ANSI_SGR_RE = re.compile(r'\x1b\[([0-9;]*)m')
# Any other CSI control sequence (cursor movement, erase, ...) that isn't an
# SGR colour code. ``styled_terminal_line`` (further below) still needs SGR
# sequences intact to colour spans, so this excludes the ``m`` terminator --
# everything else is layout plumbing a terminal would act on invisibly, and
# is not valid XML character data verbatim (e.g. plain ESC, 0x1B). Without
# stripping it, a demo whose library-level rendering path emits cursor
# movement -- MultiBar's paired reposition codes, or plain ProgressBar's
# ``line_offset``, which uses a different, unpaired ``ESC[F``/``ESC[B``
# convention -- would leak raw control bytes into the generated SVG's
# ``<text>`` content, which is simply invalid XML.
STRAY_CSI_RE = re.compile(r'\x1b\[[0-9;]*[A-Za-ln-z]')
# Matches RST inline-code markup in a docstring's first line -- stripped
# before the text is read aloud from an SVG <desc>, where the literal
# backticks would otherwise be announced along with the name. Widget-family
# docstrings (docs/examples/widgets/*.py) use double backticks (``Widget``);
# how-to and tutorial docstrings use single backticks (`Widget`) instead.
# The double-backtick pattern must be applied first and separately, not
# combined into one alternation matched in a single pass -- a naive
# `` `` | ` `` alternation run once over ``` ``Widget`` ``` would let the
# single-backtick branch match the *inner* pair of backticks first (at the
# leftmost position), consuming only one backtick from each side and
# leaving the outer two behind in the output.
RST_DOUBLE_BACKTICK_RE = re.compile(r'``([^`]*)``')
RST_SINGLE_BACKTICK_RE = re.compile(r'`([^`]*)`')
# id-safe token characters only; anything else (spaces, punctuation)
# collapses to a single hyphen. See ``slug`` for why this must be unique
# per demo.
SLUG_RE = re.compile(r'[^a-z0-9]+')
# MultiBar redraws one bar at a time: PREVIOUS_LINE(offset) (``ESC[<n>F``,
# cursor up n lines to column 0) to that bar's row, the freshly rendered
# text, then NEXT_LINE(offset) (``ESC[<n>E``) back down to the shared
# baseline below every bar (progressbar/multi.py's ``render``/``print``).
# See ``_parse_multibar_frames`` for how ``offset`` is used.
MULTIBAR_REPOSITION_RE = re.compile(
    r'\x1b\[(\d*)F\r?(.*?)\x1b\[\d*E',
    re.DOTALL,
)
# Default per-frame duration. Registry entries can override it (and add a
# final-frame hold) via ``Demo.frame_seconds``/``Demo.end_hold_seconds``;
# the README demos do, since they pace as a first impression rather than
# an inline illustration.
ANIMATION_FRAME_SECONDS = 0.08
SVG_WIDTH = 1080

CAPTURE_TIMEOUT_SECONDS = 30.0

#: Arbitrary, but a plausible time of day rather than a suspicious-looking
#: midnight/epoch value -- widgets/current_time.py and widgets/absolute_eta.py
#: are the only two demos whose *content* depends on it (a clock reading and
#: a projected finish time, respectively); see ``_demo_argv`` for why every
#: other demo is frozen too.
CAPTURE_CLOCK_INSTANT = '2024-03-14T09:41:17'


def _demo_argv(demo: Demo) -> list[str]:
    """Build the argv used to run ``demo`` under capture.

    Every demo runs through a small ``-c`` bootstrap that freezes the clock
    (via freezegun, already a test dependency) and makes ``time.sleep``
    advance it by exactly the requested amount instead of actually
    blocking, before executing the module. This lives entirely in the
    capture path -- the example modules under ``docs/examples/`` never
    import freezegun or otherwise carry capture-only behaviour, and still
    read as plain, idiomatic ``time.sleep()``-paced scripts.

    This is not only about the two demos whose displayed *content* is a
    wall-clock reading (``widgets/current-time``, ``widgets/absolute-eta``).
    ``ProgressBar``'s redraw throttle (``_needs_update``) gates on real
    elapsed time via ``timeit.default_timer()`` (``time.perf_counter``), so
    under a real, unfrozen clock the number of redraws an example manages to
    fit into its real (sub-second) runtime depends on actual OS/CPU
    scheduling jitter -- confirmed empirically by capturing the same,
    otherwise-deterministic example repeatedly back to back: the committed
    SVG's frame count (and so its bytes) differed on most attempts, for
    ordinary demos with no clock-widget in sight. Deriving the throttle's
    notion of elapsed time from a virtual clock that only moves when the
    demo itself calls ``time.sleep()`` removes real-world timing from the
    equation, making the animation reproducible.

    Two things make the bootstrap below load-bearing, not stylistic:

    1. ``time.sleep`` must be reassigned to the freezer's ``tick`` *and*
       the freeze must be a plain (non-``ignore``d) one. freezegun also
       patches ``time.perf_counter`` while frozen, and ``timeit`` re-exports
       it as ``timeit.default_timer`` -- which is exactly what
       ``_needs_update`` reads. Leaving that patch in place is what makes
       ``tick()`` (called from the reassigned ``time.sleep``) visible to
       the throttle at all; excluding ``timeit`` from the freeze (e.g. via
       ``ignore=['timeit']``, the obvious-looking safety net) instead
       leaves it bound to the *real* ``perf_counter``, which barely moves
       once ``time.sleep`` no longer blocks for real -- collapsing the
       animation to just its first and last (forced, on ``finish()``)
       frames. Confirmed empirically switching between the two.
    2. ``MultiBar`` normally renders from a background thread
       (``progressbar/multi.py``'s ``time.sleep(self.update_interval)``
       loop). Under the no-op patched sleep the demo's main loop finishes
       in microseconds of real time, so that thread got one or two real
       scheduling slices: the captured animation was a pile of identical
       early frames and a jump to 100%, and the frame count was a real
       OS-scheduling race between runs. The bootstrap therefore patches
       ``MultiBar.start`` to *not* start the thread (``join``/``stop``
       are documented no-ops with no thread running) and instead calls
       ``render()`` on every live multibar after each ``time.sleep``
       tick, which is the documented manual-drive mode. That makes the
       multibar captures complete (every update lands as a frame) and
       deterministic. The ``tick()`` lock stays for demos that spawn
       threads of their own (``howto/multibar-line-offset``), where
       concurrent ticks would corrupt freezegun's state; such demos
       remain scheduling-dependent and keep ``drift_check=False``.
    """
    bootstrap = (
        'import threading, time, runpy, freezegun\n'
        'import progressbar.multi\n'
        '_frozen = freezegun.freeze_time('
        f'{CAPTURE_CLOCK_INSTANT!r}).start()\n'
        '_tick_lock = threading.Lock()\n'
        '_multibars = []\n'
        '\n'
        'def _capture_start(self):\n'
        '    _multibars.append(self)\n'
        '\n'
        'progressbar.multi.MultiBar.start = _capture_start\n'
        '\n'
        'def _deterministic_sleep(seconds):\n'
        '    with _tick_lock:\n'
        '        _frozen.tick(seconds)\n'
        '    for _multibar in _multibars:\n'
        '        _multibar.render()\n'
        '\n'
        'time.sleep = _deterministic_sleep\n'
        f"runpy.run_path({str(demo.path)!r}, run_name='__main__')\n"
    )
    return [sys.executable, '-c', bootstrap]


def capture_demo(demo: Demo) -> list[list[str]]:
    """Run an example attached to a pty sized to ``demo.term_width``.

    A pty is what makes the examples themselves idiomatic: the library
    detects a real terminal, so the modules under ``docs/examples/`` never
    have to pass ``is_terminal=True`` or ``term_width=`` just to be
    captured.
    """
    env = os.environ.copy()
    env['COLORFGBG'] = '15;0'
    env['COLORTERM'] = 'truecolor'
    env['TERM'] = 'xterm-256color'
    env['COLUMNS'] = str(demo.term_width)
    env['PYTHONPATH'] = str(ROOT)
    env['PYTHONIOENCODING'] = 'utf-8'

    controller, worker = pty.openpty()
    try:
        # ``worker`` must close whether the ioctl or the Popen call itself
        # raises, not just on the happy path -- otherwise a failure here
        # leaks both fds (the outer finally below only closes `controller`).
        try:
            fcntl.ioctl(
                worker,
                termios.TIOCSWINSZ,
                struct.pack('HHHH', 40, demo.term_width, 0, 0),
            )
            deadline = time.monotonic() + CAPTURE_TIMEOUT_SECONDS
            process = subprocess.Popen(
                _demo_argv(demo),
                cwd=ROOT,
                env=env,
                stdout=worker,
                stderr=worker,
                close_fds=True,
            )
        finally:
            os.close(worker)

        chunks: list[bytes] = []
        while True:
            remaining = deadline - time.monotonic()
            # A demo that hangs (rather than crashing) never closes its end
            # of the pty, so a bare os.read() here would block forever --
            # the process.wait(timeout=...) below is only ever reached once
            # this loop exits. select() with a shrinking deadline is what
            # actually bounds a hung demo.
            if (
                remaining <= 0
                or not select.select([controller], [], [], remaining)[0]
            ):
                process.kill()
                process.wait()
                raise SystemExit(f'example hung: {demo.name}')
            try:
                chunk = os.read(controller, 65536)
            except OSError as error:
                if error.errno == errno.EIO:
                    break
                raise
            if not chunk:
                break
            chunks.append(chunk)

        try:
            return_code = process.wait(
                timeout=max(1.0, deadline - time.monotonic())
            )
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise SystemExit(f'example hung: {demo.name}') from None

        output = b''.join(chunks).decode('utf-8', 'replace')
        if return_code:
            excerpt = output.strip()[-500:]
            raise SystemExit(
                f'example failed: {demo.name} (exit code {return_code})\n'
                f'{excerpt}'
            )
    finally:
        os.close(controller)

    frames = parse_frames(output)
    if demo.log_lines:
        frames = keep_recent_logs_with_progress(frames, demo.log_lines)
    frames = dedupe_consecutive_frames(frames)
    return limit_animation_frames(frames, demo.max_frames) or [
        ['No output captured']
    ]


def normalize_terminal_line(line: str) -> str:
    """Strip stray (non-SGR) control sequences from a captured line.

    This used to also zero out "Elapsed Time:"/"ETA:"/"Time:" readings,
    because the original capture ran under a real, unfrozen clock and those
    readings differed on every run. Every demo's capture now runs under the
    frozen, deterministically-ticking clock instead (see ``_demo_argv``), so
    those readings are already byte-stable on their own -- proven by
    rendering ``widgets/timer``, ``readme/hero``, ``widgets/eta``,
    ``widgets/adaptive-eta``, ``widgets/file-transfer-speed`` and
    ``widgets/bar`` several times each, several seconds apart: 0 of 18
    repeats differed. Zeroing them was therefore not just unnecessary but
    actively wrong for a widget whose only content *is* such a reading --
    ``widgets/timer`` rendered as a single static "Elapsed Time: 0:00:00"
    frame, the one thing ``Timer`` exists to show. Removed rather than
    special-cased further.
    """
    return STRAY_CSI_RE.sub('', line)


def parse_frames(output: str) -> list[list[str]]:
    output = output.replace('\x1b[2K', '')

    if MULTIBAR_REPOSITION_RE.search(output):
        return _parse_multibar_frames(output)

    frames: list[list[str]] = []
    if '\f' in output:
        for raw_frame in output.split('\f'):
            # Filtered post-normalization, not just on the raw stripped
            # line: a line that is nothing but a stray control sequence
            # (see STRAY_CSI_RE) is non-empty here but normalizes away to
            # nothing, and would otherwise leave a blank line inside an
            # otherwise real frame.
            lines = [
                normalized
                for line in raw_frame.splitlines()
                if line.strip()
                and (normalized := normalize_terminal_line(line.strip()))
            ]
            if lines:
                frames.append(lines)
        return frames

    for raw_frame in output.splitlines():
        for part in raw_frame.split('\r'):
            line = normalize_terminal_line(part.strip())
            if line:
                frames.append([line])
    return frames


def _parse_multibar_frames(output: str) -> list[list[str]]:
    """Reconstruct ``MultiBar``'s per-bar redraws into combined frames.

    A lone ``ProgressBar`` redraws with a single ``\\r``, so the generic
    path above (splitting on ``\\r``/``\\f``) is enough. ``MultiBar``
    instead redraws one bar at a time, repositioning the cursor to that
    bar's row and back (see ``MULTIBAR_REPOSITION_RE``) rather than
    rewriting the whole screen -- so naively splitting on ``\\r`` would
    scatter each bar's updates across separate single-line frames, never
    showing two bars together, which defeats a "multiple concurrent bars"
    demo. ``offset`` doubles as a stable row index (1 = bottommost bar, 2 =
    the one above it, ...), so track the latest text seen at each offset
    and, after every individual bar redraw, emit a frame of everything
    known so far, top to bottom.
    """
    lines_by_offset: dict[int, str] = {}
    frames: list[list[str]] = []
    for match in MULTIBAR_REPOSITION_RE.finditer(output):
        offset = int(match.group(1) or 1)
        text = normalize_terminal_line(match.group(2).strip())
        if not text:
            continue
        lines_by_offset[offset] = text
        frames.append(
            [
                lines_by_offset[key]
                for key in sorted(lines_by_offset, reverse=True)
            ]
        )
    return frames


def keep_recent_logs_with_progress(
    frames: list[list[str]],
    log_lines: int,
) -> list[list[str]]:
    """Fold plain output lines into a trailing window above the bar redraw.

    A line is classified as "the bar's own redraw", not log/print output to
    retain, by whether it looks like a rendered ``ProgressBar`` line: a
    ``NN%`` reading (``PERCENT_RE``) or a ``|...|`` bar frame (``BAR_RE``).
    Both are checked -- not ``BAR_RE`` alone -- because ``BAR_RE``'s inner
    group only matches a fill of ``#`` characters; an unstarted bar (0%,
    rendered as ``|`` followed by *only* spaces before the closing ``|``)
    has no ``#`` yet and so does not match ``BAR_RE``, even though it is
    just as much the bar's own redraw as any other frame. Every demo that
    sets ``log_lines`` uses a plain ``ProgressBar`` with the library's
    default widgets, which always includes both ``Percentage`` and ``Bar``,
    so its own redraws are the only lines matching either pattern.

    This used to instead check for a literal ``"log:"`` prefix, which only
    happened to hold for ``readme/hero.py`` (written with that exact
    convention in mind) -- ``howto/logging_integration.py``'s real
    ``logger.info(...)`` calls and ``howto/redirect_stdout.py``'s plain
    ``print(f'Processing {filename}')`` calls have no such prefix, so both
    were silently misclassified as "progress" lines: each surfaced as its
    own isolated, bar-less frame instead of being retained above the next
    redraw, defeating the entire point of a demo whose job is to show
    output staying visible above a moving bar. Content a real demo would
    print/log is not expected to itself contain a percentage reading or a
    bar frame, so this generalizes to any current or future ``log_lines``
    demo without asking it to spell its message a particular way.
    """

    def is_progress_line(line: str) -> bool:
        return bool(PERCENT_RE.search(line) or BAR_RE.search(line))

    logs: list[str] = []
    output: list[list[str]] = []

    for frame in frames:
        log_frame = [line for line in frame if not is_progress_line(line)]
        progress_frame = [line for line in frame if is_progress_line(line)]
        if log_frame:
            logs.extend(log_frame)
            logs = logs[-log_lines:]
        if progress_frame:
            output.append(logs + progress_frame)

    return output


def dedupe_consecutive_frames(frames: list[list[str]]) -> list[list[str]]:
    """Collapse runs of consecutive, identical frames into one.

    A redraw that changes nothing visible still counts as a captured frame
    -- most visibly, ``MultiBar``'s background render thread always issues
    one final ``render(force=True)`` once every bar reports ``finished()``
    (progressbar/multi.py's ``run``), even when the immediately preceding,
    non-forced render already showed that exact settled state. Repeating an
    unchanged frame only bloats the SVG and makes the animation stutter in
    place, so drop the repeat regardless of why it happened.
    """
    deduped: list[list[str]] = []
    for frame in frames:
        if not deduped or deduped[-1] != frame:
            deduped.append(frame)
    return deduped


def limit_animation_frames(
    frames: list[list[str]],
    max_frames: int,
) -> list[list[str]]:
    if len(frames) <= max_frames:
        return frames

    last_index = len(frames) - 1
    selected = [
        round(index * last_index / (max_frames - 1))
        for index in range(max_frames)
    ]
    return [frames[index] for index in selected]


def tspan(
    text: str,
    class_name: str | None = None,
    style: str | None = None,
) -> str:
    if not text:
        return ''
    escaped = html.escape(text)
    if style is not None:
        return f'<tspan style="{html.escape(style)}">{escaped}</tspan>'
    if class_name is None:
        return escaped
    return f'<tspan class="{class_name}">{escaped}</tspan>'


def xterm_256_to_rgb(color: int) -> tuple[int, int, int]:
    if color < 16:
        palette = (
            (0, 0, 0),
            (128, 0, 0),
            (0, 128, 0),
            (128, 128, 0),
            (0, 0, 128),
            (128, 0, 128),
            (0, 128, 128),
            (192, 192, 192),
            (128, 128, 128),
            (255, 0, 0),
            (0, 255, 0),
            (255, 255, 0),
            (0, 0, 255),
            (255, 0, 255),
            (0, 255, 255),
            (255, 255, 255),
        )
        return palette[max(0, color)]

    if color < 232:
        color -= 16
        levels = (0, 95, 135, 175, 215, 255)
        return (
            levels[color // 36],
            levels[(color // 6) % 6],
            levels[color % 6],
        )

    shade = 8 + (color - 232) * 10
    return shade, shade, shade


def ansi_rgb_style(red: int, green: int, blue: int) -> str:
    return f'fill: #{red:02x}{green:02x}{blue:02x}'


def ansi_sgr_style(parameters: str, current_style: str | None) -> str | None:
    """Resolve one SGR escape's foreground-color effect on ``current_style``.

    Handles three foreground forms: extended truecolor (``38;2;r;g;b``) and
    256-color (``38;5;n``, already needed for the library's own
    ``progressbar.terminal.colors`` output -- see e.g.
    ``colors.green.fg('X')`` == ``'\\x1b[38;5;2mX\\x1b[39m'`` in
    ``tests/test_color.py``) -- and the plain, no-prefix 8/16-color codes
    (30-37, 90-97) that neither the library nor any current demo emits, but
    that a contributor hand-writing an example (as
    ``docs/examples/widgets/multi_range_bar.py`` originally did, before
    being changed to the extended form -- see task-11-report.md) would
    reasonably type from memory. Silently rendering those in the default
    color, with no error, is worse than the small added surface: 30-37 and
    90-97 map onto the exact same 16-entry palette ``xterm_256_to_rgb``
    already serves ``38;5;0`` through ``38;5;15`` from, offset by 30 (or 90
    for the bright half), so this reuses it rather than duplicating the
    palette.
    """
    codes = [int(code) if code else 0 for code in parameters.split(';')]
    index = 0
    while index < len(codes):
        code = codes[index]
        if code in {0, 39}:
            current_style = None
        elif code == 38 and index + 1 < len(codes):
            mode = codes[index + 1]
            if mode == 2 and index + 4 < len(codes):
                current_style = ansi_rgb_style(
                    codes[index + 2],
                    codes[index + 3],
                    codes[index + 4],
                )
                index += 4
            elif mode == 5 and index + 2 < len(codes):
                current_style = ansi_rgb_style(
                    *xterm_256_to_rgb(codes[index + 2]),
                )
                index += 2
            else:
                index += 1
        elif 30 <= code <= 37:
            current_style = ansi_rgb_style(*xterm_256_to_rgb(code - 30))
        elif 90 <= code <= 97:
            current_style = ansi_rgb_style(*xterm_256_to_rgb(code - 90 + 8))
        index += 1

    return current_style


def styled_ansi_terminal_line(line: str) -> str:
    output: list[str] = []
    cursor = 0
    current_style: str | None = None
    for match in ANSI_SGR_RE.finditer(line):
        output.append(tspan(line[cursor : match.start()], style=current_style))
        current_style = ansi_sgr_style(match.group(1), current_style)
        cursor = match.end()

    output.append(tspan(line[cursor:], style=current_style))
    return ''.join(output)


def styled_text_segment(
    text: str,
    absolute_start: int,
    full_line: str,
) -> str:
    ranges: list[tuple[int, int, str]] = []
    if absolute_start == 0 and text.startswith('log:'):
        ranges.append((0, 4, 'terminal-log'))
    elif (
        absolute_start == 0
        and '%' in full_line
        and (label_match := LABEL_RE.match(text))
    ):
        ranges.append(
            (label_match.start(), label_match.end(), 'terminal-label')
        )

    ranges.extend(
        (match.start(), match.end(), 'terminal-percent')
        for match in PERCENT_RE.finditer(text)
    )
    ranges.extend(
        (match.start(), match.end(), 'terminal-postfix')
        for match in POSTFIX_RE.finditer(text)
    )

    output: list[str] = []
    cursor = 0
    for start, end, class_name in sorted(ranges):
        if start < cursor:
            continue
        output.append(tspan(text[cursor:start]))
        output.append(tspan(text[start:end], class_name))
        cursor = end
    output.append(tspan(text[cursor:]))
    return ''.join(output)


def styled_bar_segment(inner: str) -> str:
    output = [tspan('|', 'terminal-bar-frame')]
    for match in re.finditer(r'#+|\s+|[^#\s]+', inner):
        value = match.group(0)
        if set(value) == {'#'}:
            class_name = 'terminal-bar-fill'
        elif value.isspace():
            class_name = 'terminal-bar-empty'
        else:
            class_name = 'terminal-bar-text'
        output.append(tspan(value, class_name))
    output.append(tspan('|', 'terminal-bar-frame'))
    return ''.join(output)


def styled_terminal_line(line: str) -> str:
    if '\x1b[' in line:
        return styled_ansi_terminal_line(line)

    output: list[str] = []
    cursor = 0
    for match in BAR_RE.finditer(line):
        output.append(
            styled_text_segment(line[cursor : match.start()], cursor, line)
        )
        output.append(styled_bar_segment(match.group('inner')))
        cursor = match.end()
    output.append(styled_text_segment(line[cursor:], cursor, line))
    return ''.join(output)


def slug(text: str) -> str:
    """Turn ``text`` into an ``id``-safe, hyphenated token.

    Used to derive each SVG's ``<title>``/``<desc>`` ids from its demo
    title, so that inlining several rendered SVGs on one page (as Task 13's
    how-to guides will) never produces duplicate ``id`` attributes -- which
    would be invalid HTML and would leave ``aria-labelledby`` pointing at
    whichever duplicate the browser happens to pick. Every demo title in
    docs/examples/_registry.py is unique, so slugifying the title alone is
    enough to keep ids unique across an entire page.
    """
    return SLUG_RE.sub('-', text.lower()).strip('-')


def demo_description(demo: Demo) -> str:
    """Return a screen-reader-worthy description of ``demo``.

    Sourced from the first line of the example module's own docstring
    (loaded the same way ``tests/test_docs_examples.py`` and the
    ``.. demo::`` directive do, via ``load_example`` -- the registry's
    single source of truth), which already reads as a complete sentence
    describing what the widget does or why the example is shaped the way
    it is (see docs/examples/**/*.py). That is far more useful read aloud
    than a generic "animated recording of {title}" placeholder. RST
    inline-code markup -- double-backtick (````Widget````) in widget
    docstrings, single-backtick (```Widget```) in how-to/tutorial ones --
    is stripped, since a screen reader would otherwise announce the
    literal backticks.
    """
    docstring = load_example(demo).__doc__
    if not docstring:
        # Unreached for every demo currently in the registry -- every
        # module under docs/examples/ has a docstring (asserted for the
        # whole registry by
        # test_every_registered_demo_module_has_a_docstring in
        # tests/test_readme_demos.py). Kept as a real fallback, not an
        # `assert`, because a future demo added without a docstring should
        # still render a usable, if generic, <desc> rather than crash the
        # whole render run over one missing accessibility nicety.
        return f'Terminal recording of {demo.title}.'
    first_line = docstring.strip().splitlines()[0].strip()
    # Order matters: strip double-backtick pairs first, as a whole pass,
    # before single-backtick pairs. A single combined `` `` | ` `` pattern
    # applied once would let the single-backtick branch match starting at
    # the *inner* pair of a ``Widget`` run first, consuming one backtick
    # from each side and leaving the outer two in the output.
    first_line = RST_DOUBLE_BACKTICK_RE.sub(r'\1', first_line)
    return RST_SINGLE_BACKTICK_RE.sub(r'\1', first_line)


def svg_document(
    title: str,
    frames: list[list[str]],
    description: str | None = None,
    *,
    frame_seconds: float = ANIMATION_FRAME_SECONDS,
    end_hold_seconds: float = 0.0,
) -> str:
    width = SVG_WIDTH
    line_height = 24
    max_lines = max(len(frame) for frame in frames)
    height = 72 + max_lines * line_height
    total_seconds = max(len(frames), 1) * frame_seconds + end_hold_seconds
    duration = f'{total_seconds:g}'
    # Without a hold, frames divide ``dur`` evenly and no ``keyTimes`` is
    # needed. With one, the extra time must all land on the final frame,
    # which is exactly what explicit ``keyTimes`` with ``calcMode=
    # "discrete"`` expresses: each frame shows from its keyTime to the
    # next, and the last one holds until ``dur``.
    key_times = ''
    if end_hold_seconds:
        starts = ';'.join(
            f'{index * frame_seconds / total_seconds:g}'
            for index in range(len(frames))
        )
        key_times = f'keyTimes="{starts}" '
    title_id = f'demo-{slug(title)}-title'
    desc_id = f'demo-{slug(title)}-desc'
    desc_text = description or f'Terminal recording of {title}.'
    frame_groups = []
    for index, frame in enumerate(frames):
        visible_values = ['0'] * len(frames)
        visible_values[index] = '1'
        visible_value_list = ';'.join(visible_values)
        base_opacity = '1' if index == 0 else '0'
        lines = []
        for row, line in enumerate(frame):
            lines.append(
                f'<text x="32" y="{72 + row * line_height}" '
                'class="terminal-line" xml:space="preserve">'
                f'{styled_terminal_line(line)}</text>'
            )
        frame_groups.append(
            f'<g opacity="{base_opacity}">'
            '<animate attributeName="opacity" '
            f'values="{visible_value_list}" '
            f'{key_times}'
            f'dur="{duration}s" '
            'repeatCount="indefinite" '
            'calcMode="discrete" />' + ''.join(lines) + '</g>'
        )

    return f'''<svg
  xmlns="http://www.w3.org/2000/svg"
  role="img"
  aria-labelledby="{title_id} {desc_id}"
  width="{width}"
  height="{height}"
  viewBox="0 0 {width} {height}"
>
  <title id="{title_id}">{html.escape(title)}</title>
  <desc id="{desc_id}">{html.escape(desc_text)}</desc>
  <style>
    .terminal-bg {{ fill: #101418; }}
    .terminal-title {{
      fill: #dce3ea;
      font: 600 16px ui-monospace, SFMono-Regular, Menlo, Consolas,
        monospace;
    }}
    .terminal-line {{
      fill: #d6e2ef;
      font: 15px ui-monospace, SFMono-Regular, Menlo, Consolas,
        monospace;
    }}
    .terminal-label {{ fill: #7dd3fc; font-weight: 700; }}
    .terminal-percent {{ fill: #facc15; }}
    .terminal-bar-frame {{ fill: #7b8794; }}
    .terminal-bar-fill {{ fill: #34d399; }}
    .terminal-bar-empty {{ fill: #44515f; }}
    .terminal-bar-text {{ fill: #d6e2ef; }}
    .terminal-postfix {{ fill: #c084fc; }}
    .terminal-log {{ fill: #fb923c; }}
    .dot-red {{ fill: #ff5f57; }}
    .dot-yellow {{ fill: #ffbd2e; }}
    .dot-green {{ fill: #28c840; }}
    @media (prefers-reduced-motion: reduce) {{
      /* Setting display: none on the animate elements does not stop
         their SMIL animation from running in every browser tested --
         confirmed empirically, Chromium 2026-08: with only that rule in
         place, every frame group's computed opacity kept cycling on its
         original schedule. A SMIL-driven value sits in the CSS cascade's
         animation layer, above normal author declarations but below
         !important ones, so overriding opacity (and display, for
         belt-and-suspenders) with !important here is load-bearing, not
         decorative -- removing it silently reintroduces the animation.
         The last frame is selected, not the first: a finished bar is more
         informative at rest than the empty starting state. Every frame
         group is a direct child of the root element and no other group
         element appears in this document, so last-of-type unambiguously
         selects the final frame. */
      animate {{ display: none; }}
      g {{ display: none !important; opacity: 0 !important; }}
      g:last-of-type {{ display: inline !important; opacity: 1 !important; }}
    }}
  </style>
  <rect class="terminal-bg" width="100%" height="100%" rx="10" />
  <circle class="dot-red" cx="28" cy="26" r="6" />
  <circle class="dot-yellow" cx="48" cy="26" r="6" />
  <circle class="dot-green" cx="68" cy="26" r="6" />
  <text class="terminal-title" x="96" y="32">{html.escape(title)}</text>
  {''.join(frame_groups)}
</svg>
'''


def render_svg(
    path: Path,
    title: str,
    frames: list[list[str]],
    description: str | None = None,
    *,
    frame_seconds: float = ANIMATION_FRAME_SECONDS,
    end_hold_seconds: float = 0.0,
) -> None:
    svg = svg_document(
        title,
        frames,
        description,
        frame_seconds=frame_seconds,
        end_hold_seconds=end_hold_seconds,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding='utf-8')


def check_svg(path: Path, expected: str) -> None:
    if not path.exists():
        raise SystemExit(f'missing generated asset: {path}')
    if path.read_text(encoding='utf-8') != expected:
        raise SystemExit(f'outdated generated asset: {path}')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Render documentation demo animations.',
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='fail if any committed SVG differs from a fresh render',
    )
    parser.add_argument(
        '--only',
        metavar='NAME',
        help='render a single demo by registry name',
    )
    args = parser.parse_args()

    if args.only:
        if args.only not in DEMOS_BY_NAME:
            raise SystemExit(f'unknown demo: {args.only}')
        demos = [DEMOS_BY_NAME[args.only]]
    else:
        demos = list(DEMOS)

    # A demo with drift_check=False is not skipped -- it is never gated:
    # print exactly which ones and why on every --check run, rather than
    # silently reporting success over a gate that only actually covers
    # some of the demos it appears to.
    if args.check:
        skipped = [demo for demo in demos if not demo.drift_check]
        if skipped:
            names = ', '.join(demo.name for demo in skipped)
            print(
                f'--check: not gating {len(skipped)} demo(s) whose capture '
                'is known not to be byte-stable across runs (see '
                f'Demo.drift_check in docs/examples/_registry.py): {names}',
                file=sys.stderr,
            )

    for demo in demos:
        if args.check and not demo.drift_check:
            continue
        frames = capture_demo(demo)
        description = demo_description(demo)
        if args.check:
            check_svg(
                demo.svg_path,
                svg_document(
                    demo.title,
                    frames,
                    description,
                    frame_seconds=demo.frame_seconds,
                    end_hold_seconds=demo.end_hold_seconds,
                ),
            )
        else:
            render_svg(
                demo.svg_path,
                demo.title,
                frames,
                description,
                frame_seconds=demo.frame_seconds,
                end_hold_seconds=demo.end_hold_seconds,
            )


if __name__ == '__main__':
    main()
