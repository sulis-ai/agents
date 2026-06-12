"""test_change_emission — Change-manifest → Change-entity (#128, DR-031).

Pins the emission helper against the REAL schema + the REAL LocalFileEntityAdapter
(the #52 port) — no mocks: `emit_change` saving through the adapter only succeeds
if the composed dict actually validates against the vendored change.schema.json.
"""

from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]

import sys  # noqa: E402
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_emission import compose_change, emit_change, resolve_for_product  # noqa: E402
from _entity_adapter_local import LocalFileEntityAdapter  # noqa: E402

_ULID = "0123456789ABCDEFGHJKMNPQRS"
_PRODUCT = f"dna:product:{_ULID}"


def _record(**over) -> dict:
    r = {
        "change_id": _ULID,
        "handle": "CH-01HQ8X",
        "slug": "fix-login-bug",
        "intent": "fix   the login   bug",   # whitespace to be flattened
        "primitive": "fix",
        "branch": "change/fix-login-bug",
        "base_sha": "7a6d267cb05960aba6246ef508ba343ee9f50442",
        "started_at": "2026-06-12T09:00:00Z",
    }
    r.update(over)
    return r


# ─── compose_change (pure) ─────────────────────────────────────────────────


def test_compose_reuses_the_manifest_ulid_as_entity_id():
    c = compose_change(change_id=_ULID, handle="CH-X", slug="s", intent="i",
                       primitive="fix", for_product=_PRODUCT, started_at="2026-06-12T09:00:00Z")
    assert c["id"] == f"dna:change:{_ULID}"
    assert c["state"] == "in-flight"          # default earliest state
    assert c["intent"] == "i"


def test_compose_flattens_intent_whitespace():
    c = compose_change(change_id=_ULID, handle="CH-X", slug="s", intent="fix   the   bug",
                       primitive="fix", for_product=_PRODUCT, started_at="2026-06-12T09:00:00Z")
    assert c["intent"] == "fix the bug"


def test_compose_omits_none_optionals_not_nulls():
    c = compose_change(change_id=_ULID, handle="CH-X", slug="s", intent="i",
                       primitive="fix", for_product=_PRODUCT, started_at="2026-06-12T09:00:00Z")
    for k in ("parent_change", "relationship", "base_sha", "branch", "by_actor", "shipped_at"):
        assert k not in c


def test_compose_parent_defaults_relationship_when_omitted():
    c = compose_change(change_id=_ULID, handle="CH-X", slug="s", intent="i", primitive="fix",
                       for_product=_PRODUCT, started_at="2026-06-12T09:00:00Z",
                       parent_change=f"dna:change:{_ULID}")
    assert c["relationship"] == "builds_on"   # never an empty link (#123 bug shape)


# ─── resolve_for_product ───────────────────────────────────────────────────


def _make_product(base: Path, pid: str) -> None:
    d = base / ".brain" / "instances" / "product-development" / "product"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{pid.rsplit(':', 1)[-1]}.jsonld").write_text(
        json.dumps({"id": pid, "name": "P", "state": "active", "sys_status": "active"}),
        encoding="utf-8")


def test_resolve_picks_the_single_product(tmp_path):
    _make_product(tmp_path, _PRODUCT)
    assert resolve_for_product(tmp_path) == _PRODUCT


def test_resolve_none_when_zero_products(tmp_path):
    assert resolve_for_product(tmp_path) is None


def test_resolve_none_when_many_products(tmp_path):
    _make_product(tmp_path, f"dna:product:{_ULID}")
    _make_product(tmp_path, f"dna:product:{'A' * 26}")
    assert resolve_for_product(tmp_path) is None   # never guess between several


# ─── emit_change through the REAL port (validates against the schema) ──────


