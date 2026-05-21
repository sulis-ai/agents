# Design Validator Skill (Orchestrator)

> **Purpose:** Orchestrate independent validator agents to assess design artifacts before Design Approval (GATE 1).
> **Architecture:** Decomposed validators running in parallel for focused, thorough validation.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│              Design Validator Orchestrator                       │
│                 (This Skill - Coordination Only)                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        │           │           │           │           │
        ▼           ▼           ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  artifact-  │ │   market-   │ │  platform-  │ │   entity-   │ │architecture-│
│  presence   │ │  evidence   │ │ conventions │ │    model    │ │ principles  │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
        │           │           │           │           │
        ▼           ▼           ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│service-layer│ │ data-access │ │ structural- │ │     ivs     │ │ servicespec │
│  patterns   │ │  patterns   │ │completeness │ │  (IVS.md)   │ │  (if req'd) │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Results Collation                             │
│              (Structured JSON from each validator)               │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Final Report                                 │
│           PASSED / BLOCKED with per-validator detail             │
└─────────────────────────────────────────────────────────────────┘
```

## Why Decomposed Validators?

| Problem with Monolithic | Solution with Decomposed |
|------------------------|--------------------------|
| Context overload (100+ checks) | Each validator focuses on 10-20 checks |
| Focus drift by check #80 | Dedicated focus per validator |
| All-or-nothing execution | Parallel independent execution |
| Hard to debug failures | Clear per-validator results |
| Hard to extend | Add new validators easily |

---

## Validators

| Validator | Focus | Checks | Skill File |
|-----------|-------|--------|------------|
| `artifact-presence` | All files exist + conditional artifacts | ART-01 to ART-14 | `validators/artifact-presence-validator.md` |
| `market-evidence` | Problem validation | ART-00*, KANO-* | `validators/market-evidence-validator.md` |
| `platform-conventions` | White-label, secrets, naming | CONV-* | `validators/platform-conventions-validator.md` |
| `entity-model` | Tenant hierarchy | ENT-* | `validators/entity-model-validator.md` |
| `architecture-principles` | Core principles, cloud abstraction | ARCH-* | `validators/architecture-principles-validator.md` |
| `service-layer-patterns` | DESIGN.md Section 9.6 | IMPL-* (design) | `validators/service-layer-patterns-validator.md` |
| `data-access-patterns` | DESIGN.md Section 9.7 | PERF-* (design) | `validators/data-access-patterns-validator.md` |
| `structural-completeness` | Template sections | STRUCT-* | `validators/structural-completeness-validator.md` |
| `ivs` | IVS.md requirements & verification | IVS-* | `validators/ivs-validator.md` |
| `nfr` | Non-functional requirements & platform fit | NFR-* | `validators/nfr-validator.md` |
| `servicespec` | ServiceSpec (if applicable) | SPEC-* | `validators/servicespec-validator.md` |
| `servicespec-delta` | ServiceSpec Delta (service_enhancement) | DELTA-* | `validators/servicespec-delta-validator.md` |
| `extension-delta` | Extension Delta (extension_enhancement) | EXTDELTA-* | `validators/extension-delta-validator.md` |
| `capability-delta` | Capability Delta (capability_enhancement) | CAPDELTA-* | `validators/capability-delta-validator.md` |
| `solution-summary` | Executive dashboard completeness | SUM-* | `validators/solution-summary-validator.md` |

---

## When This Skill Activates

This skill triggers when:
- Feature design phase is complete
- Before requesting Design Approval (GATE 1)
- User asks "validate this design", "run design validation"
- Feature-lifecycle skill needs pre-gate validation

---

## Orchestration Process

### Step 1: Gather Context

```python
feature_name = "{feature}"
feature_path = f"features/{feature_name}/"

# Read LIFECYCLE_STATE.json to determine classification
lifecycle = read(f"{feature_path}LIFECYCLE_STATE.json")
classification = lifecycle.classification

# Scope discovery (ADR-083)
scopes = lifecycle.get("scopes", {}).get("resolved", ["spec", "backend"])
multi_scope = len([s for s in scopes if s != "spec"]) > 1

# Build artifact paths based on scope layout
if multi_scope:
    # Multi-scope: scope-specific artifacts in scope directories
    design_paths = {s: f"{feature_path}{s}/DESIGN.md" for s in scopes if s != "spec"}
    ivs_paths = {s: f"{feature_path}{s}/IVS.md" for s in scopes if s != "spec"}
    ivs_paths["cross_scope"] = f"{feature_path}IVS.md"  # Cross-scope IVS at root
else:
    # Single-scope: all artifacts at root
    design_paths = {"root": f"{feature_path}DESIGN.md"}
    ivs_paths = {"root": f"{feature_path}IVS.md"}
```

### Step 2: Select Validators Based on Classification

Select validators based on feature classification:

```python
# Core validators that run for ALL classifications
core_validators = [
    ("artifact-presence", "Check all design artifacts exist"),
    ("market-evidence", "Validate market evidence and Kano scope"),
    ("platform-conventions", "Check platform convention compliance"),
    ("entity-model", "Validate entity model compliance"),
    ("architecture-principles", "Check architecture principle compliance"),
    ("service-layer-patterns", "Validate DESIGN.md Section 9.6 patterns"),
    ("data-access-patterns", "Validate DESIGN.md Section 9.7 patterns"),
    ("structural-completeness", "Check template structure compliance"),
    ("ivs", "Validate IVS.md requirements and verification specs"),
    ("nfr", "Validate NFR.md requirements and platform capability fit"),
    ("solution-summary", "Validate SOLUTION_SUMMARY.md completeness"),
]

# Classification-specific validators
classification_validators = {
    "service": [
        ("servicespec", "Validate SERVICE_SPECIFICATION.md"),
    ],
    "service_enhancement": [
        ("servicespec-delta", "Validate SERVICE_SPECIFICATION_DELTA.md"),
    ],
    "extension": [
        ("servicespec", "Validate EXTENSION_SPECIFICATION.md"),  # Uses servicespec validator
    ],
    "extension_enhancement": [
        ("extension-delta", "Validate EXTENSION_SPECIFICATION_DELTA.md"),
    ],
    "capability": [
        # No spec validator yet - uses structural-completeness
    ],
    "capability_enhancement": [
        ("capability-delta", "Validate CAPABILITY_SPECIFICATION_DELTA.md"),
    ],
    "infrastructure": [
        # No spec validators
    ],
}

# Build final validator list
validators = core_validators + classification_validators.get(classification, [])
```

### Step 3: Spawn Validators in Parallel

Spawn ALL selected validators using the Task tool with `run_in_background=true`:

```python
# Spawn all in parallel
for validator_id, description in validators:
    Task(
        subagent_type="general-purpose",
        prompt=build_validator_prompt(validator_id, feature_name),
        description=f"Validator: {validator_id}",
        run_in_background=True
    )
```

### Step 3: Collect Results

Wait for all validators to complete and collect their JSON outputs.

### Step 4: Collate Final Report

```python
results = collect_all_validator_results()

final_status = "PASS" if all(r.status == "PASS" for r in results) else "FAIL"

total_blocking = sum(r.summary.blocking_issues for r in results)
total_warnings = sum(r.summary.warning_issues for r in results)

report = generate_final_report(results, final_status)
```

### Step 5: Save Report

```
Save to: features/{feature}/reviews/design-validator-{YYYY-MM-DDTHHMMSSZ}.md
```

---

## Validator Prompt Template

Each validator receives this prompt structure:

```
You are the {validator_name} Validator - a focused, independent validator.

## Your Task

Validate {validator_focus} for feature: {feature_name}
Feature path: features/{feature_name}/

## Files to Read

{list of specific files for this validator}

## Validation Checklist

{specific checks for this validator}

## Output Format

You MUST return a JSON object following this EXACT structure:

```json
{
  "validator": "{validator_id}",
  "version": "1.0.0",
  "feature": "{feature_name}",
  "timestamp": "{ISO 8601}",
  "status": "PASS or FAIL",
  "summary": {
    "checks_total": N,
    "checks_passed": N,
    "checks_failed": N,
    "checks_skipped": N,
    "blocking_issues": N,
    "warning_issues": N
  },
  "issues": [
    {
      "check_id": "CHECK-ID",
      "severity": "BLOCKING or WARNING",
      "title": "Brief description",
      "file": "path/to/file.md",
      "line": 42,
      "evidence": "Quoted text",
      "violation": "What rule violated",
      "fix": "How to fix"
    }
  ],
  "checks": [
    {
      "check_id": "CHECK-ID",
      "description": "What this checks",
      "status": "PASS or FAIL or SKIP",
      "notes": "Optional context"
    }
  ]
}
```

## Rules

1. Read ONLY the files listed
2. Check ONLY the {check_prefix}-* checks
3. Return ONLY the JSON output - no other text
4. Be thorough but focused
```

---

## Final Report Format

```markdown
# Design Validator Report

**Feature:** {feature_name}
**Validation Date:** {YYYY-MM-DDTHHMMSSZ}
**Validated By:** Design Validator Orchestrator (v2.4.0)

## Executive Summary

| Validator | Status | Blocking | Warnings | Duration |
|-----------|--------|----------|----------|----------|
| artifact-presence | PASS/FAIL | 0 | 0 | 1.2s |
| market-evidence | PASS/FAIL | 0 | 0 | 2.3s |
| platform-conventions | PASS/FAIL | 0 | 0 | 1.8s |
| entity-model | PASS/FAIL | 0 | 0 | 1.5s |
| architecture-principles | PASS/FAIL | 2 | 1 | 2.1s |
| service-layer-patterns | PASS/FAIL | 0 | 0 | 1.9s |
| data-access-patterns | PASS/FAIL | 0 | 0 | 1.7s |
| structural-completeness | PASS/FAIL | 3 | 0 | 1.4s |
| ivs | PASS/FAIL | 0 | 0 | 1.8s |
| nfr | PASS/FAIL | 0 | 0 | 1.6s |
| servicespec | SKIP | - | - | 0.5s |
| solution-summary | PASS/FAIL | 0 | 0 | 1.6s |

**TOTAL:** {X} blocking issues, {Y} warnings

## VALIDATION DECISION

### **{PASSED / BLOCKED}**

{If BLOCKED: Summary of critical issues that must be fixed}

---

## Issues by Validator

### artifact-presence

{issues or "No issues found"}

### market-evidence

{issues or "No issues found"}

... (repeat for each validator)

---

## All Checks

### artifact-presence (ART-*)

| Check ID | Description | Condition | Status |
|----------|-------------|-----------|--------|
| ART-01 | PR_FAQ.md exists | Always | PASS |
| ART-02 | USER_GUIDE.md exists | Always | PASS |
| ART-03 | TEST_SCENARIOS.md exists | Always | PASS |
| ART-04 | DESIGN.md exists (per scope) | Always | PASS |
| ART-05 | IVS.md exists (per scope) | Always | PASS |
| ART-06 | NFR.md exists | Always | PASS |
| ART-07 | ONTOLOGY.jsonld exists | Always | PASS |
| ART-08 | TRACEABILITY.jsonld exists | Always | PASS |
| ART-09 | SOLUTION_SUMMARY.md exists | Always | PASS |
| ART-10 | MARKET_EVIDENCE.md exists | Always | PASS |
| ART-11 | LIFECYCLE_STATE.json exists | Always | PASS |
| ART-12 | UX_PROTOTYPE.md exists in `frontend-web/` | `frontend-web` in resolved scopes | PASS |
| ART-13 | ENTITY_MODEL_DELTA.md exists in `backend/` or root | Classification has entities AND `backend` in scopes | PASS |
| ART-14 | COMPONENT_SPEC.md exists in `frontend-web/` | `frontend-web` in resolved scopes | PASS |

... (repeat for each validator)

---

## Files Reviewed

| File | Validators |
|------|------------|
| LIFECYCLE_STATE.json | artifact-presence, structural-completeness |
| DESIGN.md | platform-conventions, entity-model, architecture, service-layer, data-access, structural |
| USER_GUIDE.md | platform-conventions, architecture |
| ... | ... |
```

---

## Execution Instructions

When this skill activates, execute these steps:

### 1. Identify Feature

```
Determine the feature to validate from:
- User's explicit request: "validate features/compute-provider-resource-details"
- Current context: active feature in conversation
```

### 2. Read Classification

```
Read: features/{feature}/LIFECYCLE_STATE.json
Extract: classification (service, enhancement, infrastructure, etc.)
```

### 3. Spawn All Validators

Use the Task tool to spawn each validator. Run them in parallel for efficiency:

```
Task(
  subagent_type="general-purpose",
  prompt="[Full validator prompt from validators/{name}.md]",
  description="Validator: {name}",
  run_in_background=true
)
```

**Spawn core validators (always):**
1. artifact-presence
2. market-evidence
3. platform-conventions
4. entity-model
5. architecture-principles
6. service-layer-patterns
7. data-access-patterns
8. structural-completeness
9. ivs
10. nfr
11. solution-summary

**Spawn classification-specific validators (conditional):**
12. servicespec (service, extension)
13. servicespec-delta (service_enhancement)
14. extension-delta (extension_enhancement)
15. capability-delta (capability_enhancement)

### 4. Collect Results

Read each validator's output file and parse the JSON response.

### 5. Generate Final Report

Collate all results into the final report format and determine overall status:
- **PASSED**: All validators passed (no blocking issues)
- **BLOCKED**: One or more validators have blocking issues

### 6. Save Report

```
Save to: features/{feature}/reviews/design-validator-{YYYY-MM-DDTHHMMSSZ}.md
```

### 7. Present Results

Show the user:
1. Overall status (PASSED/BLOCKED)
2. Summary table of all validators
3. List of blocking issues that need fixing
4. Location of full report

---

## Reference Documents

Each validator reads specific reference documents:

| Validator | Reference Documents |
|-----------|---------------------|
| platform-conventions | `features/PLATFORM_CONVENTIONS.md` |
| entity-model | `architecture/PLATFORM_ENTITY_MODEL.md` |
| architecture-principles | `architecture/ARCHITECTURE.md` |
| structural-completeness | `methodology templates/feature/DESIGN_TEMPLATE.md` |
| solution-summary | `methodology templates/feature/SOLUTION_SUMMARY_TEMPLATE.md` |

---

## Validator Output Schema

All validators MUST return JSON matching `skills/validators/VALIDATOR_OUTPUT_SCHEMA.md`

---

## Integration with Feature Lifecycle

```
DESIGN Phase Complete
         │
         ▼
┌─────────────────────────────────────┐
│  DESIGN VALIDATOR ORCHESTRATOR      │
│  → Spawns up to 15 parallel validators│
│  → Collates results                 │
│  → Produces unified report          │
│  → Decision: PASSED or BLOCKED      │
└─────────────────────────────────────┘
         │
         │  If BLOCKED → Fix issues → Re-run
         │  If PASSED  → Proceed to GATE 1
         ▼
★★★ GATE 1: Design Approval ★★★
```

---

## Failure Handling

| Scenario | Action |
|----------|--------|
| Validator times out | Mark as FAIL with timeout note |
| Validator returns invalid JSON | Mark as FAIL with parse error |
| Validator crashes | Mark as FAIL with error message |
| Feature folder not found | Abort with error |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.4.0 | 2026-02-24 | **Full validator materialization:** All 15 validator definition files now exist in `validators/`. 13 files created (artifact-presence, market-evidence, platform-conventions, entity-model, architecture-principles, service-layer-patterns, data-access-patterns, ivs, solution-summary, servicespec, servicespec-delta, extension-delta, capability-delta). Skills are thin wrappers; specifications live in validator files. |
| 2.3.0 | 2026-02-24 | **Template enforcement:** 3 conditional artifact checks added (ART-12 UX_PROTOTYPE, ART-13 ENTITY_MODEL_DELTA, ART-14 COMPONENT_SPEC). structural-completeness-validator.md created with STRUCT-01 to STRUCT-10. Classification-gated section enforcement per DESIGN_TEMPLATE.md v3.0.0. ADR-084. |
| 2.2.0 | 2026-01-16 | Added NFR validator for non-functional requirements and platform capability validation (12 validators total) |
| 2.1.0 | 2026-01-11 | Added solution-summary validator (11 validators total) |
| 2.0.0 | 2026-01-11 | Decomposed into 10 parallel validators (added IVS validator) |
| 1.0.0 | 2026-01-01 | Initial monolithic validator |
