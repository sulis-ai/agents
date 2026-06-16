"""Provenance stamping wrapper (#67 slice 3b).

Stamps produced_by_change / evolved_by_change on emit when a change is active.
Tested through the REAL LocalFileEntityAdapter (no mock) — so a stamped entity
only "passes" if it actually validates against the edge-bearing schemas (3a).
"""

from __future__ import annotations

import json
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _entity_adapter_local import LocalFileEntityAdapter  # noqa: E402
from _provenance_stamp import (  # noqa: E402
    ProvenanceStampingRepository, _change_ref_from, stamping_repo)

_ULID = "0123456789ABCDEFGHJKMNPQRS"
_ULID2 = "1ABCDEFGHJKMNPQRSTVWXYZ012"
_CH1 = f"dna:change:{_ULID}"
_CH2 = f"dna:change:{_ULID2}"


def _adapter(tmp_path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances", domain="product-development")


def _scenario(name="n") -> dict:
    return {
        "id": f"dna:scenario:{_ULID}", "name": name,
        "verifies": [f"dna:requirement:{_ULID}"], "exercises": f"dna:design:{_ULID}",
        "journey": f"dna:workflow:{_ULID}", "state": "draft", "sys_status": "active",
    }


def _stored(tmp_path) -> dict:
    return json.loads((tmp_path / ".brain" / "instances" / "product-development"
                       / "scenario" / f"{_ULID}.jsonld").read_text())


# ─── _change_ref_from ──────────────────────────────────────────────────────


def test_change_ref_accepts_bare_and_full(monkeypatch):
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    assert _change_ref_from(_ULID) == _CH1
    assert _change_ref_from(_CH1) == _CH1


def test_change_ref_none_when_absent_or_malformed(monkeypatch):
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    assert _change_ref_from(None) is None
    assert _change_ref_from("not-a-ulid") is None


def test_change_ref_reads_env(monkeypatch):
    monkeypatch.setenv("SULIS_CHANGE_ID", _ULID)
    assert _change_ref_from(None) == _CH1


# ─── factory ───────────────────────────────────────────────────────────────


def test_factory_returns_inner_when_no_change(monkeypatch, tmp_path):
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    a = _adapter(tmp_path)
    assert stamping_repo(a) is a               # unchanged, no wrap


def test_factory_wraps_when_change_active(tmp_path):
    a = _adapter(tmp_path)
    wrapped = stamping_repo(a, change_id=_ULID)
    assert isinstance(wrapped, ProvenanceStampingRepository)


# ─── stamping through the REAL adapter ───────────────────────────────────────


def test_new_entity_is_stamped_produced_by_change(tmp_path):
    repo = stamping_repo(_adapter(tmp_path), change_id=_ULID)
    repo.save("scenario", _scenario())
    assert _stored(tmp_path)["produced_by_change"] == _CH1


def test_resave_by_same_change_adds_no_evolved(tmp_path):
    repo = stamping_repo(_adapter(tmp_path), change_id=_ULID)
    repo.save("scenario", _scenario())
    repo.save("scenario", _scenario(name="revised"))   # same change still working
    s = _stored(tmp_path)
    assert s["produced_by_change"] == _CH1
    assert "evolved_by_change" not in s


def test_resave_by_different_change_appends_evolved(tmp_path):
    a = _adapter(tmp_path)
    stamping_repo(a, change_id=_ULID).save("scenario", _scenario())          # CH1 creates
    stamping_repo(a, change_id=_ULID2).save("scenario", _scenario("v2"))     # CH2 revises
    s = _stored(tmp_path)
    assert s["produced_by_change"] == _CH1            # original producer preserved
    assert s["evolved_by_change"] == [_CH2]


def test_change_entity_is_never_stamped(tmp_path):
    # A change isn't produced_by another change — the wrapper skips entity_type=change.
    repo = stamping_repo(_adapter(tmp_path), change_id=_ULID2)
    change = {"id": _CH1, "handle": "CH-X", "slug": "s", "intent": "i",
              "primitive": "fix", "state": "in-flight", "started_at": "2026-06-12T09:00:00Z",
              "sys_status": "active"}
    repo.save("change", change)
    stored = json.loads((tmp_path / ".brain" / "instances" / "product-development"
                         / "change" / f"{_ULID}.jsonld").read_text())
    assert "produced_by_change" not in stored


def test_pass_through_find_and_validate(tmp_path):
    repo = stamping_repo(_adapter(tmp_path), change_id=_ULID)
    repo.save("scenario", _scenario())
    assert repo.find_by_id("scenario", f"dna:scenario:{_ULID}")["id"] == f"dna:scenario:{_ULID}"
    repo.validate("scenario", _scenario())   # no raise


# ─── the seam: _try_adapter auto-wraps under an active change ────────────────


def test_try_adapter_wraps_when_change_active(tmp_path, monkeypatch):
    import _brain_emit_helper as beh
    monkeypatch.setenv("SULIS_CHANGE_ID", _ULID)
    assert isinstance(beh._try_adapter(tmp_path, domain="product-development"),
                      ProvenanceStampingRepository)


def test_try_adapter_plain_when_no_change(tmp_path, monkeypatch):
    import _brain_emit_helper as beh
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    assert not isinstance(beh._try_adapter(tmp_path, domain="product-development"),
                          ProvenanceStampingRepository)
