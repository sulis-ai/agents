---
id: ADR-005
title: Two-tier report format — founder-readable above, technical below
status: accepted
date: 2026-05-23
deciders: [iain, sea-architect-agent]
extends: external:code-review-skill — section "Report Format — Two Tiers"
---

## Context

The checkup report has two audiences: the founder (non-technical), and
engineers + downstream agents (technical). Three viable formats:

1. **Single founder-facing report.** Plain language throughout. Operators
   read it but lose the precision they need.
2. **Single technical report.** Full taxonomy throughout. Founders bounce.
3. **Two reports — `CHECKUP_FOUNDER.md` and `CHECKUP_ENGINEER.md`** — same
   findings, two writeups.
4. **Two tiers in one file** — founder-facing first, technical below a
   `## Technical detail` heading. The pattern `/sulis:code-review` validated.

## Decision

**Adopt the two-tiers-in-one-file pattern from `/sulis:code-review`.** Founder
tier reads top-down; technical tier sits below the `## Technical detail`
heading; downstream agents (`/sulis:harden-codebase`, future `/code-review` re-runs)
read the technical tier verbatim.

## Options Considered

### Option 1 — Single founder report

**Pros:** simple. One file.

**Cons:**
- Engineers lose the precise taxonomy they need to act (e.g. `/sulis:harden-codebase`
  needs to read the HD-NNN delta IDs; founder tier shouldn't carry them).
- Founder-tier translations of technical findings lose information
  (e.g. "circuit breaker missing" → "no backup plan when X is slow" loses
  the CB-vs-bulkhead distinction the engineer needs to make).

**Rejected.**

### Option 2 — Single technical report

**Pros:** engineers happy. Downstream agents happy.

**Cons:** founders bounce. The whole point of `/sulis:checkup` is the
founder uses it.

**Rejected.**

### Option 3 — Two separate files

**Pros:** clear separation. Each file optimised for its audience.

**Cons:**
- Drift. Two files diverge over time even when the same finding moves
  through each.
- Founder navigates to wrong file, reads jargon, gets frustrated.
- Authors maintain two file generators in the checkup code.

**Rejected because:** the `/sulis:code-review` decision document explicitly
called this out — two-tier-one-file is the calibrated form.

### Option 4 — Two tiers in one file (chosen)

**Pros:**
- Founder reads top-to-bottom and stops naturally when their need is met.
- Engineers scroll past founder tier to the `## Technical detail` heading.
- Same evidence; two writeups; one file; no drift risk.
- Downstream agents parse the technical tier deterministically (it
  carries the IDs they need).
- Calibrated pattern in `/sulis:code-review`'s `SKILL.md` — already proven
  to work on real PRs.

**Cons:**
- Authors writing report templates need to know both writing styles.
  Mitigated by the existing `/sulis:code-review` pattern serving as the
  template.

**Accepted because:** the pattern is already in production for code-review;
adopting it for checkup is the consistent move.

## Format specification

```
# Project checkup — {project}

> **When:** ... > **Overall:** {plain English verdict}

## At a glance
[Seven-tier traffic light]

## What needs your attention
[Findings in plain English, ordered by load-bearing-ness. Severity
 mapped to founder-friendly labels — Must fix, Strongly recommend,
 Worth fixing, Minor.]

---

## Technical detail
> Below this point is for engineers and downstream agents.

### Run metadata
[invocation_id, override_flags, ooda_cycles_executed, etc.]

### Tier-by-tier
[Each tier with full finding IDs, severity letters, source primitives,
 healing-action references, recommended_healing prototype.]

### Healing actions queued
[HD-NNN paths, perspective document paths, escalation note paths,
 dismissed-entry references.]

### Methodology self-attestation
[Per-OODA-cycle log; cycle-2/3 entry justifications; bound enforcement;
 founder-facing-conventions FE-06 passes; Reserved-Vocabulary Sweep
 result.]
```

## Translation table (mirrors /sulis:code-review)

| Internal | Founder tier |
|---|---|
| `overall_verdict: pass` | "Everything looks good" |
| `overall_verdict: partial` | "Some things need your attention" |
| `overall_verdict: fail` | "Several things need fixing" |
| `overall_verdict: stopped` | "[Tier name] needs fixing before the rest can be checked" |
| `severity: critical` | "Must fix" |
| `severity: high` | "Strongly recommend fixing" |
| `severity: medium` | "Worth fixing" |
| `severity: low` | "Minor — for awareness" |
| Tier 1..7 | Plain founder questions per TDD Part 3 ("Does it run?" etc.) |

## Founder-facing-conventions compliance

| Rule | Application in CHECKUP.md |
|---|---|
| Rule 1 (FE-06) | Every founder-tier string passes the read-aloud test. Pre-write self-check sweep covers it. |
| Rule 2 (name first, ID parenthetical) | "Build verification (tier 1)" not "Tier 1 (Build verification)". HD-NNN IDs only in the technical tier. |
| Rule 3 (echo before act, prompt before destroy) | Every numbered shortcut at the bottom of the report echoes what it'll do BEFORE doing it. Destructive shortcuts (apply auto-fix in production) prompt. |
| Rule 4 (translate at output) | Internal data (HD-NNN, OODA cycle counts, finding_id) translated to founder language at render time, not at storage. |
| Rule 5 (errors explain what + what-to-do) | If checkup itself fails (e.g. probe tool missing), report explains in founder terms what failed AND how to fix (`brew install ast-grep`). |

## Consequences

**Positive:**
- One file, two audiences, no drift.
- Founder stops reading naturally when their need is met.
- Engineers and downstream agents have full taxonomy below the fold.
- Pattern reuses an already-validated convention from `/sulis:code-review`.

**Negative:**
- Long file when there are many findings. Mitigated by passing-tier
  collapse in the at-a-glance section.

**Neutral:**
- Authors writing report templates have to maintain both registers.
  The `/sulis:code-review` SKILL.md is the canonical example to imitate.
