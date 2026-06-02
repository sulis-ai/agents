---
id: ADR-003
title: Freshness mechanism — retrieval-date + manual staleness flag; automated re-probe deferred
status: accepted
date: 2026-06-02
change: platform-contract-standard
relates-to: [FR-013, NFR-006, UC-002, MUC-003, "SRD:OpenQuestion-2"]
---

# ADR-003 — Freshness: retrieval-date stamp + manual staleness flag

## Decision

Every claim entry carries a **`retrieval-date`** (ISO-8601). On the reuse path,
the gate compares each reused claim's `retrieval-date` against a **staleness
threshold of 180 days** and surfaces claims past it for re-grounding. The
surfacing is a **manual flag** — the gate emits "this contract has N claims older
than 180 days; re-ground before relying on them" — it does **not** automatically
re-probe.

**Automated re-probe is deferred** (SRD Out of Scope) and recorded as the
canonical deferred need **`platform-contract-staleness-reprobe`**.

## The threshold

**180 days.** Rationale: long enough that a freshly-grounded contract is reused
across several changes without nagging; short enough that a platform's annual-ish
behaviour shifts (GitHub Actions runner defaults, token-permission defaults) are
caught within a release cycle. The threshold is a single named constant in the
standard so a calibration pass can tune it without touching the gate logic.

## Why

- **The date + manual flag is the minimum honest control (MUC-003).** The misuse
  case is "stale claim reused silently behind a valid-looking citation." Stamping
  the retrieval date and surfacing the age makes staleness *visible* — which is
  the whole defence. Silence is the failure; a flag is the fix.
- **Automated re-probe is genuinely out of scope.** It requires the per-platform
  probe automation (ADR-005 defers heavy automation) plus a scheduler — both
  larger than this change. Shipping the date now and deferring the automation is
  the correct slice; the date is what *enables* the later automation.
- **A named constant beats a magic number.** Calibration is expected (the
  pre-mortem names staleness as the #1 live risk); a single constant makes the
  tuning a one-line change.

## Alternatives considered

- **No date, re-ground on every reuse.** Rejected: defeats durability (NFR-006 —
  reuse must produce zero new full harness runs). Re-grounding everything every
  time is just per-change regeneration wearing a different hat.
- **Automated re-probe now.** Rejected: out of scope (SRD), and blocked on the
  probe-automation infrastructure that ADR-005 deliberately defers. Building it
  now would balloon a methodology change into an infrastructure change.
- **A per-claim TTL chosen by the author.** Rejected: invites inconsistency and a
  race-to-the-longest-TTL. A single global threshold is reviewable and uniform;
  authors don't get to grade their own freshness homework.
