---
id: WP-002
change_id: 01KV0GW39Q522P6PMFTTXH9T2E
title: write-roots resolver — add brain root + sandbox-config emit, one source for L2+L3
kind: backend
primitive: abstract
group: reorganise
status: pending
dependsOn: []
blocks: [WP-003, WP-004]
scenarios: [SC-E5]
characterisation_test: "plugins/sulis/scripts/tests/unit/test_file_scope.py (existing — pins current resolve_allowed_roots / within_allowed_scope behaviour before the extension)"
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_write_roots_resolver.py"
token_cost: { input: ~10k, output: ~8k }
---

# WP-002 — write-roots resolver: one source for file-tools + sandbox

## Context

TDD §Armor (single source of truth) + ADR-004 (extend `_file_scope`, don't
fork). The brain is moving out of the worktree, so its **resolved** path must
be a writable root; and the sandbox recipe (WP-004) needs the SAME roots as
`allowWrite` strings. This WP makes the single-source guarantee structural.
**REORGANISE-Abstract** (the existing resolver is generalised) → the
characterisation test (existing `test_file_scope.py`) must pass before and
after. Feeds WP-003 (hook) and WP-004 (sandbox recipe).

## Contract

- **Modified:** `scripts/_file_scope.py`:
  - `AllowedRoots` gains `brain_dir: Path | None`. `permitted_for(op)` includes
    it for all four ops when set (brain is shared rw).
  - `resolve_allowed_roots(...)` calls `brain_base_dir(repo_root)` (#127
    resolver — never hardcode `~/.sulis`). Sets `brain_dir` ONLY when the
    resolved brain path is **outside** the worktree (a relocated brain); leaves
    it `None` for the default in-worktree brain. Narrowest: the specific
    resolved subtree, never `~/.sulis/`.
  - **New pure function** `sandbox_write_roots(roots: AllowedRoots) -> list[str]`
    — emits the same rw roots as sandbox `allowWrite` path strings (`/abs`,
    `~/`, `./` prefixes per the sandbox docs — NOT the `//abs` permission
    syntax). The ONE adapter from `AllowedRoots` to sandbox-config shape.
- All roots stay canonical (`.resolve()`) and narrowest-root.

## Definition of Done

### Red
- [ ] `test_file_scope.py` (existing characterisation) passes unchanged →
      confirms the abstraction preserves current behaviour.
- [ ] `test_write_roots_resolver.py::test_relocated_brain_added` — a brain
      resolved outside the worktree appears as a writable root; an in-worktree
      brain adds NO extra root. **Fails** (no brain handling yet).
- [ ] `::test_sibling_change_refused` — a path under
      `~/.sulis/changes/{OTHER_ULID}/` is out of scope.
- [ ] `::test_never_whole_sulis` — `~/.sulis/` itself is never a root.
- [ ] `::test_single_source` — for a given change, the rw roots used by
      `within_allowed_scope` == the set `sandbox_write_roots(...)` emits
      (the drift-impossible assertion). Use hypothesis to vary repo_root /
      brain location.

### Green
- [ ] Implement the `brain_dir` field + conditional add + `sandbox_write_roots`.
      All Red + existing tests pass. **SC-E5 satisfied.**

### Blue
- [ ] No second roots-list anywhere (grep: sandbox emit derives only from
      `AllowedRoots`). Docstring records the git-common-dir / sandbox
      `.git`-auto-allow redundancy note (ADR-004). Confirm canonical-path
      handling (`/tmp`→`/private/tmp`) still covered by the inherited core.
