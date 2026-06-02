---
id: ADR-001
title: Gate boundary — hard-gate write/deploy, soft-recommend read-only
status: accepted
date: 2026-06-02
change: platform-contract-standard
relates-to: [FR-014, NFR-008, UC-001, "issue:137"]
---

# ADR-001 — Gate boundary: hard-gate write/deploy, soft-recommend read-only

## Decision

The Platform Contract design-stage gate **fires hard** (blocks design from
proceeding) for third-party touches that **write to or deploy through** the
platform. For **read-only** touches (a GET against a third-party API, reading
public data) the gate fires **soft** — it recommends a lightweight Platform
Contract but does not block.

This is the founder-resolved default (dispatch item 3 / FR-014 / SRD Open
Question 3), confirmed here at standard-authoring time.

## Override path

The boundary is a default, not a law. The standard records that a change author
(or the founder) may **escalate a read-only touch to hard-gated** when the
read informs a write/deploy decision (the pre-mortem reason 3: "a read-only
integration that turned out to write"). The escalation is recorded in the
change's SRD/TDD as an explicit one-line note; no ADR is required to escalate.
Conversely, **de-escalating a write/deploy touch to soft** is *not* permitted by
author discretion — it requires a new ADR superseding this one, because the
write/deploy class is exactly where a fabricated assumption is most expensive
(the triggering incident was a deploy-path touch).

## Why

- **The triggering incident was a deploy-path touch.** The reusable-workflow
  defect manifested at the first real release — a half-applied production
  release. The class of failure the standard exists to prevent lives on the
  write/deploy seam. Gating there is where the value is.
- **Read-only touches are cheaper to get wrong.** A misread of a read-only API
  contract typically surfaces as a handled error or empty result, not a
  half-applied deploy. Hard-gating every read-only GET would impose contract
  ceremony with a poor cost/benefit ratio and train authors to resent the gate.
- **NFR-008 requires the boundary be reviewed explicitly, not decided silently.**
  This ADR *is* that explicit review.

## Alternatives considered

- **Hard-gate every third-party touch (read or write).** Rejected: imposes
  contract ceremony on low-risk reads, inflating the cost of the gate and
  encouraging MUC-004 (bypass via skill-prose edit) out of friction. The
  pre-mortem's "too narrow" risk is mitigated by the escalation path above, not
  by gating everything.
- **Soft-recommend everything (no hard gate at all).** Rejected: this is the
  status quo that let the reusable-workflow incident through. A soft
  recommendation is exactly what a structural-test-green design ignores. The
  gate must be able to *block* on the write/deploy class or it is not a control.
- **Gate on data-sensitivity rather than write/deploy.** Rejected: sensitivity
  is a harder line to draw mechanically (it needs per-field classification),
  and the failure class the standard targets is integration-contract fabrication,
  not data exposure. Write/deploy is the mechanically-detectable, incident-aligned
  axis.
