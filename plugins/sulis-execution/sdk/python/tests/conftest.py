"""Test fixtures for the sulis-execution Python SDK.

The fixtures here provide a fake `wpx-*` binary directory so tests
exercise the subprocess transport end-to-end without needing the real
underlying CLI or any git/GitHub state.

A fake binary is a shell script that emits a known JSON envelope to
stdout and exits with a specified code. Tests can configure what each
fake binary does per-test via the `fake_wpx_dir` fixture's helpers.
"""
from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def fake_wpx_dir(tmp_path: Path) -> Path:
    """Return an empty directory that tests can populate with fake binaries."""
    d = tmp_path / "fake-wpx"
    d.mkdir()
    return d


def _write_fake_binary(
    target_dir: Path,
    binary_name: str,
    *,
    stdout_payload: dict[str, Any] | str | None = None,
    stderr_payload: str = "",
    exit_code: int = 0,
) -> Path:
    """Write a fake binary that emits the configured stdout/stderr/exit code.

    Returns the path to the fake binary.
    """
    binary = target_dir / binary_name
    if isinstance(stdout_payload, dict):
        stdout_text = json.dumps(stdout_payload)
    elif stdout_payload is None:
        stdout_text = ""
    else:
        stdout_text = stdout_payload

    # Use a Python shebang for portability (assumes python3 on PATH)
    script = (
        f"#!{sys.executable}\n"
        f"import sys\n"
        f"sys.stdout.write({stdout_text!r})\n"
        f"sys.stderr.write({stderr_payload!r})\n"
        f"sys.exit({exit_code})\n"
    )
    binary.write_text(script)
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return binary


@pytest.fixture
def make_fake_binary(fake_wpx_dir: Path):
    """Factory fixture for creating fake CLI binaries.

    Usage:

        make_fake_binary("wpx-pipeline",
                         stdout_payload={"ok": True, "data": {...}},
                         exit_code=0)
    """
    def _factory(
        binary_name: str,
        *,
        stdout_payload: dict[str, Any] | str | None = None,
        stderr_payload: str = "",
        exit_code: int = 0,
    ) -> Path:
        return _write_fake_binary(
            fake_wpx_dir,
            binary_name,
            stdout_payload=stdout_payload,
            stderr_payload=stderr_payload,
            exit_code=exit_code,
        )
    return _factory


@pytest.fixture
def tmp_repo_root(tmp_path: Path) -> Path:
    """A tmp directory to serve as the repo_root parameter for clients."""
    d = tmp_path / "repo"
    d.mkdir()
    return d
