---
id: WP-007
title: Build drift detector script (check-canonical-drift.py) + test suite
status: pending
kind: backend
primitive: create
group: GENERATE
sequence_id: WP-007
dependsOn: [WP-001, WP-002, WP-003, WP-004, WP-005, WP-006]
blocks: [WP-008]
estimated_token_cost:
  input: 8k
  output: 10k
tdd_section: FR-015; Form/Armor/Proof sections of TDD
adrs: [ADR-001, ADR-002]
---

## Context

Builds the canonical-vs-implementation drift detector
(`plugins/sulis/scripts/check-canonical-drift.py`) per FR-015. The
detector is the load-bearing structural defense for Path A — without
it, the canonical degrades to documentation that decays (MUC-009).

The script implements three ports (CanonicalReader, AnnotationParser,
DriftMatcher) and a composition root. Test fixtures cover the four
test scenarios in the TDD's Proof section (pass / missing-step /
extra-annotation / unhandled-failuremode).

Depends on ALL the canonical entity-authoring WPs (WP-001..006)
because the test fixtures use sanitised copies of those canonical
files, and the script is tested against the actual canonical too.

## Contract

### Module structure

```
plugins/sulis/scripts/
  check-canonical-drift.py       # CLI entry + composition root
  _canonical_drift/              # internal package (per marketplace convention)
    __init__.py
    reader.py                    # JsonLdFileReader (CanonicalReader port)
    parser.py                    # YamlCommentAnnotationParser (AnnotationParser port)
    matcher.py                   # StrictDriftMatcher (DriftMatcher port)
    report.py                    # DriftReport dataclass + JSON envelope

plugins/sulis/scripts/tests/unit/
  test_check_canonical_drift.py  # contract + integration tests
  fixtures/canonical_drift/
    fixture_pass/                # canonical + YAML aligned
    fixture_drift_missing_step/  # canonical Step has no YAML annotation
    fixture_drift_extra_annotation/  # YAML annotation has no canonical Step
    fixture_drift_unhandled_failuremode/  # Step references FailureMode that YAML doesn't catch
```

### Public API (CLI)

```bash
$ check-canonical-drift.py --instance-dir <path> --yaml-path <path>
```

Exit codes:
- 0 — all conformance checks pass
- 1 — drift detected (envelope names the gap)
- 2 — script invocation error (missing arg, file not found, malformed canonical)

JSON envelope (stdout):

```json
{
  "ok": false,
  "data": {
    "drift": [
      {"kind": "missing_in_yaml", "step": "preflight-cross-branch-drift"},
      {"kind": "missing_in_canonical", "annotation": "ghost-step"},
      {"kind": "missing_failuremode_handling",
       "step": "open-release-pr",
       "failuremode": "pr-open-but-mergeability-stuck"}
    ]
  }
}
```

### Ports (interfaces — used internally)

Per the TDD's Form section. Implementations live in `_canonical_drift/`.

## Definition of Done

### Red — Failing tests written
- [ ] `test_check_canonical_drift.py::test_jsonld_file_reader_reads_workflow_instance` — happy path
- [ ] `test_check_canonical_drift.py::test_jsonld_file_reader_validates_against_schema` — invalid instance raises with field-path
- [ ] `test_check_canonical_drift.py::test_jsonld_file_reader_reads_steps_returns_list` — Steps list parses
- [ ] `test_check_canonical_drift.py::test_yaml_annotation_parser_finds_canonical_step_comments` — annotations recovered
- [ ] `test_check_canonical_drift.py::test_yaml_annotation_parser_finds_canonical_failuremode_comments` — failuremode annotations recovered
- [ ] `test_check_canonical_drift.py::test_yaml_annotation_parser_ignores_malformed_comments` — `# canonical: foo bar` (no colons) ignored
- [ ] `test_check_canonical_drift.py::test_drift_matcher_all_pass_when_canonical_matches_yaml` — fixture_pass → empty drift, all_passed=True
- [ ] `test_check_canonical_drift.py::test_drift_matcher_reports_missing_in_yaml` — fixture_drift_missing_step → reports the missing Step name
- [ ] `test_check_canonical_drift.py::test_drift_matcher_reports_missing_in_canonical` — fixture_drift_extra_annotation → reports the orphan annotation
- [ ] `test_check_canonical_drift.py::test_drift_matcher_reports_unhandled_failuremode` — fixture_drift_unhandled_failuremode → reports the (Step, FailureMode) pair
- [ ] `test_check_canonical_drift.py::test_cli_exits_0_on_clean` — fixture_pass → exit 0
- [ ] `test_check_canonical_drift.py::test_cli_exits_1_on_drift` — any drift fixture → exit 1
- [ ] `test_check_canonical_drift.py::test_cli_exits_2_on_invocation_error` — missing --instance-dir → exit 2
- [ ] `test_check_canonical_drift.py::test_validates_tool_refs_resolve` — every Step's tool_ref resolves in tools.jsonld
- [ ] `test_check_canonical_drift.py::test_validates_handles_failures_resolve` — every Step's handles_failures entries resolve in failuremodes.jsonld
- [ ] `test_check_canonical_drift.py::test_validates_projects_match_marketplace_json` — Project names appear in marketplace.json plugins[] (MUC-008)

### Green — Implementation makes tests pass
- [ ] `plugins/sulis/scripts/check-canonical-drift.py` exists, executable
- [ ] `_canonical_drift/` internal package authored with three port implementations
- [ ] All 16 tests pass
- [ ] Script invocable from CLI with documented args
- [ ] JSON envelope emitted on stdout (matches every other `sulis-*` script)
- [ ] Cross-reference validations included (tool_ref + handles_failures + Project ↔ marketplace.json)

### Blue — Refactor complete
- [ ] Pure-function discipline — no module-level state
- [ ] Each port adapter is a small class (≤ 100 lines)
- [ ] DriftReport is a frozen dataclass; JSON serialisation centralised
- [ ] No subprocess calls; no network; no env vars (except `--repo-root` arg)
- [ ] Test coverage ≥ 95% (this is a critical structural defense; coverage matters)

## Sequence

- **dependsOn:** WP-001..006 (test fixtures use actual canonical files)
- **blocks:** WP-008 (CI step calls this script)
- **Parallelisable with:** — (this is the longest-path WP; runs alone)

## Estimated Token Cost

- **Input:** ~8k (TDD's drift detector design + all 6 entity files + brain schemas)
- **Output:** ~10k (4-file Python package + 16-test suite + 4 fixture dirs)
- **Total:** ~18k

## Notes

- The script is invoked from CI (WP-008) and locally via `python3 plugins/sulis/scripts/check-canonical-drift.py`. No daemon, no service.
- Test fixtures are tiny synthetic canonical+YAML pairs (not copies of real files). They're easier to reason about and they isolate drift-matcher logic from real canonical content.
- The Tool-existence check (Step's tool_ref resolves in tools.jsonld) is the most expensive validation — runs O(#Steps × #Tools); fine at our scale.
