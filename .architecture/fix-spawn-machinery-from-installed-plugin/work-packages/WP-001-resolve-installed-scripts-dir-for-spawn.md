---
id: WP-001
title: "Resolve the installed-plugin scripts dir for the spawned viewer exec line + origin hook"
status: pending
change_id: 01KV0WE0CH3FNT3361WGPB2HBZ
kind: backend
primitive: fix
group: REINFORCE
composite_of: ["REORGANISE-Refactor (collapse 2 __file__.parent sites → 1 resolver)", "REINFORCE-Harden (cache/override/fallback resolution)"]
characterisation_test: "test_explicit_scripts_dir_equals_install_on_single_version_machine"
sequence_id: WP-001
dependsOn: []
blocks: []
estimated_token_cost:
  input: 8k
  output: 7k
tdd_section: "../DESIGN.md (lightweight design note; no full TDD — contained fix)"
adrs: []
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_terminal_launcher_runs_viewer.py::test_viewer_exec_line_targets_installed_cache_scripts; plugins/sulis/scripts/tests/unit/test_terminal_launcher.py::test_origin_hook_targets_installed_cache_scripts"
---

## Context

`plugins/sulis/scripts/_terminal_launcher.py` self-locates the spawned window's
sibling scripts from the **launcher's own file** at two sites:

- **Line 303** (`_build_launch_script`, default/viewer path):
  `scripts_dir = Path(__file__).resolve().parent` → `_build_viewer_exec_line(...)`
  → the `exec env … python3 <scripts>/session_viewer.py …` the window runs.
- **Line 350** (`enable_origin_hook` block):
  `scripts_dir = Path(__file__).resolve().parent`; `hooks_dir = scripts_dir / "hooks"`
  → `export SULIS_SCRIPTS_DIR=<scripts>` and `GIT_CONFIG_VALUE_0=<scripts>/hooks`
  (`core.hooksPath`) for the spawned session's git.

When `sulis-change start` runs from a change worktree (the normal dogfooding
case), `__file__` **is** the worktree copy, so the spawned window execs worktree
code; the viewer (`session_viewer.py:69`) and daemon (`session_manager_daemon.py:67`)
then self-locate forward from there, so the whole chain runs worktree code. This
WP redirects both launcher sites at the **installed** plugin scripts dir; the
viewer→daemon→hooks chain then runs from the install **by construction** (DESIGN
§1). The viewer/daemon internal self-location is **not** touched (DESIGN DD-3 /
spec non-goal).

**Primitive = fix; group = REINFORCE (composite with a REORGANISE-Refactor).**
The dominant shape is a one-resolver hardening of an existing code path against a
fork-the-running-code failure mode, proven test-first. The two `__file__.parent`
call sites collapse into one named resolver (EP-07 boy-scout refactor) — the
REORGANISE component, gated by a characterisation test per Non-Negotiable #3.
No new public surface, no new component.

## Contract

### Files modified

```
plugins/sulis/scripts/_terminal_launcher.py                              (+ resolver ~20 LOC; 2 call-site edits)
plugins/sulis/scripts/tests/unit/test_terminal_launcher_runs_viewer.py   (+ resolver + viewer-exec-line RED/coverage tests)
plugins/sulis/scripts/tests/unit/test_terminal_launcher.py               (+ origin-hook RED test)
```

Touch surface = 3 path entries — well under the ≤15 MUST.

### New function

```python
def _resolve_installed_scripts_dir() -> Path:
    """Scripts dir to bake into the spawned launch script (viewer exec + hooks).

    Resolution order (DESIGN §2 / DD-2):
      1. SULIS_SPAWN_SCRIPTS_DIR (dev escape hatch, DD-1) — when set AND points
         at an existing dir, return it resolved.
      2. Newest cached install — _prune_cache.default_cache_root() joined with
         _prune_cache._SULIS_SUBPATH ("sulis-ai-agents", "sulis"), then the
         _version_pick.max_version(<dir names>) version, then "scripts" — when
         that scripts dir exists.
      3. Fallback — Path(__file__).resolve().parent (today's behaviour), so a
         pure-dev machine with no install still spawns successfully (AC-5).
    """
```

- **Env var name = `SULIS_SPAWN_SCRIPTS_DIR`** (DD-1). Do **not** reuse
  `SULIS_SCRIPTS_DIR` — that name is already an *output* of this launcher
  (line 352), and reusing it as an input is ambiguous and an inherited-value
  foot-gun.
