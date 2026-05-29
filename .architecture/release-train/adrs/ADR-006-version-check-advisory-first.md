---
id: ADR-006
title: version-check ships advisory-only this cycle; required is a later founder-gated step
status: accepted
change_id: 01KSQNPBPN7W74QVAZ25F79RNH
date: 2026-05-28
---

# ADR-006 — version-check is advisory-first; required is deferred

## Decision

The `version-check.yml` CI guard — which asserts that a plugin-affecting diff
(`plugins/sulis/**`) carries at least one new `.changesets/*.yaml` — **ships
advisory-only this cycle**: on a missing changeset it **warns and exits 0**
(does not fail the check). Promoting it to a **required** check that *blocks*
the merge is a **separate, later, founder-gated** step in a future cycle.

`main` branch protection (WP-006) is **founder-gated**: execution **pauses** to
show the founder the exact `gh api` configuration before applying it, and the
bot's ability to push the bump commit + tag is **verified on a throwaway**
before the train is relied upon.

## Context

There are two enforcement-shaped pieces in this change, and both carry a
self-lockout risk if switched on too early:

1. **version-check as a required check.** `dev` currently has unbumped commits
   with **no changesets** (this is the very situation #66 describes). If
   version-check were *required* the moment it ships, the next `dev→main` PR —
   which legitimately contains those pre-existing unlabelled commits — would be
   **blocked**, locking the team out of releasing at all. The writer (WP-002)
   must be live and reliably producing changesets *before* the absence of one
   can be a hard error.

2. **main branch protection.** Configured wrong, it either blocks the bot from
   pushing the bump (release silently fails) or is too permissive. The exact
   config is consequential enough to be a founder decision, and the bot push is
   the kind of thing that must be *proven* before being trusted.

## Alternatives considered

1. **Ship version-check as a required check immediately (rejected).** *Rejected
   because* it self-locks: the in-flight unlabelled commits on `dev` would fail
   the required check and no release could be cut. The spec's "What to avoid"
   names this explicitly: *"Do NOT enforce version-check as a required check
   before the writer is live + producing changesets."*

2. **Skip version-check entirely for now (rejected).** Ship the train without
   any guard, add enforcement "later". *Rejected because* the guard's *advisory*
   form is valuable immediately — it surfaces the missing-changeset case as a
   warning so the team sees the gap closing — and shipping the file now (warn
   mode) makes the later promotion a one-line change rather than a new file.

3. **Advisory-first, promote later behind a founder gate (CHOSEN).** Ship
   warn-only now; promote to required once the flow reliably produces
   changesets, as a deliberate, founder-authorised step. Apply `main` protection
   now (so the bot can push) but pause for founder review of the exact config +
   verify the bot push on a throwaway first.

## Consequences

- **Positive:** no self-lockout; the guard is visible (warns) from day one;
  promotion to required is a trivial, deliberate later change; branch protection
  is applied with the founder's eyes on the exact config.
- **Cost:** for one cycle, a plugin change *could* land without a changeset
  (only a warning fires). Acceptable and bounded — the next cycle promotes the
  guard to required.
- **WP-005 frontmatter/notes MUST state** advisory-only-this-cycle and that
  promotion is a separate founder-gated step. **WP-006 MUST state** the pause +
  show-exact-config + verify-bot-push-on-throwaway gate.

## Related

- ADR-001 (the flow this guard protects), WP-005 (the advisory guard),
  WP-006 (the founder-gated branch protection).
