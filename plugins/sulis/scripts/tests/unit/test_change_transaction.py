"""Change-as-transaction: produced-set query + rollback (#67 slice 3c).

ship=commit / nuke=rollback over the brain. The produced set (entities a change
created) is the change's transaction. Rollback is SOFT — sys_status=deleted,
the record kept as audit (the way nuke keeps the branch). An entity the change
merely EVOLVED (pre-existed) is never deleted by a rollback. Real adapter, no mock.
"""

from __future__ import annotations

import json
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
import sys  # noqa: E402
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_service import ChangeService  # noqa: E402
from _entity_adapter_local import LocalFileEntityAdapter  # noqa: E402
from _provenance_stamp import stamping_repo  # noqa: E402

_U1 = "0123456789ABCDEFGHJKMNPQRS"
_U2 = "1ABCDEFGHJKMNPQRSTVWXYZ012"
_CH1 = "01CHANGE1AAAAAAAAAAAAAAAAA"
_CH2 = "01CHANGE2BBBBBBBBBBBBBBBBB"


def _adapter(tmp_path) -> LocalFileEntityAdapter:
    return LocalFileEntityAdapter(
        base_dir=tmp_path / ".brain" / "instances", domain="product-development")


def _scenario(ulid: str, name="n") -> dict:
    return {
        "id": f"dna:scenario:{ulid}", "name": name,
        "verifies": [f"dna:requirement:{ulid}"], "exercises": f"dna:design:{ulid}",
        "journey": f"dna:workflow:{ulid}", "state": "draft", "sys_status": "active",
    }


def _on_disk(tmp_path, ulid) -> dict:
    return json.loads((tmp_path / ".brain" / "instances" / "product-development"
                       / "scenario" / f"{ulid}.jsonld").read_text())


# ─── adapter.iter_entities ──────────────────────────────────────────────────


def test_iter_entities_yields_all_saved(tmp_path):
    a = _adapter(tmp_path)
    a.save("scenario", _scenario(_U1))
    a.save("scenario", _scenario(_U2))
    ids = {e["id"] for e in a.iter_entities("scenario")}
    assert ids == {f"dna:scenario:{_U1}", f"dna:scenario:{_U2}"}


def test_iter_entities_empty_when_no_store(tmp_path):
    assert list(_adapter(tmp_path).iter_entities()) == []


# ─── ChangeService.produced ─────────────────────────────────────────────────


def test_produced_returns_only_entities_this_change_created(tmp_path):
    a = _adapter(tmp_path)
    stamping_repo(a, change_id=_CH1).save("scenario", _scenario(_U1))   # produced by CH1
    a.save("scenario", _scenario(_U2))                                   # unstamped
    produced = ChangeService(a).produced(_CH1)
    assert [e["id"] for e in produced] == [f"dna:scenario:{_U1}"]


# ─── rollback (nuke) — soft-delete the produced set ─────────────────────────


def test_rollback_soft_deletes_the_produced_set(tmp_path):
    a = _adapter(tmp_path)
    stamping_repo(a, change_id=_CH1).save("scenario", _scenario(_U1))
    rolled = ChangeService(a).rollback(_CH1)
    assert [e["id"] for e in rolled] == [f"dna:scenario:{_U1}"]
    # Soft: still on disk (audit), marked deleted — not removed.
    assert _on_disk(tmp_path, _U1)["sys_status"] == "deleted"


def test_rollback_leaves_other_changes_entities_untouched(tmp_path):
    a = _adapter(tmp_path)
    stamping_repo(a, change_id=_CH1).save("scenario", _scenario(_U1))
    stamping_repo(a, change_id=_CH2).save("scenario", _scenario(_U2))
    ChangeService(a).rollback(_CH1)
    assert _on_disk(tmp_path, _U2)["sys_status"] == "active"     # CH2's entity safe


def test_rollback_does_not_delete_an_evolved_only_entity(tmp_path):
    # CH1 produced it; CH2 only EVOLVED it (it pre-existed). Rolling back CH2
    # must NOT delete it — a rollback discards what the change CREATED, not what
    # it touched.
    a = _adapter(tmp_path)
    stamping_repo(a, change_id=_CH1).save("scenario", _scenario(_U1))
    stamping_repo(a, change_id=_CH2).save("scenario", _scenario(_U1, name="v2"))
    rolled = ChangeService(a).rollback(_CH2)
    assert rolled == []
    assert _on_disk(tmp_path, _U1)["sys_status"] == "active"


def test_rollback_accepts_full_change_id(tmp_path):
    a = _adapter(tmp_path)
    stamping_repo(a, change_id=_CH1).save("scenario", _scenario(_U1))
    assert len(ChangeService(a).rollback(f"dna:change:{_CH1}")) == 1


# ─── stage derived from the run-trace (#129 B3) ──────────────────────────────


def _stage_run(adapter, change_id, stage, at, ulid):
    adapter.save("lifecyclerun", {
        "id": f"dna:lifecyclerun:{ulid}", "step_name": f"change-stage:{stage}",
        "at": at, "outcome": "completed", "sys_status": "active",
        "produced_by_change": f"dna:change:{change_id}"})


def test_stage_history_derives_from_the_run_trace(tmp_path):
    a = _adapter(tmp_path)
    _stage_run(a, _CH1, "recon", "2026-06-12T09:00:00Z", _U1)
    _stage_run(a, _CH1, "specify", "2026-06-12T09:30:00Z", _U2)
    _stage_run(a, _CH1, "design", "2026-06-12T10:00:00Z", "2" + "A" * 25)
    svc = ChangeService(a)
    assert [h["stage"] for h in svc.stage_history(_CH1)] == ["recon", "specify", "design"]
    assert svc.current_stage(_CH1) == "design"


def test_stage_history_orders_by_time_not_insertion(tmp_path):
    a = _adapter(tmp_path)
    _stage_run(a, _CH1, "design", "2026-06-12T10:00:00Z", _U1)   # inserted first
    _stage_run(a, _CH1, "recon", "2026-06-12T09:00:00Z", _U2)    # earlier time
    assert [h["stage"] for h in ChangeService(a).stage_history(_CH1)] == ["recon", "design"]


def test_current_stage_none_when_no_stage_runs(tmp_path):
    assert ChangeService(_adapter(tmp_path)).current_stage(_CH1) is None


def test_stage_history_ignores_other_changes_runs(tmp_path):
    a = _adapter(tmp_path)
    _stage_run(a, _CH1, "recon", "2026-06-12T09:00:00Z", _U1)
    _stage_run(a, _CH2, "ship", "2026-06-12T09:00:00Z", _U2)   # a different change
    assert [h["stage"] for h in ChangeService(a).stage_history(_CH1)] == ["recon"]
