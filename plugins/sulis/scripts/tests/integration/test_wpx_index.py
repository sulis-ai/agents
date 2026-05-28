"""Integration tests for wpx-index.

LOAD-BEARING: includes the regression test for v0.10.5 Bug 2 (the WP
table finder previously matched the first `| ID |`-headed Markdown
table, which in real projects is often a primitive-summary table, not
the WP table).
"""

from __future__ import annotations

import pytest


def _common(tmp_project):
    """Standard args used by every wpx-index call in this module."""
    return [
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
    ]


# ─── Bug 2 regression — multi-table INDEX.md ──────────────────────────────


def test_flip_status_finds_wp_table_after_primitive_summary(
    tmp_project, seed_index, run_tool,
):
    """Regression for v0.10.5 Bug 2: wpx-index must find the canonical WP
    table even when an earlier `| ID |`-headed table precedes it (e.g.,
    a primitive-summary table). Pre-fix, flip-status would search the
    first `| ID |` table — the primitive summary — and report "WP not
    found" even though the WP exists in the second (WP) table.
    """
    seed_index("INDEX-multi-table.md")
    result = run_tool(
        "wpx-index", "flip-status",
        "--wp", "WP-002", "--to", "done", "--expected", "in_progress",
        *_common(tmp_project),
    )
    assert result.ok, f"flip-status failed: {result.error}; stderr={result.stderr}"
    text = tmp_project.index_md.read_text()
    # Verify WP-002's row in the WP table now reads `done`
    assert "| WP-002 | Second | Extend | done |" in text
    # Verify the Primitive Summary table was NOT touched
    assert "| EXPAND | Create | 17 |" in text


def test_list_ready_excludes_primitive_summary_rows(
    tmp_project, seed_index, run_tool,
):
    """Regression for v0.10.5 Bug 2: list-ready must walk the WP table,
    not the primitive-summary table that precedes it.
    """
    seed_index("INDEX-multi-table.md")
    result = run_tool("wpx-index", "list-ready", *_common(tmp_project))
    assert result.ok, f"list-ready failed: {result.error}"
    # Ready set should be derived from the WP table:
    # WP-001 done, WP-002 in_progress, WP-CHAR-01 pending (deps satisfied
    # on WP-001 done), WP-MIG-1 pending (deps on WP-CHAR-01 still pending)
    # → only WP-CHAR-01 is ready
    assert "WP-CHAR-01" in result.data["ready"]
    assert "WP-MIG-1" not in result.data["ready"]
    # And none of the primitive-summary IDs leak into the ready set
    assert "EXPAND" not in result.data["ready"]
    assert "REORGANISE" not in result.data["ready"]


def test_add_wp_targets_wp_table_not_summary_table(
    tmp_project, seed_index, seed_wp, run_tool,
):
    """Regression for v0.10.5 Bug 2: add-wp must insert into the WP table,
    not the primitive-summary table.
    """
    seed_index("INDEX-multi-table.md")
    seed_wp("WP-AUTO-012-template.md", wp_id="WP-AUTO-012", slug="auto")
    result = run_tool(
        "wpx-index", "add-wp",
        "--wp", "WP-AUTO-012", "--from-wp-file",
        *_common(tmp_project),
    )
    assert result.ok, f"add-wp failed: {result.error}"
    text = tmp_project.index_md.read_text()
    # WP-AUTO-012 should land in the WP table (after WP-MIG-1)
    assert "WP-AUTO-012" in text
    # The primitive-summary table must remain intact: EXPAND/REORGANISE/REINFORCE
    # are its three data rows. WP-AUTO-012 must NOT have landed in it.
    import re as _re
    summary_match = _re.search(
        r"## Primitive Summary\n(.+?)## Work Packages",
        text, _re.DOTALL,
    )
    assert summary_match is not None, "primitive-summary section missing"
    summary_section = summary_match.group(1)
    # Must contain its original 3 primitive groups, and NOT contain WP-AUTO-012
    assert "| EXPAND |" in summary_section
    assert "| REORGANISE |" in summary_section
    assert "| REINFORCE |" in summary_section
    assert "WP-AUTO-012" not in summary_section


def test_propagate_blocked_only_touches_wp_table(
    tmp_project, seed_index, run_tool,
):
    """Regression for v0.10.5 Bug 2: propagate-blocked must mark descendants
    in the WP table, leaving the summary table untouched.
    """
    seed_index("INDEX-multi-table.md")
    result = run_tool(
        "wpx-index", "propagate-blocked",
        "--wp", "WP-CHAR-01",
        *_common(tmp_project),
    )
    assert result.ok, f"propagate-blocked failed: {result.error}"
    text = tmp_project.index_md.read_text()
    # WP-MIG-1 depends on WP-CHAR-01 → should be marked dependency_blocked
    assert "| WP-MIG-1 |" in text
    assert "dependency_blocked" in text


