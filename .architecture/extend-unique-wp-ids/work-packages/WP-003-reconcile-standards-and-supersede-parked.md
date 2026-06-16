---
id: WP-003
title: "Reconcile WORK_PACKAGE_STANDARD id row + CW-04 to the prefixed shape; supersede the parked canonicalise-cross-wp-ids effort"
status: pending
change_id: 01KTR381SP5DMB1N8RBKHCVV9Q
kind: docs
primitive: extend
group: REINFORCE
sequence_id: WP-003
dependsOn: []
blocks: []
estimated_token_cost:
  input: 6k
  output: 4k
tdd_section: "§4 Mint path (standards), §6 Supersession; ADR-002"
adrs: [ADR-002]
verification:
  na: true
  justification: "Standards-prose edits + retirement of an empty parked stub; no runtime surface. The id shape these standards describe is verified by WP-001's tests. Correctness is a docs-truth read against the shipped matcher."
---

> **ID-SCHEME NOTE:** this WP's own id is the **bare** `WP-003` (chicken-and-egg,
> ADR-002) even though the standards it edits *document* the new prefixed shape.

## Context

Two standards describe the WP id shape and own its back-compat narrative:

- `WORK_PACKAGE_STANDARD.md` — the WP-01 `id` row (L47), which today documents
  `WP-NNN` / `WP-{SOURCE}-{NNN}` and the branch-ref realisation of change_id
  disambiguation (added for #283).
- `change-work-standard.md` — CW-04, whose **WP branch refs** subsection (added
  in CW v0.3.0 for #283) namespaces WP *branches* per change. This change adds
  the id-label twin.

Both must be reconciled to read the implemented `{CH-HANDLE}-WP-NNN` shape and
name the one-release back-compat window for legacy bare ids — exactly mirroring
how #283 documented its branch scheme and tracked its fallback removal as a
follow-up. This WP also retires the superseded parked effort (ADR-002 §4).

**Primitive = extend; group = REINFORCE / Document.** Standards prose catches up
to shipped behaviour; an empty parked stub is retired.

## Contract

### Files modified

```
plugins/sulis/references/standards/WORK_PACKAGE_STANDARD.md   (WP-01 id row L47 + version-history entry)
plugins/sulis/references/change-work-standard.md              (CW-04 id-label twin subsection + version-history entry)
.architecture/canonicalise-cross-wp-ids/                       (retire — see Behavioural contract)
```

### Behavioural contract

1. **`WORK_PACKAGE_STANDARD` WP-01 `id` row (L47)** — documents the prefixed
   shape `{CH-HANDLE}-WP-NNN` as the minted form (with `change_id:` populated),
   keeps `WP-NNN` / `WP-{SOURCE}-{NNN}` documented as the legacy/source-tagged
   shapes understood for one release, and states the back-compat window. Cross-
   references CW-04 and ADR-002 (this change) alongside the existing ADR-001
   (#283 branch scheme). A dated additive version-history entry is appended.

2. **`change-work-standard` CW-04** — gains the **WP id label** twin of the
   existing WP branch-ref subsection: a WP's id is `{CH-HANDLE}-WP-NNN`,
   globally unique across changes, with the per-change `NNN` sequence unchanged;
   legacy bare `WP-NNN` ids stay understood for one release; fallback removal is
   a tracked follow-up. A dated additive version-history entry is appended.

3. **Supersede `canonicalise-cross-wp-ids`** (ADR-002 §4) — the parked effort
   has no real design (only `.architecture/canonicalise-cross-wp-ids/
   work-packages/.executor-WP-001.md`). Retire it: remove the stale stub
   directory (or, if any process expects the path to persist, leave a one-line
   `SUPERSEDED.md` pointing at this change). Also retire its `.changes/` SPEC
   stub if one exists for it. The executor confirms which retirement form the
   repo's conventions expect; the contract is that there is exactly **one**
   canonical effort for unique WP ids (this one) and no dangling duplicate.

### What this WP is NOT

- It does **not** edit code (WP-001) or the mint/agent surfaces (WP-002).
- It does **not** remove legacy bare-id support from the standards — both shapes
  are documented as valid for one release; removal is the tracked follow-up.

## Definition of Done

### Red — n/a (standards prose)

Per EP-07, standards/prose edits and retiring an empty stub do not require a
characterisation test. The id shape these standards describe is proven by
WP-001's tests.

### Green — edits land

- [ ] `WORK_PACKAGE_STANDARD` WP-01 id row reads the prefixed shape + documents
      the one-release legacy back-compat window; version history appended.
- [ ] `change-work-standard` CW-04 carries the WP-id-label twin subsection +
      back-compat window + follow-up-removal note; version history appended.
- [ ] Both standards cross-reference ADR-002 (this change) and stay consistent
      with the #283 ADR-001 branch scheme they already reference.
- [ ] `canonicalise-cross-wp-ids` parked effort retired (stub removed or
      `SUPERSEDED.md` left, per repo convention); no dangling duplicate spec.

### Blue — hygiene

- [ ] The two standards agree with each other and with the mint surfaces
      (WP-002) on the exact shape and the exact back-compat phrasing — no drift.
- [ ] Version-history entries follow the existing additive-entry format (dated,
      "additive only — no existing requirement changed in meaning").
- [ ] The supersession is recorded once (ADR-002 already states it; the
      retirement action matches).

## Sequence

- **dependsOn:** none — independent markdown.
- **blocks:** none.
- **Parallelisable with:** WP-001, WP-002.

## Estimated Token Cost

- **Input:** ~6k (the two standards' id/CW-04 regions + the parked-effort dir).
- **Output:** ~4k (the reconciled id row + CW-04 twin subsection + two version-
  history entries + the retirement).
- **Total:** ~10k.

## Notes

- **Why separate from WP-002:** WP-002 edits *instructional* surfaces (how an
  agent mints); WP-003 edits *normative* standards (what the shape IS) and
  performs the supersession bookkeeping. Different audiences, cleanly separable;
  but both are markdown and could be executed back-to-back.
- **Why the supersession lives here, not in its own WP:** it is a one-line
  bookkeeping retirement of an empty stub, naturally bundled with the standards
  reconcile that documents the canonical effort. A standalone WP for deleting a
  stray journal file would be over-decomposition (constraint 5).

## Verification Plan

- **What is verified:** the two standards document `{CH-HANDLE}-WP-NNN` and the
  one-release back-compat window consistently with the shipped matcher (WP-001)
  and the mint surfaces (WP-002); the parked duplicate is retired. Verified by
  reading the edited standards against the shipped behaviour and confirming no
  dangling `canonicalise-cross-wp-ids` design remains — a docs-truth /
  bookkeeping check, not a test artifact (`na` per frontmatter justification).
- **Per-kind adapter (`docs`):** no executable artifact; correctness is the
  read-against-shipped-behaviour + retirement-confirmed check above.

## Acceptance Evidence

- Branch: wp/extend-unique-wp-ids/wp-003-reconcile-standards-and-supersede-parked (deleted post-merge)
- Health status: `n/a (no-deploy profile)`
- Smoke-test verdict: n/a
- Completed: `2026-06-10T08:31:54Z` (Step 12 by calling session)
