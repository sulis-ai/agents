---
# Identity (WP-01)
id: WP-006
title: "main branch protection — founder-gated config (lets the bot push the bump)"
kind: infra                             # branch-protection config via gh api
source: feature
parent_phase: release-train
change_id: 01KSQNPBPN7W74QVAZ25F79RNH

# Scope (WP-02..04)
atomic_branch: yes
estimate: small
blast_radius: high                      # changes how main accepts pushes — FOUNDER-GATED
founder_gated: true                     # execution PAUSES to show the exact gh api config before applying

# Change primitive
primitive: create
group: expand

acceptance_criteria:
  - "main branch protection requires a dev→main PR + the required status checks"
  - "enforce_admins: false — so github-actions[bot] (admin token) CAN push the bump commit + tag (WP-003's step 9)"
  - "the EXACT gh api configuration is recorded in the change (this WP file + the ship notes)"
  - "execution PAUSES to show the founder the exact gh api config BEFORE applying it (founder-gated — MUST)"
  - "the bot's ability to push the bump commit + tag is VERIFIED ON A THROWAWAY (scratch branch/repo) BEFORE the train is relied upon"

test_plan:
  unit: []
  integration: []
  verification:
    - "gh api read-back of the applied protection matches the recorded config exactly"
    - "THROWAWAY BOT-PUSH VERIFICATION: a real github-actions[bot] push of a bump-shaped commit + tag to a protected branch succeeds on a scratch target before relying on the live train"
verification_gates: [infra]

# Lineage (WP-06)
derived_from:
  - finding: spec::.changes/release-train.SPEC.md::WP-6
    found_in: .changes/release-train.SPEC.md
    severity_at_discovery: n/a
generated_by:
  activity: draft-architecture/release-train
  agent: sulis-engineering-architect
addresses_findings:
  - "issue-66::bot-must-be-able-to-push-the-bump (the protection that enables WP-003)"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
depends_on: [WP-003]                      # lands WITH WP-003 (the bot push it enables)
blocks: []

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Re-apply the prior main protection via gh api (capture it BEFORE changing it,
  in the pause step, so rollback is exact). No code change; pure config.
---

# WP-006 — `main` branch protection (FOUNDER-GATED)

## Context

TDD §Armor (the config that lets the bot be the bump authority safely). **ADR-006
governs the founder-gate.** Depends on WP-003 and lands **with** it — WP-003's
step 9 pushes the bump commit + tag as `github-actions[bot]`, which requires
`main` protection that permits the bot's push. Models honest-claude's setup (its
GHA pushes back as the bot — same shape).

## Contract — the protection config

Configure `main` (via `gh api repos/<owner>/<repo>/branches/main/protection`):

- **Require a `dev→main` PR** to merge to `main` (no direct human pushes).
- **Required status checks** — the same CI suite as the release PR (branch-ci /
  the dev→main checks).
- **`enforce_admins: false`** — the load-bearing setting: the bot uses an admin
  token, and with admin enforcement *off* it can push the bump commit + tag in
  WP-003's step 9. With it *on*, the bot's push is blocked and the release
  silently fails.

The exact `gh api` payload (fields + values) MUST be recorded verbatim in this
WP file (filled in at execution time) and in the ship notes, so it is auditable
and reversible.

## Definition of Done — Red / Green / Blue

### Red / pre-flight (FOUNDER GATE — MUST)

1. **Capture the current protection** first: `gh api
   repos/<owner>/<repo>/branches/main/protection` → save verbatim (this is the
   rollback baseline).
2. **PAUSE and show the founder the exact `gh api` config to be applied**,
   in plain English about what changes ("`main` will require a review PR to
   merge, and the release bot will be allowed to push the version bump") plus
   the exact payload for the record. **Do not apply until the founder confirms.**
   This is the founder gate — the WP MUST NOT apply protection silently.

### Green (apply, only after founder confirmation)

Apply the recorded `gh api` config. Read it back (`gh api … /protection`) and
assert it matches what was shown.

### Blue (verify the bot push BEFORE reliance — MUST)

- **Throwaway verification:** on a scratch branch/repo (or a disposable tag on a
  scratch ref), perform a real `github-actions[bot]` push of a bump-shaped
  commit + tag to a branch protected with this exact config. Confirm it
  succeeds. This proves the train can actually cut a release before the founder
  relies on it. Tear the scratch target down.
- Record the read-back config + the throwaway-verification result in the ship
  notes.

## Estimated token cost

input: ~5k / output: ~3k

## Notes

- **FOUNDER-GATED (MUST).** Execution PAUSES to show the exact `gh api` config
  before applying. This is the highest-blast-radius WP — it changes how `main`
  accepts pushes — and the bot-push must be *proven*, not assumed.
- **Lands with WP-003.** The protection and the GHA that depends on it are one
  cohesive landing — shipping the GHA without the protection means the bot
  push fails; shipping the protection without the GHA means nothing pushes.
- **`enforce_admins: false` is the one setting that makes the train work.** Get
  it wrong and the release silently fails at the push step.
