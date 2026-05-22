# Decompose Validation Rubric

<!-- summary -->
This rubric validates SEA's `/sea:decompose` output — the set of WPs
and their INDEX — before the decompose skill declares done. It catches
breakdown-stage defects that compound downstream: peer-branch
collisions, atomicity violations, hidden cyclic dependencies, missing
performance constraints, and module-naming jargon. Mirrors the
SDK validation rubric pattern — explicit phases, severity convention,
verdict computation, output report alongside `INDEX.md`.
<!-- /summary -->

> **Version:** 0.1.0
> **Status:** Active — Calibration Period (90 days from 2026-05-22)
> **Applies to:** `/sea:decompose` (SEA v0.19.0+). Designed to be invoked
> automatically by the decompose skill at the end of its workflow.
> **Audience:** Agents (or humans) validating a decomposed WP set after
> SEA has produced it.

---

## Purpose

`/sea:decompose` produces WP files + INDEX.md from a TDD. The
breakdown is where many downstream pains start:

- **Peer-branch collisions** — two parallel WPs both `Create` the
  same file (e.g., `loader/__init__.py`); the train hits a
  modify/delete or content conflict mid-rebase
- **Atomicity violations** — a WP whose purpose statement contains
  "and" or that touches >20 files; can't be reviewed cleanly, can't
  be rolled back cleanly
- **Hidden cyclic dependencies** — WP-A blocks WP-B but the WP-B file
  also blocks WP-A through a chain; not caught by author audit
- **Missing performance constraints** — request-handler WPs without
  stated SLA; downstream agents can't know what "good" looks like
- **Module-naming jargon** — abbreviations like `auth_mgr` or
  `dep_resolver_v2` that future readers won't decode without insider
  knowledge

This rubric is mechanical where possible (counts, regex, graph
algorithms), judgement where necessary (naming quality, single-
responsibility test). The reviewer agent records each check's verdict
+ evidence in the report.

The rubric exists because /sea:decompose today relies on author
attention. Mechanical checks make the breakdown's quality observable
rather than assumed.

---

## How to use this rubric

### Input the agent needs before starting

- The complete WP set: `.architecture/{project}/work-packages/WP-NNN-*.md`
- The INDEX.md at `.architecture/{project}/work-packages/INDEX.md`
- The source TDD at `.architecture/{project}/TDD.md`
- (Optional) `PRIMITIVE_TREE.jsonld` for primitive-coverage cross-check

The agent reads all WP files end-to-end (analog to CR-03 from the Code
Review Standard — full-file reads for any non-trivial input). Sampling
is forbidden — silent gaps are the failure mode this rubric exists to
prevent.

### Severity convention

Matches the Code Review Standard's severity convention:

| Severity | Meaning |
|---|---|
| **MUST** | Non-negotiable. Failures block decompose delivery; the skill must return to the corresponding step. |
| **SHOULD** | Default. Deviation requires explicit justification in the report's Findings section. |
| **MAY** | Optional. Suggested but not enforced. |

### Output the agent produces

A single Markdown file at
`.architecture/{project}/work-packages/DECOMPOSE_VALIDATION.md` with
the structure below. Mirrors the SDK rubric's output shape.

---

## Verdict

Computed deterministically from check results:

- **PASS** — every MUST passes; no SHOULD failures
- **PASS-WITH-RATIONALE** — every MUST passes; ≥1 SHOULD failure with
  documented rationale
- **FAIL** — ≥1 MUST failure

`FAIL` blocks decompose delivery. The skill reports the blocking gaps
in plain English and returns control to the founder.

---

## Summary

| Metric | Count |
|---|---|
| WPs validated | N |
| Total checks | M |
| PASS | k |
| FAIL (MUST) | b |
| FAIL-WITH-RATIONALE (SHOULD) | s |

---

## Phase-by-phase results

| Phase | PASS | FAIL | Notes |
|---|---|---|---|
| 1 Inventory completeness | ... | ... | ... |
| 2 Atomicity | ... | ... | ... |
| 3 Module naming + clean code | ... | ... | ... |
| 4 Dependency graph correctness | ... | ... | ... |
| 5 Performance + non-functional reqs | ... | ... | ... |
| 6 Peer-collision risk | ... | ... | ... |

