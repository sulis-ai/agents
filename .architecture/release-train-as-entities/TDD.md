# TDD — Encode release-train as canonical entities

**Source SPEC:** `../../.specifications/release-train-as-entities/SRD.md`
**Tier:** L (per `SIZING.md`)
**Execution path:** Path A — canonical-as-spec, imperative-as-implementation, drift-detector as bridge
**Structural template:** `sulis-brain/.specifications/business-dna/instances/sync-narrative-docs/`

## Overview

Three deliverables compose this design:

1. **Canonical entity instances** at `plugins/sulis/instances/release-train/`
   — six JSON-LD files (workflow, steps, triggers, failuremodes, projects,
   tools) authored by hand. These are the specification of truth for what
   release-train does.
2. **Drift detector** — a small Python script + CI step that reads the
   canonical instances + parses `release-on-merge.yml`'s annotations and
   fails the build when the imperative diverges from the canonical.
3. **Skill extension** — adding a dry-run-walks-canonical mode to
   `/sulis:release-train` that invokes `/sulis-brain:execute-workflow`
   for the preview (LLM-walked, token-budgeted) while leaving the actual
   ship imperative.

No new runtime, no executor port, no orchestration framework. The brain
ships the executor for the dry-run; release-on-merge.yml continues to be
the implementation; the drift detector is the bridge.

## Source specification

Driven by `SRD.md` (this folder's sibling). Functional coverage: FR-001..016
(four explicit deferrals to v2: FR-010 composition workflow, FR-013
LifecycleRun emission, FR-014 run-record artifact, NFR-004/005).

---

## Form — Structural Design

### Component inventory

| # | Component | Lives at | Kind | LOC estimate |
|---|---|---|---|---|
| 1 | Canonical workflow instance | `plugins/sulis/instances/release-train/workflow.jsonld` | JSON-LD entity | ~80 |
| 2 | Canonical steps instance | `plugins/sulis/instances/release-train/steps.jsonld` | JSON-LD entity (15 Steps) | ~400 |
| 3 | Canonical triggers instance | `plugins/sulis/instances/release-train/triggers.jsonld` | JSON-LD entity (2 Triggers) | ~30 |
| 4 | Canonical failuremodes instance | `plugins/sulis/instances/release-train/failuremodes.jsonld` | JSON-LD entity (7 FailureModes) | ~120 |
| 5 | Canonical projects instance | `plugins/sulis/instances/release-train/projects.jsonld` | JSON-LD entity (4 Projects) | ~80 |
| 6 | Canonical tools instance | `plugins/sulis/instances/release-train/tools.jsonld` | JSON-LD entity (~17 Tools; primaries fully populated, rest stubbed) | ~250 |
| 7 | Drift detector script | `plugins/sulis/scripts/check-canonical-drift.py` | Python module + CLI entry | ~200 |
| 8 | Drift-detector tests | `plugins/sulis/scripts/tests/unit/test_check_canonical_drift.py` | Pytest | ~250 |
| 9 | CI step | `.github/workflows/branch-ci.yml` (modification) | YAML | ~15 |
| 10 | YAML annotations | `.github/workflows/release-on-merge.yml` (modification) | YAML comments (`# canonical:step:<name>` per step block) | ~25 (annotations only) |
| 11 | Skill extension | `plugins/sulis/skills/release-train/SKILL.md` (modification) | Markdown prose | ~40 added |
| 12 | Configuration Vocabulary cross-ref | `plugins/sulis/README.md` (modification) | Markdown prose | ~20 added |

**Total new code/content:** ~1,500 lines (mostly JSON-LD entity data).

### Module boundaries + dependency graph

```
                  [SOURCE OF TRUTH]
                          │
            ┌─────────────┴────────────────┐
            │                              │
            ▼                              ▼
plugins/sulis/instances/release-train/   (read by)
  ├── workflow.jsonld                     │
  ├── steps.jsonld                        │
  ├── triggers.jsonld                     ├──► check-canonical-drift.py
  ├── failuremodes.jsonld                 │     │
  ├── projects.jsonld                     │     │ (called by)
  └── tools.jsonld                        │     ▼
                          │               │   .github/workflows/branch-ci.yml
                          │               │     (drift-detector step at PR time)
                          │               │
                          │               └──► /sulis-brain:execute-workflow
                          │                     (LLM-walked, dry-run preview)
                          │                     │
                          │                     │ (called by)
                          │                     ▼
                          │                   /sulis:release-train --dry-run
                          │
                          └──(conforms to, via annotations)──►
                              .github/workflows/release-on-merge.yml
                                (imperative implementation; unchanged
                                 behaviour; gains `# canonical:step:<name>`
                                 annotations only)
