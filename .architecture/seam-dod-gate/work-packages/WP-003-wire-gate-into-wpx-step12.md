---
# Identity (WP-01)
id: WP-003
title: Wire the seam-close gate into `wpx-step12 wrap` at the done-transition (step 12.2a)
status: pending
change_id: seam-dod-gate
kind: methodology
source: feat
primitive: extend
group: EXPAND

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: medium

# Lifecycle (WP-07)
sequence_id: WP-003
dependsOn: [WP-002]
blocks: []

# Composite (WP-08)
child_wps: []
kinds: null

estimated_token_cost:
  input: 7k
  output: 5k
tdd_section: §How the gate hooks into the build loop (the trigger point — wpx-step12 12.2a); §Test surface File 2
adrs: [ADR-002, ADR-003]
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/unit/test_seam_close_gate_wiring.py

rollback: |
  Revert the wpx-step12 edit (remove step 12.2a + the gate-block field from
  the wrap envelope). The done-flip and worktree-remove steps are unchanged
  by the rollback. Delete test_seam_close_gate_wiring.py's wpx-step12
  assertions (or the whole file if only this WP authored it).
---

# Wire the seam-close gate into the WP done-transition

## Context

TDD §"How the gate hooks into the build loop" + ADR-003. The atomic moment a WP
becomes `done` is `wpx-step12 wrap` step 12.2
(`wpx-index flip-status --to done --expected in_progress`). Both build paths
converge here: `run-wp --force-single` calls `wpx-step12 wrap` at its Step 4,
and the batch path (`run-all` → `wpx-train`) finalises each WP through the same
wrap. So a **single hook** at the done-transition covers both paths (ADR-003).

This WP adds **step 12.2a** to `cmd_wrap` in `plugins/sulis/scripts/wpx-step12`:
immediately after the status flip (12.2), call
`_seam_close_gate.evaluate(just_done_wp=args.wp, index_path=…, brain_base_dir=…,
repo_root=…, allow_deferred=args.allow_deferred)` and thread the
`SeamCloseResult` into the wrap JSON envelope as a `seam_close` block. On a
`blocked` verdict it emits a `gate_block` marker so the calling session halts
seam-close as "not done" — **without rolling back the flip** (the WP genuinely
reached done; it is the *seam* that is not done — ADR-003).

It also authors **File 2 — `test_seam_close_gate_wiring.py`** (the structural
wiring tests for the `wpx-step12` site), written failing-first within this WP.

## Contract

### Files modified / created

```
plugins/sulis/scripts/wpx-step12                                  (MODIFY — add step 12.2a + --allow-deferred arg)
plugins/sulis/scripts/tests/unit/test_seam_close_gate_wiring.py   (CREATE — wpx-step12 wiring assertions + the run-wp/run-all doc assertions, shared with WP-004)
```

