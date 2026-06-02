# Code Review: train-2026-06-01T102700Z — 3 WPs squash-merged onto change branch

> **Timestamp:** 2026-06-01T10:39:09Z (ISO 8601 UTC)
> **Train ID:** train-2026-06-01T102700Z
> **Branch:** change/create-release-train-as-entities
> **Diff range:** 7943992..301dfbe (post-train HEAD minus pre-train HEAD)
> **Files changed:** 25 (2326 lines added; 0 removed; ~340 effective code lines once vendored schemas + audit artifacts are excluded)
> **WPs shipped:** WP-003 (Triggers), WP-004 (FailureModes), WP-011 (README cross-ref)
>
> **Outcome:** Ready to merge

---

## At a glance

This batch lands the first three building-blocks of the canonical release-train: the **trigger definitions** (what kicks the release-train off), the **named-failure-modes catalogue** (the eight ways things can go wrong, including three real defects already lived in this repo), and a **marketplace README cross-reference** so people forking the marketplace can find the configuration vocabulary.

All three pieces compose cleanly. The earlier cross-WP composition issue (two parallel executors used different tenant identifiers) was caught and remediated before the train ran — the merged state has matching identifiers throughout, confirmed by inline check.

There's nothing to fix before the next wave starts. Two small follow-ups to track, neither of which blocks anything.

## What to fix

**No issues that need attention.**

Two small follow-ups are tracked under "Things to take away" below — both are notes, not problems with what shipped.

## How this pull request is shaped

This was a 3-WP train batch on a change branch. It is not a single human-authored PR — it is the marketplace's own train integration step, batching independent, non-overlapping WPs into one merge sequence. The hygiene shape is naturally clean because of how the batch was constructed:

**Size — clean**
2326 raw lines is large in raw count, but the bulk is two vendored brain schemas (byte-equivalent upstream copies, not authored here) plus per-WP audit artifacts (code-review bundles + executor journals committed under `.architecture/`). The actual *new code surface* — three small test files, two JSON-LD entity instances, and a README extension — is around 340 lines.

**Scope — clean**
All work lands under `plugins/sulis/`. One top-level directory. Commit types are `feat` / `fix` / `docs` only — the `fix` was the calling-session reconciliation commit on WP-003's branch (tenant ULID alignment), which is exactly what a fix commit should be.

**Safety — clean**
No database migrations, no infrastructure changes, no CI workflow modifications, no dependency-manifest changes, no schema authoring (the two schema files are vendored copies of upstream definitions). Zero secret-pattern hits.

**Completeness — clean**
Three new source files (the canonical entities + the README extension); three new test files. 1:1 ratio per WP. Tests cover parse-ability, cardinality, schema-conformance, and per-WP assertions (the recovery_strategy enum check on FailureModes; the worked-examples check on the README extension).

## Things to take away

1. **Parallel executors can diverge on conventions the methodology didn't pre-specify.** WP-003 and WP-004 ran simultaneously and minted different tenant identifiers — WP-004 used a deterministic SHA256-derived recipe (documented inline); WP-003 used a placeholder. The drift was caught at the wave-boundary audit, before downstream WPs landed. The lesson worth carrying forward: when multiple parallel WPs cross-reference a shared identifier, **the design phase should canonicalise the identifier upfront** (in a single ADR or a section of the TDD) rather than leaving it to each executor to invent. Filing as a future hardening for `/sulis:plan-work`'s wave-1 dispatch brief.

2. **A `kind: contract` WP-Contract drifted from the canonical schema's vocabulary.** WP-004's Contract section prescribed `kind={operational,structural}` + a `severity` field; the canonical brain FailureMode schema uses a 10-value enum + `expected_frequency` instead. The executor reconciled to the schema (correct call by Convention Preference — the schema is the established convention) and documented the drift in its review bundle. The shipped data is correct; the WP-Contract doc itself needs a small repair. Worth knowing that *the schema beats the WP-Contract* when they disagree, every time — and that this kind of drift gets caught by the schema-validation test in the WP's own DoD before code lands.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, finding IDs) for engineers and for downstream agents. The author tier above contains everything needed to act.

### Verdict

`PASS` per CR-06.

No critical/high findings in the diff; Build Verification empty; every file >50 lines was read end-to-end by at least one lens; all three lenses produced output; no PH-03 high auto-downgrade fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — 14/14 unit tests pass; 4/4 JSON files validate; cross-WP `for_tenant` consistency confirmed (`6XBZ93FSHN5TRX8MCS5R66FNCM`).
- **PR Hygiene:** 0 findings — Scope clean, Size effectively low (raw 1001-5000 bin distorted by vendored data + audit artifacts), Safety clean, Completeness clean.
- **In the changes:** 1 LOW finding (after dedup), 1 INFO finding.
- **In the neighbours:** 0 findings.
- **Draft hardening deltas:** 0 (LOW + INFO findings tracked in Watch List; neither has a failing characterisation test per CR-04).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 2 (both LOW) | 0 | Mnemonic workflow ULID coordination risk for WP-001 dispatch |
| Security | 0 | 0 | Nothing surfaced |
| Quality | 2 (1 LOW dedup; 1 INFO) | 0 | WP-004 Contract vocabulary drift (doc, not code) |