---

## Blocking gaps (MUST failures)

Each blocking gap cites: phase, check ID, evidence (WP filename + the
specific line / section / value), and remediation.

---

## Recommended improvements (SHOULD failures)

---

## Detailed findings per check

(Each failing check expanded here with full context.)

---

## Methodology

The validating agent attests:

```markdown
- [✓] **P1 Inventory completeness.** N WPs read end-to-end. Required sections found per WP: Context, Contract, DoD, Sequence, Token cost, Dependencies. Gaps: <list>.
- [✓] **P2 Atomicity.** Purpose statements parsed. Touch surface counted. <K> WPs exceed atomicity bounds.
- [✓] **P3 Module naming.** WP file names + Contract module names scanned for jargon. <K> findings.
- [✓] **P4 Dependency graph.** Built dependency DAG from INDEX.md. Cycles: <count>. Orphans: <count>.
- [✓] **P5 Performance + non-functional.** Per-WP performance-constraint scan. <K> WPs in request-handler primitives without stated SLA.
- [✓] **P6 Peer-collision risk.** Cross-WP file-create scan. <K> collision pairs detected.
```

---

# Phase definitions

## Phase 1 — Inventory completeness

Every WP must have the structural sections that downstream skills
depend on. Missing sections silently produce downstream failures
(executor can't read missing Context; train can't compute eligibility
without Dependencies).

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **1.01** | MUST | Every WP file has a `## Context` section | Regex `^## Context$` present | File grep |
| **1.02** | MUST | Every WP file has a `## Contract` section | Regex `^## Contract$` present | File grep |
| **1.03** | MUST | Every WP file has a `## Definition of Done` section with Red/Green/Blue | Regex `^## Definition of Done`; `Red:`, `Green:`, `Blue:` keywords present | File grep |
| **1.04** | MUST | Every WP file has a `## Sequence` section with Sequence ID | Regex `^## Sequence` + `Sequence ID:` line | File grep |
| **1.05** | MUST | Every WP file has a `## Estimated Token Cost` section | Regex `^## Estimated Token Cost`; numeric estimate present | File grep |
| **1.06** | MUST | Every WP file declares dependencies (may be `dependsOn: []` for foundation WPs) | Regex `dependsOn:` in frontmatter or Sequence section | File grep |
| **1.07** | MUST | INDEX.md lists every WP file in the directory | Set equality between INDEX rows and WP-NNN-*.md files | INDEX parse + dir listing |
| **1.08** | MUST | INDEX.md has a `## Dependency Graph` section (Mermaid or equivalent) | Section header present | INDEX grep |
| **1.09** | SHOULD | Every WP file has a primitive declaration from the 22-primitive catalogue | `primitive:` field present in frontmatter; value in catalogue list | File grep + catalogue cross-check |
| **1.10** | SHOULD | Every WP file's `## Contract` references the TDD section it maps to | Regex `TDD §\d` or `TDD.md#` link present | File grep |

---

## Phase 2 — Atomicity

A WP is the atomic unit of execution. Non-atomic WPs cause: review
fatigue, parallel-batch conflicts, partial-rollback ambiguity.

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **2.01** | MUST | WP purpose statement fits in one sentence with no "and" / "plus" / "also" | Parse the first ≤25 words of `## Context` or frontmatter `purpose:` field; assert no conjunction in the predicate | NLP heuristic + manual confirm |
| **2.02** | MUST | Touch surface ≤ 15 files | Read `Contract` section for the file list; count entries | Contract section parse |
| **2.03** | SHOULD | Touch surface ≤ 8 files | Same | Contract section parse |
| **2.04** | SHOULD | Estimated token cost ≤ 10k | Read `Estimated Token Cost` field | Field parse |
| **2.05** | SHOULD | WP has at most one change-primitive | `primitive:` is a single value; not a comma-separated list | Frontmatter parse |
| **2.06** | MUST | No WP declares "and" in its title | Title regex doesn't contain ` and ` | Title parse |
| **2.07** | MAY | WP's `Definition of Done` has ≤ 5 RGB items | Count items in Red, Green, Blue lists | RGB section parse |