```

The canonical is the apex. Three consumers: (a) the drift detector
validates conformance; (b) execute-workflow walks it for the preview;
(c) the YAML implements it (verified via the drift detector).

### Ports (interfaces — drift detector module)

```python
# Port 1 — read canonical entity instances
class CanonicalReader(Protocol):
    def read_workflow(self, instance_dir: Path) -> dict: ...
    def read_steps(self, instance_dir: Path) -> list[dict]: ...
    def read_failuremodes(self, instance_dir: Path) -> list[dict]: ...
    # ... triggers / projects / tools

# Port 2 — parse YAML annotations from release-on-merge.yml
class AnnotationParser(Protocol):
    def parse(self, yaml_path: Path) -> list[YamlAnnotation]: ...

# Port 3 — match Steps to YAML annotations + return drift report
class DriftMatcher(Protocol):
    def match(
        self,
        canonical_steps: list[dict],
        canonical_failuremodes: list[dict],
        yaml_annotations: list[YamlAnnotation],
    ) -> DriftReport: ...

# DriftReport carries:
#   - missing_in_yaml: list[StepName]       # Step in canonical, no annotation in YAML
#   - missing_in_canonical: list[StepName]  # Annotation in YAML, no Step in canonical
#   - missing_failuremode_handling: list[(StepName, FailureModeName)]
#   - all_passed: bool
```

### Adapters (concrete implementations)

| Adapter | Implements | Backed by |
|---|---|---|
| `JsonLdFileReader` | `CanonicalReader` | `json.load` of each `.jsonld` file; jsonschema validation against vendored compiled schemas at `plugins/sulis/brain/compiled/foundation/`. |
| `YamlCommentAnnotationParser` | `AnnotationParser` | Line-scan for `# canonical:step:<name>` comments + their immediate-next non-comment line for context. PyYAML for validating the file parses as YAML first. |
| `StrictDriftMatcher` | `DriftMatcher` | Set-difference matcher; reports both directions of mismatch; reports unhandled FailureModes per Step. |

### Composition root

`plugins/sulis/scripts/check-canonical-drift.py main()`:

```python
def main() -> int:
    args = parse_args()  # --instance-dir, --yaml-path
    reader = JsonLdFileReader()
    parser = YamlCommentAnnotationParser()
    matcher = StrictDriftMatcher()

    workflow = reader.read_workflow(args.instance_dir)
    steps = reader.read_steps(args.instance_dir)
    failuremodes = reader.read_failuremodes(args.instance_dir)
    annotations = parser.parse(args.yaml_path)
    report = matcher.match(steps, failuremodes, annotations)

    print_json_envelope(report)
    return 0 if report.all_passed else 1
```

JSON envelope (matches every other `sulis-*` CLI):

```json
{
  "ok": false,
  "data": {
    "drift": [
      {"kind": "missing_in_yaml", "step": "preflight-cross-branch-drift"},
      {"kind": "missing_failuremode_handling",
       "step": "open-release-pr",
       "failuremode": "pr-open-but-mergeability-stuck"}
    ]
  }
}
```

---

## Armor — Operational Hardening

### External dependencies

