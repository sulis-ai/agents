"""Collision-free finding IDs (the multi-agent numbering fix).

`wpx-findings` used to allocate SF-NNN / WP-AUTO-NNN by scanning the shared
register/dir and taking max(existing)+1 — a read-increment-write race that
collides when parallel run-all security reviews register concurrently
(the same class of bug as the DR-030 / L-43 cross-agent collision).

The fix derives both IDs deterministically from the finding's *signature*
hash (which wpx-findings already computes for dedup):
  - SF-{sig[:8]}            — collision-free, dedup-unified (same finding →
                              same id), no register scan, no race.
  - WP-AUTO-{sig[:8]}       — 1:1 with its source finding; same suffix →
                              traceable.

These tests pin: deterministic-from-signature, collision-free across
different findings, idempotent on a re-registered duplicate, and the
hex-suffix format. Backward-compat (old SF-001 decimal still parses) is
pinned in test_finding_emission.py's register-reader test.
"""

from __future__ import annotations

import json
import re

import pytest

_SF_RE = re.compile(r"^SF-[0-9a-f]{8}$")
_AUTOWP_RE = re.compile(r"^WP-AUTO-[0-9a-f]{8}$")


def _register(run_tool, repo, *, wp, severity, summary, file):
    return run_tool(
        "wpx-findings", "register",
        "--project", "p", "--repo-root", str(repo),
        "--wp", wp, "--severity", severity, "--summary", summary, "--file", file,
    )


class TestCollisionFreeFindingIds:
    def test_sf_and_autowp_ids_are_hex_derived(self, tmp_path, run_tool):
        r = _register(run_tool, tmp_path, wp="WP-001", severity="CONCERN",
                      summary="email logged in cleartext", file="auth.py")
        assert r.ok, r.stderr
        assert _SF_RE.match(r.data["sf_id"]), r.data["sf_id"]
        assert _AUTOWP_RE.match(r.data["auto_draft_wp_id"]), r.data["auto_draft_wp_id"]
        # Both share the signature suffix — the 1:1 traceability link.
        assert r.data["sf_id"].split("-", 1)[1] == r.data["auto_draft_wp_id"].rsplit("-", 1)[1]

    def test_id_is_deterministic_from_the_finding(self, tmp_path, run_tool):
        """Same (severity, summary, file) → same SF id, in two fresh repos —
        no dependence on allocation order / what else is registered."""
        a = _register(run_tool, tmp_path / "a", wp="WP-001", severity="CONCERN",
                      summary="same finding", file="x.py")
        b = _register(run_tool, tmp_path / "b", wp="WP-099", severity="CONCERN",
                      summary="same finding", file="x.py")
        assert a.data["sf_id"] == b.data["sf_id"]

    def test_different_findings_get_different_ids(self, tmp_path, run_tool):
        a = _register(run_tool, tmp_path, wp="WP-001", severity="CONCERN",
                      summary="finding one", file="a.py")
        b = _register(run_tool, tmp_path, wp="WP-001", severity="CONCERN",
                      summary="finding two", file="b.py")
        assert a.data["sf_id"] != b.data["sf_id"]
        assert a.data["auto_draft_wp_id"] != b.data["auto_draft_wp_id"]

    def test_duplicate_returns_same_id_no_new_finding(self, tmp_path, run_tool):
        """Re-registering the identical finding is idempotent: same id,
        flagged duplicate (the dedup path still works on derived ids)."""
        first = _register(run_tool, tmp_path, wp="WP-001", severity="CONCERN",
                          summary="dup me", file="d.py")
        again = _register(run_tool, tmp_path, wp="WP-002", severity="CONCERN",
                          summary="dup me", file="d.py")
        assert again.data["is_duplicate"] is True
        assert again.data["sf_id"] == first.data["sf_id"]

    def test_no_collision_across_independent_first_registrations(self, tmp_path, run_tool):
        """The race repro: two DIFFERENT findings each registered as the FIRST
        in their own register would both have been 'SF-001' under max+1.
        Derived ids make them distinct by construction."""
        a = _register(run_tool, tmp_path / "agentA", wp="WP-001", severity="CONCERN",
                      summary="agent A's finding", file="a.py")
        b = _register(run_tool, tmp_path / "agentB", wp="WP-001", severity="CONCERN",
                      summary="agent B's finding", file="b.py")
        assert a.data["sf_id"] != b.data["sf_id"], (
            "two distinct first-findings collided — the max+1 race is back"
        )
