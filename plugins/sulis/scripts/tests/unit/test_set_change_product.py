"""Tests for the set-change-product spine script (per-change product assignment).

The script sets the authoritative `for_product` link on a change's brain Change
entity, writing to the SAME brain the cockpit reads. Two paths:
  - update: an existing entity gets its link set/changed, other fields preserved;
  - compose: a change with no entity yet is composed from its change.json record.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]          # plugins/sulis/scripts
_REPO_ROOT = _SCRIPTS.parents[2]                        # repo root
_SCRIPT = _REPO_ROOT / "apps/cockpit/server/adapters/spine/set-change-product.py"

_ULID = "01CHG0000000000000000000AA"
# Valid Crockford-base32 ULIDs (the schema excludes I/L/O/U).
_PRODUCT_A = "dna:product:01ACME00000000000000000000"
_PRODUCT_B = "dna:product:01HARP00000000000000000000"


def _run(base_dir: Path, change_id: str, for_product: str, changes_dir: "Path | None" = None):
    argv = [
        sys.executable, str(_SCRIPT),
        "--scripts-dir", str(_SCRIPTS),
        "--base-dir", str(base_dir),
        "--change-id", change_id,
        "--for-product", for_product,
    ]
    if changes_dir is not None:
        argv += ["--changes-dir", str(changes_dir)]
    return subprocess.run(argv, capture_output=True, text=True)


def _run_argv(base_dir: Path, change_id: str, *extra: str):
    """Run the helper with an arbitrary flag tail (for --clear and edge cases)."""
    argv = [
        sys.executable, str(_SCRIPT),
        "--scripts-dir", str(_SCRIPTS),
        "--base-dir", str(base_dir),
        "--change-id", change_id,
        *extra,
    ]
    return subprocess.run(argv, capture_output=True, text=True)


def _entity_path(base_dir: Path, ulid: str) -> Path:
    return base_dir / "product-development" / "change" / f"{ulid}.jsonld"


def _seed_record(changes_dir: Path, ulid: str) -> None:
    rec_dir = changes_dir / ulid
    rec_dir.mkdir(parents=True, exist_ok=True)
    (rec_dir / "change.json").write_text(
        json.dumps({
            "change_id": ulid,
            "handle": "CH-0000AA",
            "slug": "assign-me",
            "intent": "a change to assign to a product",
            "primitive": "feat",
            "created_at": "2026-06-16T00:00:00Z",
            "branch": f"change/feat-{ulid}",
        }),
        encoding="utf-8",
    )


def test_compose_path_creates_entity_with_link(tmp_path):
    """A change with no brain entity is composed from its change.json + linked."""
    base_dir = tmp_path / ".brain" / "instances"
    changes_dir = tmp_path / "changes"
    _seed_record(changes_dir, _ULID)

    res = _run(base_dir, _ULID, _PRODUCT_A, changes_dir=changes_dir)
    assert res.returncode == 0, res.stderr + res.stdout
    assert json.loads(res.stdout)["ok"] is True

    entity = json.loads(_entity_path(base_dir, _ULID).read_text())
    assert entity["id"] == f"dna:change:{_ULID}"
    assert entity["for_product"] == _PRODUCT_A
    assert entity["handle"] == "CH-0000AA"  # composed from the record


def test_update_path_changes_link_and_preserves_fields(tmp_path):
    """Re-assigning an existing entity updates for_product, keeps other fields."""
    base_dir = tmp_path / ".brain" / "instances"
    changes_dir = tmp_path / "changes"
    _seed_record(changes_dir, _ULID)

    # First assignment composes the entity.
    assert _run(base_dir, _ULID, _PRODUCT_A, changes_dir=changes_dir).returncode == 0
    # Second assignment is the update path (entity now exists) — no changes-dir needed.
    res = _run(base_dir, _ULID, _PRODUCT_B)
    assert res.returncode == 0, res.stderr + res.stdout

    entity = json.loads(_entity_path(base_dir, _ULID).read_text())
    assert entity["for_product"] == _PRODUCT_B          # link changed
    assert entity["handle"] == "CH-0000AA"              # other fields preserved
    assert entity["intent"] == "a change to assign to a product"


def test_rejects_a_non_product_id(tmp_path):
    """A for_product that isn't a dna:product:<ulid> is refused, nothing written."""
    base_dir = tmp_path / ".brain" / "instances"
    res = _run(base_dir, _ULID, "not-a-product-id")
    assert res.returncode == 1
    assert json.loads(res.stdout)["ok"] is False
    assert not _entity_path(base_dir, _ULID).exists()


def test_record_less_change_without_changes_dir_errors(tmp_path):
    """No entity + no --changes-dir to compose from ⇒ a clear error, no write."""
    base_dir = tmp_path / ".brain" / "instances"
    res = _run(base_dir, _ULID, _PRODUCT_A)
    assert res.returncode == 1
    assert json.loads(res.stdout)["ok"] is False


# ── un-assign (--clear) — WP-003 ────────────────────────────────────────────


def test_clear_path_removes_link_and_is_idempotent(tmp_path):
    """--clear sets for_product back to null on an existing entity; idempotent."""
    base_dir = tmp_path / ".brain" / "instances"
    changes_dir = tmp_path / "changes"
    _seed_record(changes_dir, _ULID)

    # Assign first (compose path), so an entity with a link exists.
    assert _run(base_dir, _ULID, _PRODUCT_A, changes_dir=changes_dir).returncode == 0
    assert json.loads(_entity_path(base_dir, _ULID).read_text())["for_product"] == _PRODUCT_A

    # Clear it — explicit flag, never an empty --for-product.
    res = _run_argv(base_dir, _ULID, "--clear")
    assert res.returncode == 0, res.stderr + res.stdout
    out = json.loads(res.stdout)
    assert out["ok"] is True
    assert out["data"]["for_product"] is None

    entity = json.loads(_entity_path(base_dir, _ULID).read_text())
    # "Unassigned" is the ABSENCE of the link (the schema types for_product as
    # an optional string), so the key is removed — not set to a null value.
    assert "for_product" not in entity          # link cleared
    assert entity["handle"] == "CH-0000AA"      # other fields preserved

    # Idempotent: clearing again is a no-op success, not a failure.
    res2 = _run_argv(base_dir, _ULID, "--clear")
    assert res2.returncode == 0, res2.stderr + res2.stdout
    assert "for_product" not in json.loads(_entity_path(base_dir, _ULID).read_text())


def test_clear_and_for_product_are_mutually_exclusive(tmp_path):
    """Passing both --clear and --for-product is refused; nothing written."""
    base_dir = tmp_path / ".brain" / "instances"
    res = _run_argv(base_dir, _ULID, "--clear", "--for-product", _PRODUCT_A)
    assert res.returncode != 0
    # argparse mutual-exclusion exits 2; an in-band guard exits 1 with ok:false.
    if res.returncode == 1:
        assert json.loads(res.stdout)["ok"] is False
    assert not _entity_path(base_dir, _ULID).exists()


def test_for_product_still_rejects_empty(tmp_path):
    """The assign path's strict validation is unweakened: empty --for-product fails."""
    base_dir = tmp_path / ".brain" / "instances"
    res = _run_argv(base_dir, _ULID, "--for-product", "")
    assert res.returncode == 1
    assert json.loads(res.stdout)["ok"] is False
    assert not _entity_path(base_dir, _ULID).exists()
