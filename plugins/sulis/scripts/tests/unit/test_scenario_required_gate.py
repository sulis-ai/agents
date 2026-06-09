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