| Dependency | Where used | Resilience policy |
|---|---|---|
| `jsonschema` (compiled schemas at `plugins/sulis/brain/compiled/foundation/`) | `JsonLdFileReader.read_*` validates each instance | No network call. On schema-validation failure: drift detector exits with `{"ok": false, "error": "..."}` and CI fails. The canonical files MUST be valid before drift checking can proceed. |
| `PyYAML` (already in marketplace's `pyproject.toml`) | `YamlCommentAnnotationParser.parse` | No network call. On YAML parse failure: drift detector exits with `{"ok": false, "error": "release-on-merge.yml fails to parse"}`. The CH-01KSYZ regression test (workflow YAML parses) is already in place; this is a second line of defense. |

No retries / timeouts / circuit-breakers — the drift detector is a pure
local function. No network, no subprocess (except `python3 -c` to invoke
itself; trivial).

### Security boundary

Drift detector runs in CI (`branch-ci.yml`) on every PR. It is **read-only**
— it does not modify any file. It cannot be exploited to alter state.

The annotations in `release-on-merge.yml` are YAML comments — inert to
YAML parsers and to GitHub Actions. Adding/changing annotations cannot
change the workflow's behaviour; it only changes what the drift detector
sees.

### Secrets

No secrets in the drift detector path.

### Observability

The drift detector emits a JSON envelope; CI surfaces the failing
annotations + missing FailureMode handlings in the failed build log.
A founder reading the build failure sees plain English (per
NFR-006):

> *"Drift detector: Step 'preflight-cross-branch-drift' in canonical
> has no corresponding `# canonical:step:preflight-cross-branch-drift`
> annotation in `release-on-merge.yml`. Either update the canonical or
> add the annotation."*

### Armor primitives, MUC-by-MUC

| MUC | Armor primitive | Implementation |
|---|---|---|
| MUC-002 (workflow updated, YAML not) | Drift detector at PR time | Components 7-9 above |
| MUC-003 (Tool impl changes, schema doesn't) | Tool versioning in entity instance + schema-validated tests | Tool entity's `version` field is bumped manually when implementation_detail diverges; drift detector checks for version-coordination |
| MUC-005 (stale Tool catalogue) | Tool-existence precondition | Drift detector additionally asserts every Step's tool_ref resolves in the tools.jsonld instance |
| MUC-006 (probabilistic Step burns token budget) | Token budget on Step 5; FailureMode `probabilistic-step-token-budget-exceeded` | Encoded in steps.jsonld; LLM dry-run path honours via execute-workflow agent's budget-tracking (already in brain) |
| MUC-007 (founder gate skipped) | mechanism=human Step cannot be auto-skipped | Encoded in steps.jsonld (Step 8 mechanism=human); the LLM dry-run path respects this per brain's execute-workflow discipline |
| MUC-008 (Project ↔ marketplace.json inconsistent) | `validate-projects` precondition | Added as a drift-detector subcheck: every Project.name appears in marketplace.json's `plugins[]`; mismatch fails |
| MUC-009 (silent imperative drift) | Drift detector (load-bearing) | Same as MUC-002 |
| MUC-010 (fork-consumer Project authoring) | Configuration Vocabulary section + worked examples | SRD already covers; this design points the marketplace README at it |
| MUC-011 (abstracting on n=1) | Discipline: hand-author all 4 marketplace Projects; defer `project-discovery` | Reinforced by ADR-NN-004 (hand-author Projects in v1) |

Two MUCs (-001 coercive prompt style, -004 dispatch failure isolation)
are out-of-scope or deferred per the SRD.

---

## Proof — Verification Protocol

### Contract tests per port

**`CanonicalReader` (port 1):**
- Reads each of the 6 entity types from a known-good fixture.
- Validates each against the vendored compiled schema (jsonschema).
- Invalid instance → raises with the field-path of the violation.

**`AnnotationParser` (port 2):**
- Parses `# canonical:step:<name>` annotations from a fixture YAML.
- Returns one `YamlAnnotation` per matched comment + its line number.
- Malformed annotation (e.g. `# canonical: step open-release-pr` without colons) → ignored cleanly.

**`DriftMatcher` (port 3):**
- All Steps annotated + all FailureModes handled → `all_passed=True`, empty drift list.
- One Step missing annotation → reports `missing_in_yaml`.
- One annotation without canonical Step → reports `missing_in_canonical`.
- One Step references a FailureMode in `handles_failures` that has no recovery path in the YAML → reports `missing_failuremode_handling`.

### Integration tests (the load-bearing ones — FR-015 acceptance)

`tests/unit/test_check_canonical_drift.py` ships with fixture canonical
+ YAML pairs covering:

- **`fixture_pass/`** — canonical Steps fully annotated; FailureModes
  handled. Drift detector exits 0.
- **`fixture_drift_missing_step/`** — one canonical Step has no
  matching annotation in YAML. Drift detector exits 1; envelope names
  the missing Step.
- **`fixture_drift_extra_annotation/`** — YAML has an annotation for a
  Step that isn't in canonical. Drift detector exits 1; envelope names
  the orphan annotation.
- **`fixture_drift_unhandled_failuremode/`** — a Step lists a FailureMode
  in `handles_failures` that the YAML doesn't catch. Drift detector
  exits 1.

The `fixture_pass` shape is also used as the v1 sanity check: the
canonical instances we author for this change + the actual
`release-on-merge.yml` (with annotations added) MUST pass.

### Chaos tests

Not applicable (drift detector is a pure local function — no network,
no subprocess, no state).

---

## Trade-offs

| Decision | Chosen | Rejected | One-line reason |
|---|---|---|---|
| Execution strategy | Path A (canonical-as-spec + imperative + drift detector) | Path B (LLM walks at every release); Path C (build deterministic runner) | Path B is too slow + token-heavy for high-frequency releases; Path C is new build that doesn't ship in v1 (ADR-NN-001) |
| Annotation format | Inline `# canonical:step:<name>` comments | Sidecar `canonical-map.json` | Annotations live next to the step they describe (less indirection; one source of truth for the binding) (ADR-NN-002) |
| Drift-detection matching | Annotation-driven | Structural / pattern-matching on bash content | Pattern-matching bash is fragile (refactors break the check); annotations are explicit (ADR-NN-002) |
| Tool minting fidelity | Hand-author primaries fully; stub rest | Stub all; full-populate all | Stub all loses validation surface for primaries; full-populate violates L13 (over-investment on n=1) (ADR-NN-003) |
| Project instances | Hand-author 4 marketplace plugins | Build a discovery workflow now | L13 (don't abstract on n=1); discovery becomes its own sibling change when n=2 evidence accumulates (ADR-NN-004) |
| Composition workflow | DEFERRED to v2 | Include marketplace-release Workflow with workflow_dispatch | Requires Path C deterministic runner; release-on-merge.yml's existing iteration handles cross-Project today |

---

## Open questions

1. **Annotation placement convention.** Place the annotation
   *immediately above* the step block, or *inside* the step block as a
   `name: "Foo  # canonical:step:bar"` suffix? Recommendation: above
   (visually grouped; doesn't pollute step names). Locked in
   ADR-NN-002.
2. **Schema version coordination.** When brain bumps a foundation
   entity schema (e.g. Step v1.2.0 → v1.3.0), the marketplace's
   vendored copy + the canonical instances must update in lockstep.
   This is an existing brain-vendored-schemas discipline; called out
   here for completeness, not solved here.
3. **Marketplace plugin descriptions.** The Project entity has a
   `description` field; the marketplace.json entry also has a
   `description`. Should they be coordinated by a derived-artifact-like
   process? Defer to v2 (DerivedArtifact entity exists per DR-019 but
   v1 doesn't formalise CHANGELOG/Release-notes provenance).

### Reserved-Vocabulary Sweep

Proposed abstracts: `DriftReport`, `YamlAnnotation`, `CanonicalReader`,
`AnnotationParser`, `DriftMatcher`.

Checked against the marketplace's existing reserved-vocabulary hint —
none of these names collide with YAML kinds in use (no `Drift`,
`Annotation`, `Reader`, `Matcher` in the repo's k8s/Sulis dispatch
keys). No GLOSSARY collisions (all new terms).

**Sweep result:** 5 abstracts checked / 0 collisions found.

---

## Sizing Report

See `SIZING.md` for the full sFPC + ASR breakdown. Highlights:

- **Tier:** L (computed; not overridden)
- **TDD length:** ~340 lines (target: ≤ 400, satisfied)
- **ADRs produced:** 4 (target: 4-8, satisfied)
- **Pillar coverage applied:** Form = PARTIAL (template inherited from
  sync-narrative-docs); Armor = PARTIAL (brain ships FailureMode discipline);
  Proof = UNCOVERED (fully specified here)
- **Authoritative sources referenced:** SRD, brain v0.9.0 foundation
  schemas, sync-narrative-docs worked example
- **Sections that referenced rather than restated:** entity schemas
  (brain), execute-workflow agent contract (brain), FailureMode
  recovery_strategy enum (brain)
- **Circuit breakers triggered:** none (pure-local script)
- **Reserved-Vocabulary Sweep:** 5 abstracts checked / 0 collisions /
  0 renames / 0 shared-dispatch ADRs
