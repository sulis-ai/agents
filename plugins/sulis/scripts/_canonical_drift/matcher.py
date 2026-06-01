"""StrictDriftMatcher — port 3: match canonical to annotations and produce DriftReport.

Implements the DriftMatcher port from the TDD's Form section. Pure set-
difference logic — no I/O, no state. Multiple matchers can run concurrently
on different inputs; each call is independent.

Three primary gap surfaces (the load-bearing ones per FR-015):
- missing_in_yaml — Step in canonical with no annotation in YAML
- missing_in_canonical — annotation in YAML with no Step in canonical
- missing_failuremode_handling — Step lists a FailureMode in handles_failures
  but the YAML doesn't carry a `canonical:failuremode:<name>` annotation
  anywhere

Plus three cross-reference validations (the MUC-005, MUC-008 surface):
- validate_tool_refs — every Step.tool_ref resolves in tools.jsonld
- validate_handles_failures — every Step.handles_failures id resolves in failuremodes.jsonld
- validate_projects_against_marketplace — every Project.name appears in
  marketplace.json plugins[]
"""

from __future__ import annotations

import json
from pathlib import Path

from _canonical_drift.parser import YamlAnnotation
from _canonical_drift.report import DriftReport


class StrictDriftMatcher:
    """Match canonical entities to YAML annotations + cross-reference validations."""

    def match(
        self,
        canonical_steps: list[dict],
        canonical_failuremodes: list[dict],
        yaml_annotations: list[YamlAnnotation],
        excluded_from_yaml: list[str] | None = None,
    ) -> DriftReport:
        """Run the three primary drift checks; return a DriftReport.

        Cross-reference validations (tool_refs, handles_failures resolution,
        projects↔marketplace) are run separately via dedicated methods so
        callers can choose which surface to engage. The composition root
        (check-canonical-drift.py main) wires them all.

        `excluded_from_yaml` (default empty): a list of Step names declared
        by the envelope as by-design absent from the imperative YAML.
        Their absence is NOT counted as `missing_in_yaml` drift, and their
        FailureMode-handling entries are NOT counted as
        `missing_failuremode_handling` drift. This is the signal that
        distinguishes "the canonical names a Step that's deliberately
        handled elsewhere" (skill prose per MUC-007; the GitHub PR-merge
        UI; downstream release-prod.yml) from "the canonical names a
        Step the YAML forgot to annotate".
        """
        excluded_set = set(excluded_from_yaml or [])

        canonical_step_names = {s["name"] for s in canonical_steps}
        annotated_step_names = {a.target for a in yaml_annotations if a.kind == "step"}
        annotated_failuremode_names = {
            a.target for a in yaml_annotations if a.kind == "failuremode"
        }

        # By-design-absent Steps are subtracted from the missing_in_yaml
        # surface — their absence is expected, not drift.
        missing_in_yaml = sorted(
            (canonical_step_names - annotated_step_names) - excluded_set
        )
        missing_in_canonical = sorted(annotated_step_names - canonical_step_names)

        # FailureMode handling: for each Step, every entry in handles_failures
        # (resolved to a FailureMode.name) MUST appear as an annotation
        # somewhere in the YAML. This is a per-Step assertion — the annotation
        # need not be co-located with the Step's annotation, just present.
        # Skip excluded Steps: if the parent Step is by-design absent from
        # YAML, its FailureMode-handling annotations are also expected
        # absences.
        fm_by_id = {fm["id"]: fm["name"] for fm in canonical_failuremodes}
        missing_fm_handling: list[dict[str, str]] = []
        for step in canonical_steps:
            if step["name"] in excluded_set:
                continue
            for fm_id in step.get("handles_failures", []):
                fm_name = fm_by_id.get(fm_id)
                if fm_name is None:
                    # Unresolved — caught by validate_handles_failures; skip here.
                    continue
                if fm_name not in annotated_failuremode_names:
                    missing_fm_handling.append(
                        {"step": step["name"], "failuremode": fm_name}
                    )

        all_passed = (
            not missing_in_yaml and not missing_in_canonical and not missing_fm_handling
        )

        return DriftReport(
            all_passed=all_passed,
            missing_in_yaml=missing_in_yaml,
            missing_in_canonical=missing_in_canonical,
            missing_failuremode_handling=missing_fm_handling,
        )

    # ─── Cross-reference validations ─────────────────────────────────────

    def validate_tool_refs(
        self, canonical_steps: list[dict], canonical_tools: list[dict]
    ) -> list[tuple[str, str]]:
        """Every Step.tool_ref MUST resolve in tools.jsonld (MUC-005).

        Returns the list of (step_name, unresolved_tool_ref) pairs. Empty list
        means every Step's tool_ref resolves.
        """
        tool_ids = {t["id"] for t in canonical_tools}
        unresolved: list[tuple[str, str]] = []
        for step in canonical_steps:
            tool_ref = step.get("tool_ref")
            if tool_ref is None:
                continue  # human-mechanism Steps may carry no tool_ref
            if tool_ref not in tool_ids:
                unresolved.append((step["name"], tool_ref))
        return unresolved

    def validate_handles_failures(
        self,
        canonical_steps: list[dict],
        canonical_failuremodes: list[dict],
    ) -> list[tuple[str, str]]:
        """Every Step.handles_failures[] entry MUST resolve in failuremodes.jsonld.

        Returns (step_name, unresolved_failuremode_id) pairs.
        """
        fm_ids = {fm["id"] for fm in canonical_failuremodes}
        unresolved: list[tuple[str, str]] = []
        for step in canonical_steps:
            for fm_id in step.get("handles_failures", []):
                if fm_id not in fm_ids:
                    unresolved.append((step["name"], fm_id))
        return unresolved

    def validate_projects_against_marketplace(
        self, canonical_projects: list[dict], marketplace_json_path: Path
    ) -> list[str]:
        """Every Project.name MUST appear in marketplace.json plugins[] (MUC-008).

        Returns the list of Project names that are NOT in plugins[].
        Empty list means every canonical Project is registered in the marketplace.
        """
        if not marketplace_json_path.exists():
            raise FileNotFoundError(
                f"marketplace.json not found: {marketplace_json_path}"
            )
        marketplace = json.loads(marketplace_json_path.read_text())
        registered = {p["name"] for p in marketplace.get("plugins", [])}
        return [p["name"] for p in canonical_projects if p["name"] not in registered]
