"""test_sulis_change_emits_entity — start emits a Change brain entity (#128).

Pins the wiring (`_emit_change_entity` in sulis-change): starting a change now
creates a Change NODE in the brain, and the wiring is strictly NON-FATAL —
no product, or any failure, must never break change creation (so existing
start tests, which have no product in their tmp repos, stay green).
"""

from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
_ULID = "0123456789ABCDEFGHJKMNPQRS"
_PRODUCT = f"dna:product:{_ULID}"


@pytest.fixture(autouse=True)
def _pin_brain_at_tmp(tmp_path, monkeypatch):
    """Pin the brain at `tmp_path/.brain/instances` for these tests.

    The brain's default location is now `{sulis_state_base}/.brain/instances`
    (de-branch-scoped — no longer `<repo>/.brain`), and the repo-wide conftest
    points SULIS_STATE_DIR at its own separate tmp dir. These tests pass
    `tmp_path` as the repo root and seed/assert the brain at
    `tmp_path/.brain/instances`, so pin the brain there explicitly via
    SULIS_BRAIN_BASE_DIR (precedence-2 override — always wins over the default,
    independent of state-dir isolation). Tests that set SULIS_BRAIN_BASE_DIR to
    a different path override this per-test.
    """
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(tmp_path / ".brain" / "instances"))


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_emit_mod", str(_SCRIPTS / "sulis-change"))
    spec = importlib.util.spec_from_loader("sulis_change_emit_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_mod = _load_sulis_change()


def _metadata() -> dict:
    return {
        "change_id": _ULID, "handle": "CH-01HQ8X", "slug": "fix-login-bug",
        "primitive": "fix", "intent": "fix the login bug",
        "branch": "change/fix-login-bug", "base_sha": "7a6d267",
        "started_at": "2026-06-12T09:00:00Z",
    }


def _make_product(repo_root: Path) -> None:
    d = repo_root / ".brain" / "instances" / "product-development" / "product"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{_ULID}.jsonld").write_text(
        json.dumps({"id": _PRODUCT, "name": "P", "state": "active", "sys_status": "active"}),
        encoding="utf-8")


def test_start_emits_change_entity_when_a_product_exists(tmp_path):
    _make_product(tmp_path)
    _mod._emit_change_entity(tmp_path, _metadata())
    out = (tmp_path / ".brain" / "instances" / "product-development" / "change"
           / f"{_ULID}.jsonld")
    assert out.exists()
    e = json.loads(out.read_text())
    assert e["id"] == f"dna:change:{_ULID}"
    assert e["state"] == "in-flight"
    assert e["for_product"] == _PRODUCT


def test_mark_shipped_transitions_entity_to_shipped(tmp_path):
    # start opens in-flight; mark-shipped ships it (slice 2 lifecycle wiring).
    _make_product(tmp_path)
    _mod._emit_change_entity(tmp_path, _metadata())
    _mod._transition_change_entity(tmp_path, _ULID, "shipped")
    e = json.loads((tmp_path / ".brain" / "instances" / "product-development"
                    / "change" / f"{_ULID}.jsonld").read_text())
    assert e["state"] == "shipped" and "shipped_at" in e


def test_nuke_transitions_entity_to_nuked(tmp_path):
    _make_product(tmp_path)
    _mod._emit_change_entity(tmp_path, _metadata())
    _mod._transition_change_entity(tmp_path, _ULID, "nuked")
    e = json.loads((tmp_path / ".brain" / "instances" / "product-development"
                    / "change" / f"{_ULID}.jsonld").read_text())
    assert e["state"] == "nuked" and "valid_to" in e


def test_main_repo_root_resolves_repo_root(tmp_path):
    # #129 B2: the per-stage LifecycleRun co-locates with the Change entity by
    # resolving the MAIN repo root. From a plain repo it's the repo root.
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert _mod._main_repo_root(tmp_path) == tmp_path.resolve()


def test_nuke_rolls_back_the_produced_set(tmp_path):
    # #67 3c: nuking a change soft-deletes the entities it produced (audit kept).
    _make_product(tmp_path)
    _mod._emit_change_entity(tmp_path, _metadata())
    # An entity the change produced, stamped via the same brain.
    from _provenance_stamp import stamping_repo
    from _entity_adapter_local import LocalFileEntityAdapter
    repo = stamping_repo(LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances", domain="product-development"),
        change_id=_ULID)
    repo.save("scenario", {
        "id": f"dna:scenario:{_ULID}", "name": "n", "verifies": [f"dna:requirement:{_ULID}"],
        "exercises": f"dna:design:{_ULID}", "journey": f"dna:workflow:{_ULID}",
        "state": "draft", "sys_status": "active"})

    _mod._transition_change_entity(tmp_path, _ULID, "nuked")

    scen = json.loads((tmp_path / ".brain" / "instances" / "product-development"
                       / "scenario" / f"{_ULID}.jsonld").read_text())
    assert scen["sys_status"] == "deleted"     # rolled back (soft)
    change = json.loads((tmp_path / ".brain" / "instances" / "product-development"
                         / "change" / f"{_ULID}.jsonld").read_text())
    assert change["state"] == "nuked"


def test_transition_is_noop_for_a_change_with_no_entity(tmp_path):
    # A change started on an older plugin has no entity → transition no-ops,
    # never raises (non-fatal).
    _make_product(tmp_path)
    _mod._transition_change_entity(tmp_path, _ULID, "shipped")  # nothing emitted first
    change_dir = tmp_path / ".brain" / "instances" / "product-development" / "change"
    assert not change_dir.exists() or not list(change_dir.glob("*.jsonld"))


def test_emit_honors_configured_brain_location(tmp_path, monkeypatch):
    # #127: the change-entity wiring writes to the USER-CONFIGURED location, not
    # the hard-coded <repo>/.brain — both the write AND product-resolution route
    # through the shared resolver.
    brain = tmp_path / "elsewhere" / "instances"
    monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(brain))
    pd = brain / "product-development" / "product"
    pd.mkdir(parents=True)
    (pd / f"{_ULID}.jsonld").write_text(json.dumps(
        {"id": _PRODUCT, "name": "P", "state": "active", "sys_status": "active"}))

    _mod._emit_change_entity(tmp_path, _metadata())

    assert (brain / "product-development" / "change" / f"{_ULID}.jsonld").exists()
    assert not (tmp_path / ".brain").exists()   # nothing in the default location


def test_emit_writes_product_less_change_when_no_product(tmp_path):
    # for_product is optional — with no product to resolve, start still emits a
    # Change entity (without the product link), so product-less changes are in
    # the brain too.
    _mod._emit_change_entity(tmp_path, _metadata())
    out = (tmp_path / ".brain" / "instances" / "product-development" / "change"
           / f"{_ULID}.jsonld")
    assert out.exists()
    e = json.loads(out.read_text())
    assert "for_product" not in e and e["state"] == "in-flight"


def test_emit_never_raises_on_bad_metadata(tmp_path):
    _make_product(tmp_path)
    # Missing required fields would make a bad entity; the wiring must swallow
    # it (best-effort), never propagate — start must not break.
    _mod._emit_change_entity(tmp_path, {"change_id": _ULID})  # no handle/slug/intent/...
    # No exception = pass. (A partial entity is rejected by the port; swallowed.)
