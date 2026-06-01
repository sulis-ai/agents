#!/usr/bin/env python3
"""check-canonical-drift.py — Path A drift detector.

Reads canonical entity instances (workflow + steps + failuremodes + tools +
optionally triggers + projects) and an imperative file (YAML for the
release-train, Markdown SKILL.md for discover-project); emits a JSON
envelope on stdout naming any drift; exits 0 (clean), 1 (drift), or 2
(invocation error).

Per release-train ADR-001 + ADR-002: this is the load-bearing structural
defense for Path A. Without it, the canonical degrades to documentation
that decays (MUC-009).

The imperative parser is dispatched by file extension via
`_canonical_drift.parser.parse_annotations`: `.yml`/`.yaml` → YAML
comment scan; `.md` → HTML-comment scan (WP-009 / discover-project
ADR-001).

Usage (release-train):
    python3 plugins/sulis/scripts/check-canonical-drift.py \\
        --instance-dir plugins/sulis/instances/release-train \\
        --yaml-path .github/workflows/release-on-merge.yml \\
        [--marketplace-json .claude-plugin/marketplace.json]

Usage (discover-project, with cross-tenant boundary recognition):
    python3 plugins/sulis/scripts/check-canonical-drift.py \\
        --instance-dir .sulis/projects/my-project \\
        --yaml-path plugins/sulis/skills/discover-project/SKILL.md \\
        --cross-tenant-refs-allowed-for release_workflow_ref

Exit codes:
    0 — all conformance checks pass
    1 — drift detected (envelope's data.drift names the gaps)
    2 — invocation error (missing arg; file not found; malformed canonical)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make _canonical_drift importable when this script is invoked directly.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _canonical_drift.matcher import StrictDriftMatcher  # noqa: E402
from _canonical_drift.parser import parse_annotations  # noqa: E402
from _canonical_drift.reader import JsonLdFileReader  # noqa: E402
from _canonical_drift.report import DriftReport  # noqa: E402


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that the imperative release-on-merge.yml conforms to "
        "the canonical release-train entity instances.",
    )
    parser.add_argument(
        "--instance-dir",
        type=Path,
        required=True,
        help="Directory holding the canonical *.jsonld files (workflow, steps, …).",
    )
    parser.add_argument(
        "--yaml-path",
        type=Path,
        required=True,
        help="Path to the imperative YAML (release-on-merge.yml) under scrutiny.",
    )
    parser.add_argument(
        "--marketplace-json",
        type=Path,
        default=None,
        help="Path to .claude-plugin/marketplace.json for the Project ↔ plugins[] check "
        "(MUC-008). Optional — skipped when projects.jsonld is absent.",
    )
    parser.add_argument(
        "--validate-schemas",
        action="store_true",
        help="Run jsonschema validation on every canonical instance before matching. "
        "Defaults off (the per-WP entity-authoring tests validate at author-time).",
    )
    parser.add_argument(
        "--cross-tenant-refs-allowed-for",
        type=lambda s: [field for field in s.split(",") if field],
        default=[],
        help="Comma-separated list of reference field names that may legitimately "
        "cross tenant boundaries without being treated as drift. Example: "
        "'release_workflow_ref,belongs_to_product_ref'. The discover-project skill "
        "passes this flag because a consumer Project's release_workflow_ref points "
        "at the marketplace tenant's Workflow (ADR-002). Default empty preserves "
        "the pre-extension stricter-by-default behaviour.",
    )
    return parser.parse_args(argv)


def _emit(payload: dict, exit_code: int) -> int:
    """Print the JSON envelope and return the exit code (for sys.exit)."""
    print(json.dumps(payload))
    return exit_code


def main(argv: list[str] | None = None) -> int:
    """Composition root. Returns exit code per the contract above."""
    try:
        args = _parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as e:
        # argparse calls sys.exit on parse error. Re-emit as our JSON envelope
        # so callers (CI + the founder) get a uniform shape.
        if e.code == 0:
            return 0  # --help path
        return _emit(
            {"ok": False, "error": "invocation: missing or malformed argument"},
            2,
        )

    reader = JsonLdFileReader()
    matcher = StrictDriftMatcher()

    # ─── Read canonical entities ─────────────────────────────────────────
    try:
        steps = reader.read_steps(args.instance_dir, validate=args.validate_schemas)
        failuremodes = reader.read_failuremodes(
            args.instance_dir, validate=args.validate_schemas
        )
        tools = reader.read_tools(args.instance_dir, validate=args.validate_schemas)
        # Envelope-level by-design-absence list (tighten-drift-gate).
        # Defaults to [] when the field is absent (back-compat with
        # canonical instances authored before the field existed).
        excluded_from_yaml = reader.read_excluded_from_yaml(args.instance_dir)
    except FileNotFoundError as e:
        return _emit({"ok": False, "error": f"canonical: {e}"}, 2)
    except ValueError as e:
        return _emit({"ok": False, "error": f"canonical: {e}"}, 2)

    # ─── Parse imperative annotations (YAML or Markdown — WP-009) ────────
    # The dispatcher routes by file extension: `.yml`/`.yaml` → YAML
    # parser; `.md` → Markdown HTML-comment parser; anything else → empty.
    # The historic `--yaml-path` flag name is retained for backward
    # compatibility (release-train CI invokes the detector with it),
    # but it now accepts any supported imperative format.
    try:
        annotations = parse_annotations(args.yaml_path)
    except FileNotFoundError as e:
        return _emit({"ok": False, "error": f"imperative: {e}"}, 2)
    except ValueError as e:
        return _emit({"ok": False, "error": f"imperative: {e}"}, 2)

    # ─── Primary drift match (Step + FailureMode binding) ────────────────
    report = matcher.match(
        steps, failuremodes, annotations, excluded_from_yaml=excluded_from_yaml
    )

    # ─── Cross-reference validations ─────────────────────────────────────
    missing_tool_refs = matcher.validate_tool_refs(steps, tools)
    unresolved_handles = matcher.validate_handles_failures(steps, failuremodes)

    projects_not_in_marketplace: list[str] = []
    projects_file = args.instance_dir / "projects.jsonld"
    if projects_file.exists() and args.marketplace_json is not None:
        try:
            projects_doc = json.loads(projects_file.read_text())
        except json.JSONDecodeError as e:
            return _emit({"ok": False, "error": f"projects: {e}"}, 2)
        projects = projects_doc.get("projects", [])
        try:
            projects_not_in_marketplace = matcher.validate_projects_against_marketplace(
                projects, args.marketplace_json
            )
        except FileNotFoundError as e:
            return _emit({"ok": False, "error": f"marketplace.json: {e}"}, 2)

    # Compose the final report — fold cross-ref results in.
    has_xref_drift = bool(
        missing_tool_refs or unresolved_handles or projects_not_in_marketplace
    )
    composed = DriftReport(
        all_passed=report.all_passed and not has_xref_drift,
        missing_in_yaml=report.missing_in_yaml,
        missing_in_canonical=report.missing_in_canonical,
        missing_failuremode_handling=report.missing_failuremode_handling,
        missing_tool_refs=missing_tool_refs,
        unresolved_handles_failures=unresolved_handles,
        projects_not_in_marketplace=projects_not_in_marketplace,
    )

    envelope = composed.to_envelope()
    return _emit(envelope, 0 if composed.all_passed else 1)


if __name__ == "__main__":
    sys.exit(main())
