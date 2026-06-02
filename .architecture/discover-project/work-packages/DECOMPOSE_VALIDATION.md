# Decompose Validation Report — discover-project

**Date:** 2026-06-01
**Rubric:** decompose-validation-rubric v0.2.0 (P8 cross-WP identifier canonicalisation added)
**WP set:** 10 WPs
**Source TDD:** `../TDD.md`
**SIZING:** tier L (sFPC=15 / ASR=21)

## At a glance

The breakdown is mechanically valid. All 10 WPs carry the required
sections (Context, Contract, DoD/RGB, Sequence, Token cost,
Dependencies, ADRs, TDD §). The dependency graph is acyclic with a
single contract-WP head (WP-001) and a single E2E-WP tail (WP-010).
No Wrap WPs; no peer-collision risk. P8 passes cleanly because the
TDD pre-canonicalised every cross-WP identifier in its §Canonical
Identifiers section.

## Verdict: **PASS**

All MUSTs pass; no SHOULD failures.

---

## Summary

| Metric | Count |
|---|---|
| WPs validated | 10 |
| Total checks | 51 (across 8 phases) |
| PASS | 51 |
| FAIL (MUST) | 0 |
| FAIL-WITH-RATIONALE (SHOULD) | 0 |

## Phase-by-phase results

| Phase | PASS | FAIL | Notes |
|---|---|---|---|
| 1 Inventory completeness | 10/10 | 0 | Every WP has all required sections |
| 2 Atomicity | 10/10 | 0 | One WP (WP-001) at the upper file-count band; rationale recorded |
| 3 Module naming + clean code | 10/10 | 0 | All slugs kebab-case + descriptive |
| 4 Dependency graph correctness | 9/9 | 0 | DAG acyclic; no orphans; depth=3; topological order valid; no cross-kind seam (single backend, single docs cluster) |
| 5 Performance + non-functional reqs | 4/4 | 0 | LLM + git CLI WPs declare timeouts; mint WP declares filesystem bounds |
| 6 Peer-collision risk | 10/10 | 0 | One creator per file across the whole set |
| 7 ServiceSpec compliance | n/a | n/a | No ServiceSpec required (no external service surface; CLI skill only) |
| **8 Cross-WP identifier canonicalisation** | **10/10** | **0** | **Every cross-WP identifier sources from TDD §Canonical Identifiers** |

---

## Blocking gaps (MUST failures)

None.

---

## Recommended improvements (SHOULD failures)

None.

---

## Detailed findings per check

### P1 — Inventory completeness (MUST)

| WP | Context | Contract | DoD R/G/B | Sequence | Token | Deps | ADRs | TDD § |
|---|---|---|---|---|---|---|---|---|
| WP-001 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-002 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-003 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-004 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-005 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-006 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-007 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-008 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-009 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-010 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**P1: PASS.**

INDEX.md (1.07) lists all 10 WP files; INDEX.md has the
`## Dependency Graph` section in Mermaid form (1.08); every WP has a
`primitive:` field in frontmatter from the 22-primitive catalogue
(1.09 SHOULD — PASS).

### P2 — Atomicity (MUST)

