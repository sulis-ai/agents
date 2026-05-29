# ADR-001 — The contract renderer is a `wpx-render-contract` Python step

> Status: accepted · 2026-05-29 · change: cockpit-contract-preview

## Decision

The data-contract renderer is a deterministic **Python CLI step** named
`wpx-render-contract`, living in `plugins/sulis/scripts/` alongside the other
`wpx-*` tools, dispatched through the `wpx` shim, and built on `_wpxlib.py`
(stdlib-only, `emit_ok`/`emit_error`, `add_common_args`). It takes a worktree
path and emits a self-contained `CONTRACT.html` (plus a small manifest of what
was produced) into that worktree.

## Why

- **Convention (CP-01, internal prior art).** Every existing pipeline step the
  cockpit consumes (`wpx-worktree`, `wpx-pipeline`, `wpx-step12`) is a
  stdlib-only Python `wpx-*` script with the same arg + JSON-emit shape. A new
  rendering step that matches this is pattern-matchable by the rest of the
  toolchain and by `run-all`/design-time orchestration. The task brief makes
  this binding.
- **Determinism + no-drift.** The render must be reproducible from
  source-of-truth artifacts. A CLI step invoked at a known point in the
  pipeline (after decompose, before dispatch) is the natural seam — the cockpit
  reads the produced file, it does not render at request time.
- **Separation from the cockpit.** Keeping the renderer in the step toolchain
  (not in `apps/cockpit/server`) keeps the cockpit read-only: the cockpit
  *serves* an artifact a step *produced*. This preserves the read-only
  inventory invariant (cockpit `router.get` only; no generation in-process).

## Rejected alternatives

- **Render inside the cockpit server on request.** Rejected: breaks the cockpit
  read-only invariant, makes every page-load do CPU-bound rendering, and
  couples the renderer's dependencies (Redoc/Node tooling) into the always-on
  server process.
- **A standalone Node script.** Rejected: the wpx toolchain is Python; a Node
  step would be the only one, fragmenting the convention. Redoc's CLI is
  invoked *by* the Python step as a subprocess (see ADR-002), which keeps the
  orchestration uniform while still using the conventional renderer.

## Consequence

Downstream WPs treat `wpx-render-contract` as a peer of `wpx-worktree`. The
`wpx` dispatcher gains one subtool. The renderer's only inputs are a worktree
path + the change record; it never hard-wires a change (ADR-004).
