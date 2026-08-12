"""Build the wheels the in-browser console installs.

The console must run the version of progressbar2 being documented, not
whatever is on PyPI, so the wheel is built from the working tree at docs
build time. Neither wheel is committed.

If the ``build`` package is missing, or ``pip download`` cannot reach
PyPI, this script hard-fails rather than degrading. A docs build that
silently ships without wheels would produce a site whose in-browser
console has a dead "Run" button -- worse than a build that fails loudly
where it can be noticed (locally or on Read the Docs) before publish.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / 'docs' / '_static' / 'wheels'


#: Editor and sync-tool leftovers that must never reach a reader. These
#: are `*.py` files inside the package, so setuptools' build_py copies
#: them as modules and no declarative `exclude` can stop it -- see the
#: note in pyproject.toml.
STRAY_MODULE_MARKERS = ('.sync-conflict-', '.orig', '.rej', '.bak')


def _strip_stray_modules(wheel: pathlib.Path) -> None:
    """Rewrite the wheel without any local scratch files, and say so.

    The docs build produces the wheel the in-browser console installs, so
    a dirty working tree would otherwise ship a maintainer's leftovers to
    every reader -- silently, since nothing else inspects the wheel.

    This strips rather than fails: the files are the maintainer's to keep
    or remove, and refusing to build the docs over them would be a heavy
    price for a problem the reader never needs to know about. The warning
    is loud because the same files *will* reach PyPI if a release is ever
    cut from a dirty tree, and nothing in the release path checks.
    """
    with zipfile.ZipFile(wheel) as archive:
        entries = archive.infolist()
        stray = [
            info
            for info in entries
            if any(marker in info.filename for marker in STRAY_MODULE_MARKERS)
        ]
        if not stray:
            return
        keep = [
            (info, archive.read(info.filename))
            for info in entries
            if info not in stray
        ]

    with zipfile.ZipFile(wheel, 'w', zipfile.ZIP_DEFLATED) as archive:
        for info, payload in keep:
            archive.writestr(info, payload)

    listing = '\n  '.join(sorted(info.filename for info in stray))
    print(
        f'warning: stripped {len(stray)} local scratch file(s) from '
        f'{wheel.name}:\n  {listing}\n'
        '  They sit inside the progressbar package, so setuptools packages '
        'them as modules and no declarative exclude can stop it.\n'
        '  The docs console wheel is now clean, but a release cut from this '
        'tree would still ship them.',
        file=sys.stderr,
    )


def main() -> None:
    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True)

    # `python -m build` leaves a `build/` scratch tree at the repo root, and
    # setuptools' package discovery does not exclude it. Left in place, the
    # next run embeds the previous run's copy inside the new wheel, so the
    # wheel served to the browser grows on every local docs build and
    # carries nested duplicates of the source tree. Measured: 217 KB -> 337
    # KB after a single extra run. Clean it first.
    shutil.rmtree(ROOT / 'build', ignore_errors=True)
    for egg_info in ROOT.glob('*.egg-info'):
        shutil.rmtree(egg_info, ignore_errors=True)

    subprocess.run(
        [sys.executable, '-m', 'build', '--wheel', '--outdir', str(TARGET)],
        cwd=ROOT,
        check=True,
    )
    # Deliberately unconstrained. `pyproject.toml` declares only
    # `python-utils >= 3.8.1`, so this fetches exactly what a user running
    # `pip install progressbar2` today would get. Pinning the console
    # tighter than the package's own dependency range would make the demo
    # unrepresentative of what readers actually install -- and if a future
    # python-utils breaks progressbar2, it breaks it for everyone, not just
    # the console. Task 21's browser smoke test is the gate that catches it.
    subprocess.run(
        [
            sys.executable,
            '-m',
            'pip',
            'download',
            '--no-deps',
            '--only-binary=:all:',
            '--dest',
            str(TARGET),
            'python-utils',
        ],
        check=True,
    )

    wheels = sorted(path.name for path in TARGET.glob('*.whl'))
    if len(wheels) != 2:
        raise SystemExit(f'expected 2 wheels, found {wheels}')
    # Accept both `py3-none-any` and `py2.py3-none-any`: the Task 17 spike
    # found `uv build` emits the latter and micropip installs it happily.
    # The point of the check is "pure Python, not a compiled wheel".
    for wheel in wheels:
        if not wheel.endswith('-none-any.whl'):
            raise SystemExit(f'not a pure-Python wheel: {wheel}')

    for wheel in wheels:
        _strip_stray_modules(TARGET / wheel)

    (TARGET / 'wheels.json').write_text(
        json.dumps({'wheels': wheels}, indent=2) + '\n',
        encoding='utf-8',
    )

    # Clean up after ourselves as well as before. `build/lib/` holds a copy
    # of the package, so leaving it behind makes every later `tox -e ruff`
    # and `tox -e codespell` run scan the source twice -- and report
    # failures against a directory the developer never edited.
    shutil.rmtree(ROOT / 'build', ignore_errors=True)
    for egg_info in ROOT.glob('*.egg-info'):
        shutil.rmtree(egg_info, ignore_errors=True)


if __name__ == '__main__':
    main()
