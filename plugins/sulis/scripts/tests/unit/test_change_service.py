"""test_change_service — the ChangeService lifecycle handler (#128, slice 2).

The Change entity's lifecycle (open → ship | nuke) is now owned by one
programmatic handler over the REAL EntityRepository port — no mocks. Pins:
open emits in-flight; get reads; ship/nuke transition state through load-modify-
save; transitions on an unknown change return None (never crash); a nuked
change carries valid_to, not shipped_at.
"""

from __future__ import annotations

import json
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_service import ChangeService, _full_id  # noqa: E402
from _entity_adapter_local import LocalFileEntityAdapter  # noqa: E402

_ULID = "0123456789ABCDEFGHJKMNPQRS"
_PRODUCT = f"dna:product:{_ULID}"


def _svc(tmp_path) -> ChangeService:
    return ChangeService(LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances", domain="product-development"))


def _record() -> dict:
    return {
        "change_id": _ULID, "handle": "CH-01HQ8X", "slug": "fix-login-bug",
        "primitive": "fix", "intent": "fix the login bug",
        "started_at": "2026-06-12T09:00:00Z",
    }


def test_full_id_accepts_bare_ulid_and_full_id():
    assert _full_id(_ULID) == f"dna:change:{_ULID}"
    assert _full_id(f"dna:change:{_ULID}") == f"dna:change:{_ULID}"


def test_open_emits_in_flight(tmp_path):
    svc = _svc(tmp_path)
    e = svc.open(_record(), for_product=_PRODUCT)
    assert e["state"] == "in-flight"
    assert svc.get(_ULID)["id"] == f"dna:change:{_ULID}"


def test_open_then_ship_transitions_state_and_sets_shipped_at(tmp_path):
    svc = _svc(tmp_path)
    svc.open(_record(), for_product=_PRODUCT)
    shipped = svc.ship(_ULID, shipped_at="2026-06-12T10:00:00Z")
    assert shipped["state"] == "shipped"
    assert shipped["shipped_at"] == "2026-06-12T10:00:00Z"
    # persisted, not just returned
    assert svc.get(_ULID)["state"] == "shipped"


def test_nuke_sets_nuked_with_valid_to_and_no_shipped_at(tmp_path):
    svc = _svc(tmp_path)
    svc.open(_record(), for_product=_PRODUCT)
    nuked = svc.nuke(_ULID, at="2026-06-12T11:00:00Z")
    assert nuked["state"] == "nuked"
    assert nuked["valid_to"] == "2026-06-12T11:00:00Z"
    assert "shipped_at" not in nuked


def test_ship_unknown_change_returns_none(tmp_path):
    assert _svc(tmp_path).ship("ZZZZZZZZZZZZZZZZZZZZZZZZZZ") is None


def test_nuke_unknown_change_returns_none(tmp_path):
    assert _svc(tmp_path).nuke("ZZZZZZZZZZZZZZZZZZZZZZZZZZ") is None


def test_get_unknown_change_returns_none(tmp_path):
    assert _svc(tmp_path).get(_ULID) is None


def test_ship_uses_full_id_round_trip(tmp_path):
    # ship accepts the full dna:change:<ulid> too (the CLI passes a change_id
    # that may already be the bare ULID or the full id).
    svc = _svc(tmp_path)
    svc.open(_record(), for_product=_PRODUCT)
    assert svc.ship(f"dna:change:{_ULID}")["state"] == "shipped"