def _adapter(tmp_path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances", domain="product-development")


def test_emit_writes_a_valid_change_through_the_port(tmp_path):
    saved = emit_change(_record(), _adapter(tmp_path), for_product=_PRODUCT)
    assert saved is not None and saved["id"] == f"dna:change:{_ULID}"
    out = (tmp_path / ".brain" / "instances" / "product-development" / "change"
           / f"{_ULID}.jsonld")
    assert out.exists()
    on_disk = json.loads(out.read_text())
    assert on_disk["state"] == "in-flight" and on_disk["for_product"] == _PRODUCT


def test_emit_carries_parent_and_git_provenance(tmp_path):
    saved = emit_change(
        _record(parent_change=f"dna:change:{_ULID}", relationship="depends_on"),
        _adapter(tmp_path), for_product=_PRODUCT)
    assert saved["parent_change"] == f"dna:change:{_ULID}"
    assert saved["relationship"] == "depends_on"
    assert saved["base_sha"].startswith("7a6d267")


def test_in_flight_never_carries_shipped_at(tmp_path):
    # The invariant the prove surfaced: a shipped_at + state=in-flight is a
    # contradiction — the composer drops shipped_at while in-flight.
    saved = emit_change(
        _record(state="in-flight", shipped_at="2026-06-12T10:00:00Z"),
        _adapter(tmp_path), for_product=_PRODUCT)
    assert "shipped_at" not in saved


def test_backfill_of_a_shipped_record_derives_shipped_state(tmp_path):
    # A historical record (no `state`, but a shipped_at) must emit as shipped —
    # consistent — not in-flight-with-a-shipped_at (the prove defect).
    saved = emit_change(
        _record(shipped_at="2026-05-27T20:04:35Z"), _adapter(tmp_path), for_product=_PRODUCT)
    assert saved["state"] == "shipped"
    assert saved["shipped_at"] == "2026-05-27T20:04:35Z"


def test_started_at_falls_back_when_null(tmp_path):
    # Older records have started_at: null; fall back to created_at so the entity
    # carries a real time, never "".
    r = _record(started_at=None, created_at="2026-05-27T19:00:00Z")
    saved = emit_change(r, _adapter(tmp_path), for_product=_PRODUCT)
    assert saved["started_at"] == "2026-05-27T19:00:00Z"


def test_emit_writes_a_product_less_change(tmp_path):
    # for_product is an optional link now — a change with no resolvable product
    # still becomes a Change entity (just without the product link).
    saved = emit_change(_record(), _adapter(tmp_path))   # no for_product anywhere
    assert saved is not None
    assert "for_product" not in saved
    out = (tmp_path / ".brain" / "instances" / "product-development" / "change"
           / f"{_ULID}.jsonld")
    assert out.exists()


def test_compose_defaults_journey_to_the_lifecycle_workflow():
    # #129 B2: every change links to the change-lifecycle Workflow by default.
    from _change_lifecycle import WORKFLOW_ID
    c = compose_change(change_id=_ULID, handle="CH-X", slug="s", intent="i",
                       primitive="fix", started_at="2026-06-12T09:00:00Z")
    assert c["journey"] == WORKFLOW_ID


def test_compose_honors_an_explicit_journey():
    custom = "dna:workflow:" + ("A" * 26)
    c = compose_change(change_id=_ULID, handle="CH-X", slug="s", intent="i",
                       primitive="fix", started_at="2026-06-12T09:00:00Z", journey=custom)
    assert c["journey"] == custom


def test_compose_omits_for_product_when_absent():
    c = compose_change(change_id=_ULID, handle="CH-X", slug="s", intent="i",
                       primitive="fix", started_at="2026-06-12T09:00:00Z")
    assert "for_product" not in c


def test_emit_is_idempotent_same_ulid_overwrites(tmp_path):
    a = _adapter(tmp_path)
    emit_change(_record(), a, for_product=_PRODUCT)
    emit_change(_record(intent="revised intent"), a, for_product=_PRODUCT)
    change_dir = tmp_path / ".brain" / "instances" / "product-development" / "change"
    assert len(list(change_dir.glob("*.jsonld"))) == 1   # one change, one file
    assert json.loads((change_dir / f"{_ULID}.jsonld").read_text())["intent"] == "revised intent"