- **Composition only** (EP-03): use `_prune_cache.default_cache_root()`,
  `_prune_cache._SULIS_SUBPATH`, and `_version_pick.max_version(...)`. Do **not**
  re-derive the cache path or re-implement version ordering. Import them the same
  way the module already imports sibling leaf modules
  (`sys.path.insert(0, str(Path(__file__).parent))` is already at module top;
  add `import _prune_cache` / `import _version_pick` alongside `_change_session`).
- **Stdlib only** (NFR-5): `os`/`pathlib` + the two existing stdlib-only leaf
  modules. No new third-party import.

### Behavioural contract

1. **Override wins when valid (AC-4).** `SULIS_SPAWN_SCRIPTS_DIR` set to an
   existing directory → resolver returns it (resolved). Set-but-missing /
   unset → fall through.
2. **Newest cached install otherwise (AC-3).** With versions cached under
   `…/sulis-ai-agents/sulis/<ver>/`, the resolver returns
   `…/<max_version>/scripts`, picking the **numerically** newest via
   `_version_pick` (e.g. `0.126.0` over `0.98.0`) — never a lexical sort.
   Only returned when that `scripts` dir exists.
3. **Graceful fallback (AC-5).** No override + no cached install (or cache present
   but the resolved `scripts` dir missing) → return `Path(__file__).resolve().parent`.
   Never crash, never return an empty path.
4. **Both call sites use the resolver (AC-1, AC-2).**
   - Line 303: `scripts_dir = _resolve_installed_scripts_dir()` before
     `_build_viewer_exec_line(...)`.
   - Line 350: `scripts_dir = _resolve_installed_scripts_dir()`;
     `hooks_dir = scripts_dir / "hooks"` unchanged thereafter.
5. **Quoting unchanged (AC-6).** Every resolved path stays `shlex.quote`-d at the
   existing sites (`_build_viewer_exec_line`'s `shlex.quote(str(viewer))`;
   the `export SULIS_SCRIPTS_DIR=` / `GIT_CONFIG_VALUE_0=` `shlex.quote` calls).
   The resolver changes *which* path is quoted, not the quoting.

### Public-surface invariants (must NOT change)

- `_build_launch_script` / `_build_viewer_exec_line` signatures unchanged — they
  still accept a `scripts_dir`; only the **value** the caller passes changes.
  (Keeping `_build_viewer_exec_line(scripts_dir)` parameterised keeps it pure and
  directly unit-testable with a fake dir — do not inline the resolver into it.)
- No change to the env-scrub preamble, `SULIS_CHANGE_ID` export/binding, the
  pre-prompt sidecar, or the chat-style `entry_command` path.
- On a fully-installed single-version machine, the explicitly-resolved path
  **equals** the install (Constraint: no behavioural change other than explicit
  resolution; pinned by the characterisation test).

### What this WP is NOT

- It does **not** modify `session_viewer.py:69` or
  `session_manager_daemon.py:67` (DD-3 / spec non-goal). Pointing the exec'd
  viewer's path at the install is sufficient.
- It does **not** add caching, daemon-restart, or version-skew logic (#102 — out
  of scope).
- It does **not** widen `_build_viewer_exec_line`'s signature or change how the
  hooks block is structured beyond swapping the `scripts_dir` source.

## Definition of Done

### Red — Failing/characterisation tests written first (Non-Negotiable #1 & #3)

Add to `test_terminal_launcher_runs_viewer.py` (resolver + viewer-exec coverage)
and `test_terminal_launcher.py` (origin-hook coverage). Use a **fake cache under
`tmp_path`** and `monkeypatch` for the env var and `default_cache_root` — never
the developer's real `~/.claude`.

- [ ] **Characterisation (EP-07 — pin current behaviour before refactor):**
      `test_explicit_scripts_dir_equals_install_on_single_version_machine` —
      with a fake cache holding exactly one version whose `scripts` dir exists,
      `_resolve_installed_scripts_dir()` returns that `…/<ver>/scripts`. Confirms
      the explicit resolution equals the install on the single-version machine
      (the "no behavioural change" Constraint). *(Passes once the resolver
      exists; pins the no-regression contract.)*

- [ ] **(AC-3) newest install wins, numerically:**
      `test_resolver_picks_numerically_newest_cached_install` — fake cache with
      `0.98.0` and `0.126.0` (both with a `scripts` subdir), no override →
      resolver returns the `0.126.0/scripts` path (NOT `0.98.0`, the lexical
      winner). RED against a naive lexical implementation; proves `_version_pick`
      is used.

