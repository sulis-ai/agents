# Decompose Validation — seam-dod-gate

> **Rubric:** `plugins/sulis/references/decompose-validation-rubric.md` v0.4.0
> **Change:** CH-01KTP7 · `feat` · tier S
> **Date:** 2026-06-09
> **Validated:** 6 WP files + INDEX.md, read end-to-end, against the source TDD.

## At a glance

The decomposition itself is clean — six atomic, single-responsibility Work
Packages, an acyclic dependency graph with a clear test-first ordering, no
peer-collision risk, no module-naming jargon, and per-task verification that
matches the change's kind. **One blocking gap sits upstream of the
decomposition**: the technical blueprint (TDD) is missing the literal
`## Verification Plan` heading and the verification-questions citation the
P-VER gate requires. That is a blueprint-stage fix (one heading + one
citation line), not a decomposition defect. The WP set is otherwise
ready to build the moment that heading lands.

---

## Verdict

**GAPS_FOUND** — every decomposition-owned MUST passes (Phases 1–8, 10);
the single MUST failure is **P-VER 9.01 + 9.06 on the TDD** (a
blueprint-stage artifact), which Phase 9 inspects. Per the rubric's verdict
rule (≥1 MUST failure → FAIL), the verdict cannot be PASS until the TDD
carries its Verification Plan section + citation.

> The gap is **not** in the WPs. If the TDD's `## Verification Plan` heading +
> `VERIFICATION_QUESTIONS` citation are added by `/sulis:draft-architecture`
> (a ~5-line edit; the content already exists in the TDD's "Test surface" and
> "Where the standards changes land" sections and the SPEC's Verification
> Plan), re-running this rubric flips the verdict to **PASS**.

---

## Summary

| Metric | Count |
|---|---|
| WPs validated | 6 |
| Total checks applied | ~50 (mechanical subset of the 10 phases) |
| PASS | 49 |
| FAIL (MUST) | 1 (P-VER 9.01/9.06 on the TDD — same root gap) |
| FAIL-WITH-RATIONALE (SHOULD) | 0 |

---

## Phase-by-phase results

| Phase | PASS | FAIL | Notes |
|---|---|---|---|
| 1 Inventory completeness | ✓ | — | All 6 WPs carry Context / Contract / DoD(RGB) / Sequence / Token / dependsOn / primitive. INDEX lists all 6 + has a Dependency Graph. |
| 2 Atomicity | ✓ | — | All titles conjunction-free (WP-004 reworded). Touch surface 1–3 files each (≤8 SHOULD, ≤15 MUST). One primitive each. |
| 3 Module naming + clean code | ✓ | — | Filenames `WP-NNN-{kebab-slug}.md`; slugs are outcome-descriptive; module name `_seam_close_gate` matches the codebase's `_`-prefixed pure-module convention. |
| 4 Dependency graph correctness | ✓ | — | DAG acyclic; all dependsOn resolve; ≤5 deps each; recommended order is a valid topo sort; 2 parallel batches. CF cross-kind checks (4.08/4.09) N/A — single-kind set. |
| 5 Performance + non-functional | ✓ | — | No request-handler / endpoint / external-API primitives in the set → 5.01/5.05 not triggered. Pure-decision + standards work. |
| 6 Peer-collision risk | ✓ | — | No two WPs create the same file. Two shared test files each have one creator + one appender bound by an explicit dependsOn edge (not same-level peers). 6.06 N/A (no shared producer artifact). |
| 7 ServiceSpec compliance | — | — | N/A — no service introduced/modified (no `service-specs/`; internal methodology machinery, no network surface). |
| 8 Cross-WP identifier canonicalisation | ✓ | — | The one cross-WP identifier (`evaluate(...)` signature + `SeamCloseResult`) is sourced from the TDD §Form + WP-001 Contract; the two shared test-file paths are pinned in INDEX with single creators. No invented ULID / `dna:` literal. |
| 9 P-VER (Verification Plan) | ✗ | **9.01 + 9.06 on TDD** | SPEC has `## Verification Plan` (no placeholders). **TDD has neither the `## Verification Plan` heading nor the `VERIFICATION_QUESTIONS` citation annotation** → 9.01 + 9.06 FAIL. 9.05 (kind adapter row) + 9.08 (per-WP `verification:`) PASS. Not grandfathered (`verification_required_from` empty; `started_at` 2026-06-09). |
| 10 P-PLAT (Platform Contract) | ✓ | — | No WP carries `platform:` / `touch-class: write\|deploy` — no gated third-party write/deploy touch (internal machinery; the runner it shells out to already owns its isolation). 10.01 not triggered. |