# ─── Minimal INDEX tests — confirm baseline behaviour unchanged ───────────


def test_list_ready_minimal_index(tmp_project, seed_index, run_tool):
    seed_index("INDEX-minimal.md")
    result = run_tool("wpx-index", "list-ready", *_common(tmp_project))
    assert result.ok
    # WP-001 done; WP-002 pending (deps on WP-001 satisfied); WP-003 pending (no deps)
    ready = result.data["ready"]
    assert "WP-002" in ready
    assert "WP-003" in ready


def test_flip_status_with_expected_check(tmp_project, seed_index, run_tool):
    seed_index("INDEX-minimal.md")
    result = run_tool(
        "wpx-index", "flip-status",
        "--wp", "WP-002", "--to", "in_progress", "--expected", "pending",
        *_common(tmp_project),
    )
    assert result.ok


def test_flip_status_expected_mismatch_rejected(tmp_project, seed_index, run_tool):
    seed_index("INDEX-minimal.md")
    # WP-001 is done, not pending
    result = run_tool(
        "wpx-index", "flip-status",
        "--wp", "WP-001", "--to", "in_progress", "--expected", "pending",
        *_common(tmp_project),
    )
    assert not result.ok
    assert "expected 'pending'" in result.error


@pytest.mark.parametrize("status", [
    "step-7-complete",
    "step-7-held",
    "step-7-blocked",
])
def test_flip_status_accepts_step_7_enum_values(
    tmp_project, seed_index, run_tool, status,
):
    """Regression: v0.11.0 added step-7-* status values to the SDK + train
    eligibility logic, but wpx-index's flip-status argparse choices weren't
    updated. Result: the SDK declared these statuses valid, the train queried
    on them, but `wpx-index flip-status --to step-7-complete` rejected at
    argparse — surfaced in a real platform-repo executor session.

    Fixed in v0.15.1 by extending the choices list. Test pins the contract.
    """
    seed_index("INDEX-minimal.md")
    result = run_tool(
        "wpx-index", "flip-status",
        "--wp", "WP-002", "--to", status, "--expected", "pending",
        *_common(tmp_project),
    )
    assert result.ok, (
        f"flip-status --to {status} should be accepted; got stderr: "
        f"{result.stderr}"
    )


def test_add_wp_duplicate_rejected(tmp_project, seed_index, run_tool):
    seed_index("INDEX-minimal.md")
    result = run_tool(
        "wpx-index", "add-wp",
        "--wp", "WP-001", "--title", "Dup", "--primitive", "Create",
        *_common(tmp_project),
    )
    assert not result.ok
    assert "already in INDEX" in result.error


def test_add_wp_explicit_fields(tmp_project, seed_index, run_tool):
    seed_index("INDEX-minimal.md")
    result = run_tool(
        "wpx-index", "add-wp",
        "--wp", "WP-NEW", "--title", "Explicit",
        "--primitive", "Create", "--status", "auto-draft",
        "--depends-on", "WP-001", "--blocks", "",
        *_common(tmp_project),
    )
    assert result.ok
    text = tmp_project.index_md.read_text()
    assert "WP-NEW" in text
    assert "auto-draft" in text


def test_sync_auto_drafts_idempotent(tmp_project, seed_index, seed_wp, run_tool):
    seed_index("INDEX-minimal.md")
    seed_wp("WP-AUTO-012-template.md", wp_id="WP-AUTO-012", slug="auto")
    # First run adds the WP
    r1 = run_tool("wpx-index", "sync-auto-drafts", *_common(tmp_project))
    assert r1.ok
    assert "WP-AUTO-012" in r1.data["added"]
    # Second run is a no-op
    r2 = run_tool("wpx-index", "sync-auto-drafts", *_common(tmp_project))
    assert r2.ok
    assert r2.data["added"] == []
    assert "WP-AUTO-012" in r2.data["skipped"]


# ─── #45 / UXD-14: visual-contract write-time gate ────────────────────────


def _write_wp(wp_dir, wp_id, slug, frontmatter_lines):
    """Write a minimal WP file with the given frontmatter lines."""
    wp_dir.mkdir(parents=True, exist_ok=True)
    body = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n# " + wp_id + "\n"
    (wp_dir / f"{wp_id}-{slug}.md").write_text(body, encoding="utf-8")


