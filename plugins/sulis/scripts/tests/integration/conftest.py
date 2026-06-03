"""Per-directory conftest for integration tests.

Adds the integration test directory to sys.path so individual test modules
can `from testbed import train_testbed` directly (the TrainTestbed fixture
lives in testbed.py per HD-002).

Re-exports the `train_testbed` fixture from testbed.py so pytest's
fixture discovery finds it without each test module needing to import it
explicitly. (Tests that want to inspect helpers from testbed.py can still
`from testbed import FakeGHClient, TrainTestbed` as a normal import.)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Re-export the fixture so pytest discovers it without per-test imports.
from testbed import train_testbed  # noqa: E402, F401

# NOTE: SULIS_STATE_DIR isolation now lives in the root conftest
# (tests/conftest.py) as a repo-wide autouse fixture, so it covers unit tests
# too. It is intentionally not duplicated here.


# ─── shared brain-store fixtures ─────────────────────────────────────────────
# The capture / query / scenario CLIs all run against a temp ``.brain/instances``
# rooted under a tmp repo carrying a minimal ``.sulis/repo-contract.yml`` (the
# CLIs read the ``repo:`` shorthand to derive the canonical tenant id, ADR-002).
# Extracted here once: two integration suites (capture e2e, scenarios-from-graph)
# were each defining the same repo_root/base_dir/brain_root trio (EP-03 — extract
# the shared primitive at the 2-consumer threshold).


@pytest.fixture
def brain_repo_root(tmp_path: Path) -> Path:
    """A tmp repo root with a minimal ``.sulis/repo-contract.yml``.

    Carries ``repo: sulis-ai/agents`` (the tenant-identity shorthand) and a
    ``targets.local`` placeholder. The shorthand makes the bootstrapped backing
    chain joinable (ADR-002); the target is required by
    ``sulis-verify-acceptance`` (it resolves a target URL before running) but is
    never dereferenced by ``subprocess`` journey steps, so a placeholder is fine.
    Suites that don't run the verify CLI simply ignore the targets block.
    """
    contract_dir = tmp_path / ".sulis"
    contract_dir.mkdir(parents=True, exist_ok=True)
    (contract_dir / "repo-contract.yml").write_text(
        "repo: sulis-ai/agents\n"
        "targets:\n"
        "  local: http://localhost:0\n"
    )
    return tmp_path


@pytest.fixture
def brain_base_dir(brain_repo_root: Path) -> Path:
    """The ``.brain/instances`` directory the adapters write under."""
    return brain_repo_root / ".brain" / "instances"


@pytest.fixture
def brain_label_root(brain_repo_root: Path) -> Path:
    """The ``.brain/`` root; the roadmap sidecar lives at ``labels/roadmap.jsonld``."""
    return brain_repo_root / ".brain"
