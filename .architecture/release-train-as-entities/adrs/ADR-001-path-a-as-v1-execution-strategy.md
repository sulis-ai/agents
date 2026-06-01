---
id: ADR-001
title: Path A — canonical-as-spec + imperative + drift detector — as v1 execution strategy
status: accepted
date: 2026-06-01
deciders: [iain]
---

## Context

The release-train can be encoded as canonical entities and executed in
three ways:

- **Path A — Canonical-as-spec, imperative CI continues.** Workflow +
  Steps + Triggers + FailureModes live as canonical entities for
  documentation, audit, gap-spotting, queryability. The actual release
  machinery stays as `release-on-merge.yml` Bash-in-YAML. A drift
  detector validates the imperative implements the canonical.
- **Path B — Operator-driven via execute-workflow.** Operator runs
  `/sulis-brain:execute-workflow` at each release. LLM walks the
  canonical, no CI bot.
- **Path C — Build a deterministic runner.** Python (or other) reader
  that ingests the canonical files + dispatches Steps mechanically.
  Wired into CI.

The constraint on v1: brain v0.9.0 ships only an LLM-driven runner
(execute-workflow agent + skill). A deterministic compiled runner does
not exist. The platform's LangGraph autonomous runtime is a separate
work item in `apps/api/sulis/shared/workflows/` (research checkpoint
2026-05-31). No CI-bound binary today walks canonical entities.

Founder priorities (per SRD intent): *deterministic, cost-effective,
reliable execution of release workflows.* Token cost is load-bearing
("a huge requirement" in SRD). Most release-train Steps are
deterministic — only the CHANGELOG-drafting Step (Step 5) needs LLM
judgement.

## Decision

**Adopt Path A for v1.** Encode release-train as canonical entities;
keep `release-on-merge.yml` imperative (zero LLM tokens in CI); add a
drift detector at PR time that enforces conformance between the two.
Use the LLM-driven brain executor for the **dry-run preview** only
(`/sulis:release-train --dry-run`), where token cost is paid once per
release decision rather than per CI run.

## Options Considered

- **Path A — canonical + imperative + drift detector (CHOSEN).**
  Cheapest. Realises the gap-detection + structural-discipline benefit
  without new runtime code. Drift detector + dry-run-walks-canonical
  give the canonical operational meaning beyond documentation.
- **Path B — LLM walks at every release** — rejected because LLM in
  CI loop is slow + token-heavy + operator-gated. Not suited for
  high-frequency releases. Useful for one-off coordinated multi-repo
  releases but not the marketplace's per-Project pattern.
- **Path C — build a deterministic runner** — rejected for v1 as new
  build scope. Quote from the parallel session: *"Don't pick this for
  v1 unless the operator agrees to the new build. Probably the right
  v2 once Path A proves the canonical encoding is stable."* The right
  trigger to build Path C is: Path A canonical is stable + a second
  workflow (env-init, deploy, etc.) needs the runner.

## Consequences

- **Positive:** Zero new runtime code. The canonical's value (gap
  detection, queryability, audit-traceability) lands immediately.
  Drift detector closes the "documentation that decays" failure
  mode (SRD MUC-009). Imperative path is unchanged + battle-tested.
  Dry-run preview becomes meaningfully richer (LLM walks the canonical,
  describes each Step + its FailureModes for the founder).
- **Negative:** The canonical isn't literally executed in the
  imperative path — it's a specification the YAML must conform to.
  This requires the drift-detector discipline (FR-015 in the SRD).
  Without the drift detector, Path A reduces to documentation that
  silently decays. The detector is the load-bearing piece.
- **Neutral:** Future Path C work (a deterministic runner that walks
  canonical at CI time) becomes additive — the canonical encoding
  doesn't need to change for Path C to consume it.