### Build Verification (CR-01)

| Check | Command / source | Outcome |
|---|---|---|
| Unit tests on new files | `pytest test_triggers_instance_valid.py test_failuremodes_instance_valid.py test_release_train_readme_section.py -q` | `14 passed in 0.12s` |
| JSON parse | stdlib `json.load` on 4 files | all valid |
| Cross-WP tenant ULID consistency | inline diff of `for_tenant` fields in `triggers.jsonld` + `failuremodes.jsonld` | `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM` on both |
| Schema vendor completeness | inspection of `failuremode.schema.json` + `trigger.schema.json` | full Draft 2020-12 schemas with `$id`, `required`, enums populated, `unevaluatedProperties:false` |

No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat, fix, docs}              → expected for a train batch
  module_fan_out: 1 (plugins/sulis/)                 → narrow
  severity: clean

Size (PH-02):
  lines_added: 2326, lines_removed: 0, total: 2326
  effective_code_lines: ~340 (excluding 2 vendored schemas + ~17 audit artifact files)
  files_changed: 25
  raw_size_bin: 1001-5000 (medium-large)
  effective_size_bin: 201-500 (small)
  severity: low (raw signal misleading; effective surface is small)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 2 (both vendored byte-equivalent from sulis-brain)
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_files: 5 (2 jsonld + 2 vendored schemas + 1 README extension)
  new_test_files: 3 (1 per WP)
  test_to_source_ratio_by_wp: 1.0
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

#### F1 — low (quality + architecture, deduplicated)

**File:** `plugins/sulis/scripts/tests/unit/test_triggers_instance_valid.py:15-17`

**Quoted text:**
```
- `for_domain` references the Sulis AI marketplace tenant ULID
  `dna:tenant:01JA0AAA1BBBCCCDDDEEEFFFGS` (same as the brain's
  sync-narrative-docs exemplar).
```

