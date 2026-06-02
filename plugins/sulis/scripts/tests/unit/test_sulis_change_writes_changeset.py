"""Unit tests for changeset emission during `sulis-change finish --merge`.

The contract at `.changesets/README.md` says every ship MUST drop a changeset
unless the change is admin/docs-only (tier resolves to None). Before this
fix, `cmd_finish` squash-merged + committed + pushed without ever calling
`_changeset.write_changeset`, so the release-train saw an empty
`.changesets/` and reported "no version bump" even when dev was 43 commits
ahead of main with real shipping work.

The emission is performed by a small pure helper `_emit_changeset_for_ship`
extracted from `cmd_finish` for testability. The helper:
 - derives tier via `_changeset.tier_for_primitive(primitive)`
 - returns None (no write) when the tier resolves to None
   (admin / docs-only / unknown primitive)
 - calls `_changeset.write_changeset` with the right fields
 - raises ValueError when the metadata is missing required fields
   (e.g. `primitive`)

Loaded via the importlib-from-path shape used by the other
`sulis_change` tests (the script has no `.py` extension).
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SCRIPTS / "sulis-change"))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_mod = _load_sulis_change()
_emit_changeset_for_ship = _mod._emit_changeset_for_ship


# ─── happy path ────────────────────────────────────────────────────────────


def test_emit_writes_changeset_with_right_fields(tmp_path):
    """A normal `fix` change writes a tier=patch changeset into
    `<base_dir>/.changesets/` with the right fields."""
    base_dir = tmp_path
    metadata = {
        "change_id": "01KT37HSCFC9XKT4EYMHVTXSJB",
        "primitive": "fix",
        "slug": "ship-writes-changeset",
        "intent": "Make ship emit a changeset.",
    }
    path = _emit_changeset_for_ship(
        base_dir=base_dir, metadata=metadata, touches_plugin=True,
    )
    assert path is not None
    assert path.exists()
    assert path.parent == base_dir / ".changesets"
    text = path.read_text(encoding="utf-8")
    assert "change_id: 01KT37HSCFC9XKT4EYMHVTXSJB" in text
    assert "primitive: fix" in text
    assert "tier: patch" in text
    assert "touches_plugin: true" in text
    assert "Make ship emit a changeset." in text


def test_emit_writes_minor_tier_for_create_primitive(tmp_path):
    """`create` is a minor-tier primitive per ADR-002."""
    base_dir = tmp_path
    metadata = {
        "change_id": "01XXXXX",
        "primitive": "create",
        "slug": "do-the-thing",
        "intent": "Introduce a new behaviour.",
    }
    path = _emit_changeset_for_ship(
        base_dir=base_dir, metadata=metadata, touches_plugin=True,
    )
    text = path.read_text(encoding="utf-8")
    assert "tier: minor" in text


def test_emit_filename_uses_primitive_and_slug(tmp_path):
    """The triple-key filename is `{primitive}-{slug}-{ts}.yaml`."""
    base_dir = tmp_path
    metadata = {
        "change_id": "01XXXXX",
        "primitive": "fix",
        "slug": "ship-writes-changeset",
        "intent": "blah",
    }
    path = _emit_changeset_for_ship(
        base_dir=base_dir, metadata=metadata, touches_plugin=True,
    )
    assert path.name.startswith("fix-ship-writes-changeset-")
    assert path.name.endswith(".yaml")


# ─── tier-None skip path ──────────────────────────────────────────────────


def test_emit_returns_none_for_admin_primitive(tmp_path):
    """The README contract: admin/docs-only changes write NO changeset.
    The helper signals this with None (no write performed)."""
    base_dir = tmp_path
    metadata = {
        "change_id": "01XXXXX",
        "primitive": "admin",
        "slug": "shuffle-files",
    }
    result = _emit_changeset_for_ship(
        base_dir=base_dir, metadata=metadata, touches_plugin=False,
    )
    assert result is None
    # And no .changesets/ dir was created by side-effect
    assert not (base_dir / ".changesets").exists() or \
        not list((base_dir / ".changesets").glob("*.yaml"))


def test_emit_returns_none_for_unknown_primitive(tmp_path):
    """Unknown primitive → tier None per `tier_for_primitive` contract → no write."""
    base_dir = tmp_path
    metadata = {
        "change_id": "01XXXXX",
        "primitive": "totally-bogus-primitive",
        "slug": "x",
    }
    result = _emit_changeset_for_ship(
        base_dir=base_dir, metadata=metadata, touches_plugin=True,
    )
    assert result is None


# ─── error path ────────────────────────────────────────────────────────────


def test_emit_raises_when_primitive_missing(tmp_path):
    """A change manifest lacking `primitive` is a contract breach — the
    helper raises ValueError rather than silently skipping the write."""
    base_dir = tmp_path
    metadata = {
        "change_id": "01XXXXX",
        "slug": "x",
        # primitive missing
    }
    with pytest.raises(ValueError) as exc:
        _emit_changeset_for_ship(
            base_dir=base_dir, metadata=metadata, touches_plugin=True,
        )
    assert "primitive" in str(exc.value).lower()


def test_emit_raises_when_change_id_missing(tmp_path):
    """A change manifest lacking `change_id` is a contract breach."""
    base_dir = tmp_path
    metadata = {
        "primitive": "fix",
        "slug": "x",
        # change_id missing
    }
    with pytest.raises(ValueError) as exc:
        _emit_changeset_for_ship(
            base_dir=base_dir, metadata=metadata, touches_plugin=True,
        )
    assert "change_id" in str(exc.value).lower()


# ─── summary derivation ────────────────────────────────────────────────────


def test_emit_uses_intent_as_summary_when_present(tmp_path):
    """`metadata.intent` is the founder-readable summary; the helper writes
    it verbatim into the `summary:` block."""
    base_dir = tmp_path
    metadata = {
        "change_id": "01XXXXX",
        "primitive": "feat",
        "slug": "x",
        "intent": "Multi-line summary.\nWith two lines.",
    }
    path = _emit_changeset_for_ship(
        base_dir=base_dir, metadata=metadata, touches_plugin=True,
    )
    text = path.read_text(encoding="utf-8")
    assert "Multi-line summary." in text
    assert "With two lines." in text


def test_emit_falls_back_to_slug_when_intent_empty(tmp_path):
    """Empty intent → derive a one-liner from the slug rather than write
    an empty summary block (the founder-readable CHANGELOG would be useless
    otherwise)."""
    base_dir = tmp_path
    metadata = {
        "change_id": "01XXXXX",
        "primitive": "fix",
        "slug": "tidy-up-helper",
        "intent": "",
    }
    path = _emit_changeset_for_ship(
        base_dir=base_dir, metadata=metadata, touches_plugin=True,
    )
    text = path.read_text(encoding="utf-8")
    # The summary should be non-empty and reference the slug
    assert "summary: |" in text
    # one of these forms — derived from slug:
    assert "tidy" in text.lower() or "tidy-up-helper" in text
