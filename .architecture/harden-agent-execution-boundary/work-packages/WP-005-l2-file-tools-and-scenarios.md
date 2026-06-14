---
# Identity (WP-01)
id: WP-005
title: L2 file-tools — read/write/move/remove over the scope-resolver + the L2 scenarios
status: pending
change_id: 01KTZVX7RBE22SX6DNHA4Y6Y7B
kind: backend
source: harden
primitive: create
group: EXPAND

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: low

# Lifecycle (WP-07)
sequence_id: WP-005
dependsOn: [WP-004]
blocks: []

# Composite (WP-08)
child_wps: []
kinds: null

estimated_token_cost:
  input: 9k
  output: 8k
tdd_section: §Form (_file_tools.py); §Armor L2 (fail-closed); §Proof (L2 scenario suite, SC-L2.5 honest limit)
adrs: [ADR-001, ADR-004, ADR-005]
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/integration/test_file_tools_scenarios.py

rollback: |
  Delete _file_tools.py + test_file_tools_scenarios.py. _file_scope (WP-004)
  remains; no agent file-tool surface is wired. Inert on its own.
---

# L2 file-tools + scenarios

## Context

TDD §Form / §Armor L2 / §Proof. The four thin file-tools the agent calls —
each resolves scope via WP-004's `within_allowed_scope` **first** (move checks
**both** source and destination), then performs the I/O. Proves the full L2
scenario set end-to-end, **including the honest-limit SC-L2.5** which asserts a
subprocess bypasses the tool and names L3 as the owner
([ADR-001](../adrs/ADR-001-l1-enforcement-vs-l3-dependency.md) /
[ADR-005](../adrs/ADR-005-honest-confinement-in-tests-without-l3.md)).

EXPAND-Create: new tools composing the WP-004 resolver — not a Wrap.

## Contract

### Files

```
plugins/sulis/scripts/_file_tools.py                                  (CREATE)
plugins/sulis/scripts/tests/integration/test_file_tools_scenarios.py  (CREATE)
```

### Behaviour (pin exactly)

```python
# _file_tools.py — each returns a typed (ok, reason|payload) Result; fail-closed
def read_file(path, change_id, *, repo_root) -> FileToolResult: ...
def write_file(path, content, change_id, *, repo_root) -> FileToolResult: ...
def move_file(src, dst, change_id, *, repo_root) -> FileToolResult:
    # checks within_allowed_scope(src, ..., "move") AND (dst, ..., "write")
def remove_file(path, change_id, *, repo_root) -> FileToolResult: ...
# Every tool calls within_allowed_scope BEFORE touching the filesystem.
# A refusal returns the resolver's reason verbatim; the FS is never touched.
```

### Reused

| Symbol | From | Role |
|---|---|---|
| `within_allowed_scope`, `resolve_allowed_roots`, `AllowedRoots` | `_file_scope` (WP-004) | the scope decision — called first in every tool |

## Definition of Done

> **Satisfies (scenarios):** **SC-L2.1** (in-scope read/write/move succeed),
> **SC-L2.2** (out-of-scope read refused, incl. canonical `/tmp`→`/private/tmp`),
> **SC-L2.3** (out-of-scope write/move/remove refused fail-closed; sibling
> worktree untouched — #130 replay), **SC-L2.4** (traversal/symlink escape
> refused), **SC-L2.5** (honest boundary: subprocess bypass succeeds + asserts
> the documented limit names L3).

### Red
- [ ] `test_file_tools_scenarios.py` written failing (real tmp filesystem, real
  worktree layout under `SULIS_STATE_DIR`):
  - **SC-L2.1:** read/write/move within the worktree and other allowlisted
    roots all succeed; the file content is actually written/moved on disk.
  - **SC-L2.2:** `read_file('~/.ssh/id_rsa', …)` and a read of a **sibling
    change's** worktree are refused with a clear reason; a target passed as
    `/tmp/<x>` (whose real path is `/private/tmp/<x>` on macOS) is canonicalised
    and judged correctly.
  - **SC-L2.3:** `write_file`/`move_file`/`remove_file` pointed at the #130
    sibling-worktree path are refused **fail-closed**; assert the sibling
    worktree directory is **still present** afterward (untouched).
  - **SC-L2.4:** a `..`-escape path and a symlink pointing outside scope are
    refused for every operation.
  - **SC-L2.5 (the honest limit):** `subprocess.run(["bash","-c","cat <out-of-scope>"])`
    **succeeds** (reads the file) — asserting the tool was bypassed entirely.
    The test asserts this is the documented limit AND that `_file_tools`'
    module docstring names **L3 (the OS sandbox, `l3-os-egress-denial`)** as the
    owner of the confinement L2 structurally cannot provide. No false security.

### Green
- [ ] `_file_tools.py` created; all Red pass. Each tool resolves scope before I/O.

### Blue
- [ ] `_file_tools` docstring states: L2 contains **honest mistakes**, not
  adversaries; a subprocess bypasses it by design (SC-L2.5); **L3 owns the
  wall** (ADR-001). One scope check per tool, all routed through `_file_scope`
  (no per-tool bespoke path logic — ADR-004).
- [ ] `move_file` checks **both** endpoints; a refusal on either leaves the FS
  untouched (assert no partial move).
- [ ] Stdlib + `_file_scope` only; portable; Python 3.11-safe.

## Sequence
- **dependsOn:** WP-004 (needs the resolver).
- **Parallelisable with:** the entire L1 track — disjoint files.

## Verification Plan
- **Adapter:** `backend`. **Shape:** concrete.
- **Artifact:** `plugins/sulis/scripts/tests/integration/test_file_tools_scenarios.py`.
- **Proves:** SC-L2.1–2.5 end-to-end on a real filesystem, with SC-L2.5 asserting
  the bypass and documenting L3 ownership (the honest boundary).
