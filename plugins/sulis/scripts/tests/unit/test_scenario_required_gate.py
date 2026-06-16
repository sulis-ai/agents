"""Unit tests for the #103 scenario-required gate.

The gap: every scenario gate fired only IF scenarios existed, so a user-facing
change with zero scenarios shipped as "advisory". This gate flips the test from
*exists* to *required*: user-facing ⇒ scenarios REQUIRED (or logged exemption),
else BLOCK. It must NOT over-fire on tooling/plugin/library changes.
"""

from __future__ import annotations

import json

from _scenario_required_gate import (
    exemption_reason_for_change,
    scenario_gate,
    scenarios_present_for_change,
    spec_declares_founder_facing,
)

# A path the founder-surface classifier recognises as user-facing, and ones it
# (correctly) does not (marketplace tooling / library / tests).
_UI_PATH = "apps/web/src/components/Login.tsx"
_TOOLING_PATHS = ["plugins/sulis/scripts/sulis-change", "plugins/sulis/skills/x/SKILL.md"]


# ─── scenario_gate (the pure decision) ─────────────────────────────────────


def test_user_facing_with_no_scenarios_blocks():
    v = scenario_gate(touched_paths=[_UI_PATH], scenarios_present=False)
    assert v.verdict == "required_missing"
    assert v.user_facing is True
    assert "no verifiable scenarios" in v.reason


def test_tooling_change_with_no_scenarios_is_ok():
    # The over-fire guard: marketplace tooling / a skill edit / a script is NOT
    # a user-facing surface — scenarios don't apply, gate passes.
    v = scenario_gate(touched_paths=_TOOLING_PATHS, scenarios_present=False)
    assert v.verdict == "ok"
    assert v.user_facing is False


def test_user_facing_with_scenarios_present_is_ok():
    v = scenario_gate(touched_paths=[_UI_PATH], scenarios_present=True)
    assert v.verdict == "ok"
    assert v.user_facing is True
    assert v.scenarios_present is True


def test_user_facing_no_scenarios_but_exempted_is_ok():
    v = scenario_gate(
        touched_paths=[_UI_PATH], scenarios_present=False,
        exemption_reason="infra leg unavailable in this run; tracked in #999",
    )
    assert v.verdict == "ok"
    assert v.exempted is True
    assert v.exemption_reason and "infra leg" in v.exemption_reason


def test_blank_exemption_does_not_count():
    v = scenario_gate(touched_paths=[_UI_PATH], scenarios_present=False,
                      exemption_reason="   ")
    assert v.verdict == "required_missing"


def test_empty_diff_is_not_user_facing():
    v = scenario_gate(touched_paths=[], scenarios_present=False)
    assert v.verdict == "ok"
    assert v.user_facing is False
    assert v.nfr_scope is False


# ─── NFR trigger (#103 widening — scenarios for non-functional requirements) ─


def test_nfr_change_with_no_scenarios_blocks():
    # A change that declares/edits non-functional requirements (NFR.md) needs a
    # DRIVEN scenario too — a unit test can't prove the real production
    # condition. Not user-facing, but still in scope.
    v = scenario_gate(
        touched_paths=[".specifications/payments/NFR.md"], scenarios_present=False)
    assert v.verdict == "required_missing"
    assert v.user_facing is False
    assert v.nfr_scope is True
    assert "non-functional" in v.reason.lower()


def test_nfr_change_with_scenarios_present_is_ok():
    v = scenario_gate(
        touched_paths=[".specifications/payments/NFR.md"], scenarios_present=True)
    assert v.verdict == "ok"
    assert v.nfr_scope is True


def test_nfr_change_exempted_is_ok():
    v = scenario_gate(
        touched_paths=[".specifications/payments/NFR.md"], scenarios_present=False,
        exemption_reason="perf budget verified manually in staging; tracked #777")
    assert v.verdict == "ok"
    assert v.exempted is True


def test_user_facing_and_nfr_both_in_scope():
    v = scenario_gate(
        touched_paths=[_UI_PATH, ".specifications/p/NFR.md"], scenarios_present=False)
    assert v.verdict == "required_missing"
    assert v.user_facing is True
    assert v.nfr_scope is True


def test_tooling_with_nfr_substring_does_not_false_fire():
    # Guard: a tooling path that merely contains 'nfr' as part of another word
    # should not trip the NFR trigger. The fragments are specific (nfr.md,
    # /nfr/, non-functional) — a plain script path stays out of scope.
    v = scenario_gate(
        touched_paths=["plugins/sulis/scripts/_conform.py"], scenarios_present=False)
    assert v.verdict == "ok"
    assert v.nfr_scope is False


# ─── #301: the SPEC founder_facing flag triggers the gate at the SPECIFY ────
#     boundary, BEFORE any UI code exists in the diff. This is the gap the
#     ship-time path signal can't catch: at specify only the SPEC exists, so
#     the user-facing signal must come from the SPEC's own founder_facing flag.


def test_spec_founder_facing_flag_blocks_with_no_ui_paths():
    # The core #301 behaviour: a founder_facing SPEC with NO touched UI paths
    # (the specify/design boundary — no .tsx written yet) and no scenarios
    # must BLOCK. Today the path signal is empty, so without the flag trigger
    # this would (wrongly) pass.
    v = scenario_gate(touched_paths=[], scenarios_present=False, spec_founder_facing=True)
    assert v.verdict == "required_missing"
    assert v.user_facing is True
    assert "no verifiable scenarios" in v.reason


