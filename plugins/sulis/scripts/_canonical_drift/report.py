"""DriftReport — the JSON envelope returned by the drift detector.

Carries every gap surface the matcher can produce. Pure dataclass: no behaviour
beyond serialisation into the canonical envelope shape (matches every other
sulis-* CLI per CONVENTION CP-01).

Envelope shape:
    {"ok": <bool>, "data": {"drift": [<entry>, ...]}}

`drift` is a flat list of typed entries, one per gap. Each entry carries a
`kind` discriminator plus the fields relevant to that kind. Empty list ⇔
`all_passed=True` ⇔ `ok=True`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DriftReport:
    """Result of running the drift matcher against canonical + YAML.

    Six gap surfaces (matches the WP-007 DoD's test list one-for-one):
    - missing_in_yaml: Step names in canonical that no annotation references
    - missing_in_canonical: annotation targets that no Step in canonical declares
    - missing_failuremode_handling: (Step, FailureMode) pairs the YAML doesn't catch
    - missing_tool_refs: (Step, tool_ref) for Step.tool_ref that no Tool declares (MUC-005)
    - unresolved_handles_failures: (Step, FailureMode-id) that no FailureMode declares
    - projects_not_in_marketplace: Project names absent from marketplace.json plugins[] (MUC-008)
    """

    all_passed: bool
    missing_in_yaml: list[str] = field(default_factory=list)
    missing_in_canonical: list[str] = field(default_factory=list)
    missing_failuremode_handling: list[dict[str, str]] = field(default_factory=list)
    missing_tool_refs: list[tuple[str, str]] = field(default_factory=list)
    unresolved_handles_failures: list[tuple[str, str]] = field(default_factory=list)
    projects_not_in_marketplace: list[str] = field(default_factory=list)

    def to_envelope(self) -> dict[str, Any]:
        """Serialise to the canonical {"ok": ..., "data": {"drift": [...]}} envelope."""
        drift: list[dict[str, Any]] = []
        for name in self.missing_in_yaml:
            drift.append({"kind": "missing_in_yaml", "step": name})
        for name in self.missing_in_canonical:
            drift.append({"kind": "missing_in_canonical", "annotation": name})
        for entry in self.missing_failuremode_handling:
            drift.append(
                {
                    "kind": "missing_failuremode_handling",
                    "step": entry["step"],
                    "failuremode": entry["failuremode"],
                }
            )
        for step, tool_ref in self.missing_tool_refs:
            drift.append(
                {"kind": "missing_tool_ref", "step": step, "tool_ref": tool_ref}
            )
        for step, fm_id in self.unresolved_handles_failures:
            drift.append(
                {
                    "kind": "unresolved_handles_failures",
                    "step": step,
                    "failuremode_id": fm_id,
                }
            )
        for project in self.projects_not_in_marketplace:
            drift.append({"kind": "project_not_in_marketplace", "project": project})
        return {"ok": self.all_passed, "data": {"drift": drift}}
