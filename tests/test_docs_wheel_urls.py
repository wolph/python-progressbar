"""Rebuilt documentation wheels must not reuse stale browser cache entries."""

from __future__ import annotations

import hashlib
import runpy
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

SCRIPT_PATH: Path = (
    Path(__file__).resolve().parents[1] / 'scripts/build_docs_wheels.py'
)
wheel_url: Callable[[Path], str] = runpy.run_path(str(SCRIPT_PATH))[
    'wheel_url'
]


def test_wheel_url_changes_with_package_contents(tmp_path: Path) -> None:
    wheel: Path = tmp_path / 'progressbar2-4.5.0-py3-none-any.whl'
    wheel.write_bytes(b'old package')
    old_url: str = wheel_url(wheel)
    wheel.write_bytes(b'new package')
    new_url: str = wheel_url(wheel)
    assert old_url != new_url
    assert urlsplit(old_url).path == urlsplit(new_url).path == wheel.name
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() in new_url
