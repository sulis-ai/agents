# Decompose Validation — discover-verify-scope

> **Change:** CH-01KT48 · fix
> **Source of record:** `.changes/fix-discover-verify-scope.SPEC.md`
> **WP set:** 1 (WP-001)
> **Verdict:** **PASS** — single-WP set; atomicity, contract, and DoD complete;
> several rubric phases trivially satisfied or N/A for a contained fix.

This change skipped a full blueprint by design (right-sizing: three bug fixes
in fully-specified existing code). The SPEC.md is the design-of-record in place
of a TDD.md. The decompose rubric is applied below at the depth a contained
single-WP fix warrants.

## Rubric

### P1 — Atomicity (each WP independently implementable)

**PASS.** WP-001 is implementable from the SPEC + the three named source files
without reading any other WP (there is no other WP). The deliberate decision
**not** to split into three WPs is the load-bearing atomicity call:

- The three fixes share one code path (the discover-project post-mint verify
  gate) and one headline acceptance test (the consumer-repo regression).
- That regression test only goes green when all three land. After any single
  fix it stays red — so no single fix is independently shippable.
- Splitting would manufacture parallelism for sequential, same-capability work
  and leave the headline test red between merges.

Per the task's own guidance, 2 WPs would be permitted only with a genuine
atomicity reason to split; none exists. One WP is correct.

### P2 — Contract completeness (interfaces / types / files named)

**PASS.** WP-001's Contract names all three modified files and both new test
files, with the precise change per file:

- Fix 1: `--scope <entity-file>` argparse mode, mode-coexistence rule, entity
  shape, schema target (`project.schema.json`), allowlist reuse
  (`cross_tenant_ref_is_allowed`), and the preserved exit-code/envelope contract.
- Fix 2: the exact `__file__`-relative resolution expression.
- Fix 3: the `git symbolic-ref refs/remotes/origin/HEAD` resolution, prefix
  strip, and `main` fallback — with the unchanged `RepoRoot` dataclass shape.

### P3 — DoD is TDD-first (Red → Green → Blue, named tests)

**PASS.** Red lists 5 named, failing-first tests with nodeids, including:

- the **real-subprocess** `--scope` test (valid → exit 0; drifted → non-zero;
  no `--instance-dir`/`--yaml-path` required), and
- the **consumer-repo regression** test driving the **real** verifier from
  outside the marketplace repo on a feature branch, asserting both
  mint-persists and `primary_branch == "main"`.

Green maps each fix to the tests it greens. Blue covers refactor + the explicit
regression guard (existing release-train CI characterisation tests stay green;
`DriftDetectorExtensionMissingError` intact). The `verification:` frontmatter is
Shape 1 (concrete), adapter `backend`, artifact = the real-subprocess `--scope`
test nodeid.

### P4 — Sequence / dependency graph (no cycles, correct ordering)

**PASS (trivial).** Single node, no edges. `dependsOn: []`, `blocks: []`. No
cycle possible. RGB ordering inside the WP is documented.

### P5 — Change-primitive correctness (per change-primitives.md)

**PASS.** Primitive `fix`; group `REORGANISE` with `composite_of: [REORGANISE,
REINFORCE]`. Justified: fixes 2 + 3 are behaviour-preserving in-place
corrections (Refactor) pinned by a characterisation test per the
Characterisation-Tests-Before-Refactor MUST; fix 1 is Extend (new mode
alongside existing); the two new tests are Test (REINFORCE). No Wrap — the
Ports-vs-Wrappers and No-Band-Aid-Wrappers rules are satisfied (internal script
extended in place; no wrapper layer). `characterisation_test` frontmatter names
the consumer-repo regression test as required for any REORGANISE WP.

### P6 — Cross-kind / contract-first wiring (CF-05)

**N/A.** Single-kind backend set. No `frontend`/`async` kind, no cross-kind data
contract, so no data-contract WP and no contract-first routing required. The
`wpx-index audit-contracts` graph check is not triggered for a single-kind set.

### P7 — Visual-contract coverage

**N/A.** No user-facing visual surface. The change is CLI + library Python
(a drift-detector script and two `_discovery` modules). No visual-contract WP.

### P8 — INDEX integrity (canonical header, totals, status)

**PASS.** `wpx-index lint --project discover-verify-scope` returns
`{"data": {"header": "canonical"}, "ok": true}`. Status summary, primitive/kind
distribution, wrap audit, dependency graph, WP table, and totals are present and
internally consistent (1 pending WP; ~14k token total).

## Circuit breakers

- TDD/SPEC-length, ADR-count, and restating-authoritative-source breakers: not
  triggered — no TDD produced (blueprint skipped by design), zero ADRs (no
  decision affecting more than one component; the `git symbolic-ref` and
  `__file__` choices are established conventions taken silently per CP, recorded
  inline in the WP Contract rather than as ADRs).

## Summary

| Phase | Verdict | Note |
|---|---|---|
| P1 Atomicity | PASS | 1 WP correct; split rejected with reason |
| P2 Contract | PASS | all files + changes named |
| P3 DoD TDD-first | PASS | 5 named Red tests; RGB complete |
| P4 Sequence | PASS (trivial) | single node, no edges |
| P5 Primitive | PASS | fix / REORGANISE+REINFORCE; no Wrap |
| P6 Cross-kind | N/A | single-kind backend |
| P7 Visual contract | N/A | no visual surface |
| P8 INDEX integrity | PASS | lint: header canonical |

**Overall: PASS.** Ready for `/sulis:run-wp WP-001`.
