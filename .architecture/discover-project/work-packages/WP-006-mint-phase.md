---
id: WP-006
title: Implement Mint phase — atomic write + path safety + signal handler + slug derivation
status: pending
kind: backend
primitive: create
group: GENERATE
change_id: CH-01KT1W
sequence_id: WP-006
dependsOn: [WP-001, WP-002]
blocks: [WP-008]
estimated_token_cost:
  input: 4k
  output: 4k
tdd_section: Armor §Atomic write semantics; Armor §Path-safety check; Form §Slug derivation
adrs: [ADR-005]
---

## Context

Implements the Mint phase per TDD §Armor §Atomic write semantics +
§Path-safety check + Form §Slug derivation. The Step
`write-project-entity` (Step ULID `01KT1WDSST08WRITEPROJEC`, per TDD
§Canonical Identifiers) is the only writing step in the Workflow.

Five concerns ride together because they are all properties of the
single atomic write contract:

1. **Atomic write** — write-to-tmp-then-rename + `os.fsync` (TDD §Armor).
2. **Path safety** — resolve target + assert `is_relative_to(<consuming_repo_root>/.sulis/projects/)` before any write (NFR-004 / TDD §Armor §Path-safety check).
3. **Slug derivation** — `slug(project_name)` and `slug(monorepo_path)` per TDD §Form §Slug derivation; collision detection per MUC-007.
4. **Signal handler** — SIGINT during the write window leaves only a `.tmp` file; the signal handler + session-start sweep remove stale `.tmp` files (TDD §Armor §Atomic; MUC-002).
5. **Composition with the diff flow** — when `--update` is set, the entity composed for write merges approved-proposed + preserved-existing per ADR-005 / FR-009; the diff decisions come from the Ask phase (WP-005 prose drives the prompts, WP-008's composition root collects the answers).

Per the Ports-vs-Wrappers discriminator: this is a thin domain
function over filesystem + `entity-emitter` (reused per WP-001's
`tools.jsonld` declaration). The implementation calls the existing
entity-emitter Tool; no wrapping involved.

## Contract

### Files created

```
plugins/sulis/scripts/_discovery/
├── minter.py                     # write_project_entity + path_safety_assert + signal_handler + stale_tmp_sweep
└── slug.py                       # slug(project_name) + slug(monorepo_path)
plugins/sulis/scripts/tests/unit/
├── test_discovery_minter.py      # atomic + path-safety + cancellation tests
└── test_discovery_slug.py        # slug derivation + collision-detection tests
```

4 files.

### Module shape

```python
# plugins/sulis/scripts/_discovery/slug.py
import re

_SLUG_RE = re.compile(r"[^a-z0-9-]")

def slug_from_project_name(project_name: str) -> str:
    """Lowercase + replace non-[a-z0-9-] with '-'. Collapse runs of '-' to one."""

def slug_from_monorepo_path(path: str) -> str:
    """Lowercase the basename. apps/cli → 'cli'. packages/@scoped/foo → 'foo'.
    Strip leading '@' if present after basename extraction."""
```

```python
# plugins/sulis/scripts/_discovery/minter.py
import json
import os
import signal
import subprocess
from pathlib import Path

from _discovery.tenant import Sha256CrockfordTenantDeriver


class PathOutsideAllowedDirectoryError(Exception): ...   # NFR-004 violation
class EntityAlreadyExistsError(Exception): ...           # MUC-003
class MonorepoSlugCollisionError(Exception): ...         # MUC-007


def consuming_repo_root() -> Path:
    """git rev-parse --show-toplevel, resolved."""

def write_project_entity(
    target_path: Path,
    entity: dict,
    *,
    allow_overwrite: bool = False,
) -> None:
    """Atomic write: tmp → fsync → rename.

    Preconditions enforced before any write:
      - target_path.resolve().is_relative_to(consuming_repo_root / ".sulis" / "projects")  (NFR-004)
      - target_path.parent exists or is mkdir-able
      - target_path does not exist OR allow_overwrite=True               (MUC-003 unless --update)

    Postconditions:
      - either the full entity is at target_path, OR target_path is absent
      - no .tmp file remains on success
    """

def stale_tmp_sweep(projects_dir: Path) -> int:
    """Remove .sulis/projects/*.tmp files. Returns count removed.

    Invoked on session start AND on signal handler (TDD §Armor §Atomic).
    """

def install_sigint_handler(projects_dir: Path) -> None:
    """Register a SIGINT handler that sweeps .tmp files before exit.
    Re-raises SIGINT (default behaviour) so the operator gets a clean
    KeyboardInterrupt at the top of the stack.
    """
```

### Path-safety implementation

```python
def _assert_path_safety(target_path: Path, consuming_root: Path) -> None:
    resolved = target_path.resolve()
    allowed_dir = (consuming_root / ".sulis" / "projects").resolve()
    if not resolved.is_relative_to(allowed_dir):
        raise PathOutsideAllowedDirectoryError(
            f"Refusing to write outside {allowed_dir}: {resolved}"
        )
```

Per TDD §Armor §Path-safety check: this MUST run before mkdir, before
tmp file creation, before any I/O that touches the target — first thing
in `write_project_entity`.

## Definition of Done

### Red — Failing tests written

**Atomic write:**

- [ ] `test_discovery_minter.py::test_atomic_write_produces_target_on_success` — given a clean dir, write succeeds and `target_path` contains the full entity JSON
- [ ] `test_discovery_minter.py::test_atomic_write_leaves_no_tmp_on_success` — after a successful write, `*.tmp` files in the dir == 0
- [ ] `test_discovery_minter.py::test_atomic_write_calls_fsync_before_rename` — instrument via `monkeypatch` on `os.fsync` to assert it's called before `tmp.replace(target)`
- [ ] `test_discovery_minter.py::test_sigint_between_write_and_rename_leaves_only_tmp` — chaos shim raises SIGINT after `tmp.write_text` but before `tmp.replace`; assert `target_path` does NOT exist and ONLY `target_path.with_suffix(".jsonld.tmp")` exists
- [ ] `test_discovery_minter.py::test_stale_tmp_sweep_removes_dot_tmp_files` — given `.sulis/projects/foo.jsonld.tmp` + `.sulis/projects/bar.jsonld` in a fixture, `stale_tmp_sweep` removes only the `.tmp` file and returns 1
- [ ] `test_discovery_minter.py::test_idempotent_after_cancellation` — sweep removes stale `.tmp`; re-running discovery produces the same outcome as a first-time run (NFR-003)

**Path safety:**

- [ ] `test_discovery_minter.py::test_path_safety_blocks_symlink_traversal` — given a symlink at `.sulis/projects/evil → /tmp/evil-target`, `write_project_entity` raises `PathOutsideAllowedDirectoryError`
- [ ] `test_discovery_minter.py::test_path_safety_blocks_dotdot_traversal` — `target_path = repo_root / ".sulis" / "projects" / ".." / "evil.jsonld"` raises
- [ ] `test_discovery_minter.py::test_path_safety_blocks_marketplace_projects_write` — attempting to write to `plugins/sulis/instances/release-train/projects.jsonld` raises (the marketplace-projects-corruption case from TDD §Armor §Path-safety check)
- [ ] `test_discovery_minter.py::test_path_safety_runs_before_any_io` — instrument `Path.mkdir` + `Path.write_text` via `monkeypatch`; assert neither is called when path safety fails

**Pre-existing entity (MUC-003):**

- [ ] `test_discovery_minter.py::test_refuses_overwrite_without_allow_flag` — target exists, `allow_overwrite=False` → raises `EntityAlreadyExistsError`
- [ ] `test_discovery_minter.py::test_allows_overwrite_with_flag` — target exists, `allow_overwrite=True` → writes successfully

**Slug derivation + collision (TDD §Form §Slug derivation; MUC-007):**

- [ ] `test_discovery_slug.py::test_slug_from_project_name_lowercases` — `"Payments App"` → `"payments-app"`
- [ ] `test_discovery_slug.py::test_slug_from_project_name_replaces_special_chars` — `"My/Repo.v2"` → `"my-repo-v2"`
- [ ] `test_discovery_slug.py::test_slug_from_project_name_collapses_runs` — `"Acme   //  App"` → `"acme-app"` (single `-` between tokens)
- [ ] `test_discovery_slug.py::test_slug_from_monorepo_path_basename` — `"apps/cli"` → `"cli"`
- [ ] `test_discovery_slug.py::test_slug_from_monorepo_path_strips_scope` — `"packages/@scoped/foo"` → `"foo"`
- [ ] `test_discovery_slug.py::test_slug_is_deterministic` — 100 invocations same input → same output

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/scripts/_discovery/slug.py` authored
- [ ] `plugins/sulis/scripts/_discovery/minter.py` authored
- [ ] All 18 Red tests pass
- [ ] Coverage on both files ≥ 90%
- [ ] `write_project_entity` runs path-safety FIRST, then existence check, then mkdir + tmp write + fsync + rename — order matters and is documented in the function docstring

### Blue — Refactor complete

- [ ] Path-safety + existence-check + atomic-write are three private helpers; `write_project_entity` composes them — read like a recipe
- [ ] Signal handler installation is idempotent (calling `install_sigint_handler` twice doesn't double-register)
- [ ] No global module state (no module-level `installed_handler` flag; the registration is keyed by `projects_dir`)
- [ ] Each function carries `# canonical:step:<name>` annotation matching the Step it implements

## Sequence

- **dependsOn:**
  - WP-001 (the Step entity `write-project-entity` and Tool `entity-emitter` reuse declaration live there)
  - WP-002 (`Sha256CrockfordTenantDeriver` is imported here to populate `belongs_to_tenant` when the composition root invokes the mint)
- **blocks:** WP-008 (skill prose imports `write_project_entity`, `stale_tmp_sweep`, `install_sigint_handler`, and the slug helpers)
- **Parallelisable with:** WP-003, WP-004, WP-005, WP-007, WP-009 (no shared files)

## Estimated Token Cost

- **Input:** ~4k (TDD §Armor §Atomic + §Path-safety + §Slug; MUC-002 / MUC-003 / MUC-007 system response strings)
- **Output:** ~4k (`minter.py` ≈ 180 LOC + `slug.py` ≈ 50 LOC + test files ≈ 260 LOC)
- **Total:** ~8k

## Performance

- The mint operation is bounded by filesystem latency only (no LLM, no network). Atomic-write + fsync on a typical Project entity (≤5KB JSON) completes in <50ms on local disk.
- `stale_tmp_sweep` is O(n) over `.sulis/projects/*.tmp` files; in practice this is 0..1 files per run.

## Notes

- The atomic-write pattern is POSIX-guaranteed (`os.replace` is atomic on the same filesystem). Cross-filesystem moves are out of scope — `.sulis/projects/` is inside the repo, so always same-filesystem.
- Symlink-traversal protection: `.resolve()` follows symlinks before the `is_relative_to` check. If `.sulis/projects/evil` is a symlink to `/tmp/...`, `.resolve()` produces `/tmp/...` which is not under `<repo_root>/.sulis/projects` → raises. Tested explicitly.
- The signal handler intentionally re-raises SIGINT after sweeping — operators get a clean `KeyboardInterrupt`, not a silent absorption. TDD §Armor §Atomic write semantics names this behaviour.
- Slug collision detection lives in the composition root (WP-008's skill prose), not in `minter.py`. This WP exposes the building block (`slug_from_project_name`, `slug_from_monorepo_path`); the composition logic decides what to do when a slug collides with an existing sibling.
