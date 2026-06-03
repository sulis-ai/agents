"""WP-006 — integration (e2e) tests for the ``sulis-capture`` CLI.

The thin executable front door of the capture path. These tests invoke the
**real** CLI as a subprocess against a temp ``.brain/instances`` and the
**real** vendored schemas under
``plugins/sulis/brain/compiled/{foundation,product-development}/`` — no mock
store (MEA-09). They pin the CLI's JSON-envelope consumer contract
(CONTRACT_FIRST): ``{"ok": true, "data": {...}}`` exit 0 /
``{"ok": false, "error": "..."}`` exit 1, with ``main()`` never raising
(NFR-01).

This is the concrete artifact named in the TDD Verification Plan §4
(``test_capture_lands_whole_chain``).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent  # plugins/sulis/scripts
_CLI = _SCRIPTS_DIR / "sulis-capture"

_OPP_ID_RE = re.compile(r"^dna:opportunity:[0-9A-HJKMNP-TV-Z]{26}$")
_REQ_ID_RE = re.compile(r"^dna:requirement:[0-9A-HJKMNP-TV-Z]{26}$")
_TENANT_ID_RE = re.compile(r"^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$")
_PRODUCT_ID_RE = re.compile(r"^dna:product:[0-9A-HJKMNP-TV-Z]{26}$")

_WHY = "Captured ideas keep getting lost because they have no why."
_WHAT = "Every captured idea is rooted in an Opportunity before it lands."


# ─── fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """A tmp repo root carrying a minimal ``.sulis/repo-contract.yml``.

    The CLI reads the ``repo:`` shorthand from this file to seed the canonical
    tenant identity (ADR-002). A real shorthand here makes the chain joinable.
    """
    contract_dir = tmp_path / ".sulis"
    contract_dir.mkdir(parents=True, exist_ok=True)
    (contract_dir / "repo-contract.yml").write_text("repo: sulis-ai/agents\n")
    return tmp_path


@pytest.fixture
def base_dir(repo_root: Path) -> Path:
    """The ``.brain/instances`` directory the adapters write under."""
    return repo_root / ".brain" / "instances"


@pytest.fixture
def brain_root(repo_root: Path) -> Path:
    """The ``.brain/`` root (parent of ``instances``); the roadmap sidecar
    lives under it at ``labels/roadmap.jsonld``."""
    return repo_root / ".brain"


def _run_cli(repo_root: Path, base_dir: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke the real ``sulis-capture`` CLI as a subprocess.

    The CLI is run through the current interpreter (``sys.executable``) so it
    finds the sibling ``_brain_capture`` / ``_entity_adapter_local`` modules
    via the script's own ``sys.path`` insert.
    """
    cmd = [
        sys.executable,
        str(_CLI),
        "--repo-root", str(repo_root),
        "--base-dir", str(base_dir),
        *args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def _parse(proc: subprocess.CompletedProcess) -> dict:
    """Parse the CLI's stdout as the JSON envelope; fail loudly if it isn't."""
    assert proc.stdout.strip(), f"no stdout; stderr={proc.stderr!r}"
    return json.loads(proc.stdout)


def _instance_files(base_dir: Path) -> list[Path]:
    return sorted(base_dir.rglob("*.jsonld"))


# ─── the six named tests (WP-006 Red) ───────────────────────────────────────


def test_capture_lands_whole_chain(repo_root: Path, base_dir: Path) -> None:
    """quick capture with a what → exit 0, ok:true, whole chain on disk.

    Tenant + Product + Opportunity + Requirement all exist, and the chain
    ``Requirement.source`` → ``Opportunity.for_product`` → ``Product`` →
    ``Tenant`` resolves end-to-end with no dangling ref.
    """
    proc = _run_cli(
        repo_root, base_dir,
        "--why-intensity", "quick",
        "--why", _WHY,
        "--what", _WHAT,
        "--seed", "whole-chain-seed",
    )
    assert proc.returncode == 0, f"stderr={proc.stderr!r} stdout={proc.stdout!r}"
    env = _parse(proc)
    assert env["ok"] is True
    data = env["data"]

    opp_id = data["opportunity_id"]
    req_id = data["requirement_id"]
    assert _OPP_ID_RE.match(opp_id)
    assert _REQ_ID_RE.match(req_id)
    tenant_id = data["chain"]["tenant_id"]
    product_id = data["chain"]["product_id"]
    assert _TENANT_ID_RE.match(tenant_id)
    assert _PRODUCT_ID_RE.match(product_id)
    assert data["bootstrapped"] is True

    # Every tier is on disk in its domain/type subtree.
    def _load(domain: str, etype: str, eid: str) -> dict:
        ulid = eid.rsplit(":", 1)[-1]
        path = base_dir / domain / etype / f"{ulid}.jsonld"
        assert path.exists(), f"missing {path}"
        return json.loads(path.read_text())

    tenant = _load("foundation", "tenant", tenant_id)
    product = _load("product-development", "product", product_id)
    opportunity = _load("product-development", "opportunity", opp_id)
    requirement = _load("product-development", "requirement", req_id)

    # Whole chain — no dangling ref.
    assert requirement["source"] == opp_id
    assert opportunity["for_product"] == product_id
    assert product["belongs_to_tenant"] == tenant_id
    assert tenant["id"] == tenant_id


def test_capture_no_why_returns_ok_false(repo_root: Path, base_dir: Path) -> None:
    """quick + blank why → exit 1, ok:false, error mentions 'why'; store
    unchanged (FR-02). Nothing is written, not even the backing chain."""
    proc = _run_cli(
        repo_root, base_dir,
        "--why-intensity", "quick",
        "--why", "",
        "--what", _WHAT,
        "--seed", "no-why-seed",
    )
    assert proc.returncode == 1, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    env = _parse(proc)
    assert env["ok"] is False
    assert "why" in env["error"].lower()
    # Store untouched — the why-first gate fires before any write.
    assert _instance_files(base_dir) == []


def test_capture_idempotent_same_seed(repo_root: Path, base_dir: Path) -> None:
    """Two runs, same seed → same ids, no duplicate instance files (NFR-04)."""
    args = (
        "--why-intensity", "quick",
        "--why", _WHY,
        "--what", _WHAT,
        "--seed", "idempotent-seed",
    )
    first = _parse(_run_cli(repo_root, base_dir, *args))
    files_after_first = _instance_files(base_dir)
    second = _parse(_run_cli(repo_root, base_dir, *args))
    files_after_second = _instance_files(base_dir)

    assert first["ok"] is True and second["ok"] is True
    assert first["data"]["opportunity_id"] == second["data"]["opportunity_id"]
    assert first["data"]["requirement_id"] == second["data"]["requirement_id"]
    assert first["data"]["chain"] == second["data"]["chain"]
    # No duplicate files — the second run overwrites in place.
    assert files_after_first == files_after_second


def test_capture_roadmap_flag_lands_in_sidecar(
    repo_root: Path, base_dir: Path, brain_root: Path
) -> None:
    """--roadmap → emitted ids present in ``.brain/labels/roadmap.jsonld``."""
    proc = _run_cli(
        repo_root, base_dir,
        "--why-intensity", "quick",
        "--why", _WHY,
        "--what", _WHAT,
        "--seed", "roadmap-seed",
        "--roadmap",
    )
    assert proc.returncode == 0, f"stderr={proc.stderr!r}"
    env = _parse(proc)
    assert env["ok"] is True
    assert env["data"]["roadmap"] is True

    sidecar = brain_root / "labels" / "roadmap.jsonld"
    assert sidecar.exists(), f"missing roadmap sidecar at {sidecar}"
    members = json.loads(sidecar.read_text())["members"]
    assert env["data"]["opportunity_id"] in members
    assert env["data"]["requirement_id"] in members


def test_brain_unavailable_returns_ok_false(repo_root: Path, base_dir: Path) -> None:
    """Point the adapters at a schemas dir with no vendored schemas →
    exit 1, ok:false, no traceback (NFR-01)."""
    empty_schemas = repo_root / "_no_schemas_here"
    empty_schemas.mkdir(parents=True, exist_ok=True)
    proc = _run_cli(
        repo_root, base_dir,
        "--why-intensity", "quick",
        "--why", _WHY,
        "--what", _WHAT,
        "--seed", "brain-down-seed",
        "--schemas-dir", str(empty_schemas),
    )
    assert proc.returncode == 1, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    env = _parse(proc)
    assert env["ok"] is False
    assert env["error"]  # a plain message, not empty
    # No Python traceback leaked to stderr — main() never raises.
    assert "Traceback (most recent call last)" not in proc.stderr


def test_missing_repo_contract_returns_ok_false(tmp_path: Path) -> None:
    """No ``.sulis/repo-contract.yml`` → exit 1, ok:false, plain message;
    no crash (Contract invariant: degrade, never crash).

    Uses a bare tmp dir with no contract file so the repo-shorthand resolve
    returns ``None`` before any adapter is touched.
    """
    bare_root = tmp_path / "no_contract"
    bare_root.mkdir(parents=True, exist_ok=True)
    proc = _run_cli(
        bare_root, bare_root / ".brain" / "instances",
        "--why-intensity", "quick",
        "--why", _WHY,
        "--what", _WHAT,
        "--seed", "no-contract-seed",
    )
    assert proc.returncode == 1, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    env = _parse(proc)
    assert env["ok"] is False
    assert env["error"]
    assert "Traceback (most recent call last)" not in proc.stderr


def test_envelope_shape_matches_siblings(repo_root: Path, base_dir: Path) -> None:
    """ok:true payload has the documented keys; ok:false payload is only
    ``ok``+``error`` — identical envelope shape to the sibling CLIs."""
    ok_proc = _run_cli(
        repo_root, base_dir,
        "--why-intensity", "quick",
        "--why", _WHY,
        "--what", _WHAT,
        "--seed", "envelope-seed",
    )
    ok_env = _parse(ok_proc)
    assert set(ok_env.keys()) == {"ok", "data"}
    assert ok_env["ok"] is True
    assert set(ok_env["data"].keys()) == {
        "opportunity_id", "requirement_id", "roadmap", "chain", "bootstrapped",
    }
    assert set(ok_env["data"]["chain"].keys()) == {"tenant_id", "product_id"}

    err_proc = _run_cli(
        repo_root, base_dir,
        "--why-intensity", "quick",
        "--why", "",
        "--seed", "envelope-err-seed",
    )
    err_env = _parse(err_proc)
    assert set(err_env.keys()) == {"ok", "error"}
    assert err_env["ok"] is False
    assert isinstance(err_env["error"], str)
