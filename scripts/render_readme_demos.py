from __future__ import annotations

import argparse
import html
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / 'docs' / '_static'
TIMING_FIELD_RE = re.compile(
    r'\b(Elapsed Time|ETA|Time):(\s+)\d+:\d{2}:\d{2}',
)
BAR_RE = re.compile(r'\|(?P<inner>(?:#+[\s#]*|))\|')
PERCENT_RE = re.compile(r'\b\d{1,3}%')
POSTFIX_RE = re.compile(r'\b[A-Za-z_][\w-]*=[^\s,]+')
LABEL_RE = re.compile(r'[A-Za-z][\w-]*:?')
ANSI_SGR_RE = re.compile(r'\x1b\[([0-9;]*)m')
ANIMATION_FRAME_SECONDS = 0.08
MAX_ANIMATION_FRAMES = 24
SVG_WIDTH = 1080


@dataclass(frozen=True)
class Demo:
    name: str
    title: str
    snippet: str
    log_lines: int = 0


DEMOS = [
    Demo(
        'hero',
        'Progress with clean logs',
        """
import sys
import time
import progressbar

with progressbar.ProgressBar(
    total=24,
    desc='Build',
    fd=sys.stdout,
    redirect_stdout=True,
    line_breaks=False,
    is_terminal=True,
    enable_colors=True,
    term_width=112,
) as bar:
    for step in range(24):
        if step in {8, 16}:
            print(f'log: completed step {step}')
        bar.update(step + 1, force=True)
        time.sleep(0.005)
""",
        log_lines=2,
    ),
    Demo(
        'multibar',
        'Multiple active jobs',
        """
import io
import re
import progressbar

fd = io.StringIO()
multibar = progressbar.MultiBar(
    fd=fd,
    total=24,
    enable_colors=True,
    initial_format=None,
    finished_format=None,
    remove_finished=None,
    sort_reverse=False,
    term_width=112,
)
build = multibar['build']
test = multibar['test']
terminal_control_re = re.compile(r'\\x1b\\[[0-9;]*[A-Za-ln-z]')

def emit_frame():
    output = terminal_control_re.sub('', fd.getvalue())
    for line in output.split('\\r'):
        line = line.strip()
        if line:
            print(line)
    print('\\f', end='')
    fd.seek(0)
    fd.truncate(0)

multibar.render(force=True, flush=True)
emit_frame()

for step in range(24):
    build.update(step + 1, force=True)
    test_value = min(24, max(0, round((step - 3) * 1.2)))
    test.update(test_value, force=True)
    multibar.render(force=True, flush=True)
    emit_frame()
""",
    ),
    Demo(
        'unknown-length',
        'Unknown length',
        """
import sys
import progressbar

with progressbar.ProgressBar(
    max_value=progressbar.UnknownLength,
    fd=sys.stdout,
    line_breaks=False,
    is_terminal=True,
    enable_colors=True,
    term_width=112,
) as bar:
    for value in range(0, 120, 10):
        bar.update(value, force=True)
""",
    ),
]


def capture_demo(demo: Demo) -> list[list[str]]:
    env = os.environ.copy()
    env['COLORFGBG'] = '15;0'
    env['COLORTERM'] = 'truecolor'
    env['PYTHONPATH'] = str(ROOT)
    env['PYTHONIOENCODING'] = 'utf-8'
    try:
        result = subprocess.run(
            [sys.executable, '-c', demo.snippet],
            cwd=ROOT,
            env=env,
            text=True,
            encoding='utf-8',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired as error:
        raise SystemExit(f'timed out capturing demo: {demo.name}') from error

    frames = parse_frames(result.stdout)
    if demo.log_lines:
        frames = keep_recent_logs_with_progress(frames, demo.log_lines)
    return limit_animation_frames(frames) or [['No output captured']]


def normalize_terminal_line(line: str) -> str:
    return TIMING_FIELD_RE.sub(
        lambda match: f'{match.group(1)}:{match.group(2)}0:00:00',
        line,
    )


def frames_from_output(output: str) -> list[list[str]]:
    return limit_animation_frames(parse_frames(output)) or [
        ['No output captured']
    ]


def parse_frames(output: str) -> list[list[str]]:
    frames: list[list[str]] = []
    output = output.replace('\x1b[2K', '')
    if '\f' in output:
        for raw_frame in output.split('\f'):
            lines = [
                normalize_terminal_line(line.strip())
                for line in raw_frame.splitlines()
                if line.strip()
            ]
            if lines:
                frames.append(lines)
        return frames

    for raw_frame in output.splitlines():
        for part in raw_frame.split('\r'):
            line = part.strip()
            if line:
                frames.append([normalize_terminal_line(line)])
    return frames


def keep_recent_logs_with_progress(
    frames: list[list[str]],
    log_lines: int,
) -> list[list[str]]:
    logs: list[str] = []
    output: list[list[str]] = []

    for frame in frames:
        log_frame = [line for line in frame if line.startswith('log:')]
        progress_frame = [
            line for line in frame if not line.startswith('log:')
        ]
        if log_frame:
            logs.extend(log_frame)
            logs = logs[-log_lines:]
        if progress_frame:
            output.append(logs + progress_frame)

    return output


def limit_animation_frames(frames: list[list[str]]) -> list[list[str]]:
    if len(frames) <= MAX_ANIMATION_FRAMES:
        return frames

    last_index = len(frames) - 1
    selected = [
        round(index * last_index / (MAX_ANIMATION_FRAMES - 1))
        for index in range(MAX_ANIMATION_FRAMES)
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


def svg_document(title: str, frames: list[list[str]]) -> str:
    width = SVG_WIDTH
    line_height = 24
    max_lines = max(len(frame) for frame in frames)
    height = 72 + max_lines * line_height
    duration = f'{max(len(frames), 1) * ANIMATION_FRAME_SECONDS:g}'
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
            f'dur="{duration}s" '
            'repeatCount="indefinite" '
            'calcMode="discrete" />' + ''.join(lines) + '</g>'
        )

    return f'''<svg
  xmlns="http://www.w3.org/2000/svg"
  width="{width}"
  height="{height}"
  viewBox="0 0 {width} {height}"
>
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
  </style>
  <rect class="terminal-bg" width="100%" height="100%" rx="10" />
  <circle class="dot-red" cx="28" cy="26" r="6" />
  <circle class="dot-yellow" cx="48" cy="26" r="6" />
  <circle class="dot-green" cx="68" cy="26" r="6" />
  <text class="terminal-title" x="96" y="32">{html.escape(title)}</text>
  {''.join(frame_groups)}
</svg>
'''


def render_svg(path: Path, title: str, frames: list[list[str]]) -> None:
    svg = svg_document(title, frames)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding='utf-8')


def check_svg(path: Path, expected: str) -> None:
    if not path.exists():
        raise SystemExit(f'missing generated asset: {path}')
    if path.read_text(encoding='utf-8') != expected:
        raise SystemExit(f'outdated generated asset: {path}')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for demo in DEMOS:
        output = STATIC_DIR / f'progressbar-{demo.name}.svg'
        frames = capture_demo(demo)
        if args.check:
            check_svg(output, svg_document(demo.title, frames))
        else:
            render_svg(output, demo.title, frames)


if __name__ == '__main__':
    main()