---

## Phase 3 — Module naming + clean code

Module names + WP file names should be discoverable without insider
knowledge. The marketplace's `wpx-` prefix problem (resolved via the
v0.2.0 SDK rename + glossing) is exactly the class this phase catches
at the breakdown stage.

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **3.01** | MUST | WP filenames follow the `WP-NNN-{descriptive-slug}.md` pattern | Regex `WP-[A-Z0-9-]+-[a-z0-9-]+\.md` | Directory listing |
| **3.02** | MUST | No WP file name uses single-letter abbreviations (e.g., `WP-001-AM.md` for auth manager) | Slug part has no 1-2 char tokens unless they're widely-understood (API, URL, ID) | Slug parse |
| **3.03** | SHOULD | WP file slugs are kebab-case and describe the OUTPUT of the WP (`introduce-payments` vs `payments`) | Slug starts with a verb or noun-phrase that's an outcome | Slug grep |
| **3.04** | SHOULD | Module names in `Contract` sections are discoverable (no abbreviations of common terms) | Scan Contract section for module names; cross-check against an abbreviation blocklist (`mgr`, `svc` standalone, `auth_mgr`, `dep_v2`, `_v3`) | Contract grep + blocklist |
| **3.05** | SHOULD | New package directories (per `Contract`) have purpose names that aren't generic (`utils`, `helpers`, `common` standalone) | Scan for these terms in new-package paths | Contract grep |
| **3.06** | MAY | WP file slugs ≤ 6 words | Slug split-by-dash length | Slug parse |
| **3.07** | SHOULD | Module name doesn't include the project's internal jargon prefix (e.g., `wpx-`, `cms_`, `xyz_`) — unless the WP's purpose is explicitly to USE that prefix | Scan against per-project jargon list (configured in INDEX.md `jargon_prefixes:` field if present) | Contract grep |

---

## Phase 4 — Dependency graph correctness

The decomposition's dependency DAG must be acyclic, transitively
consistent, and free of orphans.

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **4.01** | MUST | Dependency DAG has no cycles | Build graph from `dependsOn:` declarations; run cycle-detection (DFS or Tarjan); pass if empty | Graph algorithm |
| **4.02** | MUST | Every `dependsOn:` target exists in the WP set | Resolve each dependency ID; pass if all resolve | Set membership |
| **4.03** | SHOULD | No WP has more than 5 direct dependencies | Count `dependsOn:` entries per WP | Frontmatter parse |
| **4.04** | SHOULD | Transitive-closure depth ≤ 8 | Longest path in the DAG | Graph algorithm |
| **4.05** | SHOULD | No orphan WPs (no incoming or outgoing edges) UNLESS the WP is explicitly a foundation WP | Find isolated nodes; cross-check against `foundation:` flag in frontmatter | Graph + frontmatter |
| **4.06** | MAY | At least one parallelisable batch (multiple WPs at the same DAG level, no shared dependencies) exists | Compute topological levels; assert ≥1 level has ≥2 WPs | Graph algorithm |
| **4.07** | MUST | INDEX.md's Recommended Implementation Order is a valid topological sort | Verify the order respects all `dependsOn` relations | Order check |

---

## Phase 5 — Performance + non-functional requirements

