---
id: WP-005
title: Extend plan-work to emit the platform: / touch-class: WP-frontmatter field
status: pending
change_id: "01KT3X2M0JHFN583DKKV77W83C"
kind: methodology
primitive: extend
group: EXPAND
sequence_id: WP-005
dependsOn: [WP-004]
blocks: [WP-007]
estimated_token_cost:
  input: 4k
  output: 3k
tdd_section: "Open Architecture Questions OAQ-4 (line 206); Decomposition signal (lines 333-335); FR-015"
adrs: [ADR-006]
verification:
  adapter: methodology
  artifact: tests/methodology/test_plan_work_platform_field.py::test_plan_work_emits_platform_field
---

## Context

Extends `plugins/sulis/skills/plan-work/SKILL.md` so it **emits** the
`platform:` / `touch-class:` WP-frontmatter field on any WP that touches a
third-party platform. This is the detection signal P-PLAT (WP-004) reads to
decide whether a WP set requires a Platform Contract (OAQ-4 / MUC-004).

**TDD reference:** OAQ-4 (line 206) recommends an *explicit* `platform:` +
`touch-class: write|deploy|read` field on the integration WP, set by
`/sulis:plan-work` — scanning prose for platform names is brittle. The
Decomposition signal (lines 333-335) explicitly says: *carry OAQ-4 into
`plan-work` so P-PLAT has a detection signal.* This WP is that carry.

**This change dogfoods its own field.** This very WP set uses the new field:
WP-006 (the GitHub Actions contract) declares `platform: github-actions,
touch-class: read-only` — authoring the contract *reads* GitHub docs, it does
not write to or deploy through GitHub. WP-005 makes `plan-work` capable of
emitting that declaration for future changes.

**Why this depends on WP-004.** P-PLAT defines the *meaning* of `platform:` /
`touch-class:` (the values, the write/deploy-vs-read-only semantics, the
fail condition). `plan-work` *emits* a field whose contract is owned by
P-PLAT. Emitting before the meaning is fixed risks divergence.

**Why this is separate from WP-003 (gate wiring).** WP-003 owns the *design*
skills (`specify`, `draft-architecture`); WP-005 owns the *decomposition*
skill (`plan-work`). Disjoint file surface — no collision. The design phase
asks for a contract; the decompose phase tags WPs so the rubric can check.

**Pre-Work Prior-Art Check:** `plan-work/SKILL.md` already emits a rich
WP-frontmatter block (including the `verification:` field added by the
verification-by-design change). This WP **extends** that emission with two
more keys; it does not restructure the frontmatter machinery.

## Contract

### Files modified

- `plugins/sulis/skills/plan-work/SKILL.md` — EXTEND (frontmatter emission +
  the triage that decides when to set the field).

### What plan-work emits

When a WP's scope touches a third-party platform, `plan-work` sets:

```yaml
platform: "<lowercase-hyphenated slug>"    # the platform the WP touches
touch-class: "write | deploy | read-only"  # per ADR-001 gate posture
```

The skill prose gains:
- **A triage step:** does this WP touch a third-party platform? If yes, set
  `platform:` to the slug and `touch-class:` per the operation
  (write/deploy/read-only — the same axis ADR-001 gates on).
- **The default:** WPs that touch no third party omit both fields (absence =
  "no gated touch", which P-PLAT reads as not-applicable).
- **Cross-reference:** the field's full semantics + the fail condition live in
  P-PLAT (WP-004) — `plan-work` references the rubric phase, does not restate it.

## Definition of Done

### Red — Failing test written first

- [ ] `tests/methodology/test_plan_work_platform_field.py::test_plan_work_emits_platform_field`
  asserts:
  - `plan-work/SKILL.md` documents the `platform:` + `touch-class:`
    frontmatter keys.
  - It states the write/deploy/read-only value set.
  - It references the P-PLAT rubric phase (by name `P-PLAT`) as the consumer.
- [ ] Initial run FAILS (the field is not documented yet).

### Green — Implementation makes the test pass

- [ ] Extend `plan-work/SKILL.md` with the triage step + the two frontmatter
  keys + the read-only-default behaviour.
- [ ] Reference P-PLAT (WP-004) as the field consumer (no restating of
  P-PLAT's fail logic).
- [ ] Red-phase test passes.

### Blue — Refactor + polish

- [ ] The new keys sit alongside the existing `verification:` field in the
  documented frontmatter block (one coherent WP-frontmatter schema).
- [ ] The triage step is FE-aware: the founder-facing rationale (why a WP is
  tagged) uses plain language, not internal IDs.
- [ ] No duplication of ADR-001's gate-posture table — reference it.

## Sequence

- **Sequence ID:** WP-005
- **dependsOn:** WP-004 (P-PLAT owns the field's meaning + fail condition).
- **blocks:** WP-007 (the conformance/fixture tests assert P-PLAT detects via
  this field on a synthetic WP set).
- **Parallelisable with:** WP-006 (disjoint file surface — this WP owns
  `plan-work/SKILL.md`; WP-006 owns `github-actions.md`). Note both can run
  once their respective upstreams land.

## Estimated Token Cost

- **Input:** ~4k (`plan-work/SKILL.md` + ADR-006 + the OAQ-4 disposition).
- **Output:** ~3k (triage step + frontmatter key docs).
- **Total:** ~7k.

## Notes

- **Authority split (intentional):** P-PLAT (WP-004) owns the *meaning* of the
  field; `plan-work` (this WP) owns *emitting* it. This keeps the enforcer as
  the single source of the field's semantics and avoids two divergent
  descriptions.
- This change is the **first dogfood** of the field — WP-006 carries
  `platform: github-actions, touch-class: read-only` in its own frontmatter.
- `read-only` for WP-006 is correct: authoring the GitHub Actions contract
  *reads* GitHub docs (and runs read-only probes); it does not write to or
  deploy through GitHub.

## Verification Plan (per-WP)

- **Adapter:** `methodology` — **Shape 1 (concrete).**
- **Artifact:** `tests/methodology/test_plan_work_platform_field.py::test_plan_work_emits_platform_field`.
- **Observable:** a future change touching a platform gets its integration WPs
  tagged so P-PLAT can detect the gated touch. Structural test asserts the
  emission prose + the P-PLAT reference; end-to-end detection is exercised by
  WP-007's synthetic WP-set fixtures.
- **No resilience primitive:** methodology prose.