- [ ] **(AC-4) override wins:**
      `test_resolver_honours_spawn_scripts_dir_override` — set
      `SULIS_SPAWN_SCRIPTS_DIR` to an existing tmp dir while a fake cache also
      exists → resolver returns the override dir, not the cache pick. Also assert
      a **set-but-missing** override falls through to the cache pick (not a hard
      fail).

- [ ] **(AC-5) graceful fallback:**
      `test_resolver_falls_back_to_module_dir_with_no_install_no_override` —
      empty/absent fake cache, no override → resolver returns
      `Path(tl.__file__).resolve().parent`. No exception, non-empty path.

- [ ] **(AC-1) viewer exec line carries the installed path:**
      `test_viewer_exec_line_targets_installed_cache_scripts` — with a fake cache
      (newest version `scripts` dir) and `default_cache_root` monkeypatched at
      it, `_build_launch_script(_GOOD_ULID, tmp_path)` emits an
      `exec … python3 <cache>/…/scripts/session_viewer.py …` line — the **cache**
      path, NOT `Path(tl.__file__).parent/session_viewer.py`. Assert the cache
      scripts path string is in the script and the module-dir viewer path is not.

- [ ] **(AC-2) origin-hook exports carry the installed path:** in
      `test_terminal_launcher.py`,
      `test_origin_hook_targets_installed_cache_scripts` — with the same fake
      cache, `_build_launch_script(_GOOD_ULID, tmp_path, enable_origin_hook=True)`
      emits `export SULIS_SCRIPTS_DIR=<cache>/…/scripts` and
      `GIT_CONFIG_VALUE_0=<cache>/…/scripts/hooks` — the cache paths, NOT the
      module dir.

- [ ] **(AC-6) injection guard preserved:**
      `test_resolved_path_still_shlex_quoted_in_script` — point the override at a
      tmp dir whose name contains shell metacharacters
      (e.g. `a dir; $(echo evil)`); the emitted viewer exec line and the
      `SULIS_SCRIPTS_DIR` / `GIT_CONFIG_VALUE_0` exports single-quote it, and the
      generated script parses under `bash -n` (mirror the existing
      `test_build_viewer_exec_line_shlex_quotes_args` pattern).

### Green — Implementation makes the tests pass

- [ ] `_resolve_installed_scripts_dir()` added to `_terminal_launcher.py`,
      composing `_prune_cache.default_cache_root()` / `_SULIS_SUBPATH` +
      `_version_pick.max_version(...)`, with the DD-2 resolution order and the
      `SULIS_SPAWN_SCRIPTS_DIR` (DD-1) escape hatch. Stdlib-only (NFR-5).
- [ ] Line 303 site: `scripts_dir = _resolve_installed_scripts_dir()`.
- [ ] Line 350 site: `scripts_dir = _resolve_installed_scripts_dir()`;
      `hooks_dir = scripts_dir / "hooks"` unchanged.
- [ ] All seven Red tests above pass.
- [ ] **All existing launcher tests stay green** — in particular the viewer/
      origin-hook/bash-parse regression tests in both suites
      (`test_default_exec_line_runs_viewer_not_claude`,
      `test_build_viewer_exec_line_targets_colocated_viewer` — see note below,
      `test_viewer_path_preserves_origin_hook`,
      `test_build_launch_script_wires_origin_hook`,
      `test_generated_viewer_script_parses_under_bash`,
      `test_generated_viewer_script_runs_to_exec_under_bash`).

> **Pre-existing test to reconcile.**
> `test_build_viewer_exec_line_targets_colocated_viewer` (runs_viewer suite,
> ~line 56) passes `Path(tl.__file__).resolve().parent` **explicitly** into
> `_build_viewer_exec_line` and asserts the co-located viewer path. Because
> `_build_viewer_exec_line` keeps its `scripts_dir` parameter (we do NOT inline
> the resolver into it), this test stays valid as-is — it tests the pure builder
> with a caller-supplied dir, which is exactly the seam the new tests exercise
> with a *different* (cache) dir. No edit needed; confirm it still passes.

### Blue — Refactor / hygiene complete

- [ ] **The two `Path(__file__).resolve().parent` call sites (303, 350) are gone**
      — both replaced by the single `_resolve_installed_scripts_dir()` call
      (EP-07: the file is left better — one named resolver, not two duplicated
      self-locations). `grep -n "Path(__file__).resolve().parent" _terminal_launcher.py`
      shows only the resolver's own fallback line (and the module-top
      `sys.path.insert`), not the two former call sites.
- [ ] Resolver has a docstring stating the resolution order + why
      `SULIS_SPAWN_SCRIPTS_DIR` (not `SULIS_SCRIPTS_DIR`) — DD-1 rationale inline
      so the next reader doesn't re-litigate it.
