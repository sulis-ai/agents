"""Wire the auto-back-merge SHELL suite into the pytest CI gate (WP-009).

branch-ci runs `uv run pytest tests/unit/ -q` as its fast gate — it does
NOT execute `run.sh` or any `*.sh` test directly. Without this wrapper,
the bash suite (the canonical-string parity test, the chaos race-window
test, the reconciled methodology characterisation test, …) would author
correctly but never run in CI — it would be discoverable only by a
maintainer who knows to invoke `run.sh` by hand.

This wrapper makes the shell suite a first-class CI citizen: it invokes
`plugins/sulis/scripts/tests/run.sh` as a subprocess and asserts a clean
exit. `run.sh` itself orchestrates every `test_*.sh` under unit/,
integration/, chaos/, and methodology/ and exits non-zero on any
failure (it prints the FAILED list to stderr, which we surface on
failure). This keeps the whole change inside WP-009's contract
(`plugins/sulis/scripts/tests/`) — no CI-YAML edit required, which is
out of this WP's scope.

Acceptance tie-in: WP-009 DoD requires the full test run GREEN
"including the .sh methodology tests, not just pytest". This is the
seam that makes that true under the existing `pytest tests/unit/` gate.

Stdlib only (subprocess + pathlib). bash is required on the runner; it
is present on ubuntu-latest (branch-ci) and on macOS dev machines.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo root
_TESTS_DIR = Path(__file__).resolve().parents[1]
_RUN_SH = _TESTS_DIR / "run.sh"


def test_run_sh_exists() -> None:
    assert _RUN_SH.is_file(), f"shell-suite orchestrator missing at {_RUN_SH}"


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not on PATH")
def test_abm_shell_suite_passes() -> None:
    """The whole bash suite (unit/integration/chaos/methodology) is green.

    Delegates to run.sh, which discovers and runs every test_*.sh and
    exits 0 iff all pass. On failure we surface run.sh's stdout+stderr
    (which names the FAILED tests) so the CI log is actionable.
    """
    proc = subprocess.run(
        ["bash", str(_RUN_SH)],
        capture_output=True,
        text=True,
        cwd=str(_TESTS_DIR),
        timeout=300,
    )
    assert proc.returncode == 0, (
        "auto-back-merge shell suite (run.sh) failed.\n"
        f"--- stdout ---\n{proc.stdout}\n"
        f"--- stderr ---\n{proc.stderr}"
    )
