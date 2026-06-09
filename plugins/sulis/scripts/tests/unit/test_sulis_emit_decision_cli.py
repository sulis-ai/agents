"""Tests for the `sulis-emit-decision` CLI — end-to-end via subprocess.

The CLI is what `/sulis:draft-architecture` shells out to. These tests pin the
JSON envelope contract (`{ok, data}` / `{ok, error}`), the default base-dir
resolution under the repo root, and the success/failure semantics callers can
rely on.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_DECISION_ID_RE = re.compile(r"^dna:decision:[0-9A-HJKMNP-TV-Z]{26}$")


_VALID_ADR = """---
id: ADR-001
title: Decouple integration from release via changesets
status: accepted
change_id: 01KSQNPBPN7W74QVAZ25F79RNH
date: 2026-05-28
closes: 66
---

# ADR-001 — Decouple integration from release via changesets

## Decision

Integration and release are separated.

## Context

Coupling left release to agent discipline.

## Options Considered

- Per-change bump — rejected.
- Changeset-based release-train — chosen.

## Consequences

Bump becomes deterministic.
"""


_BAD_ADR = """---
id: ADR-099
title: ADR missing its decision section
status: proposed
date: 2026-05-30
---

# ADR-099

## Context
Something.
"""


class TestSulisEmitDecisionCli:
    """End-to-end CLI shape: subprocess in, JSON envelope out."""

    def test_round_trips_a_valid_adr_to_a_persisted_jsonld(
        self, tmp_path: Path, run_tool
    ) -> None:
        adr_path = tmp_path / "ADR-001.md"
        adr_path.write_text(_VALID_ADR)

        result = run_tool(
            "sulis-emit-decision",
            "--from-adr", str(adr_path),
            "--repo-root", str(tmp_path),
        )

        assert result.ok, (
            f"expected ok=true, got returncode={result.returncode}\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        # The CLI returns the persisted instance's id + on-disk path. The @id
        # is a freshly-minted ULID (WP-012 collision fix), not the change_id.
        decision_id = result.data["decision_id"]
        assert _DECISION_ID_RE.fullmatch(decision_id), (
            f"id failed schema pattern: {decision_id}"
        )
        assert decision_id != "dna:decision:01KSQNPBPN7W74QVAZ25F79RNH"

        written = Path(result.data["path"])
        assert written.exists(), f"expected file at {written}"

        # Round-trip — what we wrote validates against the schema (same
        # contract as the adapter unit tests, but exercised through the CLI).
        loaded = json.loads(written.read_text())
        assert loaded["id"] == decision_id
        assert loaded["state"] == "accepted"  # status→state translation
        assert loaded["sys_status"] == "active"
        assert "Changeset-based" in " | ".join(loaded["options_considered"])

    def test_emits_under_repo_root_brain_instances_by_default(
        self, tmp_path: Path, run_tool
    ) -> None:
        adr_path = tmp_path / "ADR-001.md"
        adr_path.write_text(_VALID_ADR)

        result = run_tool(
            "sulis-emit-decision",
            "--from-adr", str(adr_path),
            "--repo-root", str(tmp_path),
        )

        assert result.ok
        written = Path(result.data["path"])

        # Default layout: <repo-root>/.brain/instances/<domain>/<entity>/<ulid>.jsonld
        # The ULID is freshly minted per emission (WP-012), so assert the
        # directory shape + filename pattern rather than a fixed ULID.
        rel = written.relative_to(tmp_path)
        assert rel.parent == Path(
            ".brain/instances/product-development/decision"
        )
        assert re.fullmatch(
            r"[0-9A-HJKMNP-TV-Z]{26}\.jsonld", rel.name
        ), f"unexpected decision filename: {rel.name}"

    def test_respects_explicit_base_dir(self, tmp_path: Path, run_tool) -> None:
        adr_path = tmp_path / "ADR-001.md"
        adr_path.write_text(_VALID_ADR)
        custom = tmp_path / "custom-brain"

        result = run_tool(
            "sulis-emit-decision",
            "--from-adr", str(adr_path),
            "--base-dir", str(custom),
            "--repo-root", str(tmp_path),
        )

        assert result.ok
        written = Path(result.data["path"])
        assert custom in written.parents
        assert written.exists()

    def test_kind_bdr_flag_persists_a_business_decision(
        self, tmp_path: Path, run_tool
    ) -> None:
        # WP-012: the CLI surfaces `--kind bdr` so a business decision persists
        # with `kind: bdr`, distinct from a default ADR.
        bdr_path = tmp_path / "BDR-001.md"
        bdr_path.write_text(_VALID_ADR)  # body shape is identical; kind differs

        result = run_tool(
            "sulis-emit-decision",
            "--from-adr", str(bdr_path),
            "--kind", "bdr",
            "--repo-root", str(tmp_path),
        )

        assert result.ok, (
            f"expected ok=true, got returncode={result.returncode}\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )
        loaded = json.loads(Path(result.data["path"]).read_text())
        assert loaded["kind"] == "bdr"

    def test_default_kind_is_adr(self, tmp_path: Path, run_tool) -> None:
        adr_path = tmp_path / "ADR-001.md"
        adr_path.write_text(_VALID_ADR)

        result = run_tool(
            "sulis-emit-decision",
            "--from-adr", str(adr_path),
            "--repo-root", str(tmp_path),
        )

        assert result.ok
        loaded = json.loads(Path(result.data["path"]).read_text())
        assert loaded["kind"] == "adr"

    def test_rejects_invalid_adr_with_clear_error_envelope(
        self, tmp_path: Path, run_tool
    ) -> None:
        adr_path = tmp_path / "ADR-099.md"
        adr_path.write_text(_BAD_ADR)

        result = run_tool(
            "sulis-emit-decision",
            "--from-adr", str(adr_path),
            "--repo-root", str(tmp_path),
        )

        assert not result.ok, "expected ok=false for invalid ADR"
        assert result.error is not None
        # Error message must name the missing required field
        assert "decision" in result.error.lower()
        # Exit code: 1 on validation failure
        assert result.returncode == 1

    def test_returns_error_for_missing_adr_path(
        self, tmp_path: Path, run_tool
    ) -> None:
        result = run_tool(
            "sulis-emit-decision",
            "--from-adr", str(tmp_path / "does-not-exist.md"),
            "--repo-root", str(tmp_path),
        )

        assert not result.ok
        assert result.error is not None
        assert "not found" in result.error.lower()