---

## Blocking gaps (MUST failures)

### P-VER 9.01 + 9.06 — the TDD is missing its Verification Plan section + citation

- **Phase / check:** Phase 9, checks 9.01 (`## Verification Plan` heading present in SRD **and TDD**) and 9.06 (artifact cites `VERIFICATION_QUESTIONS.md` with the HTML-comment annotation).
- **Evidence:** `.architecture/seam-dod-gate/TDD.md` — `grep -ni "verification plan\|VERIFICATION_QUESTIONS"` returns nothing. The SPEC (`.changes/feat-seam-dod-gate.SPEC.md:88`) **does** carry `## Verification Plan` with substantive, placeholder-free content, so the SRD side of 9.01 passes; the TDD side fails.
- **Why it's not a decomposition defect:** the per-WP `verification:` frontmatter (9.08) is present and correct on all six WPs, and the change `kind: methodology` has a valid adapter row (9.05). The TDD's *content* covers verification thoroughly (the "Test surface" section enumerates the three test files + the 12 cases; "Where the standards changes land" names the standards tests). What's absent is only the **literal `## Verification Plan` heading + the citation annotation** the gate keys on — a `/sulis:draft-architecture` responsibility.
- **Remediation (route back to blueprint):**
  ```
  P-VER: 9.01 + 9.06 failed for .architecture/seam-dod-gate/TDD.md.
  Remediation: add a `## Verification Plan` heading to the TDD (the SEA
  system prompt's TDD output spec requires it), populated from the existing
  "Test surface" + SPEC Verification Plan content, immediately preceded by:
  <!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->
  Then re-run decompose-validation.
  ```

---

## Recommended improvements (SHOULD failures)

None. No SHOULD failed.

Two observations carried forward (not failures):

- **WP-005 → WP-006 and WP-003 → WP-004 are file-ordering edges, not semantic
  ones.** Each pair shares a test file (one creator, one appender). The
  dependency is the boring, collision-safe choice (P6 6.03). An executor that
  preferred maximum parallelism could have the creator WP scaffold an empty
  test file so the pairs run fully parallel — but the explicit edge is correct
  as-is.
- **No characterisation test is mandated** because no REORGANISE primitive
  appears. WP-003 touches existing code (`wpx-step12`) but as EXPAND-Extend
  (adds step 12.2a; no structural refactor of existing steps). Its DoD re-runs
  the existing `wpx-step12` integration tests as behaviour-safety — the
  spirit of characterisation without the MUST being triggered.

---

## Detailed findings per check

### P2 Atomicity — WP-004 title reworded (resolved during validation)

The original WP-004 title — *"Document the seam-close gate in `run-wp/SKILL.md`
and `run-all/SKILL.md`"* — contained the coordinating conjunction "and" (a
2.06 MUST failure on the mechanical scan, even though 2.01's predicate test
passed: one action, "document", over two targets). Reworded to *"Document the
seam-close gate in the build-loop skills (run-wp, run-all)"* — conjunction-free.
INDEX WP-table row updated to match. Re-scan: no ` and ` in any title.

### P9 9.08 — per-WP verification adapter aligned to change kind (resolved)

WP-004/005/006 edit skill / standards prose and initially carried `kind: docs`
with `adapter: methodology` — a 9.08 mismatch (docs-kind would map to the
`documentation` adapter: link-resolution + readability). Their verification is
genuinely structural pytest doc-shape assertions (the `methodology` adapter
shape), not link/readability checks, so the WPs were aligned to
`kind: methodology` — kind and adapter now agree across all six WPs. The whole
change is methodology machinery; this is the honest kind.

---

## Methodology

The validating agent attests:

- [✓] **P1 Inventory completeness.** 6 WPs read end-to-end. Required sections found per WP: Context, Contract, DoD (Red/Green/Blue), Sequence (with Sequence ID), Estimated Token Cost, dependsOn, primitive, verification block. INDEX lists all 6 WP files (set equality with directory) and has a Dependency Graph (Mermaid). Gaps: none.
- [✓] **P2 Atomicity.** Purpose statements parsed — single action each, no conjunction in any predicate. Touch surface counted per Contract: 1–3 files each (max WP-004 = 3). 0 WPs exceed the ≤15 MUST or ≤8 SHOULD bound. 0 titles contain " and " (after WP-004 rework). One primitive per WP.
- [✓] **P3 Module naming.** WP filenames match `WP-NNN-{kebab-slug}.md`; slugs are outcome-descriptive (`author-…`, `wire-…`, `document-…`, `add-…`, `amend-…`). The one new module `_seam_close_gate.py` follows the repo's `_`-prefixed pure-module convention (peer to `_acceptance_gate.py`, `_verify_scenario_coverage.py`); no abbreviation jargon. 0 findings.
- [✓] **P4 Dependency graph.** Built the DAG from dependsOn: WP-001→WP-002→WP-003→WP-004; WP-002→WP-004; WP-005→WP-006. Cycles: 0 (DFS clean). Orphans: 0 (WP-001 and WP-005 are foundation roots with outgoing edges). All dependsOn targets resolve. Recommended Implementation Order verified as a valid topological sort. Max direct deps: 2 (WP-004). Parallel batches: 2 (WP-001‖WP-005 at t=0; WP-002‖WP-006 at t=1). 4.08/4.09 N/A (single-kind).
- [✓] **P5 Performance + non-functional.** Per-WP primitive scan: no `add-endpoint`/`add-handler`/`add-service`/`add-route`/`add-integration` primitives → 5.01/5.05 not triggered. Pure-decision module + standards/doc edits carry no SLA obligation. 0 WPs in request-handler primitives without an SLA.
- [✓] **P6 Peer-collision risk.** Cross-WP file-create scan: each created file (`_seam_close_gate.py`, `test_seam_close_gate.py`, `test_seam_close_gate_wiring.py`, `test_seam_close_standards_presence.py`) has exactly one creator. The two shared test files each have one appender bound by an explicit dependsOn edge (WP-004→WP-003, WP-006→WP-005) so they are never same-level parallel peers on the same file. 0 collision pairs. 6.06 N/A (no shared producer artifact / manifest).
- [✓] **P7 ServiceSpec compliance.** N/A — no service introduced or modified; no `service-specs/` directory; the change is internal methodology machinery with no network surface. 0 manifests to validate.
- [✓] **P8 Cross-WP identifier canonicalisation.** 1 cross-WP shared identifier extracted (the `evaluate(...)` signature + `SeamCloseResult` dataclass) — sourced from TDD §Form + pinned in WP-001's Contract, consumed by WP-002 (implements) and WP-003 (calls). The two shared test-file paths are pinned in the INDEX P8 table with single creators. No ULID-shape or `dna:*:*` literal invented inline (the `dna:requirement:…`/`dna:scenario:…` shapes appear only as type references to existing brain entities). 0 inline-unsourced identifiers.
- [✗] **P9 P-VER (Verification Plan).** Grandfather: not grandfathered (`verification_required_from` empty = dogfood; `started_at` 2026-06-09 ≥ empty → checks run). SRD `## Verification Plan` present + placeholder-free (9.01 SRD ✓, 9.02 ✓, 9.03 N/A — no `n/a` subsections). **TDD `## Verification Plan` absent (9.01 TDD ✗) and TDD `VERIFICATION_QUESTIONS` citation absent (9.06 ✗).** 9.04 N/A (no `existing` infra paths cited in a per-integration strategy block). 9.05 ✓ (`kind: methodology` has an adapter row). 9.07 N/A (no citation present to currency-check — subsumed by 9.06). 9.08 ✓ (all 6 WPs carry `verification:` with `adapter: methodology` matching change kind). Net: 2 MUST failures, same root gap (TDD lacks the VP section + citation).
- [✓] **P10 P-PLAT (Platform Contract).** Grandfather: same as P9 (checks run). 0 WPs carry `platform:` / `touch-class: write|deploy` — no gated third-party write/deploy touch (the change adds a decision module + a hook + standards prose; the runner it invokes owns its own isolation). 10.01 not triggered; 10.02–10.06 N/A (no contract referenced); 10.07 N/A. Pass.

---

## Anti-patterns self-check

- Did not skip any phase silently — Phases 7 and 10 recorded N/A with reasons; Phase 9 recorded the MUST failure.
- Read all 6 WP files end-to-end (not sampled).
- Did not auto-pass P9 on a "looks fine" judgement — the mechanical grep for the TDD heading + citation drove the failure.
- Verdict computed deterministically: ≥1 MUST failure → GAPS_FOUND.