def test_add_frontend_wp_without_visual_contract_is_refused(
    tmp_project, seed_index, run_tool,
):
    """A kind: frontend WP with no visual_contract must be refused loudly at
    add-wp (the #45 write-time gate) — not silently admitted to the INDEX."""
    seed_index("INDEX-minimal.md")
    _write_wp(tmp_project.wp_dir, "WP-050", "cancel-ui", [
        "id: WP-050",
        "title: Cancel-flow UI",
        "kind: frontend",
        "primitive: create",
        "status: pending",
        "dependsOn: [WP-001]",
    ])
    result = run_tool(
        "wpx-index", "add-wp", "--wp", "WP-050", "--from-wp-file",
        *_common(tmp_project),
    )
    assert not result.ok, "frontend WP without a visual contract must be refused"
    assert "visual_contract" in (result.error or "")
    assert "WP-050" not in tmp_project.index_md.read_text()


def test_add_frontend_wp_with_visual_contract_succeeds(
    tmp_project, seed_index, run_tool,
):
    """A kind: frontend WP that declares + dependsOn its visual-contract WP is
    admitted."""
    seed_index("INDEX-minimal.md")
    _write_wp(tmp_project.wp_dir, "WP-051", "cancel-ui", [
        "id: WP-051",
        "title: Cancel-flow UI",
        "kind: frontend",
        "primitive: create",
        "status: pending",
        "visual_contract: WP-049",
        "dependsOn: [WP-049]",
    ])
    result = run_tool(
        "wpx-index", "add-wp", "--wp", "WP-051", "--from-wp-file",
        *_common(tmp_project),
    )
    assert result.ok, f"add-wp failed: {result.error}"
    assert "WP-051" in tmp_project.index_md.read_text()


def test_add_frontend_wp_with_logged_exemption_succeeds(
    tmp_project, seed_index, run_tool,
):
    """The only bypass: an explicit, logged exemption."""
    seed_index("INDEX-minimal.md")
    _write_wp(tmp_project.wp_dir, "WP-052", "data-only", [
        "id: WP-052",
        "title: Non-visual frontend wiring",
        "kind: frontend",
        "primitive: create",
        "status: pending",
        "visual_contract: exempt — config-only change, no rendered delta",
        "dependsOn: [WP-001]",
    ])
    result = run_tool(
        "wpx-index", "add-wp", "--wp", "WP-052", "--from-wp-file",
        *_common(tmp_project),
    )
    assert result.ok, f"exempt frontend WP should be admitted: {result.error}"
    assert "WP-052" in tmp_project.index_md.read_text()


def test_visual_contract_wp_cannot_go_done_unsigned(
    tmp_project, seed_index, run_tool,
):
    """#45 runtime gate: a visual-contract WP whose mockup isn't signed off
    must be refused at flip-status --to done (so the frontend WPs depending on
    it stay undispatchable)."""
    seed_index("INDEX-minimal.md")
    # WP-001 exists in INDEX-minimal; make it the (unsigned) visual contract.
    _write_wp(tmp_project.wp_dir, "WP-001", "visual", [
        "id: WP-001",
        "title: Visual contract — dashboard",
        "kind: contract",
        "contract_type: visual",
        "mockup: contracts/visual/dashboard.html",
        "signed_off_at:",          # not signed off
        "provenance: draft",
    ])
    result = run_tool(
        "wpx-index", "flip-status", "--wp", "WP-001", "--to", "done",
        *_common(tmp_project),
    )
    assert not result.ok, "unsigned visual contract must not reach done"
    assert "signed off" in (result.error or "").lower()


def test_visual_contract_wp_goes_done_when_signed_off(
    tmp_project, seed_index, run_tool,
):
    """Once signed off, the visual-contract WP flips to done normally."""
    seed_index("INDEX-minimal.md")
    _write_wp(tmp_project.wp_dir, "WP-001", "visual", [
        "id: WP-001",
        "title: Visual contract — dashboard",
        "kind: contract",
        "contract_type: visual",
        "mockup: contracts/visual/dashboard.html",
        "signed_off_at: 2026-05-27T14:00:00Z",
        "provenance: production-approved",
    ])
    result = run_tool(
        "wpx-index", "flip-status", "--wp", "WP-001", "--to", "done",
        *_common(tmp_project),
    )
    assert result.ok, f"signed-off contract should flip to done: {result.error}"


