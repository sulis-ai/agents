---
# Identity (WP-01)
id: WP-005
title: "version-check.yml CI guard — ADVISORY-FIRST this cycle (warn, exit 0)"
kind: infra                             # GitHub Actions workflow
source: feature
parent_phase: release-train
change_id: 01KSQNPBPN7W74QVAZ25F79RNH

# Scope (WP-02..04)
atomic_branch: yes
estimate: small
blast_radius: low                       # advisory-only — never blocks a merge this cycle

# Change primitive
primitive: create
group: expand

acceptance_criteria:
  - ".github/workflows/version-check.yml exists; runs on change/* branches AND on the dev→main PR"
  - "asserts: a plugin-affecting diff (plugins/sulis/**) should carry >=1 new .changesets/*.yaml"
  - "ADVISORY-FIRST: on a missing changeset it WARNS and EXITS 0 — it does NOT fail the check this cycle"
  - "the workflow + this WP explicitly state advisory-only-this-cycle and that promotion to a REQUIRED (blocking) check is a SEPARATE, later, FOUNDER-GATED step in a future cycle"
  - "also (advisory) checks plugin.json version == marketplace sulis-entry version and surfaces drift as a warning"

test_plan:
  unit: []
  integration: []
  verification:
    - "branch-ci / workflow lint green"
    - "ASSERT ADVISORY SEMANTICS: a plugin-diff WITHOUT a changeset produces a warning and the job exits 0 (not 1) — the explicit proof it ships warn-only"
verification_gates: [infra]

# Lineage (WP-06)
derived_from:
  - finding: spec::.changes/release-train.SPEC.md::WP-5
    found_in: .changes/release-train.SPEC.md
    severity_at_discovery: n/a
generated_by:
  activity: draft-architecture/release-train
  agent: sulis-engineering-architect
addresses_findings:
  - "issue-66::make-every-plugin-change-labelled-structural (advisory phase)"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
depends_on: [WP-004]                      # ships after the train is live + producing changesets (bootstrapping)
blocks: [WP-007]

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Delete .github/workflows/version-check.yml. Since it is advisory (exit 0),
  removal changes no merge outcomes — it only removes a warning.
---

# WP-005 — `version-check.yml` CI guard (ADVISORY-FIRST)

## Context

TDD §Armor (the structural enforcement that makes "every plugin change is
labelled" real — but staged to avoid self-lockout). **ADR-006 is the governing
decision: advisory-first this cycle; required is a separate later founder-gated
step.** Depends on WP-004 (ships *after* the train is live + producing
changesets — bootstrapping point 3). Models honest-claude's `version-check.yml`,
but **deliberately downgraded to warn-only** for this cycle.

> **Why advisory and not required (MUST encode in the workflow comment + this
> WP):** `dev` currently has unbumped commits with **no changesets** (the #66
> situation). A *required* version-check would block the very next `dev→main` PR
> — the one carrying those legitimate pre-existing unlabelled commits — and lock
> the team out of releasing. The writer (WP-002) must be live and reliably
> producing changesets before the *absence* of one can be a hard error. So this
> cycle: warn + exit 0. Promotion to a required, blocking check is a separate,
> deliberate, founder-authorised step in a later cycle.

## Contract — the workflow

`on:` — push to `change/**` branches AND `pull_request: branches: [main]` (the
dev→main PR).

One job. The verification step:

```bash
TOUCHED=$(git diff --name-only "$BASE...HEAD" -- plugins/sulis/ | wc -l | tr -d ' ')
PENDING=0; [ -d .changesets ] && PENDING=$(ls .changesets/*.yaml 2>/dev/null | wc -l | tr -d ' ')

if [ "$TOUCHED" -gt 0 ] && [ "$PENDING" -eq 0 ]; then
  echo "::warning::This change touches plugins/sulis/ but has no .changesets/*.yaml."
  echo "::warning::Run /sulis:change ship (it writes one), or add one per .changesets/README.md."
  echo "ADVISORY this cycle — not blocking. (Promotion to a required check is a later, founder-gated step.)"
  exit 0     # <-- ADVISORY: warn, do NOT fail
fi
echo "changeset state consistent with the plugin diff (advisory check)"
```

Plus an advisory version-sync check (warn, not fail) that `plugin.json .version`
== `marketplace sulis-entry .version`.

## Definition of Done — Red / Green / Blue

### Red

The "failing test" for this advisory guard is the **inverse** of a normal guard:
assert that a plugin-diff-without-a-changeset **exits 0** (warns, does not
block). Author that expectation first (hand-trace / a scratch run): a missing
changeset must NOT fail the check this cycle. If the check ever exits non-zero on
a missing changeset, the WP has shipped the wrong (required) behaviour.

### Green

Author `.github/workflows/version-check.yml` per the contract, warn-only
(`::warning::` + `exit 0`). The workflow header comment MUST state advisory-this-
cycle + the self-lockout reason + that required is a later founder-gated step
(copy the rationale from ADR-006).

### Blue

- Confirm **no** code path in the workflow `exit 1`s on a missing changeset this
  cycle. The only non-zero exits permitted are genuine infrastructure errors
  (e.g. malformed YAML), not the missing-changeset case.
- Confirm the `BASE` ref resolves correctly for both triggers (change/* push vs
  the dev→main PR).
- Leave a single TODO(deferred) comment at the `exit 0` marking the future
  promotion to `exit 1`, with `RESOLVE_BY` left to the founder-gated cycle and a
  pointer to ADR-006 (so the promotion site is obvious and documented).

## Estimated token cost

input: ~5k / output: ~3k

## Notes

- **`kind: infra`.** Advisory semantics are the entire point — the verification
  gate is "missing changeset → exit 0".
- **MUST NOT promote to required in this WP.** Promotion is a separate WP in a
  later cycle, gated on (a) the writer reliably producing changesets and (b)
  explicit founder authorisation. Shipping required now is the self-lockout the
  spec's "What to avoid" forbids.