def test_spec_founder_facing_flag_with_scenarios_is_ok():
    v = scenario_gate(touched_paths=[], scenarios_present=True, spec_founder_facing=True)
    assert v.verdict == "ok"
    assert v.user_facing is True


def test_spec_founder_facing_flag_exempted_is_ok():
    v = scenario_gate(
        touched_paths=[], scenarios_present=False, spec_founder_facing=True,
        exemption_reason="guided-CLI surface; scenarios tracked in #998")
    assert v.verdict == "ok"
    assert v.exempted is True


def test_spec_not_founder_facing_no_paths_is_ok():
    # A non-founder-facing SPEC with no UI paths and no NFRs stays out of scope.
    v = scenario_gate(touched_paths=[], scenarios_present=False, spec_founder_facing=False)
    assert v.verdict == "ok"
    assert v.user_facing is False


def test_spec_flag_default_is_off_preserves_path_behaviour():
    # Regression: omitting spec_founder_facing keeps the original path-driven
    # behaviour exactly (the ship-time call site that doesn't pass the flag).
    blocked = scenario_gate(touched_paths=[_UI_PATH], scenarios_present=False)
    assert blocked.verdict == "required_missing"
    clean = scenario_gate(touched_paths=_TOOLING_PATHS, scenarios_present=False)
    assert clean.verdict == "ok"


# ─── spec_declares_founder_facing (the SPEC-frontmatter reader) ─────────────


def _write_spec(tmp_path, stem, frontmatter):
    d = tmp_path / ".changes"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.SPEC.md").write_text(
        f"---\n{frontmatter}\n---\n# Spec\nbody\n", encoding="utf-8")


def test_spec_declares_founder_facing_true(tmp_path):
    _write_spec(tmp_path, "feat-x", "founder_facing: true")
    assert spec_declares_founder_facing(tmp_path, "feat-x") is True


def test_spec_declares_founder_facing_false(tmp_path):
    _write_spec(tmp_path, "feat-x", "founder_facing: false")
    assert spec_declares_founder_facing(tmp_path, "feat-x") is False


def test_spec_declares_founder_facing_missing_flag(tmp_path):
    _write_spec(tmp_path, "feat-x", "primitive: feat")
    assert spec_declares_founder_facing(tmp_path, "feat-x") is False


def test_spec_declares_founder_facing_no_spec_file(tmp_path):
    assert spec_declares_founder_facing(tmp_path, "feat-x") is False


# ─── scenarios_present_for_change (presence detection) ─────────────────────


def _write_scenarios(tmp_path, stem, nodes):
    d = tmp_path / ".changes"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.scenarios.jsonld").write_text(
        json.dumps({"@graph": nodes}), encoding="utf-8")


def test_present_when_scenario_node_exists(tmp_path):
    _write_scenarios(tmp_path, "feat-x", [{"@id": "dna:scenario:abc", "@type": "Scenario"}])
    assert scenarios_present_for_change(tmp_path, "feat-x") is True


def test_absent_when_file_missing(tmp_path):
    assert scenarios_present_for_change(tmp_path, "feat-x") is False


def test_absent_when_no_scenario_nodes(tmp_path):
    _write_scenarios(tmp_path, "feat-x", [{"@id": "dna:workflow:w", "@type": "Workflow"}])
    assert scenarios_present_for_change(tmp_path, "feat-x") is False


def test_absent_when_malformed(tmp_path):
    d = tmp_path / ".changes"
    d.mkdir(parents=True, exist_ok=True)
    (d / "feat-x.scenarios.jsonld").write_text("{not json", encoding="utf-8")
    assert scenarios_present_for_change(tmp_path, "feat-x") is False


# ─── exemption_reason_for_change (the logged escape) ───────────────────────


def test_exemption_marker_read(tmp_path):
    d = tmp_path / ".changes"
    d.mkdir(parents=True, exist_ok=True)
    (d / "feat-x.scenarios-exempt").write_text("non-user-facing infra leg\n", encoding="utf-8")
    assert exemption_reason_for_change(tmp_path, "feat-x") == "non-user-facing infra leg"


def test_exemption_absent_when_no_marker(tmp_path):
    assert exemption_reason_for_change(tmp_path, "feat-x") is None


def test_exemption_blank_marker_is_none(tmp_path):
    d = tmp_path / ".changes"
    d.mkdir(parents=True, exist_ok=True)
    (d / "feat-x.scenarios-exempt").write_text("   \n", encoding="utf-8")
    assert exemption_reason_for_change(tmp_path, "feat-x") is None


def test_scenarios_present_detects_canonical_scenarios_key(tmp_path):
    """Regression (#104): the authored file shape is {"scenarios":[{"id":"SC-01",...}]}
    with SC-NN ids (no dna:scenario @id). A non-empty scenarios list IS 'present' —
    the gate previously only matched @graph/top-list and missed every real file."""
    from _scenario_required_gate import scenarios_present_for_change
    changes = tmp_path / ".changes"
    changes.mkdir()
    (changes / "harden-x.scenarios.jsonld").write_text(
        '{"slug":"x","scenarios":[{"id":"SC-01","name":"do X observe Y","steps":[]}]}',
        encoding="utf-8",
    )
    assert scenarios_present_for_change(tmp_path, "harden-x") is True
    # empty scenarios list ⇒ absent
    (changes / "harden-y.scenarios.jsonld").write_text('{"scenarios":[]}', encoding="utf-8")
    assert scenarios_present_for_change(tmp_path, "harden-y") is False
