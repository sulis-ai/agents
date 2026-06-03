"""Integration tests for the WP-008 `sulis-brain-query` CLI traverse modes.

These drive the *executable* (`sulis-brain-query`) as a subprocess — the
contract surface a skill or the Sulis agent invokes — and assert the JSON
envelope (`{"ok":true,"data":{"count":N,"entities":[...]}}`) plus the exit
code. They cover the five new mutually-exclusive modes added on top of the
existing `--list`/`--by-id`/`--verifying`/`--passing-verifying` group:

    --open      = draft requirements + hypothesis opportunities (merged/deduped)
    --done      = implemented/verified requirements
    --roadmap   = sidecar members resolved to entities
    --by-type {opportunity,requirement}
    --by-state STATE          (composable with --by-type)

The new verbs delegate to the WP-007 query seam (`find_requirements(state=)`,
`find_opportunities(state=)`, `find_roadmap`) and the `_OPEN_*`/`_DONE_*`
module constants — the CLI never re-derives the open/done state mapping
(ADR-006 single-source).

Seeding mirrors `tests/unit/test_brain_query_views.py`: the read seam treats
each instance as an opaque dict (no schema-validation on read), so the
fixtures write minimal entities carrying the schema-valid `state` values the
views filter on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# The executable under test lives in the scripts dir, three levels up from
# tests/integration/.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_CLI = _SCRIPTS_DIR / "sulis-brain-query"


# ─── Seed ids ────────────────────────────────────────────────────────────
_REQ_DRAFT = "dna:requirement:01ABCDEFGHJKMNPQRSTVWXYZ12"
_REQ_APPROVED = "dna:requirement:01BCDEFGHJKMNPQRSTVWXYZ123"
_REQ_IMPLEMENTED = "dna:requirement:01CDEFGHJKMNPQRSTVWXYZ1234"
_REQ_VERIFIED = "dna:requirement:01DEFGHJKMNPQRSTVWXYZ12345"
_OPP_HYPOTHESIS = "dna:opportunity:01EFGHJKMNPQRSTVWXYZ123456"
_OPP_VALIDATED = "dna:opportunity:01FGHJKMNPQRSTVWXYZ1234567"


# ─── Fixtures / helpers ─────────────────────────────────────────────────────


def _write_entity(base: Path, entity_type: str, entity_id: str, state: str) -> None:
    """Write one opaque instance under `base/product-development/<type>/`."""
    ulid = entity_id.split(":")[-1]
    p = base / "product-development" / entity_type / f"{ulid}.jsonld"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"id": entity_id, "state": state, "sys_status": "active"}))


def _write_roadmap_sidecar(brain_root: Path, members: list) -> None:
    """Write the ADR-001 roadmap sidecar at `<brain_root>/labels/roadmap.jsonld`."""
    sidecar = brain_root / "labels" / "roadmap.jsonld"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps({"label": "roadmap", "members": members}))


@pytest.fixture()
def seeded_store(tmp_path: Path) -> Path:
    """Seed a mixed graph + roadmap sidecar; return the `.brain/instances` dir.

    The roadmap sidecar lives at `<tmp>/.brain/labels/`; the entity instances
    at `<tmp>/.brain/instances/`. The CLI's `--base-dir` points at the latter;
    `--roadmap` resolves the brain root from it.
    """
    instances = tmp_path / ".brain" / "instances"
    _write_entity(instances, "requirement", _REQ_DRAFT, "draft")
    _write_entity(instances, "requirement", _REQ_APPROVED, "approved")
    _write_entity(instances, "requirement", _REQ_IMPLEMENTED, "implemented")
    _write_entity(instances, "requirement", _REQ_VERIFIED, "verified")
    _write_entity(instances, "opportunity", _OPP_HYPOTHESIS, "hypothesis")
    _write_entity(instances, "opportunity", _OPP_VALIDATED, "validated")
    _write_roadmap_sidecar(tmp_path / ".brain", [_OPP_HYPOTHESIS, _REQ_IMPLEMENTED])
    return instances


def _run_cli(base_dir: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke the CLI as a subprocess with `--base-dir` pinned, repo-root cwd-free."""
    return subprocess.run(
        [sys.executable, str(_CLI), "--base-dir", str(base_dir), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _ids(stdout: str) -> set:
    """Parse a success envelope's stdout → the set of entity ids."""
    payload = json.loads(stdout)
    assert payload["ok"] is True, payload
    return {e["id"] for e in payload["data"]["entities"]}


# ─── --open / --done / --roadmap named views ───────────────────────────────


def test_open_done_roadmap_modes(seeded_store: Path) -> None:
    # --open = draft requirements + hypothesis opportunities (merged/deduped).
    proc = _run_cli(seeded_store, "--open")
    assert proc.returncode == 0, proc.stderr
    assert _ids(proc.stdout) == {_REQ_DRAFT, _OPP_HYPOTHESIS}

    # --done = implemented + verified requirements.
    proc = _run_cli(seeded_store, "--done")
    assert proc.returncode == 0, proc.stderr
    assert _ids(proc.stdout) == {_REQ_IMPLEMENTED, _REQ_VERIFIED}

    # --roadmap = sidecar members resolved to entities.
    proc = _run_cli(seeded_store, "--roadmap")
    assert proc.returncode == 0, proc.stderr
    assert _ids(proc.stdout) == {_OPP_HYPOTHESIS, _REQ_IMPLEMENTED}

    # Envelope shape: count matches entities length.
    payload = json.loads(proc.stdout)
    assert payload["data"]["count"] == len(payload["data"]["entities"]) == 2


# ─── --by-type composed with --by-state ────────────────────────────────────


def test_by_type_by_state_compose(seeded_store: Path) -> None:
    # --by-type requirement --by-state approved → only the approved requirement.
    proc = _run_cli(seeded_store, "--by-type", "requirement", "--by-state", "approved")
    assert proc.returncode == 0, proc.stderr
    assert _ids(proc.stdout) == {_REQ_APPROVED}

    # --by-type without --by-state → all of that type.
    proc = _run_cli(seeded_store, "--by-type", "opportunity")
    assert proc.returncode == 0, proc.stderr
    assert _ids(proc.stdout) == {_OPP_HYPOTHESIS, _OPP_VALIDATED}

    # --by-type opportunity --by-state hypothesis → only the hypothesis opp.
    proc = _run_cli(seeded_store, "--by-type", "opportunity", "--by-state", "hypothesis")
    assert proc.returncode == 0, proc.stderr
    assert _ids(proc.stdout) == {_OPP_HYPOTHESIS}

    # --by-state is an option, not a mode: alone it doesn't satisfy the
    # required mutually-exclusive group, so argparse rejects (exit 2). It is
    # only meaningful as a narrowing modifier on --by-type.
    proc = _run_cli(seeded_store, "--by-state", "draft")
    assert proc.returncode == 2, proc.stdout
    assert "is required" in proc.stderr


# ─── empty store → count:0, exit 0 (NFR-01) ────────────────────────────────


def test_empty_store_count_zero(tmp_path: Path) -> None:
    empty = tmp_path / ".brain" / "instances"  # never created

    for args in (
        ("--open",),
        ("--done",),
        ("--roadmap",),
        ("--by-type", "requirement"),
        ("--by-type", "opportunity", "--by-state", "hypothesis"),
    ):
        proc = _run_cli(empty, *args)
        assert proc.returncode == 0, (args, proc.stderr)
        payload = json.loads(proc.stdout)
        assert payload == {"ok": True, "data": {"count": 0, "entities": []}}, args


# ─── new modes are mutually exclusive with the existing ones ────────────────


def test_new_modes_mutually_exclusive_with_existing(seeded_store: Path) -> None:
    # --open + --list together → argparse rejects (exit 2).
    proc = _run_cli(seeded_store, "--open", "--list", "requirement")
    assert proc.returncode == 2, proc.stdout
    assert "not allowed with" in proc.stderr or "mutually exclusive" in proc.stderr


# ─── existing modes still behave (regression) ──────────────────────────────


def test_existing_modes_unaffected(seeded_store: Path) -> None:
    # --list opportunity enumerates every opportunity, unchanged.
    proc = _run_cli(seeded_store, "--list", "opportunity")
    assert proc.returncode == 0, proc.stderr
    assert _ids(proc.stdout) == {_OPP_HYPOTHESIS, _OPP_VALIDATED}

    # --by-id fetches the single matching instance, unchanged.
    proc = _run_cli(seeded_store, "--by-id", _REQ_DRAFT)
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["data"]["count"] == 1
    assert payload["data"]["entities"][0]["id"] == _REQ_DRAFT

    # --by-id for an absent id → count:0, exit 0 (existing best-effort shape).
    proc = _run_cli(seeded_store, "--by-id", "dna:requirement:01ZZZZZZZZZZZZZZZZZZZZZZZZZ")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["data"]["count"] == 0
