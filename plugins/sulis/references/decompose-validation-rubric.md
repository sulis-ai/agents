---
verification_required_from: ""    # ISO-8601 date; filled in by `sulis-change finish` at merge of CH-01KT2B (verification-by-design). Empty string means P-VER applies to every change for which it can resolve `started_at` (the NFR-005 dogfood gate); a filled value gates P-VER on changes whose `started_at` postdates it (the ADR-002 grandfather scope).
platform_contract_required_from: ""    # ISO-8601 date; filled in by `sulis-change finish` at merge of the platform-contract-standard change. Empty string means P-PLAT applies to every change for which it can resolve `started_at`; a filled value gates P-PLAT on changes whose `started_at` postdates it (the ADR-006 grandfather scope, mirroring P-VER's verification_required_from).
---

# Decompose Validation Rubric

<!-- summary -->
This rubric validates SEA's `/sulis:plan-work` output — the set of WPs
and their INDEX — before the decompose skill declares done. It catches
breakdown-stage defects that compound downstream: peer-branch
collisions, atomicity violations, hidden cyclic dependencies, missing
performance constraints, and module-naming jargon. Mirrors the
SDK validation rubric pattern — explicit phases, severity convention,
verdict computation, output report alongside `INDEX.md`.
<!-- /summary -->

> **Version:** 0.5.0
> **Status:** Active — Calibration Period (90 days from 2026-05-22)
> **Applies to:** `/sulis:plan-work` (SEA v0.19.0+). Designed to be invoked
> automatically by the decompose skill at the end of its workflow.
> **Audience:** Agents (or humans) validating a decomposed WP set after
> SEA has produced it.

---

## Purpose

`/sulis:plan-work` produces WP files + INDEX.md from a TDD. The
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