> **Peer-collision note (rubric P6):** `test_seam_close_gate_wiring.py` is
> **created** by this WP (sole creator). WP-004 adds its run-wp/run-all
> assertion functions by **modifying** the same file. WP-004 `dependsOn`
> WP-003 is **not** required for collision-safety (they touch different
> functions), but to avoid a same-level modify/create race the file is created
> here and WP-004 only appends — see INDEX peer-collision table. The
> run-wp/run-all *doc* assertions are authored here as **failing** (the skills
> aren't documented yet); WP-004 makes them pass.

### The wrap-envelope addition

```python
# wpx-step12 cmd_wrap, after Step 12.2 (the flip):
summary["seam_close"] = {
    "verdict": result.verdict,         # observed | blocked | not-closed
    "seam": result.seam_title,         # founder-facing title; "" when not-closed
    "reason": result.reason,           # founder-English; empty when silent
}
if result.verdict == "blocked":
    summary["gate_block"] = {          # the calling session reads this to halt seam-close
        "stage": "seam-close",
        "message": result.reason,
    }
```

The wrap still `emit_ok`s (the flip succeeded); the `gate_block` field is the
signal the orchestrator surfaces in founder English. The exit code / flip are
**not** changed (ADR-003: don't roll back the flip).

### New CLI arg

```
--allow-deferred   (store_true, default False)   # threaded to evaluate(allow_deferred=...)
```

Mirrors `sulis-verify-acceptance`'s flag and the ship gate's threading — the
conscious, logged escape (TDD §"The explicit deferred escape hatch"). Default
OFF = observed-or-blocked.

### Wiring tests authored here (File 2, mirrors `test_ship_acceptance_gate_wiring.py`)

| Test | Asserts | Made-green-by |
|---|---|---|
| `test_wpx_step12_invokes_seam_close_gate` | `wpx-step12` source references / imports `_seam_close_gate` and calls it after the status flip | **this WP** |
| `test_seam_gate_blocks_on_blocked_verdict` | the wrap path emits a `gate_block` on a `blocked` seam (text/structural assertion mirroring `test_ship_blocks_on_blocked_verdict`) | **this WP** |
| `test_seam_gate_treats_deferred_as_blocking_by_default` | `wpx-step12` documents observed-or-blocked + threads `--allow-deferred` (mirrors the ship deferred test) | **this WP** |
| `test_runwp_documents_seam_close_gate` | `run-wp/SKILL.md` documents the seam-close gate at WP-done | **WP-004** |
| `test_runall_documents_seam_close_gate` | `run-all/SKILL.md` documents the gate firing when a seam-spanning WP completes | **WP-004** |

## Definition of Done

### Red — Failing tests written
- [ ] `test_seam_close_gate_wiring.py` created with all five assertions above.
- [ ] Before the `wpx-step12` edit, `test_wpx_step12_invokes_seam_close_gate`, `test_seam_gate_blocks_on_blocked_verdict`, `test_seam_gate_treats_deferred_as_blocking_by_default` **fail** (no 12.2a yet).
- [ ] `test_runwp_documents_seam_close_gate` / `test_runall_documents_seam_close_gate` also fail (skills not yet documented — WP-004's Green).

### Green — Implementation makes tests pass
- [ ] `wpx-step12 cmd_wrap` gains step 12.2a calling `_seam_close_gate.evaluate(...)` after the flip, threading the result into the envelope + `gate_block` on `blocked`.
- [ ] `--allow-deferred` arg added to the `wrap` subparser and passed to `evaluate`.
- [ ] The three `wpx-step12` wiring tests pass; the two run-wp/run-all doc tests still fail (owned by WP-004).
- [ ] `wpx-step12`'s existing tests (`tests/integration/test_wpx_step12.py`, `test_wpx_step12_idempotence.py`) still pass — the flip + worktree-remove behaviour is unchanged; a `not-closed`/no-seam wrap behaves exactly as before (characterisation safety).

### Blue — Refactor complete
- [ ] The gate call is **best-effort-never-fatal for evidence** but **decisive for the verdict**: a brain-store write failure inside the runner does not change the wrap's success (inherited from the runner contract); a `blocked` *decision* does set `gate_block`. The two are not conflated.
- [ ] step 12.2a is a small, named helper (not inline sprawl) so the wrap stays readable; the helper resolves `index_path` / `brain_base_dir` / `repo_root` from `paths_from_args(args)` consistently with the existing steps.
- [ ] No new operator vocabulary in the envelope's founder-facing `message`; the raw `result.reason` (already stripped by WP-002) is passed through verbatim.

## Sequence
- **dependsOn:** WP-002 (the `evaluate` it calls must exist)
- **blocks:** — (WP-004 depends on this WP for the shared wiring-test file; see INDEX)
- **Parallelisable with:** WP-005, WP-006 (disjoint files)

## Estimated Token Cost
- **Input:** ~7k (`wpx-step12` full source, the ship-wiring test, WP-002's contract, ADR-003)
- **Output:** ~5k (≈ 40 LOC wrap edit + ~80 LOC wiring tests)
- **Total:** ~12k

## Notes
- **Why one hook, not run-wp + run-all (ADR-003):** both paths finalise through `wpx-step12 wrap`; hooking at the per-WP done-flip is one site, one test surface, correct firing whether a seam closes inside a batch or across two batches. run-wp/run-all only *document* the gate (WP-004) — they carry no behaviour.
- **Why after the flip, not before (ADR-003):** the seam-close predicate asks "are all WPs on both sides of this seam now `done`?" — it must read post-flip INDEX state. Running before the flip would force a special-case for "…and this one, about to flip."
- **Defence-in-depth (ADR-002):** this is the *primary* catch; the ship gate (4.8) stays as a backstop on the same runner. This WP does not touch `change/SKILL.md`.

## Verification Plan
- **Adapter:** `methodology` (structural assertions over live tool text + the existing `wpx-step12` integration tests as characterisation).
- **Concrete artifact:** `plugins/sulis/scripts/tests/unit/test_seam_close_gate_wiring.py`.
- **What this WP's verification proves:** the gate actually fires at the done-transition (not a gate in name only — mirrors the ship-wiring test's purpose), a `blocked` seam emits the halt signal without rolling back the flip, and the `--allow-deferred` escape is wired. The existing wpx-step12 integration tests confirm no regression to the flip/worktree behaviour.
