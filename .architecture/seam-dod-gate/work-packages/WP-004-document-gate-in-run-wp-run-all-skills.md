---
# Identity (WP-01)
id: WP-004
title: Document the seam-close gate in the build-loop skills (run-wp, run-all)
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
sequence_id: WP-004
dependsOn: [WP-002, WP-003]
blocks: []

# Composite (WP-08)
child_wps: []
kinds: null

estimated_token_cost:
  input: 5k
  output: 4k
tdd_section: §How the gate hooks (run-wp/run-all document the gate); §Test surface File 2 (the two doc assertions)
adrs: [ADR-003]
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/unit/test_seam_close_gate_wiring.py

rollback: |
  Revert the run-wp/SKILL.md and run-all/SKILL.md additions (pure prose
  appends). The two doc-assertion tests revert to Red. No code behaviour
  changes — the skills only describe the gate; the logic lives in wpx-step12.
---

# Document the seam-close gate in the build-loop skills

## Context

TDD §"How the gate hooks into the build loop" + ADR-003 §Consequences:
*"run-wp / run-all SKILL.md gain documentation of the seam-close gate and its
founder-English block surfacing (no behaviour in the skills themselves beyond
surfacing the wrap envelope's gate-block)."*

The behaviour lives in `wpx-step12` (WP-003). This WP makes the two build-loop
skills **describe** the gate so (a) the wiring tests
`test_runwp_documents_seam_close_gate` / `test_runall_documents_seam_close_gate`
(authored failing in WP-003) pass, and (b) a session reading either skill knows
that a `blocked` seam at WP-done halts seam-close and how the founder-English
block is surfaced.

`kind: methodology` — the change is methodology machinery; this WP edits skill
prose but its verification is structural pytest doc-shape assertions (the
`methodology` adapter shape), not link/readability checks (which would be the
`documentation` adapter). Kind and adapter agree (P-VER 9.08).

## Contract

### Files modified

```
plugins/sulis/skills/run-wp/SKILL.md    (MODIFY — add a seam-close-gate subsection at the WP-done step)
plugins/sulis/skills/run-all/SKILL.md   (MODIFY — add a seam-close-gate subsection at seam-spanning-WP completion)
```

### Files modified (shared test file — append only)

```
plugins/sulis/scripts/tests/unit/test_seam_close_gate_wiring.py
    (MODIFY — the two run-wp/run-all doc-assertion functions; created by WP-003)
```

> **Peer-collision note (rubric P6):** `test_seam_close_gate_wiring.py` is
> created by WP-003 (sole creator); this WP only **appends** its two assertion
> functions. `dependsOn: WP-003` makes the create-before-append ordering
> explicit so the two WPs never co-create the file.

### What the documentation states (both skills)

1. **When it fires:** at the WP done-transition (`wpx-step12 wrap` step 12.2a) —
   for run-all, specifically when a seam-spanning WP (integration / `kind:
   composite`, or the last WP of a contract fan-out) completes.
2. **What it does:** drives the closing seam's covering Scenarios via the
   acceptance runner and reads observed-or-blocked over the real saved record.
3. **What `blocked` means:** seam-close halts as "not done" — surfaced in
   **founder English** (which seam, by title; what wasn't driven). The skill
   shows the `gate_block` field from the wrap envelope to the founder; it does
   **not** invent its own message.
4. **The escape:** a knowingly-deferred seam proceeds with `--allow-deferred`,
   recorded — default is observed-or-blocked.
5. **Defence-in-depth (ADR-002):** this is the primary catch; the ship gate
   (4.8) remains a backstop.

### Doc-shape assertions made green by this WP (File 2)

| Test | Asserts |
|---|---|
| `test_runwp_documents_seam_close_gate` | `run-wp/SKILL.md` contains a seam-close-gate subsection naming the WP-done firing point + the observed-or-blocked + `--allow-deferred` discipline |
| `test_runall_documents_seam_close_gate` | `run-all/SKILL.md` documents the gate firing when a seam-spanning WP completes |

## Definition of Done

### Red — Failing tests written
- [ ] The two assertions exist (authored failing in WP-003); confirm they fail before this WP's edits (skills not yet documented).

### Green — Implementation makes tests pass
- [ ] `run-wp/SKILL.md` gains the seam-close-gate subsection at the WP-done step.
- [ ] `run-all/SKILL.md` gains the seam-close-gate subsection at seam-spanning-WP completion.
- [ ] `test_runwp_documents_seam_close_gate` and `test_runall_documents_seam_close_gate` pass.
- [ ] WP-003's three `wpx-step12` wiring tests still pass (this WP doesn't touch them).

### Blue — Refactor complete
- [ ] The prose is **founder-English at the surfacing layer** (FE): the example block the skill shows the founder names the seam by title and the un-driven behaviour, with no `dna:` / `WP-` ids. Internal IDs (ADR-NN, CF-12) appear only in cross-reference footnotes, not in the founder-facing example.
- [ ] Both subsections cross-reference CF-12 (the timing rule) and ADR-002 (ship-gate-as-backstop) by name, consistent with the skills' existing cross-reference style.
- [ ] No behavioural instructions added beyond surfacing the wrap envelope's `gate_block` (the skills carry no gate logic — ADR-003).

## Sequence
- **dependsOn:** WP-002 (so the docs describe the real module behaviour), WP-003 (creates the shared wiring-test file this WP appends to; also the behaviour the docs describe)
- **blocks:** —
- **Parallelisable with:** WP-005, WP-006 (different files) — but ordered after WP-003 for the shared-file create-before-append rule

## Estimated Token Cost
- **Input:** ~5k (both SKILL.md files, the TDD hook section, WP-003's envelope contract)
- **Output:** ~4k (≈ two prose subsections + two assertion functions)
- **Total:** ~9k

## Notes
- **Why a separate WP from WP-003:** WP-003 owns the *behaviour* (wpx-step12) + the structural site tests; this WP owns the *documentation* in two different skill files. Splitting keeps each WP single-responsibility and lets the docs land after the behaviour they describe is real (so the prose doesn't describe a not-yet-wired gate). Both are `kind: methodology` (the verification is structural pytest assertions);
the split is by responsibility (behaviour vs documentation), not by kind.
- **Why it appends to WP-003's test file rather than its own:** the two doc assertions belong to the same File-2 wiring suite as the wpx-step12 assertions (TDD §Test surface File 2 enumerates all five together). One file, one creator (WP-003), append-only by WP-004 — the rubric-P6-clean shape.

## Verification Plan
- **Adapter:** `methodology` (structural doc-shape assertions; the skills are read by sessions, not executed).
- **Concrete artifact:** `plugins/sulis/scripts/tests/unit/test_seam_close_gate_wiring.py` (the two `*_documents_seam_close_gate` assertions).
- **What this WP's verification proves:** both build-loop skills document the seam-close gate at the correct firing point with the observed-or-blocked + `--allow-deferred` discipline and the founder-English surfacing — so a session running either skill knows a `blocked` seam halts seam-close and how to show it to the founder.
