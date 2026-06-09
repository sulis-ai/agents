"""Tests for `LocalFileEntityAdapter` — the file-backed implementation of the
`EntityRepository` port.

Pins the round-trip contract for the first marketplace consumer of the Brain↔OS
compile outputs (Track 1, plugins repo):

  - a VALID entity instance saves + finds back unchanged.
  - an INVALID instance rejects at write — no file persists.
  - find_by_id for a missing id returns None.
  - the validation is real: it loads the vendored `decision.schema.json` and
    runs JSON Schema 2020-12 against the instance — no fake-stub validator.

Why Decision first: it's the smallest spine entity, has no nested cross-refs to
elaborate, and the vendored schema's pattern bites all the load-bearing rules
(ULID-shaped id, required fields, two-lifecycle `sys_status`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _entity_repository import EntityValidationError
from _entity_adapter_local import LocalFileEntityAdapter


# ─── helpers ──────────────────────────────────────────────────────────────


def _valid_decision() -> dict:
    """A Decision instance that passes the vendored decision.schema.json."""
    return {
        "id": "dna:decision:01JX0AAAAAAAAAAAAAAAAAAAAA",
        "title": "Adopt PostgreSQL with logical replication",
        "state": "accepted",
        "context": "We need durable, queryable order storage.",
        "decision": "PostgreSQL with logical replication.",
        "options_considered": ["PostgreSQL", "DynamoDB", "MySQL"],
        "consequences": "More operational complexity; better durability.",
        "sys_status": "active",
    }


# ─── tests ────────────────────────────────────────────────────────────────


class TestLocalFileEntityAdapterRoundTrip:
    """save → find_by_id round-trip for a valid Decision."""

    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_save_valid_decision_writes_a_jsonld_file_under_the_expected_path(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        d = _valid_decision()

        adapter.save("decision", d)

        ulid = d["id"].split(":")[-1]
        written = (
            tmp_path
            / ".brain"
            / "instances"
            / "product-development"
            / "decision"
            / f"{ulid}.jsonld"
        )
        assert written.exists(), f"expected file at {written}"

    def test_find_by_id_returns_the_saved_decision_unchanged(
        self, adapter: LocalFileEntityAdapter
    ) -> None:
        d = _valid_decision()
        adapter.save("decision", d)

        retrieved = adapter.find_by_id("decision", d["id"])

        assert retrieved == d


class TestLocalFileEntityAdapterRejection:
    """Invalid instances reject at write — no file persists."""

    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_save_decision_missing_required_field_raises_and_writes_nothing(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        bad = _valid_decision()
        del bad["decision"]  # required field

        with pytest.raises(EntityValidationError) as exc_info:
            adapter.save("decision", bad)

        # The error must name the violation in plain terms so a caller can act
        # on it.
        assert "decision" in str(exc_info.value).lower()

        # And: no file may have been written.
        decision_dir = (
            tmp_path / ".brain" / "instances" / "product-development" / "decision"
        )
        files = list(decision_dir.glob("*.jsonld")) if decision_dir.exists() else []
        assert files == [], f"unexpected file(s) on rejection: {files}"

    def test_save_decision_with_malformed_id_pattern_raises(
        self, adapter: LocalFileEntityAdapter
    ) -> None:
        bad = _valid_decision()
        bad["id"] = "not-a-dna-decision-ulid"  # fails the regex pattern

        with pytest.raises(EntityValidationError):
            adapter.save("decision", bad)

    def test_save_decision_with_invalid_state_enum_raises(
        self, adapter: LocalFileEntityAdapter
    ) -> None:
        bad = _valid_decision()
        bad["state"] = "ratified"  # not in [proposed, accepted, superseded]

        with pytest.raises(EntityValidationError):
            adapter.save("decision", bad)


class TestLocalFileEntityAdapterMissing:
    """find_by_id of an id that was never saved returns None (not raise)."""

    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_find_by_id_returns_none_for_missing(
        self, adapter: LocalFileEntityAdapter
    ) -> None:
        retrieved = adapter.find_by_id(
            "decision", "dna:decision:01JX0ZZZZZZZZZZZZZZZZZZZZZ"
        )

        assert retrieved is None


class TestLocalFileEntityAdapterPathConfinement:
    """Defense-in-depth: a traversal-laden id / entity_type cannot escape the
    store, on either the read or the write path (the file-write primitive is
    self-defending — it does not trust an upstream caller's validation)."""

    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    @pytest.mark.parametrize(
        "evil_id",
        [
            "dna:decision:../../../../etc/passwd",
            "dna:decision:..",
            "dna:decision:/etc/passwd",
            "dna:decision:a/b",
            "dna:decision:a\x00b",
        ],
    )
    def test_find_by_id_with_traversal_segment_raises(
        self, adapter: LocalFileEntityAdapter, evil_id: str, tmp_path: Path
    ) -> None:
        # find_by_id builds the instance path from the raw id — a traversal
        # segment must be rejected, not read.
        with pytest.raises(EntityValidationError):
            adapter.find_by_id("decision", evil_id)

    def test_save_with_traversal_id_raises_and_writes_nothing_outside_base(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        evil = _valid_decision()
        evil["id"] = "dna:decision:../../../../tmp/escaped"

        with pytest.raises(EntityValidationError):
            adapter.save("decision", evil)

        # Nothing escaped to the parent of base_dir.
        escaped = tmp_path.parent / "tmp" / "escaped.jsonld"
        assert not escaped.exists()

    def test_traversal_in_entity_type_raises(
        self, adapter: LocalFileEntityAdapter
    ) -> None:
        with pytest.raises(EntityValidationError):
            adapter.find_by_id("../decision", "dna:decision:01JX0AAAAAAAAAAAAAAAAAAAAA")


class TestLocalFileEntityAdapterAtomicWrite:
    """save() is atomic: a temp file in the same dir is os.replace'd into place,
    leaving no partial / leftover temp file even across re-saves."""

    @pytest.fixture
    def adapter(self, tmp_path: Path) -> LocalFileEntityAdapter:
        return LocalFileEntityAdapter(
            base_dir=tmp_path / ".brain" / "instances",
            domain="product-development",
        )

    def test_save_leaves_no_temp_file_and_content_is_complete(
        self, adapter: LocalFileEntityAdapter, tmp_path: Path
    ) -> None:
        d = _valid_decision()
        adapter.save("decision", d)
        # re-save (the upsert path) to exercise replace-over-existing.
        adapter.save("decision", d)

        decision_dir = (
            tmp_path / ".brain" / "instances" / "product-development" / "decision"
        )
        # exactly one .jsonld, and NO leftover .tmp files.
        jsonld = list(decision_dir.glob("*.jsonld"))
        temps = list(decision_dir.glob(".*tmp")) + list(decision_dir.glob("*.tmp"))
        assert len(jsonld) == 1, f"expected one entity file, got {jsonld}"
        assert temps == [], f"leftover temp file(s): {temps}"

        # content is the full, valid JSON (not truncated).
        import json as _json

        assert _json.loads(jsonld[0].read_text()) == d
