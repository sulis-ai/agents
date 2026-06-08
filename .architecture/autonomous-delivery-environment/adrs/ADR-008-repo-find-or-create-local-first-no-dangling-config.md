# ADR-008 — Repo find-or-create is local-first, confirm-gated, and leaves no dangling config

- **Status:** accepted
- **Date:** 2026-06-04
- **Change:** CH-01KT50 · autonomous-delivery-environment
- **Deciders:** SEA (one branch — the create *location* — is founder-owned)

## Context

During onboarding the founder may or may not already have a repo for their
Product (FR-35). The flow branches:

- **Repos exist** → find/configure from the founder's pointer, bounded to the
  chosen area (FR-N7), reusing the discovery skills (ADR-007).
- **No repo** → create one for the founder. Creating a real git/GitHub repo
  is a **consequential, possibly-external** act (FR-N10).

Both branches end by setting `Project.source.repo` and persisting the config
(FR-36). Two safety requirements bound the create branch: it must be
confirmed first, and a *failed* create must **not** leave a Product/Project
config pointing at a repo that was never created (FR-N10, FR-N11).

This decision also touches a genuinely **founder-owned** question: when a new
repo is created, is it a **local-only** git repo, or a repo on a **hosted
remote** (e.g. GitHub) under the founder's account? That choice has a
business/data-exposure consequence (publishing code, needing hosting
credentials) — it is not an engineering convention to take silently.

## Decision

**Repo find-or-create is one orchestration with two branches, confirm-gated,
with all-or-nothing config persistence; the create-location default is
local-only, with hosted-remote as a separately-confirmed founder choice.**

- **Find branch (repos exist):** the discovery skills locate and configure
  the repo within the chosen area; no creation occurs; `Project.source` is
  set from the found repo.
- **Create branch (no repo):** on explicit founder confirmation (FR-N6 /
  FR-N10), the app creates a repo and sets `Project.source.repo` from it.
- **Create location (founder-owned):** the **recorded safe default is a
  local-only git repo** (`git init`) in the founder's chosen area — no
  external account, no network, nothing published. This keeps the
  consequential act fully reversible and avoids needing the founder's
  hosting credentials in this slice. **Creating on a hosted remote (GitHub
  etc.) is an additional, separately-confirmed step** the founder may choose;
  it is surfaced as an open question, not taken silently.
- **No dangling config (FR-N10 / FR-N11):** the config (`Project.source`) is
  persisted **only after** the repo is confirmed-created (or found) and
  reachable. A confirmed create that **fails** surfaces a clear plain-English
  failure and persists **no** Product/Project whose `source.repo` points at
  the missing repo — the graph is left exactly as it was before the attempt.

This composes with ADR-007's all-or-nothing persistence: the repo step is the
precondition the config persistence waits on.

## Alternatives considered

- **Default to hosted-remote (GitHub) creation (rejected as the default).**
  Irreversible-ish (a public/private repo now exists on a third party),
  needs the founder's hosting credentials in-scope for this slice, and
  publishes code the founder may not have meant to publish. Local-only is the
  safe, reversible default; hosted-remote is opt-in. (This is the
  founder-owned call — recorded as an open question, not closed by SEA.)
- **Persist config first, attach repo later (rejected).** Leaves a dangling
  `Project.source` on failure — the exact FR-N10 / FR-N11 failure mode.
- **Skip the create branch — require an existing repo (rejected).** Breaks
  the cold-start promise (UC-07): a founder with nothing yet could not be
  onboarded. The create branch is what makes "the agent does the setup *for*
  you" true.

## Consequences

- The find branch verifies in CI against `fixture-project-directory` (find /
  configure a seeded repo, no creation).
- The create branch verifies in CI against `fixture-repo-create-target`: a
  writable temp dir as the local `git init` target (no network), plus a
  deliberately-failing variant asserting the confirm gate (FR-N10) and the
  no-dangling-config rule (FR-N10 / FR-N11). The live hosted-remote create
  path is verified manually if/when the founder chooses it.
- The create-location question is carried into the TDD's Open Architecture
  Questions as the single genuinely founder-owned decision in this expansion.