The rubric exists because /sulis:plan-work today relies on author
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
| 7 ServiceSpec compliance (Lovable Test) | ... | ... | ... |
| 8 Cross-WP identifier canonicalisation | ... | ... | ... |
| 9 P-VER (Verification Plan) | ... | ... | ... |
| 10 P-PLAT (Platform Contract) | ... | ... | ... |

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
- [✓] **P6 Peer-collision risk.** Cross-WP file-create scan. <K> collision pairs detected. Shared-fixture scan (6.07): <K> logical-fixture collisions (dir-vs-file normalised) — `wpx-index audit-contracts`.
- [✓] **P7 ServiceSpec compliance.** <N> manifests parsed via `sulis-validate-servicespec`. Lovable Test: <K> manifests PASS, <M> PASS-WITH-RATIONALE, <B> FAIL. Aggregate MUST failures: <count>.
- [✓] **P8 Cross-WP identifier canonicalisation.** <K> cross-WP shared identifiers extracted from WP Contracts. <M> resolve to an authoritative upstream source (TDD section / ADR / instance file). <N> inline identifiers flagged — see /sulis:plan-work step 7c for the remediation path.
- [✓] **P9 P-VER (Verification Plan).** <N> artifacts checked (SRD + TDD + WP set). Section presence: <K> pass / <M> fail. Placeholder scan: <K> pass / <M> fail. Citation presence: <K> pass / <M> fail. Per-WP `verification:` field: <K> pass / <M> fail. Grandfather: <N> grandfathered changes skipped.
- [✓] **P10 P-PLAT (Platform Contract).** <N> WPs scanned for `platform:` / `touch-class:`. Gated write/deploy touches: <K> with a referenced Platform Contract / <M> missing (MUST). Schema-invariant checks (10.03..10.06): <K> pass / <M> fail. Freshness (10.07, SHOULD): <N> claims past 180 days flagged. Grandfather: <N> changes started before `platform_contract_required_from` skipped.
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
| **4.08** | MUST | Cross-kind seam has a data-contract WP (#48 / CF-01 / WP-08.5) | If the set spans ≥2 of backend/frontend/async, a `kind: contract` (data; `contract_type` ≠ visual) WP exists | `wpx-index audit-contracts` |
| **4.09** | MUST | No direct cross-kind dependency edge (#48 / CF-05) | No WP `dependsOn` a WP of a *different* implementation kind — cross-kind deps route through the contract WP (parallel-not-sequential) | `wpx-index audit-contracts` |

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
| **6.06** | MUST | When ≥2 producer WPs emit into the **same logical artifact** (manifest, registry, codegen output), the artifact's identity — filename, path, and merge semantics — is pinned as an **explicit shared constant in the contract WP** they all `dependsOn`. Producers reference the constant verbatim; they do NOT independently choose a filename. (CF-11, anchor #107.) | Scan producer Contracts for shared logical outputs; assert each is sourced from a single named constant declared in the contract WP | Contract parse + cross-WP constant-import audit |
| **6.07** | MUST | When ≥2 WPs `Create` a **test fixture** that resolves to the **same logical name**, they MUST be serialised — one upstream WP authors the fixture and every consumer `dependsOn` it. Two non-dependent WPs that each author the same logical fixture FAIL. **The contract-seam precondition of 6.06 does NOT apply** — this fires for same-kind WPs with no contract between them. **Normalise dir-vs-file forms before comparing**: strip a trailing slash and a single file extension, so `sample-tool-surface/` (dir + manifest) and `sample-tool-surface.json` (flat file) compare EQUAL. Remedy: serialize (add a dep) or hoist a single fixture-authoring upstream WP both consumers `dependsOn`. (#106, anchor CH-01KTRJ.) | Parse each WP's `fixtures_created:` / `**Files created:**` fixture paths; normalise to logical names; FAIL any logical name authored by ≥2 WPs with no dependency between them. Mechanically: `wpx-index audit-contracts` (runs `validate_fixture_collisions`). | Contract parse + `wpx-index audit-contracts` |

Anchor case (`CH-01KTRJ`, fixture-shape-collision lesson #106): during a
parallel build, two non-dependent same-batch WPs each authored the same
logical fixture under divergent conventions — WP-001 created
`tests/fixtures/methodology/sample-tool-surface/` (a directory + a
`manifest.json`) while WP-002 created
`tests/fixtures/methodology/sample-tool-surface.json` (a flat file). No
layer treated a shared fixture as a serialise-or-hoist point, so it only
blew up at bundled-tip CI: the loader silently resolved the directory form,
breaking WP-002's test. This is the SAME structural defect as 6.06
(`#107` — two parallel WPs independently authoring one logical thing) but
with the contract seam removed (test fixtures, same-kind WPs). 6.07 drops
the contract-seam precondition and adds the dir-vs-file normalisation so the
two forms compare equal. Check 6.07 catches this class; `wpx-index
audit-contracts` enforces it mechanically via `validate_fixture_collisions`.

> **Fixture loaders SHOULD fail loud on ambiguous resolution.** A loader
> that finds both a directory form and a flat-file form of the same logical
> fixture SHOULD error rather than silently pick one — defence in depth
> behind 6.07's decompose-time gate. (SHOULD, not built here; 6.07 is the
> primary control.)

---

## Phase 7 — ServiceSpec compliance (the Lovable Test)

The phase that addresses the design-stage **service-contract** failure
mode. Every service the design introduces or modifies must come out
with a paired ServiceSpec manifest at
`.architecture/{project}/service-specs/{name}.servicespec.yaml` (per
the methodology gate in `/sulis:draft-architecture` step 10 and CF-10).
**The Lovable Test is the completeness bar**: an AI agent must be able
to build a working integration against the manifest *with no human docs*.
This phase mechanically checks the manifests against that bar.

Run the mechanical checks via:

```bash
plugins/sulis/scripts/sulis-validate-servicespec --from-manifest <path>
```

Per manifest, the CLI emits `verdict + issues[]` as JSON. Aggregate the
issues into the table below across the full set of manifests in
`service-specs/`. A FAIL on any manifest blocks decompose delivery.

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **7.01** | MUST | Every service named in the TDD has a paired ServiceSpec manifest | Cross-check `service-specs/` dir entries against the TDD's service inventory | Dir listing vs TDD parse |
| **7.02** | MUST | Each manifest is valid YAML and a mapping at the root | `yaml.safe_load` returns a dict | YAML parse |
| **7.03** | MUST | Each manifest declares ≥1 operation | `operations` is a non-empty list | Manifest parse |
| **7.04** | MUST | Every operation has a non-empty `description` | Per-op field check | Manifest parse |
| **7.05** | MUST | Every operation has `user_guide.whenToUse` (string, non-empty) | Per-op field check (also accepts `userGuide`) | Manifest parse |
| **7.06** | SHOULD | Every operation's user_guide also has `prerequisites` and `nextSteps` | Per-op field check | Manifest parse |
| **7.07** | MUST | Every error in the catalog has `httpStatus` (integer) | Per-error field check | Manifest parse |
| **7.08** | MUST | Every error has `user_action` (non-empty) | Per-error field check (also accepts `userAction`) | Manifest parse |
| **7.09** | MUST | Every error has `developer_action` (non-empty) | Per-error field check (also accepts `developerAction`) | Manifest parse |
| **7.10** | SHOULD | Every error declares a `retryable` flag | Per-error field check | Manifest parse |
| **7.11** | MUST | Every entity reference (`dna:entity:X`) resolves to a vendored compiled schema | File existence at `plugins/sulis/brain/compiled/{domain}/{X}.schema.json` | Schema-dir check |
| **7.12** | MUST | Every operation has a `binding` with `host` / `basePath` / `method` / `auth` | Per-op binding field check | Manifest parse |
| **7.13** | MUST | Every operation's `permission` is structurally namespaced (contains `:`) | Permission regex; reject bare names | Manifest parse |
| **7.14** | MAY | Operations declare `leadsTo` for HATEOAS / state navigation | Per-op field check | Manifest parse |

**On scope.** Slice 2 (this phase) is the *mechanical* half of the
Slice 1 design-stage gate. Field shape follows the platform's
**SPEC-006 / Service Registration** spec; tolerant of minor casing
variants (`user_guide` / `userGuide`, `user_action` / `userAction`)
so a SPEC-006 refinement doesn't break the validator. **Slice 3**
will extend the Brain compiler to *emit* the manifest's `entities`
block automatically from the same compiled JSON Schemas the validator
checks against — closing the loop entities-to-services. Until then,
the design author writes the manifest by hand and this phase catches
gaps.

---

## Phase 8 — Cross-WP identifier canonicalisation

Parallel-dispatched WPs that cross-reference a shared identifier
(ULID, slug, version literal, namespace, `dna:*:*` shape) MUST resolve
that identifier through an authoritative upstream source — a TDD
"Canonical Identifiers" section, an `ADR-NN-canonical-identifiers.md`,
an existing instance file the WP set references, or the SRD glossary.
Without an upstream source each executor invents its own value and the
values diverge.

Anchor case (`CH-01KSZ4`, release-train-as-entities wave 1): WP-003
and WP-004 both minted a tenant ULID. WP-004 used a deterministic
`SHA256(name) → Crockford-base32` recipe; WP-003 used a placeholder
pattern. The calling session caught the divergence at the post-train
audit and reconciled WP-003's branch by hand (commit `4360684 fix(release-train):
canonicalise tenant ULID`) before downstream WPs inherited the drift.
The mechanical analog of `/sulis:plan-work` step 7c lives here as
Phase 8.

| ID | Severity | Check | Pass criterion | Evidence |
|---|---|---|---|---|
| **8.01** | MUST | Every cross-WP shared identifier resolves to an authoritative upstream source | For each identifier appearing in ≥2 WP Contracts, find a citation to a TDD "Canonical Identifiers" section, an `ADR-NN-canonical-identifiers.md`, an existing instance file, or the SRD glossary | Contract grep + upstream-source grep |
| **8.02** | MUST | No ULID-shape literal (`01[A-Z0-9]{24}` Crockford-base32) is invented inline in a WP Contract without an upstream source | Scan Contract sections for ULID-shape strings; cross-check each against the upstream-source set | Contract regex + source set membership |
| **8.03** | MUST | No `dna:*:*` or `urn:*:*` identifier appears in ≥2 WP Contracts without an upstream source | Same shape, different prefix pattern | Contract regex + source set membership |
| **8.04** | SHOULD | Each cross-WP shared identifier's upstream source documents its minting recipe (e.g., `SHA256(name) → Crockford base32`) — so a future regenerate produces the same value | Cross-check the upstream source for a "Recipe" / "Derivation" sub-section | Source-section parse |
| **8.05** | SHOULD | Single-WP-scoped identifiers (only one WP references them) carry a `# canonical-source: <reference>` annotation OR are flagged inline as scope-local | Contract grep for annotation; cross-check identifier appears in only one WP | Contract + cross-reference set |
| **8.06** | MAY | Composite WPs that fan out cross-kind dependencies declare the shared identifier set in the parent's Contract | Parent Contract section explicitly lists `shared_identifiers:` | Composite Contract parse |

**Verdict semantics.** A Phase 8 MUST failure is a methodology defect
in the WP set — halt decomposition; route back to
`/sulis:draft-architecture` to add the canonical source (TDD section
or ADR), then restart decompose-validate after the upstream is in
place. A SHOULD failure with rationale (e.g., the upstream source is
implicit from a stable third-party convention) is acceptable; rationale
documented in the report's Recommended improvements section.

**Pass-with-rationale.** An inline identifier MAY pass with rationale
if the WP Contract carries a `# canonical-source: <reference>`
annotation that names the upstream (even an external one, like an
RFC ULID spec); the annotation is the explicit acknowledgement that
the identifier is sourced, not invented.

---

## Phase 9 — P-VER (Verification Plan)

The phase that addresses the **design-time verification gap**: the
methodology refinement (CH-01KT2B) asks the verification questions
at `/sulis:specify`, `/sulis:draft-architecture`, and
`/sulis:plan-work` time, and this rubric check enforces that the
answers exist + have substance + cite the canonical question set
at
[`plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`](standards/VERIFICATION_QUESTIONS.md).

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

**This rubric does not duplicate the question text.** The eight
failure modes below test the *presence and shape* of the answers
each consumer artifact (SRD, TDD, WP) records — the questions
themselves live in the canonical, and consumers cite it by relative
path (NFR-004 single-source-of-truth, MUC-003 defence).

Anchor cases: `release-train` and `discovery` both shipped without
end-to-end verification, surfacing two latent defects post-merge.
P-VER is the mechanical gate that turns *"verification can't be
bolted on at the end"* into an enforceable contract.

### Grandfather sub-phase

Before any 9.01..9.08 check runs, the rubric resolves the
grandfather verdict (per [ADR-002](../../.architecture/verification-by-design/adrs/ADR-002-must-scope-from-merge-date.md)
and [ADR-006](../../.architecture/verification-by-design/adrs/ADR-006-grandfathering-edit-policy.md)):

1. Read the `verification_required_from:` constant from this file's
   YAML front matter. (Filled in by `sulis-change finish` when
   CH-01KT2B merges to `dev`. Empty until then.)
2. Read `started_at` from `.changes/{slug}.yaml` for the candidate
   change.
3. Compare:
   - If `verification_required_from` is **empty** (pre-merge state —
     the dogfood case): run all 9.01..9.08 checks against the live
     artifacts. NFR-005 — the change cannot merge unless its own
     rubric passes against its own artifacts.
   - If `started_at` **precedes** `verification_required_from`:
     return `PASS — grandfathered` and skip all 9.01..9.08 checks.
     A typo fix on a grandfathered change inherits this verdict
     (ADR-006 — edits do not retroactively trigger compliance).
   - If `started_at` is **on or after** `verification_required_from`:
     run all 9.01..9.08 checks.
   - If `started_at` is **missing or unparseable**: fall back to
     "not grandfathered" and apply P-VER normally. A change record
     without a parseable start timestamp cannot prove its
     grandfather eligibility.

The trigger is the change record's `started_at` value, **not** the
lines of code being edited. A new `CH-NNNNNN` created after the
merge date is gated by P-VER even if it patches code shipped by a
grandfathered ancestor (ADR-006 substantial-backfill clause).

### Failure modes

The eight checks below are the Armor pillar's gate-integrity
primitives — one per MUC system response in
[`MISUSE_CASES.md`](../../.architecture/verification-by-design/MISUSE_CASES.md)
and one per failure mode in the TDD's
[Armor pillar table](../../.architecture/verification-by-design/TDD.md).

| ID | Severity | Check | Pass criterion | Source MUC + TDD row |
|---|---|---|---|---|
| **9.01** | MUST | `## Verification Plan` section present in the SRD and TDD under inspection | Regex `^##\s+Verification\s+Plan$` matches in each artifact | (structural — ADR-001 anchors the literal heading) |
| **9.02** | MUST | No placeholder content in any required subsection | Block-list scan (`TBD`, `tbd`, `todo`, `…`, bare blanks) + ≥30 substantive characters per subsection | MUC-001 / TDD Armor row 1 |
| **9.03** | MUST | Subsections answering `n/a` carry a ≥30-character justification on the same line or the next line | Per-subsection scan; bare `n/a` without justification fails | MUC-008 / TDD Armor row 8 |
| **9.04** | MUST | Named `existing` infrastructure paths resolve to real files in the repo | Repo grep against each cited path in the artifact's "Per-integration verification strategy" subsection | MUC-002 / TDD Armor row 2 |
| **9.05** | MUST | The change's `kind:` value has an adapter row in the canonical's kind-to-adapter table | Lookup the change record's `kind:` against `VERIFICATION_QUESTIONS.md` adapter table; fail with the FR-008 verbatim instruction if absent | MUC-007 / TDD Armor row 7 |
| **9.06** | MUST | The artifact contains a literal citation to `VERIFICATION_QUESTIONS.md` | Regex match on the canonical's relative path + the HTML-comment annotation shape (`<!-- VERIFICATION_QUESTIONS source: … vX.Y.Z -->`) | MUC-003 / TDD Armor row 3 |
| **9.07** | MUST | The citation's version is within currency of the canonical's `version` field | Parse canonical's `version:` front-matter value; parse citation's annotation version; fail if more than one minor version behind | MUC-004 / TDD Armor row 4 |
| **9.08** | MUST | Per-WP `verification:` frontmatter present + adapter matches the change's `kind:` | YAML parse of each WP file's frontmatter; the `verification.adapter` value must equal the change `kind:` (or be one of the additional-adapters listed in the WP) | MUC-006 + MUC-007 / TDD Armor rows 6 + 7 |

### Verdict semantics

A Phase 9 MUST failure halts decomposition. The skill reports the
blocking gap to the founder with this exact failure-message shape:

```
P-VER: {check ID} failed for {artifact path}.
Remediation: {one-line action}.
```

Remediation strings are founder-readable (FE-04 — concrete
next-action, no jargon). The intent is that a founder reading the
error knows exactly which file to open and what to add. Sample
remediations the rubric implementation should emit:

- **9.01 failure:** *"Add a `## Verification Plan` heading to
  `<artifact>` and populate the six subsections. Template at
  `plugins/sulis/skills/requirements-templates/SKILL.md` § Verification
  Plan template."*
- **9.02 failure:** *"Subsection '`<name>`' in `<artifact>` is a
  placeholder. Replace `TBD` with a concrete answer of at least 30
  characters — see Q1..Q4 in
  `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`."*
- **9.03 failure:** *"Subsection '`<name>`' answers `n/a` without
  justifying why. Add a sentence explaining why this subsection
  legitimately does not apply (Q9 / Q17 guidance in the canonical)."*
- **9.04 failure:** *"`<artifact>` claims `existing` infrastructure at
  `<path>`, but no file at that path exists in the repo. Either fix
  the path, classify the integration as `deferred` with a canonical
  need identifier, or remove the entry."*
- **9.05 failure:** *"Change `kind: <value>` has no adapter row in
  `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`. Add
  the row via a methodology change (ADR-007), then re-run P-VER."*
- **9.06 failure:** *"`<artifact>` is missing the citation to
  `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`. Add
  the canonical HTML-comment annotation immediately before the
  `## Verification Plan` section."*
- **9.07 failure:** *"`<artifact>` cites `VERIFICATION_QUESTIONS.md
  v<X>.<Y>.<Z>`, but the canonical is now `v<A>.<B>.<C>`. Re-read the
  canonical and update the annotation; check whether any question has
  been added that affects this artifact."*
- **9.08 failure:** *"WP `<file>` is missing the `verification:`
  frontmatter field — or its `adapter:` value (`<got>`) does not match
  the change's `kind:` (`<expected>`). See ADR-003 for the three
  valid shapes (concrete / deferred / trivial carveout)."*

A SHOULD failure does not currently exist in this phase — every
9.01..9.08 check is MUST. A future calibration pass may demote
specific checks to SHOULD if false-positive data warrants (per the
Calibration section below).

**Pass-with-rationale** does not apply to P-VER. The eight checks
are gates, not heuristics; a failure is a real defect or a real
grandfather verdict, never a stylistic preference.

---

## Phase 10 — P-PLAT (Platform Contract)

P-PLAT is the **mechanical enforcement leg** of the defence-in-depth
platform-contract gate. The friendly front leg is the prose in the
`specify` + `draft-architecture` skills (detect a gated third-party
touch, ask for a contract). P-PLAT is the leg that cannot be talked
past: a gated write/deploy third-party touch with no referenced
Platform Contract fails P-PLAT **regardless of any prose edits** —
the control for MUC-004 (a weakened prose gate must not be able to
bypass the rubric). It mirrors P-VER's structure exactly (ADR-006);
where P-VER cites a mechanism, P-PLAT references it rather than
restating it.

See [`../standards/PLATFORM_CONTRACT_STANDARD.md`](../standards/PLATFORM_CONTRACT_STANDARD.md)
for the claim-entry schema (PC-01..08) every stored contract conforms
to; P-PLAT enforces that schema on the contracts a WP set references.

### Detection signal — the `platform:` / `touch-class:` WP-frontmatter field (OAQ-4)

P-PLAT detects a gated third-party touch via an **explicit
WP-frontmatter declaration**, not by scanning prose (brittle and
MUC-004-adjacent). `plan-work` emits the field (see step 7d); P-PLAT
is the authority on its meaning:

```yaml
platform: "<lowercase-hyphenated platform slug>"   # e.g. github-actions
touch-class: "write | deploy | read-only"
```

- A WP set with **any** WP carrying `touch-class: write` or `deploy`
  plus a `platform:` value MUST reference a Platform Contract at
  `plugins/sulis/references/platform-contracts/<platform>.md`, or
  P-PLAT fails.
- `touch-class: read-only` → soft (advisory note, no fail) per
  ADR-001.

### Grandfather sub-phase (before any P-PLAT.NN check)

Read the candidate change's `started_at` and compare against the
`platform_contract_required_from` front-matter constant. A change
started before the constant passes `PASS — grandfathered` (NFR-005).
An empty constant (pre-merge / the dogfood window) runs all checks
against live artifacts. This is the **same mechanism P-VER uses** —
see Phase 9's grandfather sub-phase; P-PLAT does not restate it
(ADR-006).

### Failure-mode checks

One row per contract-integrity control (TDD Armor table A-1..A-8),
each with a deterministic pass criterion:

| ID | Severity | Check | Pass criterion | MUC |
|---|---|---|---|---|
| **10.01** | MUST | Gated write/deploy touch ⇒ a referenced Platform Contract | WP-set scan: any `touch-class: write\|deploy` + `platform: X` ⇒ `platform-contracts/X.md` exists & is referenced | MUC-004 / FR-015 |
| **10.02** | MUST | Contract carries a harness-run reference | Front-matter `harness-run:` (run id) non-empty | MUC-007 / A-8 |
| **10.03** | MUST | Every `inferred: false` claim has source + quote + retrieval-date | Schema-invariant scan of the contract | MUC-001 / A-1 |
| **10.04** | MUST | No `inferred: true` claim carries a `source` | Schema-invariant scan (an inferred claim is not source-backed) | MUC-006 / A-4 |
| **10.05** | MUST | Every `load_bearing: true` claim has probe + probe-result (or a justified `deferred: <id>`) | Schema-invariant scan | MUC-005 / A-6 |
| **10.06** | MUST | `probe-result: confirmed` ⇒ non-empty `probe-evidence` | Schema-invariant scan | MUC-005 / A-6 |
| **10.07** | SHOULD | Claims within the freshness window (retrieval-date ≤ 180 days on reuse) | Date compare; advisory flag | MUC-003 / A-5 |

### Verdict semantics

Any P-PLAT **MUST** failure (10.01..10.06) collapses the verdict to
GAPS_FOUND with the founder-readable remediation:

> *"This change needs a Platform Contract for {platform} before it can
> ship — at `plugins/sulis/references/platform-contracts/{platform}.md`.
> I'll ground one against {platform}'s own docs."*

**Pass-with-rationale** does not apply to P-PLAT, exactly as for
P-VER — the six MUST checks are gates, not heuristics. The SHOULD
check (10.07) is advisory: a stale-claim flag does not fail the
verdict but is surfaced for re-grounding (ADR-006).

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
- **Change Work Standard CW-01..CW-08** — when /sulis:plan-work runs
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
| 0.2.0 | 2026-06-01 | Added Phase 8 — Cross-WP identifier canonicalisation. Anchor case: CH-01KSZ4 release-train wave-1 tenant-ULID divergence between WP-003 and WP-004. Mechanical analog of `/sulis:plan-work` step 7c. |
| 0.3.0 | <date filled at merge> | Added Phase 9 — P-VER (Verification Plan). 8 failure-mode checks (9.01..9.08) + grandfather sub-phase + `verification_required_from:` merge-date constant in front matter. Anchor cases: release-train + discovery dogfood — both shipped without end-to-end verification, surfacing two latent defects post-merge. (CH-01KT2B verification-by-design.) |
| 0.5.0 | 2026-06-10 | Added Phase 6 check 6.07 — shared-fixture collision. Two non-dependent WPs that `Create` a test fixture resolving to the same LOGICAL name FAIL. Drops 6.06's contract-seam precondition (test fixtures, same-kind WPs, no contract between them) and normalises dir-vs-file forms before comparing (strip trailing slash + a single extension, so `sample-tool-surface/` and `sample-tool-surface.json` compare equal). Remedy: serialize (add a dep) or hoist a single fixture-authoring upstream WP. Enforced mechanically by `wpx-index audit-contracts` (`validate_fixture_collisions`), unit + integration tested. Added a SHOULD note that fixture loaders fail loud on ambiguous resolution (defence in depth, not built). Anchor case: CH-01KTRJ / lesson #106 — WP-001 `sample-tool-surface/` (dir+manifest) vs WP-002 `sample-tool-surface.json` (flat file); loader silently resolved the dir form, breaking WP-002's test at bundled-tip CI. |
| 0.4.0 | <date filled at merge> | Added Phase 10 — P-PLAT (Platform Contract). 7 checks (10.01..10.07) — 6 MUST schema/provenance gates + 1 SHOULD freshness flag — + grandfather sub-phase + `platform_contract_required_from:` merge-date constant. Detection via the `platform:` / `touch-class:` WP-frontmatter field (emitted by plan-work). Mechanical enforcement leg of the defence-in-depth platform-contract gate (prose front leg in specify + draft-architecture). Anchor case: the v0.87.0 release broke because a reusable workflow was placed in an unsupported location — a GitHub Actions platform behaviour we assumed instead of grounding (#137). (platform-contract-standard change; ADR-006.) |