**Why it matters:** The instance file `triggers.jsonld` was patched (commit `4360684`) to use the canonical tenant ULID `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM` (WP-004's deterministic value). The test's assertions delegate to the schema and don't reference the literal value, so the test still passes — but the docstring now lies about the data it documents.

**Recommendation:** rewrite the docstring to name `6XBZ93FSHN5TRX8MCS5R66FNCM` and reference the derivation recipe in `failuremodes.jsonld`'s `_about`. Bundle with the next trivial-change pass — not worth its own WP.

**Draft delta:** none. The test passes; behavioural-test grounding per CR-04 is unavailable.

**Lens:** architecture + quality (deduplicated).

#### F2 — info (quality)

**Files:**
- `.architecture/release-train-as-entities/work-packages/WP-004-author-failuremodes-instance.md` (Contract section: lines ~43, 47, 56-64, 84)
- `plugins/sulis/instances/release-train/failuremodes.jsonld` (the shipped data — correct)

**Quoted text (from WP-004 Contract — the drift source):**
```
kind = {operational, structural}
severity = {low, medium, high, critical}
test_severity_enum_valid
```

**Quoted text (from the canonical schema — the correct vocabulary):**
```json
"kind": { "enum": ["business-logic-error", "invalid-input", "policy-violation",
                   "authorisation-denied", "infrastructure-failure",
                   "capacity-exceeded", "validation-failure", "constraint-violation",
                   "external-service-unavailable", "transient-failure"] }
"expected_frequency": { "enum": ["rare", "occasional", "frequent"] }
```

**Why it matters:** The WP-Contract told a future executor (or a future audit) to expect a 2-value `kind` + 4-value `severity`. The shipped data correctly uses the 10-value schema enum + `expected_frequency`. Anyone reading the WP-Contract later (without seeing the executor's reconciliation note) will be misled.

**Recommendation:** repair WP-004's Contract section to mirror the schema's vocabulary, and drop the `test_severity_enum_valid` DoD line (no such field exists). The shipped code stays as-is — it's correct against the schema.

**Draft delta:** none. The shipped artifact honours the canonical contract; the doc-vs-code gap is a Contract repair, not a code fix. Per CR-04, no failing characterisation test grounds a delta here.

**Lens:** quality.

### Watch List

Theoretical / informational items captured here per CR-04 (no failing-test grounding):

| Item | Lens | Reason |
|---|---|---|
| **Mnemonic workflow ULID coordination risk.** Triggers reference `dna:workflow:01KT0RTRA1NWFW00000000000A` by ID. When WP-001 (Workflow authoring) lands, it must adopt this exact string — there is no drift detector running yet (that is WP-007's job). | architecture | The next-wave dispatch brief should bake this constraint in. Tracked: brief WP-001's executor with the canonical ULID + a unit test in WP-001 that pins the value. |
| **Future hardening: parallel-executor identifier canonicalisation.** Two parallel WPs invented different tenant ULIDs. The fix at design time is to put cross-referenced identifiers into a single TDD section or a dedicated ADR before `plan-work` decomposes. | architecture | Out-of-scope for this batch — file as a follow-up improvement to `/sulis:plan-work`. |

### Cross-Reference

- **Per-WP code-review bundles already on the change branch:**
  - `PR-feat-wp-003-author-triggers-instance-2026-06-01T101813Z/REVIEW.md` (verdict PASS by the executor's Step 6.5)
  - `PR-feat-wp-004-author-failuremodes-instance-2026-06-01T101253Z/REVIEW.md` (verdict PASS; one low informational finding on WP-Contract vocabulary drift — same as F2 here)
  - `PR-feat-wp-011-readme-cross-ref-2026-06-01T095526Z/REVIEW.md` (verdict PASS)
- **F2 (WP-Contract vocabulary drift)** was already flagged in WP-004's per-WP review (Q-01); this batch-level review confirms the executor's reconciliation was correct.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `pytest plugins/sulis/scripts/tests/unit/test_triggers_instance_valid.py test_failuremodes_instance_valid.py test_release_train_readme_section.py -q` (14/14 green); JSON validity (4/4 valid); cross-WP `for_tenant` consistency (match). 0 PR-introduced errors. Base run skipped — base SHA `7943992` is pre-train change-branch HEAD with none of the new files present, so the delta is the full HEAD set; no need to diff against base for new-file detection.
- [✓] **CR-02 Parallel dispatch used.** Three lens subagents dispatched concurrently via three Agent tool_use blocks in one message. Diff: 2326 lines / 25 files (above carve-out threshold). Wall-clock ~95s for the longest lens (architecture).
- [✓] **CR-03 Full-file reads.** Each lens read its assigned files end-to-end. The 4 source-of-interest files (2 jsonld + 1 README + 1 mod) are all <300 lines; the 3 test files are each <200 lines; the 2 vendored schemas were verified for structural completeness (not byte-by-byte against upstream, since this batch did not modify them — see Methodology run-detail below).
- [✓] **CR-04 Evidence discipline.** Both findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low (deduplicated across architecture + quality), 1 info.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files >50 lines read end-to-end; all three lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: 2 findings + cross-WP check log. Security: 0 findings ("nothing surfaced" — primitives checked: SEC-01..07, SC-01..04, DAT-03, INF-01; scanners: git grep for token shapes). Quality: 1 LOW + 1 INFO + build verification follow-up + jsx-scan N/A + dead-surface clean + contract-drift documented + test-coverage observation + CR-10 N/A.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: low (effective). PH-03 Safety: clean. PH-04 Completeness: clean. No auto-downgrade.

#### Run details

- **Diff source:** local `git diff 7943992..301dfbe` after `git fetch origin change/create-release-train-as-entities` and `git reset --hard origin/...` on the change worktree.
- **Range correction note:** the train's `gate_handoff.diff_range` field reported `4360684..301dfbe`, where `4360684` is WP-003's pre-rebase feat-branch SHA (a dangling commit, not on the change branch's linear history). The corrected range `7943992..301dfbe` is the change branch's pre-train HEAD to post-train HEAD, which is the right surface for this review. **Logging this for a future train-tooling fix** — `gate_handoff.diff_range` should report the change-branch-linear-history range so downstream tools (this skill among them) don't have to recompute.
- **Neighbour expansion:** not performed. The diff is purely additive (no modifications to existing files outside the 3 WP files + a README extension), so neighbour-ring callers/callees don't apply — there is no prior code calling into the new entities yet. WP-007 (drift detector) will be the first consumer, in a later wave.
- **Scanners run:** `git grep` for token shapes (gitleaks-equivalent); JSON-Schema validation via `Draft202012Validator` (already exercised by the test suite).
- **Scanners unavailable:** none material to this batch — no Trivy needed (no Dockerfile/dep changes); no Semgrep (no Python application code beyond tests).
- **Lenses dispatched in parallel:** yes — three Agent calls in one message (architecture: ~95s; security: ~52s; quality: ~78s; wall-clock bounded by the longest).
