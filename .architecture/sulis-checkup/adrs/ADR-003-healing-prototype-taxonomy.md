---
id: ADR-003
title: Six healing prototypes, one per finding shape, not one per tier
status: accepted
date: 2026-05-23
deciders: [iain, sea-architect-agent]
---

## Context

Every finding needs a healing path. The brief named six candidates drawn from
existing marketplace patterns:

1. **Auto-fix** (`/sea:harden`)
2. **Auto-draft remediation WP** (`/sulis-execution:backfill-*`)
3. **Founder shortcut** (`/sulis:inbox` `[1] resume`)
4. **Adversarial human-in-the-loop** (`/idc:adversarial-review`)
5. **Escalate to SRD** (`requirements-analyst`)
6. **Defer / accept-as-known** (`/sea:verify` OPEN_RISK)

The brief asks for a healing strategy *per tier*. The implicit assumption
is that each tier has one healing prototype. That assumption is wrong —
the right granularity is **per finding shape**, not per tier.

## Decision

Adopt all six healing prototypes. Each tier's primitives **classify findings
into prototypes** based on the finding's shape, NOT based on tier identity.
Tier identity informs the *primary* prototype (e.g. tier 4 leans
auto-fix-heavy because `/sea:harden` is tier-4-shaped) but every tier can
produce findings of any prototype.

The classification rule (decided per finding by the source primitive):

| Finding shape | Healing prototype |
|---|---|
| Mechanical, single-line, deterministic test for success | Auto-fix |
| Concrete gap, fix has one canonical shape, but requires careful change | Auto-draft remediation WP |
| Routine action the founder triggers (read, open, re-run) | Founder shortcut |
| Design decision (rename, split, redesign) | Adversarial HIL |
| Missing requirement, not missing code | Escalate to SRD |
| Acknowledged risk, no fix this run | Defer / accept-as-known |

## Options Considered

### Option A — One prototype per tier (rejected)

**Pros:** simple to explain ("tier 2 = auto-fix; tier 5 = adversarial").

**Cons:** wrong-shape-fit at every tier. Tier 2 has both auto-fixable
findings (rotate this secret) AND design findings (this access-control
gap needs threat-model review). Forcing all tier 2 into one prototype
produces bad healing for half the cases.

**Rejected because:** tiers are about *what gets checked*, prototypes are
about *what shape the fix takes*. Conflating them destroys the model.

### Option B — Single uniform prototype (always draft WP) (rejected)

**Pros:** simplest possible flow. Every finding becomes a WP; founder ships
WPs through the executor.

**Cons:**
- Loses the auto-fix wins at tier 4 (`/sea:harden`'s reason for existing).
- Annoying for trivial fixes ("write me a WP to add a timeout to this
  function" is comically over-process for a one-line change).
- The marketplace already has six healing patterns in use; converging
  on one would mean re-implementing what already works.

**Rejected because:** the existing prototypes work. The win is *composing*
them coherently, not eliminating them.

### Option C — Six prototypes, classification driven by finding shape (chosen)

**Pros:**
- Reuses every existing marketplace pattern.
- Each finding gets the right shape of fix.
- Founder's mental model is unchanged ("I get a draft fix for this; I
  get a shortcut for that; I get a perspective for the third") — the
  checkup just *aggregates* and *routes*.

**Cons:**
- Six surfaces have six UXes. Some inconsistency.
- Source skills need to be classification-aware (they need to declare
  which prototype each of their findings is). This is a one-time
  per-skill cost.

**Accepted because:** the inconsistency cost is dwarfed by the wrong-shape
cost of options A and B.

## Per-tier *primary* prototype (not exclusive)

The TDD's per-tier table captures this in detail. Summary:

| Tier | Primary prototype | Secondary |
|---|---|---|
| 1 | Auto-draft WP (build errors → fix-this WP) | Founder shortcut (open at error) |
| 2 | Auto-fix (secret rotation, header add) | Adversarial (access control); Escalate (CVE coord) |
| 3 | Auto-draft WP (test failures → per-test WP) | Escalate to SRD (spec ambiguity); shortcut (re-run test) |
| 4 | Auto-fix via `/sea:harden` (timeouts, OTel) | Auto-draft WP (per-call-site judgement) |
| 5 | Auto-draft WP (naming changes) | Adversarial (module splits); defer (legitimate jargon) |
| 6 | Auto-draft WP (dead-code removal) | Adversarial (migration state); defer (low-value tests) |
| 7 | Defer (whole tier deferred for v1) | — |

## How classification information travels

Each source primitive (e.g. `/sea:codebase-audit`) tags each finding with
its prototype in the finding's metadata. The checkup aggregator reads the
tag and routes accordingly. Schema (cross-reference TDD §7):

```python
class Finding(TypedDict):
    finding_id: str
    tier: int
    source: str
    severity: ...
    recommended_healing: Literal[
        "auto_fix", "draft_wp", "shortcut",
        "adversarial", "escalate_srd", "defer"
    ]
    hard_stop: bool
```

Source skills that pre-date this design will be updated incrementally to
add the `recommended_healing` field. Until then, checkup applies a
default-by-tier mapping (the primary column above) as a fallback.

## Consequences

**Positive:**
- Existing patterns reused; no new healing-pattern to invent.
- Founders see the right shape of fix for each finding.
- New skills authored under `sulis:add-skill` will declare their
  prototype mappings as part of Gate 2 scope lock (one extra item).

**Negative:**
- Source skills must declare prototypes per finding (one-time cost).
- The checkup needs a fallback for legacy findings (default-by-tier map).
- The healing UX surface area is larger than a single-prototype design;
  founders learn six patterns instead of one.

**Neutral:**
- The healing prototype taxonomy is a marketplace-wide vocabulary. It
  belongs in `plugins/sulis/references/healing-prototypes.md` (new ref
  doc, to be authored alongside checkup) — same plugin as
  `founder-facing-conventions.md`.

## Per-prototype contracts

For SRD-author reference. Each prototype must satisfy:

| Prototype | Contract |
|---|---|
| `auto_fix` | Target HD-NNN-{slug}.md drafted at `status: accepted` (skips proposed → accepted promotion). Runs `/sea:harden HD-NNN` immediately. Failing characterisation test MUST exist or auto-fix is downgraded to draft_wp. |
| `draft_wp` | HD-NNN-{slug}.md drafted at `status: proposed`. Promotion to `accepted` is a founder action. Then `/sea:harden` picks it up. |
| `shortcut` | A numbered action in the CHECKUP.md report's "What to do" section. Echo-before-act per founder-facing-conventions Rule 3. |
| `adversarial` | A perspective document drafted at `.checkup/{project}/perspectives/{finding-id}.md` containing the finding context, the proposed approaches, and the trade-offs. Surfaced as a shortcut "review perspective" in the report. |
| `escalate_srd` | A short note at `.checkup/{project}/escalations/{finding-id}.md` naming the spec question + the recommended SRD action. Surfaced as a shortcut "open SRD facilitation" in the report. |
| `defer` | Recorded in `.checkup/{project}/dismissed.json` with reason + date + revisit trigger (per inbox dogfood OPEN_RISK structure). Surfaced in report's "Previously dismissed" section in subsequent runs. |
