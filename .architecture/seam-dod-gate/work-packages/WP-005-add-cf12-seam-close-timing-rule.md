---
# Identity (WP-01)
id: WP-005
title: Add CF-12 (seam-close DoD timing rule) to CONTRACT_FIRST_STANDARD.md
status: pending
change_id: seam-dod-gate
kind: methodology
source: feat
primitive: extend
group: EXPAND

# Scope (WP-02..04)
atomic_branch: yes
estimate: small
blast_radius: low

# Lifecycle (WP-07)
sequence_id: WP-005
dependsOn: []
blocks: []

# Composite (WP-08)
child_wps: []
kinds: null

estimated_token_cost:
  input: 4k
  output: 3k
tdd_section: §Where the standards changes land — CONTRACT_FIRST_STANDARD.md new CF-12
adrs: [ADR-002, ADR-004, ADR-005]
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/unit/test_seam_close_standards_presence.py

rollback: |
  Revert the CF-12 section append + the version-history row in
  CONTRACT_FIRST_STANDARD.md. Pure append (ADR-style); no existing CF-NN
  section is edited. The CF-12 presence test reverts to Red.
---

# Add CF-12 — Real-data acceptance is driven at seam-close (MUST)

## Context

TDD §"Where the standards changes land" → `CONTRACT_FIRST_STANDARD.md` new
**CF-12**. CF-07 says *what* "done at the seam" means (wired mock→real +
conformance check). CF-12 adds the **timing**: the seam's real-data acceptance
is driven **at seam-close, not deferred to ship**. This is the contract-first
application of the observed-or-blocked Definition-of-Done discipline.

Pure append after CF-11 (the standard's existing tail), mirroring how CF-11 was
added in v0.2.0. The seam *definition* stays owned by CF-01..CF-07 — this change
does **not** redefine the seam (SPEC constraint); CF-12 adds only the
timing-and-DoD rule on top.

`kind: methodology` — the change is methodology machinery; this WP edits a
standards file but its verification is a structural pytest presence assertion
(the `methodology` adapter shape). Kind and adapter agree (P-VER 9.08).

## Contract

### Files modified

```
plugins/sulis/references/standards/CONTRACT_FIRST_STANDARD.md
    (MODIFY — append `### CF-12 …` after CF-11; add a version-history row)
```

### Files created

```
plugins/sulis/scripts/tests/unit/test_seam_close_standards_presence.py
    (CREATE — sole creator; WP-006 appends its WP-standard assertion)
```

> **Peer-collision note (rubric P6):** `test_seam_close_standards_presence.py`
> is created here (sole creator). WP-006 **appends** its
> `test_work_package_standard_seam_close_dod` assertion to the same file.
> WP-006 `dependsOn` WP-005 makes the create-before-append order explicit.

### CF-12 wording (per TDD, verbatim)

```markdown
### CF-12 — Real-data acceptance is driven at seam-close, not at ship · MUST

A contract-first seam's **real-data behaviour** (the producer's actual output
crossing to the real consumer) MUST be driven the moment the seam closes — when
the integration WP completes, or when the contract WP and all the producer +
consumer WPs that `dependsOn` it reach `done` — **not** deferred to the ship
stage. The drive uses the change's covering Scenarios (the Scenarios that
verify the requirements the seam's two sides implement) against a standing app,
reading the observed-or-blocked verdict over the **real saved record**. A seam
with **no covering Scenario** is **blocked** (its real-data behaviour was never
driven), not silently passed. A seam needing an execution tier that isn't live
yet (e.g. agent-step) is **blocked** until it is, escapable only by a conscious,
recorded deferral.

CF-07 says *what* "done at the seam" means (wired + conformant). CF-12 says
*when* it is checked (seam-close, the moment it is cheap to fix) — re-timing the
catch earlier than the ship-stage backstop. This is the contract-first
application of the **observed-or-blocked** Definition-of-Done discipline.

**Anti-pattern:** letting both sides pass hermetically against fixtures, merging
them adjacent, and discovering at ship that the real data never crossed the seam
— the slow find-one-fix-one tail this rule exists to kill.
```

### Test authored here

| Test | Asserts |
|---|---|
| `test_contract_first_standard_has_cf12` | `CONTRACT_FIRST_STANDARD.md` contains a `CF-12` seam-close-timing rule with the MUST severity and the no-covering-Scenario-blocks clause |

## Definition of Done

### Red — Failing tests written
- [ ] `test_seam_close_standards_presence.py` created with `test_contract_first_standard_has_cf12`, **failing** before the CF-12 append.

### Green — Implementation makes tests pass
- [ ] `### CF-12 …` appended to `CONTRACT_FIRST_STANDARD.md` after CF-11, with the verbatim wording above.
- [ ] A version-history row added (mirroring the CF-11 row style) noting CF-12 (MUST) + the provenance (CH-01KTP7 seam-DoD gate).
- [ ] `test_contract_first_standard_has_cf12` passes.
- [ ] No existing CF-01..CF-11 section content is modified (append-only).

### Blue — Refactor complete
- [ ] CF-12 cross-references CF-07 (the anchor) by ID and names the ship gate as the *backstop* (ADR-002) so the timing relationship is explicit.
- [ ] Heading depth matches its peers (`### CF-NN`, same as CF-01..CF-11).
- [ ] The rule's prose is the standards-doc register (read by humans + agents at session start); founder-English isn't required here (this file is operator-facing methodology), but no broken cross-references.

## Sequence
- **dependsOn:** — (pure standards append; no code dependency; starts at t=0)
- **blocks:** — (WP-006 depends on this WP only for the shared test-file create-before-append)
- **Parallelisable with:** WP-001 (and, after WP-001, WP-002/003) — disjoint files

## Estimated Token Cost
- **Input:** ~4k (CONTRACT_FIRST_STANDARD.md tail + CF-07/CF-11 for style + TDD wording)
- **Output:** ~3k (≈ the CF-12 section + version row + one presence test)
- **Total:** ~7k

## Notes
- **Why split from the WP-standard amendment (WP-006):** two different standards files, two distinct rules (CF-12 = timing; WP-standard = DoD wording + `implements:` field). Bundling them would put an "and" in the title and touch two files for two responsibilities (rubric P2). Kept atomic.
- **Requirement-bridge dependency:** CF-12's resolution leans on the contract WP exposing `implements:` — that field is added by WP-006. CF-12 ships referencing it; WP-006 lands it. Neither blocks the other for *correctness* (the journey-filtered fallback in WP-002 keeps the gate working without `implements:`), so they run in parallel.

## Verification Plan
- **Adapter:** `methodology` (standards-doc presence assertion + at-least-one-other-eyes review at PR time).
- **Concrete artifact:** `plugins/sulis/scripts/tests/unit/test_seam_close_standards_presence.py::test_contract_first_standard_has_cf12`.
- **What this WP's verification proves:** CF-12 exists in the contract-first standard with the MUST severity, the seam-close timing rule, and the no-covering-Scenario-blocks clause — so the methodology now codifies the timing the gate enforces.
