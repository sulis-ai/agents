---
id: WP-021
title: "Repo find-or-create: local-first, confirm-gated, no dangling config"
kind: backend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: chat
parent_group: discovery

atomic_branch: yes
estimate: 6h
blast_radius: medium       # the consequential, possibly-irreversible-ish repo create act
primitive: EXPAND-Create
group: expand
acceptance_criteria:
  - "FIND branch (repos exist): locates + configures the repo from the founder's pointer, bounded to the chosen area (FR-N7); sets Project.source = {repo, path, primary_branch} from the found repo; NO creation occurs (FR-35, ADR-008)"
  - "CREATE branch (no repo): on an explicit confirm (FR-N6/FR-N10), creates a repo — DEFAULT local-only `git init` in the chosen area, no network, nothing published, fully reversible (ADR-008); hosted-remote is a SEPARATELY-confirmed createTarget, NOT the default"
  - "NO DANGLING CONFIG (FR-N10/FR-N11): Project.source is persisted ONLY AFTER the repo is found-or-created AND reachable AND confirmed; a confirmed create that FAILS surfaces a clear plain-English failure (REPO_CREATE_FAILED) and persists NO config pointing at the missing repo — the graph is left exactly as it was"
  - "Create runs behind the confirmGate (WP-020); an unconfirmed create never touches the filesystem (FR-N6)"
  - "Subprocess (git) bounded by the existing 5s-class timeout discipline (TDD §3.6); the act is observable in the discovery act-log {act, outcome, code?} — never directory contents (NFR-SEC-03 posture)"
test_plan:
  unit:
    - "apps/cockpit/server/tests/repoFindOrCreate.test.ts (NEW) — find branch against fixture-project-directory (finds/configures, no creation); create branch git init into fixture-repo-create-target (confirm-gated); simulated create-failure persists NO config (the dangling-config assertion, FR-N10/N11); unconfirmed create is a no-op (FR-N6)"
  integration: []
  verification:
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0 (repo create reaches consequence only via the sanctioned discovery path, not a new file-level gate exception — ADR-006)"
    - "branch-ci green"
verification_gates: [unit, integration, smoke]
verification:
  adapter: backend
  artifact: "apps/cockpit/server/tests/repoFindOrCreate.test.ts"
  deferred-to-follow-on: fixture-repo-create-target
  # find/create/no-dangling-config concrete against fixtures now; the LIVE
  # hosted-remote create path (if founder opts in) is deferred + manual.

derived_from:
  - finding: "ADR-008 repo find-or-create local-first / confirm-gated / no dangling config; TDD §3.6 all-or-nothing persistence + §2.4 repoFindOrCreate row; FR-35, FR-N6, FR-N10, FR-N11; openapi OnboardingRequest.repoChoice"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-008-repo-find-or-create-local-first-no-dangling-config.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-04T09:20:00Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-017, WP-020]   # ProjectSource type + the confirm gate the create waits on

child_wps: []
kinds: null

# LOCKED founder decision baked in (this slice):
#   create default = LOCAL-ONLY git init; no GitHub publish unless separately confirmed.
locked_decisions:
  - "repo create default is LOCAL-ONLY (git init); hosted-remote (GitHub) is a separately-confirmed createTarget, never silent (ADR-008, founder-locked)"

# safety posture on the consequential create act:
security_constraints:
  - "Create is confirm-gated (WP-020) and local-first; nothing published, no hosting credentials needed in this slice (FR-N10, ADR-008)"
  - "Failed create persists NO config; the graph is left untouched (FR-N10, FR-N11) — all-or-nothing"
  - "Search bounded to the chosen area on the find branch (FR-N7)"

verifies_scenario: "PENDING-MINT:G"   # Set-up-by-talking (UC-07) — the repo-create step; aggregated under scenario G

rollback: |
  New repoFindOrCreate lib + tests. Remove the file + test; revert the commit.
  No persistence happens except after a confirmed reachable repo, so removal
  cannot leave dangling state. No read surface affected.
---

# Repo find-or-create: local-first, confirm-gated, no dangling config

## Why

During onboarding the founder may or may not have a repo for their Product
(FR-35). The flow branches: **find** an existing one (configure it, bounded to
the chosen area, FR-N7) or **create** one. Creating a repo is a consequential,
possibly-external act (FR-N10), so it is **confirm-gated** (WP-020) and —
per the **founder-locked decision** for this slice — **local-only by default**
(`git init`, no network, nothing published, fully reversible; ADR-008).
Hosted-remote (GitHub) is a *separately-confirmed* choice, never silent. The
hard safety rule (FR-N10/FR-N11): a **failed** create leaves **no** dangling
`Project.source` pointing at a repo that was never created.

## What changes

- `apps/cockpit/server/lib/discovery/repoFindOrCreate.ts` (NEW, EXPAND-Create) — `find(pointer, chosenArea) → ProjectSource` (configure existing, no creation) and `create({createTarget: local|hosted-remote}, chosenArea, confirm) → ProjectSource | Failure`. Default `createTarget = local`. Persists `Project.source` only after the repo is reachable + confirmed; on failure persists nothing.

## How

Reuse the discovery skills for the find branch (ADR-007), bounded to the
chosen area. The create branch runs `git init` (local) behind the confirm gate
(WP-020), inside the existing 5s-class subprocess timeout discipline. The
persistence call is the **last** step and is conditional on reachable+confirmed
— this is the all-or-nothing guarantee (ADR-008). Reaching consequence uses
the sanctioned discovery path, so the read-only gate gains no new file-level
write exception (ADR-006).

## Tests

`repoFindOrCreate.test.ts` — find against `fixture-project-directory`
(configures, no creation); create `git init` into `fixture-repo-create-target`
(confirm-gated); a simulated create-failure persists **no** config (the
dangling-config assertion); unconfirmed create is a no-op.

`verification:` — find / create / no-dangling-config are **concrete** against
fixtures now; the **live hosted-remote** create (if the founder opts in) is
**deferred** + manual (`fixture-repo-create-target` covers the local CI path).

## Scenario linkage

Part of scenario **G — "Set up by talking (cold-start onboarding)"** (UC-07):
the repo find-or-create step. Author scenario G and backfill its
`dna:scenario:<ULID>` (aggregated in WP-027).

## Rollback

Remove the lib + test; revert. All-or-nothing persistence means removal leaves
no dangling state.
