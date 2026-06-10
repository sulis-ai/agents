"""SC-17 driver round-trip — `_drive_decisions.py` + `_assert_bdr_adr.py`.

These exercise the two SC-17 scripts the WP-012 Contract ships:

  - `_drive_decisions.py` drives the real emit path for an ADR + a BDR (both
    sharing a `change_id`, the pre-fix collision trigger) and persists both.
  - `_assert_bdr_adr.py` reads the persisted instances and exits 0 iff the BDR
    is `kind: bdr`, the ADR is `kind: adr`, and their `@id`s differ.

Together they are the SC-17 gate: a business decision is recorded distinct from
a technical ADR. The asserter's failure paths are covered too, so a regression
(kind dropped, @id collision reintroduced) flips the gate red.
"""

from __future__ import annotations

import json
from pathlib import Path

import _assert_bdr_adr
import _drive_decisions


class TestDriveDecisions:
    """`_drive_decisions.py` drives the real emit path for an ADR + a BDR."""

    def test_drive_persists_two_distinct_decisions(self, tmp_path: Path) -> None:
        rc = _drive_decisions.main(["--out", str(tmp_path)])

        assert rc == 0
        manifest = tmp_path / "decisions.manifest"
        assert manifest.exists()

        by_kind = _assert_bdr_adr._load_manifest(manifest)
        assert set(by_kind) == {"adr", "bdr"}

        adr = json.loads(by_kind["adr"].read_text())
        bdr = json.loads(by_kind["bdr"].read_text())
        assert adr["kind"] == "adr"
        assert bdr["kind"] == "bdr"
        # Both sources shared a change_id — the @ids must still differ.
        assert adr["id"] != bdr["id"]


class TestAssertBdrAdr:
    """`_assert_bdr_adr.py` is the SC-17 verdict gate."""

    def test_passes_on_a_clean_drive(self, tmp_path: Path) -> None:
        assert _drive_decisions.main(["--out", str(tmp_path)]) == 0

        rc = _assert_bdr_adr.main(
            ["--manifest", str(tmp_path / "decisions.manifest")]
        )

        assert rc == 0

    def test_fails_when_bdr_kind_is_wrong(self, tmp_path: Path) -> None:
        # Drive, then corrupt the BDR's kind on disk → the gate must go red.
        _drive_decisions.main(["--out", str(tmp_path)])
        manifest = tmp_path / "decisions.manifest"
        by_kind = _assert_bdr_adr._load_manifest(manifest)

        bdr = json.loads(by_kind["bdr"].read_text())
        bdr["kind"] = "adr"  # regression: BDR mis-recorded as an ADR
        by_kind["bdr"].write_text(json.dumps(bdr))

        rc = _assert_bdr_adr.main(["--manifest", str(manifest)])

        assert rc == 1

    def test_fails_when_ids_collide(self, tmp_path: Path) -> None:
        # Force the ADR's @id to equal the BDR's → the collision the fix
        # prevents; the gate must catch it.
        _drive_decisions.main(["--out", str(tmp_path)])
        manifest = tmp_path / "decisions.manifest"
        by_kind = _assert_bdr_adr._load_manifest(manifest)

        bdr = json.loads(by_kind["bdr"].read_text())
        adr = json.loads(by_kind["adr"].read_text())
        adr["id"] = bdr["id"]
        by_kind["adr"].write_text(json.dumps(adr))

        rc = _assert_bdr_adr.main(["--manifest", str(manifest)])

        assert rc == 1

    def test_bad_manifest_exits_2(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.manifest"
        bad.write_text("this is not a valid manifest line\n")

        rc = _assert_bdr_adr.main(["--manifest", str(bad)])

        assert rc == 2

    def test_missing_persisted_file_exits_2(self, tmp_path: Path) -> None:
        # A well-formed manifest pointing at a decision file that isn't there
        # (e.g. a deleted instance) is a bad-input failure, not a verdict.
        manifest = tmp_path / "decisions.manifest"
        manifest.write_text(
            f"kind=adr\t{tmp_path / 'missing-adr.jsonld'}\n"
            f"kind=bdr\t{tmp_path / 'missing-bdr.jsonld'}\n"
        )

        rc = _assert_bdr_adr.main(["--manifest", str(manifest)])

        assert rc == 2
