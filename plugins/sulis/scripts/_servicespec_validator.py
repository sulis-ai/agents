"""ServiceSpec manifest validator — the Lovable Test (Decompose Validation
Rubric Phase 7).

Pairs with the Slice 1 design-stage methodology gate (`/sulis:draft-architecture`
step 10 emits a ServiceSpec manifest per service). This module mechanically
checks every emitted manifest against the Lovable Test bar: an AI agent must
be able to build a working integration against the manifest with no human docs.

The validator is **pure-data**: take a parsed manifest dict, return a list of
`Issue` records. Caller chooses how to surface (CLI envelope, rubric report,
test assertion). Verdict computation matches the rest of the rubric's
`PASS / PASS-WITH-RATIONALE / FAIL` shape.

Per-check rationale lives in
`plugins/sulis/references/decompose-validation-rubric.md` (Phase 7 section);
this module is the executable half. Field shape follows the platform's
**SPEC-006 / Service Registration** spec; tolerant of minor casing variants
(`user_guide` / `userGuide`, `user_action` / `userAction`) so a single
refinement in SPEC-006 doesn't break the validator. Tighten when SPEC-006
commits.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml


_HERE: Final[Path] = Path(__file__).resolve().parent
_DEFAULT_SCHEMAS_DIR: Final[Path] = _HERE.parent / "brain" / "compiled"


# `dna:entity:{name}` — `name` is a-z + underscores + digits (lower-snake)
_DNA_ENTITY_RE: Final = re.compile(r"^dna:entity:([a-z_][a-z0-9_]*)$")


@dataclass(frozen=True)
class Issue:
    """One rubric finding."""
    check_id: str       # e.g. "7.04"
    severity: str       # "MUST" | "SHOULD" | "MAY"
    message: str        # plain-English finding
    location: str       # field path, e.g. "operations[0].user_guide.whenToUse"


# ─── public API ───────────────────────────────────────────────────────────


def validate_servicespec(
    manifest: dict,
    *,
    schemas_dir: Path | None = None,
    domain: str = "product-development",
) -> list[Issue]:
    """Run the Lovable Test against a parsed ServiceSpec manifest.

    Returns a list of `Issue` records. Empty list = no findings. The caller
    derives a verdict via `compute_verdict`.

    Args:
        manifest: the parsed YAML/JSON ServiceSpec manifest (a dict).
        schemas_dir: directory of vendored compiled entity schemas. Defaults
            to `plugins/sulis/brain/compiled/` so entity-ref checks resolve
            against the marketplace's vendored Brain output.
        domain: entity-schema domain for resolving `dna:entity:X` references.
            Defaults to `"product-development"`.
    """
    schemas_dir = schemas_dir if schemas_dir is not None else _DEFAULT_SCHEMAS_DIR
    issues: list[Issue] = []

    _check_operations(manifest, issues)
    _check_errors(manifest, issues)
    _check_entity_references(manifest, schemas_dir, domain, issues)

    return issues


def validate_servicespec_file(
    path: Path,
    *,
    schemas_dir: Path | None = None,
    domain: str = "product-development",
) -> list[Issue]:
    """Validate a manifest at `path`.

    Returns the issues list; YAML / structural failures produce a single
    7.02 / 7.02-equivalent issue rather than raising.
    """
    text = Path(path).read_text(encoding="utf-8")
    try:
        manifest = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [Issue(
            check_id="7.02",
            severity="MUST",
            message=f"manifest is not valid YAML: {exc}",
            location=str(path),
        )]
    if not isinstance(manifest, dict):
        return [Issue(
            check_id="7.02",
            severity="MUST",
            message="manifest root is not a mapping",
            location=str(path),
        )]
    return validate_servicespec(manifest, schemas_dir=schemas_dir, domain=domain)


def compute_verdict(issues: list[Issue]) -> str:
    """Verdict per the rubric: PASS / PASS-WITH-RATIONALE / FAIL.

    - PASS: no MUST + no SHOULD failures.
    - PASS-WITH-RATIONALE: no MUST failures; ≥1 SHOULD failure.
    - FAIL: ≥1 MUST failure.
    """
    severities = {i.severity for i in issues}
    if "MUST" in severities:
        return "FAIL"
    if "SHOULD" in severities:
        return "PASS-WITH-RATIONALE"
    return "PASS"


# ─── check groups (each appends to `issues` in place) ─────────────────────


def _check_operations(manifest: dict, issues: list[Issue]) -> None:
    """7.03–7.06 + 7.12–7.13."""
    ops = manifest.get("operations")

    # 7.03 — at least one operation
    if not ops or not isinstance(ops, list):
        issues.append(Issue(
            check_id="7.03",
            severity="MUST",
            message="manifest declares no operations (or `operations` is not a list)",
            location="operations",
        ))
        return

    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            issues.append(Issue(
                check_id="7.03",
                severity="MUST",
                message=f"operation entry is not a mapping",
                location=f"operations[{i}]",
            ))
            continue

        loc_prefix = f"operations[{i}]"
        op_name = op.get("name") or f"<unnamed-op-{i}>"
        named = f"{loc_prefix} ({op_name})"

        # 7.04 — description present
        if not _truthy_str(op.get("description")):
            issues.append(Issue(
                check_id="7.04",
                severity="MUST",
                message="operation has no description",
                location=named,
            ))

        # 7.05 — user_guide.whenToUse present
        ug = op.get("user_guide") or op.get("userGuide") or {}
        if not isinstance(ug, dict) or not _truthy_str(ug.get("whenToUse")):
            issues.append(Issue(
                check_id="7.05",
                severity="MUST",
                message="operation has no user_guide.whenToUse",
                location=named,
            ))

        # 7.06 — also prerequisites + nextSteps (SHOULD)
        if isinstance(ug, dict):
            if not _truthy_list_or_str(ug.get("prerequisites")):
                issues.append(Issue(
                    check_id="7.06",
                    severity="SHOULD",
                    message="operation user_guide has no prerequisites",
                    location=named,
                ))
            if not _truthy_list_or_str(ug.get("nextSteps")):
                issues.append(Issue(
                    check_id="7.06",
                    severity="SHOULD",
                    message="operation user_guide has no nextSteps",
                    location=named,
                ))

        # 7.12 — binding (host / basePath / method / auth)
        binding = op.get("binding")
        if not isinstance(binding, dict):
            issues.append(Issue(
                check_id="7.12",
                severity="MUST",
                message="operation has no binding",
                location=named,
            ))
        else:
            for field in ("host", "basePath", "method", "auth"):
                if not _truthy_str(binding.get(field)):
                    issues.append(Issue(
                        check_id="7.12",
                        severity="MUST",
                        message=f"operation binding missing required field: {field}",
                        location=f"{named}.binding.{field}",
                    ))

        # 7.13 — permission is structurally namespaced
        permission = op.get("permission")
        if not _truthy_str(permission):
            issues.append(Issue(
                check_id="7.13",
                severity="MUST",
                message="operation has no permission",
                location=named,
            ))
        elif ":" not in str(permission):
            issues.append(Issue(
                check_id="7.13",
                severity="MUST",
                message=(
                    f"operation permission is not structurally namespaced "
                    f"(no colon, e.g. 'storage.entities:create'): {permission!r}"
                ),
                location=f"{named}.permission",
            ))


def _check_errors(manifest: dict, issues: list[Issue]) -> None:
    """7.07–7.10."""
    errors = manifest.get("errors")
    if errors is None or not isinstance(errors, dict):
        return  # no catalog is OK at this phase; 7.03 governs operation count

    for code, err in errors.items():
        loc = f"errors.{code}"
        if not isinstance(err, dict):
            issues.append(Issue(
                check_id="7.07",
                severity="MUST",
                message="error catalog entry is not a mapping",
                location=loc,
            ))
            continue

        # 7.07 — httpStatus present and int
        if "httpStatus" not in err:
            issues.append(Issue(
                check_id="7.07",
                severity="MUST",
                message="error has no httpStatus",
                location=loc,
            ))
        elif not isinstance(err["httpStatus"], int):
            issues.append(Issue(
                check_id="7.07",
                severity="MUST",
                message=(
                    f"error httpStatus must be an integer; got "
                    f"{type(err['httpStatus']).__name__}"
                ),
                location=loc,
            ))

        # 7.08 — user_action present
        ua = err.get("user_action") or err.get("userAction")
        if not _truthy_str(ua):
            issues.append(Issue(
                check_id="7.08",
                severity="MUST",
                message="error has no user_action",
                location=loc,
            ))

        # 7.09 — developer_action present
        da = err.get("developer_action") or err.get("developerAction")
        if not _truthy_str(da):
            issues.append(Issue(
                check_id="7.09",
                severity="MUST",
                message="error has no developer_action",
                location=loc,
            ))

        # 7.10 — retryable flag (SHOULD)
        if "retryable" not in err:
            issues.append(Issue(
                check_id="7.10",
                severity="SHOULD",
                message="error has no retryable flag",
                location=loc,
            ))


def _check_entity_references(
    manifest: dict,
    schemas_dir: Path,
    domain: str,
    issues: list[Issue],
) -> None:
    """7.11 — entity refs resolve to vendored compiled schemas."""
    entities = manifest.get("entities")
    if entities is None:
        return  # no entities block is acceptable for services that don't own entities
    if not isinstance(entities, list):
        issues.append(Issue(
            check_id="7.11",
            severity="MUST",
            message="entities block is not a list",
            location="entities",
        ))
        return

    for i, ent in enumerate(entities):
        loc = f"entities[{i}]"
        # Allow either a bare string `dna:entity:X` or `{id: "dna:entity:X"}`.
        ent_id = ent.get("id") if isinstance(ent, dict) else ent
        if not isinstance(ent_id, str):
            issues.append(Issue(
                check_id="7.11",
                severity="MUST",
                message="entity reference must be a string id (`dna:entity:X`) or `{id: ...}`",
                location=loc,
            ))
            continue
        match = _DNA_ENTITY_RE.match(ent_id)
        if not match:
            issues.append(Issue(
                check_id="7.11",
                severity="MUST",
                message=(
                    f"entity reference is not a valid `dna:entity:X` form: "
                    f"{ent_id!r}"
                ),
                location=loc,
            ))
            continue
        entity_name = match.group(1)
        schema_path = schemas_dir / domain / f"{entity_name}.schema.json"
        if not schema_path.exists():
            issues.append(Issue(
                check_id="7.11",
                severity="MUST",
                message=(
                    f"entity reference does not resolve to a vendored compiled "
                    f"schema: {ent_id} (looked at {schema_path})"
                ),
                location=loc,
            ))


# ─── small helpers ────────────────────────────────────────────────────────


def _truthy_str(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _truthy_list_or_str(v) -> bool:
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return len(v) > 0
    return False
