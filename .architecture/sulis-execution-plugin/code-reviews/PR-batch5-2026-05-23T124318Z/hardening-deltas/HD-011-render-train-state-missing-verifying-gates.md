---
id: HD-011
title: render_train_state_plain_english missing verifying_gates description; contains dead code_review entry
status: proposed
severity: MEDIUM
pillar: form
source: code-review:PR-batch5-2026-05-23T124318Z
lens: quality
created: 2026-05-23
---

## Context

`scripts/_wpxlib.py::render_train_state_plain_english` (line 2126) renders
a founder-friendly summary of a train's state for `wpx-train inspect`.
The `phase_descriptions` dict (lines 2146-2158) maps phase names to
plain-English explanations.

Batch 5 added the `verifying_gates` phase to `PHASES` (line 1789) but
**did not add a corresponding entry to `phase_descriptions`**. Result:
`wpx-train inspect <train-paused-at-gates>` shows:

```
Train train-2026-05-23T124318Z
  Started: ...
  Phase: verifying_gates
  Bundle (3 work packages): ...
```

No `→ description` line — the founder gets a phase name they don't
recognise with no guidance. The `recovery_hint` set by
`_finalise_awaiting_gates` does surface (via the lines 2163-2166
block), so the founder isn't fully stranded, but the missing description
is inconsistent with every other phase in the dict.

## Adjacent finding — dead `code_review` key

The same dict has an entry for phase `code_review` (line 2150) that is
**not in `PHASES`**. `PHASES` does not list `code_review` (line 1782-1794).
The key is unreachable from any code path that goes through
`update_train_phase` (which validates against `PHASES`).

This is pre-existing dead code from an earlier design iteration of the
gate-handoff feature (Option A from HD-007's "tension" section —
pause-then-resume). Batch 5 should have removed it when it picked
Option B (verifying_gates + mark-gates-complete).

## Severity

**MEDIUM.** Not a behavioural bug — `wpx-train inspect` still works; the
phase name itself is shown; the recovery_hint covers the practical
guidance. But:

1. Inconsistent founder UX. Every other phase has a description.
2. The dead `code_review` entry is misleading for future contributors —
   it suggests a phase that doesn't exist.

Quality-lens finding; not blocking the commit. Worth fixing in the
same batch as a 4-line edit.

## Verification — failing test (RED)

```python
def test_phase_descriptions_covers_every_phase_and_only_those_phases():
    """HD-011 RED — render_train_state_plain_english's phase_descriptions
    must have one entry per PHASES value (so inspect always renders a
    description), and no extras."""
    import _wpxlib
    # The dict lives inside the function; extract via a probe state.
    # Iterate over PHASES; for each, check render produces a "→" line.
    bundle_stub: list = []
    for phase in _wpxlib.PHASES:
        state = {
            "train_id": "test", "started_at": "2026-01-01T00:00:00Z",
            "phase": phase, "bundle": bundle_stub, "phase_history": [],
        }
        out = _wpxlib.render_train_state_plain_english(state)
        assert " → " in out, (
            f"HD-011: phase {phase!r} has no description in "
            f"phase_descriptions. Founder sees the phase name with no "
            f"explanation."
        )

    # And check: the dict has no keys that aren't in PHASES (dead code).
    # Extract the dict via source inspection — function-local, so this is
    # the cleanest gate.
    import inspect
    src = inspect.getsource(_wpxlib.render_train_state_plain_english)
    for stale in ("code_review",):
        assert stale not in src, (
            f"HD-011: phase_descriptions contains dead key {stale!r} "
            f"that is not in PHASES."
        )
```

## Recommendation

Add `verifying_gates` to `phase_descriptions`; remove `code_review`:

```python
phase_descriptions = {
    "pending": "Selected the bundle of work; about to start rebasing.",
    "rebasing": "Rebasing the feature branches onto each other in a temp clone.",
    "ci_running": "Waiting for the bundled-tip CI to come back.",
    "merging": "Squash-merging each branch to the base in order.",
    "deploying": "Waiting for the deploy workflow to complete.",
    "verifying": "Running health + smoke checks against the deploy.",
    "verifying_gates": (
        "Deploy + health + smoke green. Waiting on Step 10.5 code-review "
        "and Step 11 security review. The calling session dispatches "
        "both, then invokes `wpx-train mark-gates-complete` to finalise."
    ),
    "success": "Done. All work merged + deployed + verified.",
    "failed": "Failed. The revert path ran; branches restored.",
    "paused": "Paused. Needs attention before it can continue.",
    "aborted": "Aborted by founder. Branches restored to their pre-train state.",
}
```

(Drop the `code_review` line.)

## ADDED / MODIFIED / REMOVED

### MODIFIED

- `scripts/_wpxlib.py` line 2146-2158: add `verifying_gates` entry;
  remove `code_review` entry.

### ADDED

- `scripts/tests/unit/test_wpx_train_state_machine.py` (or appropriate
  unit file): new test `test_phase_descriptions_covers_every_phase_and_only_those_phases`.

## Sequence

Independent — can ship in the same commit as HD-010 or as a follow-up.
