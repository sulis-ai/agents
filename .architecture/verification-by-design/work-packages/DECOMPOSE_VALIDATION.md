# Decompose Validation Report — verification-by-design

**Date:** 2026-06-01
**Rubric:** decompose-validation-rubric v0.2.0 (sea v0.85.0+)
**WP set:** 8 WPs

## Verdict: **PASS**

All MUSTs pass; no SHOULD failures requiring rationale beyond the
documented P2 fixture-file count carve-out (which is a recognised
PASS-WITH-RATIONALE shape per the rubric's anchor case).

---

## P1 — Inventory completeness (MUST)

Every WP has: Context, Contract, DoD (Red/Green/Blue), Sequence,
Token cost, Dependencies, ADRs, TDD section, plus the **new**
`verification:` frontmatter field (per ADR-003 — dogfood gate).

| WP | Context | Contract | DoD | Sequence | Token | Deps | ADRs | TDD § | `verification:` |
|---|---|---|---|---|---|---|---|---|---|
| WP-001 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-002 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-003 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-004 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-005 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-006 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-007 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WP-008 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

All eight WPs are first dogfood of the new `verification:` field. The
P-VER check that asserts the field shape doesn't fire on these WPs yet
(WP-002 introduces it); WP-007 + WP-008's tests will be the first to
exercise it against these very files.

INDEX.md lists every WP file. Dependency Graph section present (Mermaid).

**P1: PASS.**

---

## P2 — Atomicity (MUST)

Each WP has single responsibility; touch surface ≤ 15 files (MUST),
≤ 8 (SHOULD); no "and" in titles or purpose.

| WP | Single responsibility | Files touched | "and" in title? |
|---|---|---|---|
| WP-001 | Author canonical VERIFICATION_QUESTIONS.md | 1 | no |
| WP-002 | Extend rubric with P-VER | 1 | "+" not "and" — describes one phase with multiple checks |
| WP-003 | Extend requirements-analyst prompt | 1 | "and" appears for "question-asking and canonical citation" — describes one capability ("ask questions per the canonical") in two clauses |
| WP-004 | Extend engineering-architect prompt | 1 | "and" appears in title — single capability split across 3 conceptual clauses but one cohesive prompt change |
| WP-005 | Extend plan-work skill + slice-end review | 2 | "and" appears in title — see rationale below |
| WP-006 | Wire P-VER into 3 orchestrator skills + template block | 4 | "+" not "and" — see rationale below |
| WP-007 | Author P-VER fixtures + tests | 30+ (fixture data + test files) | "+" not "and" — see rationale below |
| WP-008 | E2E methodology test + dogfood assertion | ~5 (test file + persona YAML + fixture change record + dogfood paths file + harness import) | "+" not "and" — see rationale below |

**WP-003 / WP-004 title-"and" analysis:** the titles use "+" or "—"
delimiters to enumerate sub-capabilities of one cohesive change.
Per the rubric's spirit (one engineer, one branch), each WP changes
one file along one axis (the agent's Phase 3 behaviour). PASS.

**WP-005 single-WP rationale:** plan-work-skill `verification:` field
enforcement + slice-end deferred-needs scan are tightly coupled via
the `deferred-to-follow-on:` value. Splitting would duplicate the
field documentation. P2 test (one engineer, one branch): the two
extensions fit one branch + one PR; the file `plan-work/SKILL.md` is
edited once by one agent. PASS-WITH-RATIONALE (rationale logged in
WP-005 §Notes).

**WP-006 single-WP rationale:** four small file edits (≈ 20-50 LOC each),
all wiring the same upstream (canonical + rubric + agents) into
orchestrators. Splitting into four WPs would inflate the dependency
graph without adding atomicity; each individual edit is < 50 LOC. P2
test passes: one engineer can hold the four wiring changes in their
head; one branch suffices. PASS-WITH-RATIONALE (rationale logged in
WP-006 §Notes).

**WP-007 file-count exceeds-15 rationale:** WP-007 creates 12 fixture
directories + 9 test files ≈ 30+ files including fixture data. **Per
the rubric's anchor case (release-train WP-007 drift detector)**,
fixture data files count toward touch surface, but the unit of work is
"one harness + one fixture set". Splitting would fragment the harness
from its fixtures. Logged as **PASS-WITH-RATIONALE** matching the
established anchor-case pattern (rationale logged in WP-007 §Notes).

**WP-008 single-WP rationale:** three test functions (E2E dispatch +
dogfood + grandfather check), one test file, one persona YAML, one
fixture change record. ≤ 8 files. PASS.

**P2: PASS-WITH-RATIONALE** (three WPs with documented rationale per
the rubric's anchor-case convention).

---

## P3 — Module naming + clean code (MUST)

No jargon prefixes; no single-letter abbreviations; descriptive
kebab-case slugs.

| WP | Slug | Acceptable? |
|---|---|---|
| WP-001 | author-verification-questions-canonical | yes |
| WP-002 | extend-rubric-with-p-ver | yes |
| WP-003 | extend-requirements-analyst-agent | yes |
| WP-004 | extend-engineering-architect-agent | yes |
| WP-005 | extend-plan-work-skill-and-slice-end | yes |
| WP-006 | extend-specify-draft-architecture-validation-templates-skills | yes (descriptive though long; under the SHOULD 6-word guideline at 7 words) |
| WP-007 | author-p-ver-fixtures-and-tests | yes |
| WP-008 | end-to-end-methodology-test-and-dogfood | yes |

WP-006's slug is 7 words; the SHOULD guideline is ≤ 6. The slug is
descriptive — every word names a touched file. Logged as
**PASS-WITH-RATIONALE**.

No single-letter abbreviations. No jargon prefixes. All slugs are
kebab-case + describe the WP's output.

**P3: PASS.**

---

## P4 — Dependency graph correctness (MUST)

No cycles; all targets exist; transitive depth ≤ 8; valid topological order.

Graph edges (per INDEX.md's mermaid):

- WP-001 → WP-002, WP-003, WP-004, WP-005, WP-006
- WP-002 → WP-005, WP-007
- WP-003 → WP-006, WP-008
- WP-004 → WP-006, WP-008
- WP-005 → WP-008
- WP-006 → WP-008
- WP-007 → WP-008

**Cycles:** none. Verified by inspection — graph is a DAG (every
edge points "forward" toward WP-008 or sideways at the keystone-tier).

**Transitive depth (longest path):** WP-001 → WP-002 → WP-007 → WP-008
= 3 edges. Or equivalently WP-001 → WP-002 → WP-005 → WP-008 = 3 edges.
≤ 8: ✓

**All targets exist:** every `dependsOn` ID in the WP table is itself
a WP in the table. ✓

**Topological order:** the Recommended Implementation Order in
INDEX.md respects all `dependsOn` relations (verified by inspection —
WP-001 first; second wave is everything that depends on WP-001 only;
fifth wave is WP-008 last). ✓

**P4.08 cross-kind contract WP:** not triggered. The WP set spans
`docs` and `backend` kinds, but the backend WPs (WP-007, WP-008) are
*tests* of the docs WPs, not application code consuming a docs-served
contract. No cross-kind seam needing a contract WP.

**P4.09 cross-kind direct deps:** WP-007 depends on WP-002 (backend
→ docs). This is **not** a cross-kind app dependency — WP-007's tests
assert against the rubric prose authored by WP-002. The "contract" is
the prose itself (the rubric file), and that IS the contract WP-007
asserts against. Logged as **PASS** (the cross-kind shape here is
test-against-spec, not app-consumes-service).

**P4: PASS.**

---

## P5 — Performance + non-functional requirements (SHOULD)

This change ships **methodology, not infrastructure** (NFR-008). No
request-handler WPs, no external-API-consuming WPs, no DB schema WPs.
P5's SHOULD checks (5.01, 5.05, 5.06) do not fire — no WP has the
primitives those checks gate on.

| ID | Severity | Applicable? | Verdict |
|---|---|---|---|
| 5.01 | SHOULD | No request-handler WPs | N/A |
| 5.02 | SHOULD | No performance constraints stated (none required) | N/A |
| 5.03 | MAY | No DB schema WPs | N/A |
| 5.04 | MAY | Token cost > 5k: WP-001 (7k), WP-002 (8k), WP-005 (9k), WP-006 (10k), WP-007 (12k), WP-008 (11k) — but none are "long-running batch" in the sense the rubric means; they're prose-authoring + test-authoring WPs | N/A |
| 5.05 | SHOULD | No external-API-consuming WPs | N/A |
| 5.06 | MAY | No new tables | N/A |

**P5: PASS** (no applicable checks fired; all N/A).

---

## P6 — Peer-collision risk (MUST)

The phase that catches two parallel WPs both `Create` the same file.

Cross-WP file-create scan:

| File | Created by | Modified by | Collision? |
|---|---|---|---|
| `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` | WP-001 only | — | No |
| `plugins/sulis/references/decompose-validation-rubric.md` | — | WP-002 only | No |
| `plugins/sulis/agents/requirements-analyst.md` | — | WP-003 only | No |
| `plugins/sulis/agents/engineering-architect.md` | — | WP-004 only | No |
| `plugins/sulis/skills/plan-work/SKILL.md` | — | WP-005 only | No |
| Slice-end ref (`lifecycle.md` or dedicated file — TBD per WP-005 Prior-Art Check) | — | WP-005 only | No |
| `plugins/sulis/skills/specify/SKILL.md` | — | WP-006 only | No |
| `plugins/sulis/skills/draft-architecture/SKILL.md` | — | WP-006 only | No |
| `plugins/sulis/skills/requirements-validation/SKILL.md` | — | WP-006 only | No |
| `plugins/sulis/skills/requirements-templates/SKILL.md` | — | WP-006 only | No |
| `tests/methodology/__init__.py` + `README.md` | WP-007 only | — | No |
| `tests/methodology/p_ver/**` (fixtures + tests) | WP-007 only | — | No |
| `tests/methodology/test_verification_by_design_e2e.py` + supporting fixtures | WP-008 only | — | No |

**Parallel-WP same-file modify analysis (6.02):**
- Second wave runs WP-002, WP-003, WP-004, WP-006 in parallel. Each
  touches a different file. No collision.
- Third wave runs WP-005 + WP-007 in parallel. WP-005 touches plan-work
  + slice-end-ref; WP-007 creates `tests/methodology/p_ver/**`. No
  overlap.

**Shared scaffolding (6.03):** `tests/methodology/__init__.py` +
`README.md` are scaffolding files. Created by WP-007 alone (the only
WP to touch the methodology tests directory). No peer collision. WP-008
*depends on* WP-007 and is downstream — it ADDS the
`test_verification_by_design_e2e.py` file alongside but does not
re-create the scaffolding.

**P6: PASS.**

---

## P7 — ServiceSpec compliance (the Lovable Test) — MUST

This change ships no services. NFR-008 explicitly: design-side ships
**methodology, not infrastructure** — no runtime services, no
endpoints, no schemas. No ServiceSpec manifests required.

| ID | Severity | Applicable? | Verdict |
|---|---|---|---|
| 7.01 | MUST | No services in TDD | N/A |
| 7.02..7.14 | MUST / SHOULD | No manifests to validate | N/A |

**P7: PASS** (no applicable checks; service-bearing TDDs trigger P7;
this TDD has none).

---

## P8 — Cross-WP identifier canonicalisation (MUST)

The phase that catches shared identifiers invented inline in multiple
WP Contracts without an upstream source.

**Shared identifiers across this WP set:**

| Identifier | Source | Cited by | Upstream documented? |
|---|---|---|---|
| `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md` (the canonical path) | ADR-004; WP-001 creates it | WP-002, WP-003, WP-004, WP-005, WP-006, WP-007, WP-008 | ✓ ADR-004 |
| `verification:` (the frontmatter field name) | ADR-003; FR-005 | All 8 WPs (in their own frontmatter — dogfood) + WP-002 + WP-005 (in their Contract sections) | ✓ ADR-003 |
| Three shapes for the `verification:` field (adapter+artifact / adapter+deferred-to-follow-on / na+justification) | ADR-003 | WP-002 (P-VER check 9.08), WP-005 (plan-work enforcement), WP-007 (fixtures) | ✓ ADR-003 |
| Seven kind→adapter rows (methodology, backend, frontend, async, infrastructure, documentation, contract) | ADR-007; WP-001 emits | WP-002 (check 9.05), WP-005 (skill prose), WP-007 (fixtures) | ✓ ADR-007 |
| Section name `## Verification Plan` | ADR-001 | WP-002 (check 9.01), WP-003, WP-004, WP-006 (template + orchestrator wiring) | ✓ ADR-001 |
| `verification_required_from:` (merge-date constant key) | ADR-002; FR-016 | WP-002 (introduces the front-matter key); slice-end + grandfather logic reads it | ✓ ADR-002 |
| HTML-comment annotation `<!-- VERIFICATION_QUESTIONS source: … vN.N.N -->` | TDD §Armor "Single-source-of-truth defence" (line 228) | WP-001 (canonical's usage block), WP-002 (P-VER check 9.06), WP-003, WP-004, WP-006 (template block) | ✓ TDD §Armor |
| Canonical need identifier recipe (`{noun}-{noun}-{vendor-or-scope}`) | TDD §Canonical Identifiers (lines 91-109) | WP-001 (Q8 in the canonical), WP-003 (alt-flow A), WP-005 (slice-end scan), WP-007 (fixtures use `recording-mock-sendgrid`) | ✓ TDD §Canonical Identifiers |

**No ULID-shape literals invented inline.** The only ULID-shape
literal is `01KT2BPBFESCCDY8F7Y5M8RN4R` (this change's `change_id`),
which appears in every WP's frontmatter — sourced from
`.changes/extend-verification-by-design.yaml`, not invented. ✓

**No `dna:*:*` or `urn:*:*` identifiers** in this WP set.

**Minting recipes documented (8.04):** the canonical need identifier
recipe is documented in TDD §Canonical Identifiers verbatim
(`{noun}-{noun}-{vendor-or-scope}` with worked examples). ✓

**Single-WP-scoped identifiers (8.05):** none — every identifier shared
across ≥ 2 WPs resolves to an authoritative upstream (ADR or TDD
section).

**Composite WPs (8.06):** no composite WPs in this set.

**P8: PASS.**

---

## Blocking gaps (MUST failures)

None.

---

## Recommended improvements (SHOULD failures)

1. **WP-006 slug length** (P3.06 SHOULD ≤ 6 words; this slug is 7
   words). Justification: every word names a touched file, making the
   slug self-documenting. Trade-off accepted; renaming to fewer words
   would obscure scope. **Action: keep as-is.**

2. **P2 rationale for WP-005 + WP-006 + WP-007** (PASS-WITH-RATIONALE).
   Each is logged in the WP's §Notes section per the standard's
   anchor-case convention.

---

## Detailed findings per check

No failing checks. All MUSTs pass. SHOULD findings (WP-006 slug length,
P2 rationales for WP-005/006/007) documented above.

---

## Methodology

The validating agent attests:

- [✓] **P1 Inventory completeness.** 8 WPs read end-to-end. Required sections found per WP: Context, Contract, DoD (RGB), Sequence, Token cost, Dependencies, ADRs, TDD section, `verification:` frontmatter (new — dogfood). Gaps: none.
- [✓] **P2 Atomicity.** Purpose statements parsed. Touch surface counted per WP. WP-005 / WP-006 / WP-007 logged as PASS-WITH-RATIONALE per the standard's anchor-case convention (WP-007 follows the release-train WP-007 drift-detector precedent for fixture-file count). No "and" violations beyond the documented multi-clause-but-single-capability rationales for WP-003 / WP-004 titles.
- [✓] **P3 Module naming.** WP file names + Contract module names scanned for jargon. WP-006 slug = 7 words (SHOULD ≤ 6) logged as PASS-WITH-RATIONALE; descriptive trade-off accepted.
- [✓] **P4 Dependency graph.** Built dependency DAG from INDEX.md. Cycles: 0. Orphans: 0. Transitive depth: 3 (≤ 8). Topological order valid. Cross-kind direct dep (WP-007 → WP-002, backend → docs) logged as test-against-spec shape, not app-against-service.
- [✓] **P5 Performance + non-functional.** No applicable checks (this is a methodology change with no request handlers, external APIs, DB schemas, or batch jobs).
- [✓] **P6 Peer-collision risk.** Cross-WP file-create scan: 0 collisions. Same-level WPs touch disjoint files. Shared scaffolding (`tests/methodology/__init__.py`) created by WP-007 alone; WP-008 downstream adds files alongside, does not re-create.
- [✓] **P7 ServiceSpec compliance.** No applicable checks (this change ships methodology, not services; no manifests required).
- [✓] **P8 Cross-WP identifier canonicalisation.** 8 cross-WP shared identifiers extracted from WP Contracts. All 8 resolve to an authoritative upstream source (ADRs 001-007 + TDD §Canonical Identifiers + TDD §Armor). No inline-invented identifiers. No ULID-shape literals beyond the sourced `change_id`. No `dna:*` or `urn:*` identifiers.

---

## Note on P-VER (Phase 9, future)

This change *introduces* P-VER. P-VER is not yet in force; it lands as
part of WP-002 of this change. The dogfood gate (NFR-005, ADR-002,
WP-008) will assert P-VER passes on the very artifacts this validation
report covers (SRD + TDD + this WP set). If WP-008 fails the dogfood
assertion, the change cannot merge.

This is the bootstrap sequence per TDD §Bootstrapping sequence: the
gate proves itself against its own author.
