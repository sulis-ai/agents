---
# Identity (WP-01)
id: WP-002
title: "/sulis:change ship writes a changeset (replaces the manual bump expectation)"
kind: docs                              # SKILL.md edit to the ship flow (no executable module of its own)
source: feature
parent_phase: release-train
change_id: 01KSQNPBPN7W74QVAZ25F79RNH

# Scope (WP-02..04)
atomic_branch: yes
estimate: small
blast_radius: medium                    # touches the ship flow every change runs

# Change primitive
primitive: extend
group: expand

acceptance_criteria:
  - "plugins/sulis/skills/change/SKILL.md ship flow gains a new REQUIRED step (sibling of 4.6 capture-lessons) that writes ONE changeset BEFORE the squash-merge, via _changeset.py"
  - "the new step calls _changeset.write_changeset with change_id + primitive + computed tier + touches_plugin + summary"
  - "the step SKIPS writing a changeset when tier_for_primitive returns None (admin / docs-only changes) — documented, not an error"
  - "the ship flow no longer carries any manual version-bump expectation (it never had one in the ship-to-dev path; the step writes a changeset and explicitly does NOT bump — see TDD 'Ambiguity resolved' #1)"
  - "the changeset is written on the change branch so it lands on dev with the squash-merge (it is part of the merged diff)"
  - "the ship report (step 7) states the changeset written (or that none was needed for an admin/docs-only change), never as a question"

test_plan:
  unit: []                              # the change is a SKILL.md body edit; _changeset.py is proven by WP-001
  integration: []
  verification:
    - "branch-ci green on the WP branch (markdown lint / any skill-shape checks)"
    - "this change's OWN ship exercises the new step end-to-end (writes the create-release-train changeset) — the live proof"
verification_gates: [docs]              # link-integrity + skill-shape

# Lineage (WP-06)
derived_from:
  - finding: spec::.changes/release-train.SPEC.md::WP-2
    found_in: .changes/release-train.SPEC.md
    severity_at_discovery: n/a
generated_by:
  activity: draft-architecture/release-train
  agent: sulis-engineering-architect
addresses_findings:
  - "issue-66::ship-flow-does-not-mandate-version-bump (the writer half)"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
depends_on: [WP-008]                     # consumes _changeset.write_changeset + tier_for_primitive against the FINALISED tier map; WP-008 transitively carries the WP-001 keystone
blocks: []

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Revert the SKILL.md edit. The ship flow returns to its prior shape (no
  changeset step). _changeset.py (WP-001) stays — it is just no longer called
  from the ship flow.
---

# WP-002 — `/sulis:change ship` writes a changeset

## Context

TDD §Form (the **producer** of the changeset seam). ADR-001 (the decoupling),
ADR-002 (tier from primitive → the skip-when-None rule), ADR-005 (the contract
it writes against). Depends on WP-001 (the keystone helper).

This is a **producer** in the CONTRACT_FIRST seam: it writes the YAML that
WP-003 (GHA) and WP-004 (skill) read. It cannot land before WP-001.

## Contract — the new ship step

Add a new **REQUIRED** step to `plugins/sulis/skills/change/SKILL.md`, in the
`ship` flow, as a **sibling of step 4.6 (Capture lessons)** — i.e. after the
review gate (4.5) and the lesson capture (4.6), **before** the squash-merge
(step 5). Suggested numbering: **step 4.7 (Write the changeset, REQUIRED)**.

The step (resolving `$SCRIPTS_DIR` exactly as the existing flow does):

```bash
# Compute the tier from the change's primitive (ADR-002).
python3 -c "
import sys; sys.path.insert(0, '$SCRIPTS_DIR')
import _changeset, datetime, json
tier = _changeset.tier_for_primitive('<primitive>')   # from the change manifest
if tier is None:
    print(json.dumps({'wrote': False, 'reason': 'admin/docs-only — no changeset'}))
else:
    p = _changeset.write_changeset(
        '.changesets',                                    # str dir — coerced to Path by the keystone (WP-009)
        change_id='01KSQNPBPN7W74QVAZ25F79RNH',          # this change's ULID
        primitive='<primitive>',
        tier=tier,
        touches_plugin=True,                              # true when the diff touches plugins/sulis/**
        summary='''<the change intent, founder-readable>''',
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    print(json.dumps({'wrote': True, 'path': str(p), 'tier': tier}))
"
git add .changesets/   # the changeset is part of the merged diff, lands on dev
```

> **`changesets_dir` accepts a `str`.** The first cut of this snippet passed
> `'.changesets'` to a `write_changeset` whose body called `.mkdir()` directly,
> which crashed with `AttributeError: 'str' object has no attribute 'mkdir'` (the
> batch code-review CR-BATCH-01). **WP-009 hardened the keystone to coerce
> `Path(changesets_dir)` at entry of both `write_changeset` and `read_changesets`**,
> so the plain-`str` `'.changesets'` above is correct as-written — keep it (no
> `from pathlib import Path` needed in the ship snippet). Do not revert to a call
> that assumes the keystone takes a `Path` only.

`touches_plugin` is `True` when `git diff --name-only origin/dev...HEAD --
plugins/sulis/` is non-empty; the step computes it from the diff (mirror the
existing diff-size probe in step 4.5). When the change does **not** touch
`plugins/sulis/**` AND the primitive maps to `None`, write no changeset.

**The step writes a changeset and explicitly does NOT bump any version** — the
GHA owns the bump now (ADR-004). The spec's "remove the manual version bump"
(WP-2) is honoured: the ship-to-dev flow never had a bump step (see TDD
"Ambiguity resolved" #1 — the manual bump lives in the *promotion* ceremony,
retired by WP-007), and this step makes the not-bumping explicit.

## Definition of Done — Red / Green / Blue

### Red

This WP is a SKILL.md body edit; the executable proof is WP-001's unit suite
(already green). The "failing test" surrogate is: **before** the edit, the ship
flow has no changeset step — confirm by reading the current SKILL.md. The
acceptance gate is that this change's **own ship** writes the
`create-release-train` changeset (the live proof the step works end-to-end).

### Green

Edit `plugins/sulis/skills/change/SKILL.md`:
1. Insert step 4.7 (Write the changeset) between 4.6 and 5, with the bash above
   and founder-English framing (no mechanism narration — report what's now true,
   not how `_changeset.py` works; FE-09).
2. Update step 7 (Report) to state the changeset written
   ("Recorded this as a `minor` release note.") or that none was needed
   (admin/docs-only) — **never as a question** (AAF-08).
3. Add a short note to the `## Gotchas` section: the changeset is written before
   the merge so it lands on `dev` with the squash; admin/docs-only changes write
   none.

### Blue

- Confirm the step's framing matches the founder-English of the surrounding
  steps (lead with outcome; no `_changeset` / `SULIS_CHANGE_ID` narration).
- Confirm the `$SCRIPTS_DIR` resolution reuses the block already at the top of
  the skill (don't duplicate the resolver — reference it).
- Cross-check that step 4.7 does not reintroduce any bump language; the only
  version touch is the GHA's (WP-003).

## Estimated token cost

input: ~6k / output: ~3k

## Notes

- **`kind: docs`** because the deliverable is a SKILL.md edit; the executable
  surface it calls (`_changeset.py`) is proven by WP-001's `kind: backend` unit
  suite. No new tests here — adding unit tests for a markdown body would be
  testing prose.
- **This change's own ship is the live integration test** for the step (the
  spec's bootstrapping point 5: this change ships through the OLD flow's manual
  bump one last time, but the NEW changeset step runs and writes the
  `create-release-train` changeset that the NEXT release's train will consume).
