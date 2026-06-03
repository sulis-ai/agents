---
id: WP-006
title: Create sulis-capture CLI (JSON envelope)
status: pending
change_id: 01KT60QGXQDF3Q3QPXQ354N5Q0
kind: backend
sequence_id: WP-006
dependsOn: [WP-004]
blocks: [WP-009, WP-013]
estimated_token_cost:
  input: 8k
  output: 3k
tdd_section: Form — dependency picture (sulis-capture CLI); Proof — CLI envelope contract
adrs: [ADR-003, ADR-005, ADR-002]
primitive: create
group: expand
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/integration/test_capture_e2e.py::test_capture_lands_whole_chain
---

## Context

The thin executable front door of the **Capture path** — `sulis-capture`,
mirroring the existing `sulis-emit-*` / `sulis-brain-query` CLI shape (top-
level executable script under `plugins/sulis/scripts/`, `argparse`, the
`{"ok":…}` JSON envelope, `_ok`/`_err` helpers). It constructs the two
domain adapters (foundation + product-development per the TDD two-domain
detail), resolves the repo shorthand from `.sulis/repo-contract.yml`, calls
`_brain_capture.capture_idea(...)`, and translates the result (or a
`CaptureError`/exception) into the envelope. It **never raises out of
main()** (NFR-01). EXPAND-Create.

This is also where the integration (e2e) test lives — the concrete artifact
named in the TDD Verification Plan §4.

## Contract

```text
sulis-capture
  --why-intensity {quick,full}     (required)
  --why TEXT                       (quick path one-liner)
  --what TEXT                      (optional requirement statement)
  --opportunity-id dna:opportunity:<ulid>   (full path — analyst-emitted id)
  --seed TEXT                      (required for deterministic ids / dogfood / tests)
  --roadmap                        (flag — mark Roadmap)
  --base-dir DIR                   (default: <repo-root>/.brain/instances)
  --repo-root DIR                  (default: git toplevel or cwd)

stdout: {"ok": true,  "data": {"opportunity_id":..., "requirement_id":...|null,
                               "roadmap": bool, "chain": {...}, "bootstrapped": bool}}  exit 0
        {"ok": false, "error": "<plain message>"}                                       exit 1
```

Contract invariants (the CLI envelope is the consumer contract, CONTRACT_FIRST):
- **Envelope shape** is identical to the sibling CLIs: `{"ok":true,"data":{...}}` / `{"ok":false,"error":...}`.
- **Exit codes:** 0 on `ok:true`, 1 on `ok:false`.
- **`main()` never raises** — `CaptureError`, `EntityValidationError`, `FileNotFoundError`, and brain-unavailable all become `{"ok":false,"error":...}` exit 1 (NFR-01).
- **Two-domain adapter construction** — `LocalFileEntityAdapter(base_dir,"foundation")` + `LocalFileEntityAdapter(base_dir,"product-development")` passed into `capture_idea`.
- **Repo shorthand** read from `.sulis/repo-contract.yml`; if absent, degrade with a plain-English `ok:false` (never crash).
- The `full` path's plain-English "run the opportunity-analyst first" guidance is rendered by the **skill** (WP-009), not the CLI — the CLI only accepts the resolved `--opportunity-id`.

## Definition of Done

### Red — Failing tests written
- [ ] `tests/integration/test_capture_e2e.py::test_capture_lands_whole_chain` — invoke the CLI against a temp `.brain/instances`; assert exit 0, `ok:true`, and that Tenant+Product+Opportunity+Requirement exist on disk with a whole `source`→`for_product`→`belongs_to_tenant` chain (no dangling).
- [ ] `tests/integration/test_capture_e2e.py::test_capture_no_why_returns_ok_false` — `--why-intensity quick` with blank `--why` → exit 1, `ok:false`, error mentions "why"; store unchanged.
- [ ] `tests/integration/test_capture_e2e.py::test_capture_idempotent_same_seed` — run twice with same `--seed` → same ids, no duplicate instance files (NFR-04).
- [ ] `tests/integration/test_capture_e2e.py::test_capture_roadmap_flag_lands_in_sidecar` — `--roadmap` → ids present in `.brain/labels/roadmap.jsonld`.
- [ ] `tests/integration/test_capture_e2e.py::test_brain_unavailable_returns_ok_false` — point at a base-dir with no vendored schemas → exit 1, `ok:false`, no traceback (NFR-01).
- [ ] `tests/integration/test_capture_e2e.py::test_envelope_shape_matches_siblings` — `ok:true` payload has the documented keys; `ok:false` payload has only `ok`+`error`.

### Green — Implementation makes tests pass
- [ ] All Red tests pass.
- [ ] `_ok`/`_err`/`_resolve_repo_root` patterned on the existing `sulis-brain-query` / `sulis-emit-opportunity` CLIs (reuse the shape; do not invent a new envelope).
- [ ] Script is executable (`chmod +x`), shebang `#!/usr/bin/env python3`, registered the same way the sibling emit CLIs are.
- [ ] Boring code: explicit `argparse`, no dynamic arg construction.

### Blue — Refactor complete
- [ ] If the repo-root/base-dir/`_ok`/`_err` boilerplate is duplicated verbatim across CLIs, note it for a shared `_cli_env.py` extraction — but only extract if WP scope already touches both (Boy-Scout scope rule: don't unbounded-side-quest). Otherwise leave a `TODO(deferred)` with a follow-on note.
- [ ] No new behaviour in Blue.
- [ ] All tests green after refactor.

## Sequence
- **dependsOn:** WP-004 (imports `capture_idea`)
- **blocks:** WP-009 (the skill invokes this CLI), WP-013 (dogfood emits through this CLI)
- **Parallelisable with:** WP-008 (the traverse CLI)

## Estimated Token Cost
- **Input:** ~8k (this WP + WP-004 contract + a sibling CLI for the shape)
- **Output:** ~3k (CLI script + integration test file)
- **Total:** ~11k

## Notes
- This CLI is the seam the dogfood WP (WP-013) drives — capture this change's own ideas *through* this CLI, never via `--from-srd` (TDD sequencing note).
- The integration test uses the real `LocalFileEntityAdapter` and real vendored schemas — no mock store (MEA-09).
