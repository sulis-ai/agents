---
id: ADR-004
title: Fail-fast on missing Project entity — no auto-route to discovery
status: accepted
date: 2026-06-01
deciders: [iain]
resolves: SRD Open Question 2
---

## Context

When a founder runs any sulis command in a consumer repo with no
`.sulis/projects/<slug>.jsonld`, the command can't bind to a Project
entity. Two ways to handle this:

1. **Auto-route to discovery.** Detect the missing entity, transparently
   launch `/sulis:discover-project`, then resume the originally
   requested command.
2. **Fail-fast with a clear error.** Surface the missing-entity
   condition + tell the founder to run `/sulis:discover-project`
   first.

The marketplace already has a stated principle from `release-train`
ADR-001: *governance over mystification*. The founder should always
know what command is about to run.

Auto-routing has surface appeal — "less friction for the founder" —
but the cost is hidden state changes:

- Discovery writes a Project entity at `.sulis/projects/<slug>.jsonld`.
  That's a change the founder didn't explicitly ask for.
- Discovery asks human questions during its Ask phase. Auto-routing
  inverts the founder's mental model — they invoked one command and
  ended up answering questions for a different command's prereq.
- A failed discovery (e.g., non-git directory) under auto-routing
  surfaces as "the command failed for an unrelated reason" — harder to
  diagnose than a clean fail-fast.

## Decision

**Fail-fast with a clear error.** No auto-routing.

When a sulis command (release-train, run-wp, etc.) needs a Project
entity and doesn't find one, it exits non-zero with an explicit
message:

> *"No Project entity found at `.sulis/projects/<slug>.jsonld`. This
> repo has not been set up for Sulis yet. Run `/sulis:discover-project`
> first to mint the Project entity, then re-run this command."*

The founder sees one effect from one command. No silent state changes.
No nested human-ask flows. No surprise file writes.

This decision also rules out the optional v2 auto-suggest Trigger
named in SRD FR-003 — the canonical `discover-project` Workflow ships
with one Trigger only (manual), and the v2 trigger is deferred until
real founder-experience evidence shows fail-fast is too costly.

## Options Considered

- **Fail-fast with clear error (CHOSEN).** Aligns with governance
  principle. One command, one effect. Founder always knows what's
  about to happen.
- **Auto-route to discovery** — rejected. Silent state changes; nested
  human-ask flows; harder-to-diagnose failures; weakens the principle
  the marketplace explicitly committed to in release-train ADR-001.
- **Prompt the founder "run discovery now? Y/n"** — rejected as a
  half-measure. Either we trust the founder to read the error and run
  the right command, or we don't. The prompt itself is a UI surface
  with its own failure modes (timeouts, non-interactive contexts).

## Consequences

- **Positive:** Founder always knows what command runs. No surprise
  writes. The clear-error path makes the recovery action obvious
  (run the named command). Consistent with the marketplace's stated
  governance principle.
- **Negative:** A first-time consumer who runs `/sulis:release-train`
  before discovery sees a single error rather than a transparent flow.
  Mitigation: the error message itself is the next-step instruction;
  one-line copy-paste to recovery.
- **Neutral:** Auto-suggest Trigger remains a v2 option. If we get
  data showing fail-fast is genuinely too costly (e.g., founders
  bouncing off the error rather than running discovery), the v2
  Trigger can ship later. v1 stance is conservative.

## Composition

This decision affects:

- `triggers.jsonld` — only ONE Trigger in v1 (`manual-discover-project-invocation`).
- Other sulis skills (release-train, run-wp, etc.) need their
  Project-entity-required prerequisite check to surface the error in
  the form named above. **This is out of scope for this change** — the
  prereq check lives in those other skills; the next consumer of
  `.sulis/projects/<slug>.jsonld` to add the check should reference
  this ADR.

The v2 deferral is captured in `ARCH.yaml` `deferred_to_v2`.
