"""Smoke test: `wpx` resolves its OWN scripts dir, not a cache pick (#49).

`wpx` lives IN scripts/ alongside its `wpx-*` siblings, so it must resolve
relative to itself via `realpath($0)` — never by globbing the plugin cache
(which mis-ranks versions lexically). This test invokes `wpx resolve`:

  1. via its absolute path, and
  2. via a symlink in a temp dir,

and asserts both report the real scripts directory. The symlink case proves
`realpath` (not `dirname $0`) is used — a bare `dirname` would report the
symlink's directory, not the tool's true home.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent
_WPX = _SCRIPTS_DIR / "wpx"


def _run_resolve(invoke_path: Path, cwd: Path) -> str:
    # Scrub the real cache from HOME so a cache-glob fallback cannot
    # accidentally satisfy the test; only self-location should succeed.
    env = dict(os.environ)
    env["HOME"] = str(cwd)
    proc = subprocess.run(
        [str(invoke_path), "resolve"],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"wpx resolve failed: {proc.stderr}"
    return proc.stdout.strip()


def test_resolves_own_dir_via_absolute_path(tmp_path):
    resolved = _run_resolve(_WPX, tmp_path)
    assert Path(resolved).resolve() == _SCRIPTS_DIR.resolve()


def test_resolves_own_dir_via_symlink(tmp_path):
    link = tmp_path / "wpx-link"
    link.symlink_to(_WPX)
    resolved = _run_resolve(link, tmp_path)
    # Must point at the real scripts dir, NOT tmp_path (the symlink's home).
    assert Path(resolved).resolve() == _SCRIPTS_DIR.resolve()
