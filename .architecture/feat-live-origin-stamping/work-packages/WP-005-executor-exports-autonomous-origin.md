---
wp: WP-005
change_id: 01KTHP2NYQ1A3WHPJD75VP31NT
title: Executor exports autonomous SULIS_ORIGIN at commit time
kind: backend
primitive: expand-create
group: expand
status: ready
dependsOn: []
estimated_token_cost: { input: ~16k, output: ~6k }
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_executor_autonomous_origin.py
---

# WP-005 — Executor exports autonomous `SULIS_ORIGIN` at commit time

## Context

TDD §2/§3/§5 (component 5), ADR-013. The launcher already wires the
`prepare-commit-msg` hook for the executor session (`_terminal_launcher.py`
`enable_origin_hook`), but the hook is a no-op until `SULIS_ORIGIN` is set. The
executor's commit step (Step 7) must export the autonomous origin so the hook
stamps it. The run-ulid is **per lifecyclerun** (one launched terminal runs many),
so the export is at COMMIT time, not a static launch-script export (ADR-016 D4).

Independent of the TS track — depends only on #216's grammar (already present).

## Contract

A small, testable env-builder the executor's commit step uses (Python helper next to
the existing scripts, e.g. `_origin_stamp.autonomous_env(run, confidence)` returning
`{"SULIS_ORIGIN": format_trailer(autonomous_origin(...))[len("Sulis-Origin: "):]}` —
i.e. the bare body the hook's `parse_origin_env` accepts), plus the executor
agent/seam exporting it in the commit step's environment.

- Reuse `_origin_stamp.autonomous_origin` + `format_trailer` — **no new formatter**.
- `confidence` is OPTIONAL: when no per-run confidence scalar exists, build
  `run=`-only (the constructor + format already support this). Do NOT invent a value.
- Non-fatal (MUST): a missing/empty run-ulid → no export, commit proceeds unstamped
  (degrade to inferred). Never abort the commit.

The executor-agent wiring (the actual `export SULIS_ORIGIN=…` before `git commit`)
is part of this WP: update `agents/executor.md` Step 7 (and any wpx commit seam) to
set the env from the helper. Keep it boring — one exported var, consumed by the
existing hook.

## Definition of Done

### Red
- [ ] `test_executor_autonomous_origin.py`:
      - run-ulid present → env value parses (via `parse_origin_env`) to
        `{kind:'autonomous', run:<ulid>}` (+ `confidence` only if supplied).
      - run-ulid absent/empty → no `SULIS_ORIGIN` (helper returns no env / None).
      - the emitted body is the exact bare-body grammar the hook accepts.
      Fails until the helper exists.
- [ ] Degradation: simulate the hook with the exported env on a real test commit
      (reuse #216's hook test pattern) → trailer present; with no env → commit lands
      unstamped, no error.

### Green
- [ ] Implement the autonomous env-builder reusing #216 constructors/format.
- [ ] Wire `agents/executor.md` Step 7 (and the wpx commit seam if one exists) to
      export it before commit; document the run-ulid source (lifecyclerun) inline.

### Blue
- [ ] `pytest plugins/sulis/scripts/tests/unit/test_executor_autonomous_origin.py` green.
- [ ] No re-implementation of trailer formatting (assert via reuse of `format_trailer`).
- [ ] confidence-omitted path produces a valid `run=`-only trailer.