- [ ] `ruff check` + `ruff format --check` clean on the three modified files.
- [ ] Full launcher unit suite green:
      `pytest plugins/sulis/scripts/tests/unit/test_terminal_launcher.py
      plugins/sulis/scripts/tests/unit/test_terminal_launcher_runs_viewer.py`.

## Sequence

- **dependsOn:** none — sole WP in this change.
- **blocks:** none.
- **Parallelisable with:** n/a.

## Estimated Token Cost

- **Input:** ~8k (the two launcher call-site regions + `_build_viewer_exec_line`
  + `_prune_cache` + `_version_pick` + both existing test suites for the
  monkeypatch/fixture patterns).
- **Output:** ~7k (~20-LOC resolver + 2 one-line call-site swaps + ~7 unit tests
  with fake-cache `tmp_path` setup).
- **Total:** ~15k.

## Notes

- **Why one WP (DD-4):** resolver + the two redirects are one atomic change — the
  redirect cannot land without the resolver, and the characterisation test gates
  both. Splitting would yield a resolver-added-but-unused WP plus a wholly
  dependent second WP — no value in the split.
- **Why the cache `scripts`-dir-exists guard:** a cache root can hold a version
  dir whose layout is partial/mid-install; requiring the concrete `scripts`
  subdir to exist before returning it keeps the resolver from baking a
  non-existent path into the spawn (falls through to the next tier instead).
- **No TDD / no ADR / journey-walk exempt:** contained, non-user-facing build
  machinery (the surface is the `sulis-change` spawn path, not a founder-facing
  product surface). Design decisions live in `../DESIGN.md`; an ADR would be
  ceremony for a single-resolver fix following established in-repo composition.

## Verification Plan

- **What behaviour is verified:** a change started from inside a worktree spawns
  a window whose launch script execs `session_viewer.py` from the **installed
  cache** path and whose origin-hook exports (`SULIS_SCRIPTS_DIR`,
  `core.hooksPath`) point at the **installed cache** `scripts` / `scripts/hooks`
  — not the spawning worktree. With several versions cached, the
  numerically-newest wins. A valid override redirects the resolver; with no
  install and no override the spawn still succeeds against the launcher's own
  dir. Every resolved path stays `shlex.quote`-d.
- **Verification environment:** local + CI, pure unit tests against the pure
  `_build_launch_script` / `_build_viewer_exec_line` / `_resolve_installed_scripts_dir`,
  with a **fake cache under `tmp_path`** and `monkeypatch` for the env var and
  `default_cache_root`. No real `~/.claude` touched, no terminal spawned.
- **Bootstrap-from-zero:** a fresh clone at the merge SHA runs
  `pytest plugins/sulis/scripts/tests/unit/test_terminal_launcher.py
  plugins/sulis/scripts/tests/unit/test_terminal_launcher_runs_viewer.py` and the
  new tests plus all existing launcher tests pass with no extra setup (stdlib +
  pytest only; the fake cache is built in-test under `tmp_path`).
- **Per-integration strategy:** the only "integration" is the plugin cache layout
  on disk. Strategy: **in-memory / real-tmp** — a fake cache tree is materialised
  under `tmp_path` and `default_cache_root` is monkeypatched at it (no mock of the
  resolver's logic; the real `_version_pick` / `_prune_cache` run against real
  dirs). Classification: `existing` (both leaf helpers exist and are unit-tested;
  this WP composes them). No vendor mock, no network — fully hermetic.
- **Per-kind adapter (`backend`):** verification artifacts are pytest nodeids:
  - `test_terminal_launcher_runs_viewer.py::test_explicit_scripts_dir_equals_install_on_single_version_machine` (characterisation)
  - `…::test_resolver_picks_numerically_newest_cached_install` (AC-3)
  - `…::test_resolver_honours_spawn_scripts_dir_override` (AC-4)
  - `…::test_resolver_falls_back_to_module_dir_with_no_install_no_override` (AC-5)
  - `…::test_viewer_exec_line_targets_installed_cache_scripts` (AC-1)
  - `…::test_resolved_path_still_shlex_quoted_in_script` (AC-6)
  - `test_terminal_launcher.py::test_origin_hook_targets_installed_cache_scripts` (AC-2)
- **Verification shape:** **concrete** — the WP ships its own RED→GREEN unit
  tests the moment it lands. No deferred infrastructure.
- **Acceptance trace:** AC-1..AC-6 each map to a named test above; the
  characterisation test pins the no-behavioural-change Constraint on a
  single-version machine.