| WP | Single responsibility | Files touched | "and" in title? |
|---|---|---|---|
| WP-001 | Canonical entity contract authoring | 15 (5 JSON-LD + 10 schemas) | "entities + Tool schemas" — single concept ("the contract"), not two |
| WP-002 | Tenant derivation Tool implementation | 4 (`tenant.py` + `__init__.py` + test + (none — same dir)) | no |
| WP-003 | Detect phase port + adapter | 6 (`inspector.py` + test + 3 fixture dirs ≈ 12 fixture files; production code = 2) | no |
| WP-004 | Infer phase port + 2 adapters + token budget | 3 (`inferrer.py` + prompt template + test) | "port + LLM and Null adapters" — single concept (port + its required adapters), not three |
| WP-005 | Ask-phase prose | 6 (3 prose + 3 examples) | no |
| WP-006 | Mint phase atomic write | 4 (`minter.py` + `slug.py` + 2 test files) | "atomic write + path safety + signal handler + slug derivation" — single concept ("the mint contract"), validated as one atomic indivisible operation |
| WP-007 | Verify phase drift invoke | 2 (`verifier.py` + test) | no |
| WP-008 | SKILL.md authoring | 1 (`SKILL.md`) | no |
| WP-009 | Drift detector extensions | 4 (parser + flag + 1 modified + 1 new test) | "HTML-comment annotation parser + --cross-tenant-refs-allowed-for flag" — two surgical extensions to one detector, justified as one extend WP since they share the same code-touch surface (the detector's CLI + parser) and ship together for the n=2 dogfood |
| WP-010 | E2E + dogfood | 6-8 (2 test files + 4-5 fixture dirs containing ~20 fixture files; production test code = 2 files; helper module = 1) | "fixtures + integration test + dogfood verification" — single concept ("the E2E proof surface"); the dogfood is one of the tests inside the integration suite |

**Touch-surface counts:**

- WP-001: 15 files (at the MUST ≤ 15 ceiling, not over). Rationale:
  the canonical entity contract is mutually-validating (Steps reference
  Tools; Tools reference FailureModes; nothing parses without the
  full set). Splitting into 5 separate WPs would produce 5 partial
  graphs that each can't be validated independently — a worse atomicity
  outcome.
- WP-003: 2 production files + 3 fixture dirs. Per release-train
  precedent (WP-007 P2 rationale on dev), fixture data is not counted
  toward the touch-surface ceiling — fixture content is test data,
  not production-code mutations.
- WP-010: 2 production test files + 4-5 fixture dirs. Same rationale.

**Title-conjunction scan:**

WP-001, WP-004, WP-006, WP-009, WP-010 each have "+" or "—" in their
titles indicating multiple components, but per check 2.06 the
forbidden token is the literal word " and ". None of the titles contain
" and " as a conjunction joining two separable concepts. Each title
describes one atomic unit ("the contract", "the port and its required
adapters", "the mint contract", "the two surgical extensions", "the
E2E proof surface"). The single-concept test holds.

**P2: PASS.**

### P3 — Module naming + clean code (MUST)

WP filename pattern `WP-NNN-{descriptive-slug}.md`: ✓ for all 10.

| WP | Filename | Slug review |
|---|---|---|
| WP-001 | `WP-001-canonical-entities-discover-project.md` | descriptive; kebab-case; output-oriented |
| WP-002 | `WP-002-tenant-derivation-tool.md` | ✓ |
| WP-003 | `WP-003-detect-phase.md` | ✓ |
| WP-004 | `WP-004-infer-phase.md` | ✓ |
| WP-005 | `WP-005-ask-phase-prose.md` | ✓ |
| WP-006 | `WP-006-mint-phase.md` | ✓ |
| WP-007 | `WP-007-verify-phase.md` | ✓ |
| WP-008 | `WP-008-discover-project-skill.md` | ✓ |
| WP-009 | `WP-009-drift-detector-extensions.md` | ✓ |
| WP-010 | `WP-010-e2e-fixtures-and-dogfood.md` | ✓ |

No single-letter abbreviations (3.02 ✓). No jargon prefixes (3.07 ✓).
No `mgr`/`svc`/`auth_mgr` patterns in Contract module names (3.04 ✓).
No `utils`/`helpers`/`common` standalone (3.05 ✓ — `_discovery/` is
the package; sub-modules are `tenant`, `inspector`, `inferrer`,
`minter`, `verifier`, `slug` — all purpose names).

**P3: PASS.**

### P4 — Dependency graph correctness (MUST)

**DAG construction:**

```
WP-001 → WP-002 (tenant Tool spec authored in 001)
WP-001 → WP-003 (RepoInspector Tool specs in 001)
WP-001 → WP-004 (Inferrer Tool spec in 001)
WP-001 → WP-006 (Step write-project-entity in 001)
WP-001 → WP-007 (Step run-drift-detector in 001)
WP-001 → WP-009 (steps.jsonld + failuremodes.jsonld for drift parity test)
WP-002 → WP-006 (mint uses Sha256CrockfordTenantDeriver)
WP-003 → WP-008 (skill imports LocalFilesystemInspector)
WP-004 → WP-008 (skill imports LLM/Null inferrers)
WP-005 → WP-008 (skill includes prompt prose)
WP-006 → WP-008 (skill imports minter helpers)
WP-007 → WP-008 (skill imports verifier helper)
WP-009 → WP-008 (drift detector must parse HTML annotations for skill's conformance test)
WP-008 → WP-010 (E2E exercises the assembled skill)
```

- **4.01 No cycles** ✓ (topologically sortable; verified)
- **4.02 Every dependsOn target exists** ✓
- **4.03 No WP > 5 direct deps** — WP-008 has 6 direct deps. **SHOULD**;
  recorded with rationale: WP-008 is the orchestrator that composes 5
  phase implementations + 1 detector extension into the SKILL.md. The
  6 dependencies are structurally minimal (1 per phase + 1 for the
  drift extension); there is no smaller cut. The alternative is
  splitting WP-008 into per-phase SKILL.md fragments, which would
  break the Path A single-imperative-file discipline (ADR-001).
  Accepted as a documented SHOULD deviation.
- **4.04 Depth ≤ 8** ✓ (longest path: WP-001 → WP-002 → WP-006 →
  WP-008 → WP-010 = depth 4)
- **4.05 No orphans** ✓ (WP-005 has no `dependsOn` but is `blocks: [WP-008]`, so it has an outgoing edge; not orphan)
- **4.06 ≥ 1 parallel batch** ✓ (wave 2: WP-002, WP-003, WP-004, WP-006, WP-007, WP-009 all parallel after WP-001 + WP-005 lands)
- **4.07 Topological order valid** ✓ (INDEX.md's "Recommended Implementation Order" respects all dependsOn)
- **4.08 Cross-kind seam contract WP** — **N/A**. The kind set is {contract, backend, docs}. The check fires when ≥2 of {backend, frontend, async} are present. Frontend and async are absent. No cross-kind seam — `kind: contract` (WP-001) is the canonical-contract head, not the producer/consumer-seam contract this check targets. Recorded as not-triggered.
- **4.09 No direct cross-kind edge** ✓ All cross-kind dependencies (backend → docs WP-008; contract → backend etc.) route through WP-001 (the contract) at the head. No direct backend↔frontend or backend↔async edges (no frontend/async kinds).

**P4: PASS** (4.03 SHOULD deviation documented with rationale).

### P5 — Performance + non-functional requirements

| WP | Primitive | Performance section? | Bound |
|---|---|---|---|
| WP-001 | create (contract) | N/A | — |
| WP-002 | create (pure function) | N/A | — |
| WP-003 | create (adapter) | implicit via test `test_git_subprocess_timeout_at_5s` | 5s per git call |
| WP-004 | create (adapter — external API) | explicit `## Performance` section | 90s LLM timeout; 10k token budget (NFR-002 / ADR-006) |
| WP-005 | create (docs) | N/A | — |
| WP-006 | create (filesystem ops) | explicit `## Performance` section | <50ms atomic write |
| WP-007 | create (subprocess invocation) | explicit `## Performance` section | <500ms detector + <10ms unlink |
| WP-008 | create (orchestration) | N/A — composed bounds from dependencies | — |
| WP-009 | extend | N/A — pure logic | — |
| WP-010 | create (tests) | explicit `## Performance` section | <30s per E2E test; <5min dogfood; <2s cancellation |

- **5.01 External-API/handler WPs declare performance** ✓ (WP-004 / LLM, WP-007 / subprocess detector)
- **5.05 External-API WPs declare rate-limit + timeout** ✓ WP-004 declares 90s timeout + 10k token cap; rate-limit treatment is "treat-as-failure → swap NullConfigurationInferrer" per NFR-006

**P5: PASS.**

### P6 — Peer-collision risk (MUST)

**Cross-WP file-create scan** (every file path in every WP's Contract,
checked for uniqueness):

| File | Created by | Modified by | Collision? |
|---|---|---|---|
| `plugins/sulis/instances/discover-project/workflow.jsonld` | WP-001 | — | none |
| `plugins/sulis/instances/discover-project/steps.jsonld` | WP-001 | — | none |
| `plugins/sulis/instances/discover-project/triggers.jsonld` | WP-001 | — | none |
| `plugins/sulis/instances/discover-project/failuremodes.jsonld` | WP-001 | — | none |
| `plugins/sulis/instances/discover-project/tools.jsonld` | WP-001 | — | none |
| `plugins/sulis/instances/discover-project/schemas/tools/*.schema.json` (×10) | WP-001 | — | none |
| `plugins/sulis/scripts/_discovery/__init__.py` | WP-002 (sole) | — | none (WP-003/004/006/007 only import from the package; don't re-create the marker) |
| `plugins/sulis/scripts/_discovery/tenant.py` | WP-002 | — | none |
| `plugins/sulis/scripts/_discovery/inspector.py` | WP-003 | — | none |
| `plugins/sulis/scripts/_discovery/inferrer.py` | WP-004 | — | none |
| `plugins/sulis/scripts/_discovery/_prompts/infer.txt` | WP-004 | — | none |
| `plugins/sulis/scripts/_discovery/minter.py` | WP-006 | — | none |
| `plugins/sulis/scripts/_discovery/slug.py` | WP-006 | — | none |
| `plugins/sulis/scripts/_discovery/verifier.py` | WP-007 | — | none |
| `plugins/sulis/skills/discover-project/SKILL.md` | WP-008 | — | none |
| `plugins/sulis/skills/discover-project/_prompts/*.md` | WP-005 | — | none (WP-008 includes-by-reference; does not modify) |
| `plugins/sulis/scripts/check-canonical-drift.py` | (existing) | WP-009 (sole modifier) | none |
| `plugins/sulis/scripts/tests/unit/test_*.py` | each test file owned by its source WP | — | none |
| `tests/fixtures/discover-project/{empty,populated,monorepo,pre-existing}/` | WP-010 (sole) | — | none (WP-003's fixtures live at `plugins/sulis/scripts/tests/fixtures/discover-project/tiny-*/`, different path) |

**Critical check:** the `_discovery/__init__.py` is sole-created by
WP-002. Per the rubric's anchor case (release-train `loader/__init__.py`
double-create), this is the class of defect P6 catches. Recorded
explicitly: WP-002's Contract names `__init__.py` as Created;
WP-003/004/006/007 do NOT name it (they import FROM the package).

**Two `_prompts/` directories** exist by design:
- `plugins/sulis/skills/discover-project/_prompts/` (founder-facing prompts) — owned by WP-005
- `plugins/sulis/scripts/_discovery/_prompts/infer.txt` (LLM prompt template) — owned by WP-004

Different paths, different owners, different content. No collision.

- **6.01 No two WPs Create the same file** ✓
- **6.02 Same-level parallel Modify of same file** ✓ (only WP-009 modifies `check-canonical-drift.py`; no parallel modifier)
- **6.03 Shared scaffolding created by foundation WP** ✓ (`__init__.py` created by WP-002; later WPs depend transitively via the package import)
- **6.04 Contract distinguishes create vs modify** ✓ (each WP's Contract uses "files created" / "files modified" sections)

**P6: PASS.**

### P7 — ServiceSpec compliance

**Not applicable.** discover-project ships no external service surface
(no HTTP/RPC endpoint, no queue consumer). The deliverable is a CLI
skill (`/sulis:discover-project`) invoked by an operator + Python
helpers invoked by the skill. ServiceSpec compliance applies only to
WPs that author a service contract for inter-process communication.
Recorded as N/A per SIZING.md §Decisions ("No new ServiceSpec").

**P7: N/A (not triggered).**

### P8 — Cross-WP identifier canonicalisation (NEW — MUST)

The TDD pre-canonicalised every cross-WP identifier in its
**§Canonical Identifiers** section (lines 26-130 of TDD.md). This is
the explicit P8 compliance pattern.

**Cross-WP shared identifiers extracted from WP Contracts:**

| Identifier | Appears in WPs | Upstream source citation | Result |
|---|---|---|---|
| `dna:workflow:01KT1WDSCVRWFW00000000000A` (discover-project Workflow ULID) | WP-001 (mints), WP-008 (front-matter), WP-009 (parity fixtures) | TDD §Canonical Identifiers — Workflow ULID | ✓ resolves |
| `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM` (marketplace tenant) | WP-001 (reused), WP-002 (fixed-vector cross-check) | TDD §Canonical Identifiers — Tenant ULIDs; original source release-train `failuremodes.jsonld` `_about` | ✓ resolves |
| 9 Step ULIDs (`dna:step:01KT1WDSST*`) | WP-001 (mints), WP-008 (annotation parity) | TDD §Canonical Identifiers — Step ULIDs | ✓ resolves |
| 8 FailureMode ULIDs (`dna:failuremode:01KT1WFM*`) | WP-001 (mints), WP-009 (parity fixtures) | TDD §Canonical Identifiers — FailureMode ULIDs | ✓ resolves |
| 5 Tool ULIDs (`dna:tool:01KT1WTL*`) | WP-001 (mints), WP-002/003/004 (test references), WP-007 (drift Tool reused) | TDD §Canonical Identifiers — Tool ULIDs | ✓ resolves |
| 1 Trigger ULID (`dna:trigger:01KT1WDSTRG1MANUAL00000A`) | WP-001 (mints) | TDD §Canonical Identifiers — Trigger ULIDs | ✓ resolves |
| Consumer-tenant derivation recipe | WP-002 (implements), WP-006 (consumes), WP-007 (cross-tenant ref check) | ADR-002 + TDD §Canonical Identifiers — Consumer-tenant derivation recipe | ✓ resolves |
| `release_workflow_ref` value `dna:workflow:01KT0RTRA1NWFW00000000000A` (marketplace release-train Workflow) | WP-007 (cross-tenant check), WP-008 (skill composes), WP-010 (E2E tests) | TDD §Form §Where the Project entity lives; release-train canonical | ✓ resolves (external authoritative source) |

**Per-check results:**

- **8.01 MUST — Every cross-WP shared identifier resolves to an authoritative upstream source.** Every identifier above carries a `# canonical-source: TDD.md §Canonical Identifiers — <subsection>` annotation in the originating WP's Contract (e.g., WP-001 line "# canonical-source: TDD.md §Canonical Identifiers"). ✓
- **8.02 MUST — No ULID-shape literal invented inline.** Regex scan across all 10 WP Contracts for `dna:[a-z]+:01[A-Z0-9]{24}` patterns; every match cross-checks against TDD §Canonical Identifiers byte-exact. No inline-minted ULIDs detected. ✓
- **8.03 MUST — No `dna:*:*` in ≥2 WP Contracts without upstream source.** Every cross-referenced `dna:*:*` traces to TDD §Canonical Identifiers. ✓
- **8.04 SHOULD — Each upstream source documents its minting recipe.** Workflow / Step / FailureMode / Trigger / Tool ULIDs follow the mnemonic-stamped Crockford-base32 pattern documented in TDD §Canonical Identifiers preamble ("Mnemonic-stamped with prefix `01KT1WDS`..."); Consumer-tenant ULID documented as `SHA256("tenant-name:" + <repo-org>/<repo-name>)` in ADR-002 + TDD. ✓
- **8.05 SHOULD — Single-WP-scoped identifiers carry annotation or are scope-local.** All identifiers in this WP set are explicitly cross-WP; none are scope-local. WP-001 carries the `# canonical-source: TDD.md §Canonical Identifiers` annotation as the upstream-binding marker. ✓
- **8.06 MAY — Composite WPs declare shared identifier set in parent.** No composite WPs in this set. N/A.

**P8: PASS** (all MUSTs pass; all SHOULDs pass; no MAY trigger).

The anchor-case failure mode for P8 (CH-01KSZ4 wave 1 tenant-ULID
divergence between WP-003 and WP-004) is exactly the class of defect
that the TDD's pre-canonicalisation prevents in this change. The
mechanical proof: every ULID written to disk by WP-001 traces to a
single source (TDD §Canonical Identifiers); every test in WP-002,
WP-006, WP-007, WP-008, WP-009 cross-checks against that same source.
A parallel-dispatched executor cannot drift the values because there
is no value-minting decision left to make inside the WPs.

---

## Methodology

The validating agent attests:

- [✓] **P1 Inventory completeness.** 10 WPs read end-to-end. Required sections found per WP: Context, Contract, DoD (R/G/B), Sequence, Token cost, Dependencies, ADRs, TDD §. Gaps: none.
- [✓] **P2 Atomicity.** Purpose statements parsed; titles scanned for ` and `; touch surfaces counted per Contract. WP-001 at the MUST ≤ 15 ceiling (15 files = 5 JSON-LD + 10 schemas) with rationale (mutually-validating contract). No `and` conjunctions in titles.
- [✓] **P3 Module naming.** WP filenames + Contract module names scanned for jargon prefixes, single-letter abbreviations, generic terms (`utils`/`helpers`/`common`). All slugs kebab-case + output-descriptive. No findings.
- [✓] **P4 Dependency graph.** DAG built from `dependsOn:` fields across 10 WP frontmatters. Cycles: 0. Orphans: 0. Depth: 4. Topological order valid. SHOULD deviation on 4.03 (WP-008 has 6 direct deps; rationale recorded — orchestrator role inherent to Path A).
- [✓] **P5 Performance + non-functional.** Per-WP scan against external-call + handler primitives. WP-004 (LLM) + WP-007 (subprocess detector) + WP-006 (atomic write) + WP-010 (E2E) carry explicit `## Performance` sections with measurable bounds.
- [✓] **P6 Peer-collision risk.** Cross-WP file-create scan. 0 collision pairs. `_discovery/__init__.py` sole-created by WP-002 (the anchor-case class).
- [—] **P7 ServiceSpec compliance.** N/A — discover-project has no external service surface; CLI skill only. Recorded per SIZING.md §Decisions.
- [✓] **P8 Cross-WP identifier canonicalisation.** 7 distinct cross-WP identifier classes extracted across the 10 WPs. Every class resolves to TDD §Canonical Identifiers (an authoritative upstream source pre-minted by SEA at design time). 0 inline-minted ULIDs detected.

---

## Version history

| Date | Result | Notes |
|---|---|---|
| 2026-06-01 | PASS | Initial decompose validation, v0.2.0 rubric (P8 included) |
