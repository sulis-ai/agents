---
id: ADR-004
title: The GHA is the one bump authority; bash duplicates _changeset.py logic
status: accepted
change_id: 01KSQNPBPN7W74QVAZ25F79RNH
date: 2026-05-28
---

# ADR-004 — GitHub Action is the single bump authority (Option B)

## Decision

**The version bump + CHANGELOG assembly + changeset deletion + tag + push is
performed by a GitHub Action (`release-on-merge.yml`) running as
`github-actions[bot]` on push to `main`** — not by a local script run by an
agent or founder. This is the founder-chosen Option B.

The release flow becomes:

```
change ships → writes a changeset → lands on dev (no bump)
   ↓ (accumulate)
/sulis:release-train → opens a reviewed dev→main PR (read-only; no bump)
   ↓ (review + merge)
push to main → release-on-merge.yml (the ONE authority) bumps + tags + pushes
```

The bump tier computation in the GHA is implemented in **bash that mirrors
`_changeset.py`'s logic** (cumulative `max` tier, `next_version` per series).
The bash and the Python are intentionally **two implementations of the same
contract** (`.changesets/README.md`).

## Context

The spec offered two release shapes:

- **A local script** the agent/founder runs to bump on `dev` then promote.
- **Option B: a CI-gated, bot-attributed GHA** that owns the bump on merge to
  `main`.

The founder chose Option B. The existing repo already has the surrounding
machinery: `promote-dev-to-main.yml` (a manual `workflow_dispatch` taking a
hand-typed `version`) and `release-prod.yml` (turns a pushed `v*` tag into a
GitHub Release). Option B replaces the *hand-typed version* half of that
ceremony with a deterministic bot.

## Alternatives considered

1. **Local bump script (rejected).** A `python3 _changeset.py bump` the agent
   runs on `dev`, then promote. *Rejected because* it keeps the bump dependent on
   an agent remembering to run it (the #66 failure mode), is not CI-gated, and is
   not bot-attributed (the commit author is whoever ran it). Less robust than a
   single CI authority.

2. **Shell out to `_changeset.py` from the GHA (considered, not chosen for the
   bump math).** The GHA could `python3 -c "import _changeset; …"` to reuse the
   exact functions. *Not chosen for the in-workflow tier math* because the
   honest-claude reference workflow does the computation in inline bash (`grep`/
   `awk`/`jq`), which keeps the workflow self-contained (no `sys.path` plumbing,
   no import of a plugin-internal module from CI) and matches the proven shape.
   **The duplication is accepted and made safe** by: (a) the contract
   (`.changesets/README.md`) being the single source of truth both
   implementations conform to; (b) `_changeset.py`'s unit tests pinning the
   Python side; (c) the GHA's post-bump verification catching any divergence at
   release time. This is a deliberate, documented duplication, not drift.

   > **Note for the executor (WP-003):** if shelling out to `_changeset.py`
   > proves clean in practice (the module is import-safe from the checked-out
   > repo with `sys.path` pointed at `plugins/sulis/scripts`), preferring that
   > over re-implemented bash is an acceptable Blue-stage improvement — it
   > collapses the duplication. The contract is the same either way.

3. **GHA as the one authority, bash mirrors the contract (CHOSEN).** Robust
   (CI-gated, single authority, bot-attributed), matches the proven honest-claude
   shape, and the duplication is bounded + verified.

## Consequences

- **Positive:** one authority, no two-bump drift; bot-attributed commit; the
  bump only happens behind the `dev→main` review gate.
- **Cost:** bash/Python duplication of the tier math (accepted; see alt 2);
  requires `main` branch protection configured so the bot can push (ADR-006 /
  WP-006).
- **The loop-guard** (`if: !startsWith(head_commit.message, 'release: sulis')`)
  prevents the bot's own push from re-triggering the workflow.
- **`promote-dev-to-main.yml`'s hand-typed `version` input is retired** from the
  documented flow by WP-007 (the train owns the version now). The workflow file
  itself may remain as a manual recovery path, but the *documented ceremony* no
  longer asks a human to type a version.

## Related

- ADR-003 (what the GHA bumps), ADR-006 (the branch protection that lets the bot
  push), WP-003 (the workflow), WP-004 (the read-only PR-drafting skill),
  WP-007 (retiring the manual-bump expectation from the docs).