Request-handler-class WPs without stated performance bounds are a
recurring gap. The executor can't optimise what hasn't been specified;
code-review can't flag performance regressions without a baseline.

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **5.01** | SHOULD | Every WP with primitive `add-endpoint`, `add-handler`, `add-service`, `add-route` has a `## Performance` section in its Contract OR a `performance:` frontmatter field | Cross-check primitive vs Performance section presence | Primitive + section parse |
| **5.02** | SHOULD | When stated, performance constraints have a measurable bound (e.g., "p95 latency < 200ms for 1000 records", not "should be fast") | Regex for unit + numeric bound in Performance section | Section parse |
| **5.03** | MAY | WPs touching DB schema have a `## Index Strategy` note or reference to one | Cross-check primitive (`add-schema`, `add-migration`) vs section presence | Section parse |
| **5.04** | MAY | Long-running batch WPs (token cost > 5k) include a stream/pagination/chunking note in the Contract | Token cost gate + section grep | Frontmatter + section parse |
| **5.05** | SHOULD | WPs that consume external APIs declare rate-limit + timeout expectations | Cross-check primitive (`add-integration`, `add-external-call`) vs section presence | Primitive + section parse |
| **5.06** | MAY | WPs that introduce new tables declare expected row count growth | `## Growth Profile` section in Contract | Section parse |

---

## Phase 6 — Peer-collision risk

The phase that directly addresses the `loader/__init__.py` class of
defect: two parallel WPs both `Create` the same file. Without this
check, the train hits the conflict mid-rebase and has to revert
or auto-resolve (poorly).

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **6.01** | MUST | No two WPs `Create` the same file path (across the entire WP set) | Parse `Contract.files.create` lists from each WP; cross-check set intersections; FAIL if any | Contract parse |
| **6.02** | MUST | If two WPs `Modify` the same file AND they're at the same DAG level (parallel candidates), they're flagged for review | Same-level analysis + Contract `files.modify` parse | Graph + Contract parse |
| **6.03** | SHOULD | Shared scaffolding (`__init__.py`, `index.ts`, `mod.rs`) is created by a foundation WP that other WPs depend on; not co-created by peers | Scan for scaffolding files; assert single creator | Contract parse |
| **6.04** | SHOULD | Each WP's `Contract` explicitly distinguishes `files.create` from `files.modify` | Sections structured per the contract template | Contract template check |
| **6.05** | MAY | The Recommended Implementation Order surfaces peer-collision-risk WPs sequentially (not in parallel) | Cross-check 6.01/6.02 results against the order | Order analysis |

---

## Anti-patterns for the validation run itself

The validating agent must NOT:

- **Skip phases** without recording the skip in Methodology with a
  one-line reason
- **Sample WPs** instead of reading the full set — the rubric exists
  because incomplete validation is the failure mode
- **Auto-pass** a check on a "looks fine" judgement when the
  mechanical check would have failed
- **Compute the verdict any way other than the deterministic rule** —
  see Verdict section above

---

## Calibration

CR-10's calibration pattern applies. Each check's pass/fail rate is
recorded during the 90-day window (starting 2026-05-22). Patterns
to watch:

- A check with consistent >50% false-positive rate is over-strict;
  threshold or severity will be tuned in v0.2
- A check that never fires in real runs is either redundant or
  set too loose; reviewed and either tightened or removed
- A real breakdown defect that slipped past this rubric earns a new
  check (with the defect as the anchor case)

The anchor case for v0.1.0 is the platform-repo slice-2 breakdown
where two parallel WPs both created `apps/api/sulis/shared/workflows/loader/__init__.py`. Check 6.01 catches this class.

---

## Composition with other standards

- **Code Review Standard CR-01..CR-10** — this rubric is the
  pre-execution analog to CR's post-execution review. CR catches
  what survived this rubric.
- **Founder English FE-01..FE-11** — the report's verdict + blocking
  gaps sections pass FE-06; the rubric body itself is internal
  taxonomy and lives below an `## At a glance` section in the
  output.
- **Change Work Standard CW-01..CW-08** — when /sea:decompose runs
  inside a change worktree, the validation report lives alongside
  the change's INDEX.md.
- **Critical Thinking Standard** — this rubric is the result of
  applying CTS to decompose's quality risk: MECE phases, primitive
  grounding (each check is atomic + irreducible), balanced
  investigation (anti-patterns section discloses what the rubric
  could miss), falsifiability (90-day calibration window with stop /
  pivot criteria).

## Version history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-05-22 | Initial release. 6 phases. ~30 checks. Anchor case: platform-repo loader/__init__.py collision. |