def test_non_contract_wp_done_flip_is_unaffected(
    tmp_project, seed_index, run_tool,
):
    """A normal WP with no WP file (or non-contract) flips to done untouched —
    the gate is a no-op for anything that isn't a visual-contract WP."""
    seed_index("INDEX-minimal.md")
    result = run_tool(
        "wpx-index", "flip-status", "--wp", "WP-002", "--to", "done",
        *_common(tmp_project),
    )
    assert result.ok, f"ordinary WP done-flip must be unaffected: {result.error}"


# ─── #48: audit-contracts (graph-level data-contract wiring) ──────────────


def test_audit_contracts_passes_clean_cross_kind_set(
    tmp_project, seed_index, run_tool,
):
    """A cross-kind set with a data contract + clean wiring passes."""
    seed_index("INDEX-minimal.md")
    _write_wp(tmp_project.wp_dir, "WP-100", "contract", [
        "id: WP-100", "title: API contract", "kind: contract",
        "contract_type: data", "primitive: create", "status: pending",
    ])
    _write_wp(tmp_project.wp_dir, "WP-101", "api", [
        "id: WP-101", "title: Backend", "kind: backend",
        "primitive: create", "status: pending", "dependsOn: [WP-100]",
    ])
    _write_wp(tmp_project.wp_dir, "WP-102", "ui", [
        "id: WP-102", "title: Frontend", "kind: frontend",
        "primitive: create", "status: pending",
        "visual_contract: WP-100", "dependsOn: [WP-100]",
    ])
    result = run_tool("wpx-index", "audit-contracts", *_common(tmp_project))
    assert result.ok, f"clean cross-kind set should pass: {result.error}"
    assert result.data["violations"] == []


def test_audit_contracts_flags_missing_data_contract(
    tmp_project, seed_index, run_tool,
):
    """A backend+frontend seam with no data-contract WP is flagged."""
    seed_index("INDEX-minimal.md")
    _write_wp(tmp_project.wp_dir, "WP-101", "api", [
        "id: WP-101", "title: Backend", "kind: backend",
        "primitive: create", "status: pending",
    ])
    _write_wp(tmp_project.wp_dir, "WP-102", "ui", [
        "id: WP-102", "title: Frontend", "kind: frontend",
        "primitive: create", "status: pending",
        "visual_contract: exempt — test", "dependsOn: [WP-101]",
    ])
    result = run_tool("wpx-index", "audit-contracts", *_common(tmp_project))
    assert not result.ok, "missing data contract must fail the audit"
    assert "data-contract" in (result.error or "")


def test_audit_contracts_noop_for_single_kind(
    tmp_project, seed_index, run_tool,
):
    """A single-kind set (the INDEX-minimal default — no WP files) is not a
    seam, so the audit passes trivially."""
    seed_index("INDEX-minimal.md")
    result = run_tool("wpx-index", "audit-contracts", *_common(tmp_project))
    assert result.ok, f"single-kind set should pass: {result.error}"


# ─── #60: lint — decompose-time canonical-header gate ─────────────────────


def test_lint_passes_canonical_index(tmp_project, seed_index, run_tool):
    """The canonical INDEX-minimal header passes the lint (exit 0)."""
    seed_index("INDEX-minimal.md")
    result = run_tool("wpx-index", "lint", *_common(tmp_project))
    assert result.ok, f"canonical INDEX should pass lint: {result.error}"
    assert result.returncode == 0


def test_lint_rejects_noncanonical_header(tmp_project, run_tool):
    """A drifted header (`| WP | Title | kind | Primitive |`) is rejected
    loudly: non-zero exit + a message naming the expected canonical header.

    This is the #60 regression — pre-fix the table was invisible to the
    run-all loop and failed silently mid-run; the lint surfaces it at
    decompose time instead."""
    tmp_project.index_md.write_text(
        "# Work Package Index\n\n"
        "## Work Packages\n\n"
        "| WP | Title | kind | Primitive | Status | Depends On | Blocks |\n"
        "|---|---|---|---|---|---|---|\n"
        "| WP-001 | Foundation | backend | create | pending | — | WP-002 |\n",
        encoding="utf-8",
    )
    result = run_tool("wpx-index", "lint", *_common(tmp_project))
    assert not result.ok, "drifted header must be rejected"
    assert result.returncode != 0
    assert "| ID | Title |" in (result.error or "")


def test_lint_rejects_missing_wp_table(tmp_project, run_tool):
    """An INDEX with no WP table at all also fails the lint."""
    tmp_project.index_md.write_text(
        "# Work Package Index\n\nNo work-package table here yet.\n",
        encoding="utf-8",
    )
    result = run_tool("wpx-index", "lint", *_common(tmp_project))
    assert not result.ok
    assert "| ID | Title |" in (result.error or "")
