---
id: WP-009
title: Add `# canonical:step:<name>` + `# canonical:failuremode:<name>` annotations to release-on-merge.yml
status: pending
kind: infra
primitive: extend
group: EXPAND
sequence_id: WP-009
dependsOn: [WP-002, WP-004]
blocks: []
estimated_token_cost:
  input: 3k
  output: 1k
tdd_section: ADR-002; FR-012
adrs: [ADR-002]
---

## Context

Adds inline `# canonical:step:<step-name>` and
`# canonical:failuremode:<failuremode-name>` comments to
`.github/workflows/release-on-merge.yml` per ADR-002. Each existing
step block in the YAML gets one or more annotations naming the
canonical Step it implements + the FailureModes it handles. These
annotations are inert to YAML/Actions parsers but are read by the
drift detector (WP-007) to verify conformance.

Depends on WP-002 (need the canonical Step names) + WP-004 (need
the FailureMode names).

## Contract

For each step block in `release-on-merge.yml` that implements one of
the canonical Steps, add `# canonical:step:<step-name>` immediately
above the `- name:` line. If the same block also recovers from a
FailureMode, add `# canonical:failuremode:<failuremode-name>` on the
next comment line.

Example (annotated):

```yaml
      # canonical:step:compute-next-version
      - name: Compute next version
        id: compute
        if: steps.detect.outputs.skip != 'true'
        run: |
          # ... existing bash unchanged ...

      # canonical:step:wait-for-checks-and-mergeability
      # canonical:failuremode:release-pr-conflicts-with-target-at-merge
      # canonical:failuremode:pr-checks-fail
      # canonical:failuremode:pr-open-but-mergeability-stuck
      - name: Wait for checks
        ...
```

**Annotation rules:**
- One annotation per `# canonical:step:` per step block (no multi-step blocks; if a block implements two canonical Steps, split the block).
- FailureMode annotations are 0..N per block (a step may handle zero or many FailureModes).
- Annotations appear immediately above the `- name:` line, with no blank lines between.
- Annotations are bash comments (YAML doesn't see them as content).

## Definition of Done

### Red — Failing tests written
- [ ] (No new tests; the drift detector itself — WP-007 — IS the test for this WP. The drift detector should pass on the annotated YAML.)
- [ ] In CI: WP-007's drift detector run against `release-on-merge.yml` exits 0 (no drift)

### Green — Implementation makes tests pass
- [ ] Every canonical Step (15 from WP-002) has exactly one `# canonical:step:<name>` annotation somewhere in `release-on-merge.yml`
- [ ] Each Step's `handles_failures` FailureModes have corresponding `# canonical:failuremode:<name>` annotations in the same block
- [ ] No orphan annotations (annotations for Steps/FailureModes that don't exist in canonical)
- [ ] The YAML still parses (existing `test_github_workflows_parse.py` regression covers this)
- [ ] release-on-merge.yml behaviour unchanged (annotations are inert; existing test fixtures still pass)

### Blue — Refactor complete
- [ ] Annotation placement consistent (always immediately above `- name:`)
- [ ] No duplicate annotations
- [ ] If a step block implements multiple canonical Steps → block split into two annotated blocks (atomicity per ADR-002)

## Sequence

- **dependsOn:** WP-002 (canonical Step names), WP-004 (canonical FailureMode names)
- **blocks:** —
- **Parallelisable with:** WP-007, WP-010, WP-011

## Estimated Token Cost

- **Input:** ~3k (current release-on-merge.yml ~300 lines + canonical Step + FailureMode names from WP-002/004)
- **Output:** ~1k (~25 annotation comments added; no other YAML changes)
- **Total:** ~4k

## Notes

- Some canonical Steps may map to MULTIPLE blocks in YAML (e.g.
  `bump-version-files` is the one Step that loops; the YAML has one
  jq call per version_file). For those, ALL the corresponding blocks
  get the `# canonical:step:bump-version-files` annotation — the
  drift detector accepts >1 implementation block per canonical Step
  (multi-binding).
- Conversely, a single YAML block CANNOT carry two distinct
  `# canonical:step:X` annotations — split the block instead.
- This WP is the front-line conformance work: it's what makes the
  canonical "real" against the imperative. If a canonical Step has
  no YAML annotation, the drift detector catches it in WP-008's CI
  step.
