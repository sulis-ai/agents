---
founder_facing: false
---

# Spec — Spawned change windows run from the installed plugin, not a worktree copy

**Change:** CH-3FNT33 · fix

## Intent

When a change is started from inside another change's session, the spawned
terminal window must run its machinery — the desktop **viewer**, the session
**daemon** the viewer cold-starts, and the git **commit hooks** — from the
**installed plugin** (the versioned copy under the plugin cache), never from
the spawning change's worktree copy of the code.

Today it does the opposite. The launcher (`_terminal_launcher.py`) decides
where its sibling scripts live by looking at the file it is *itself* running
from (`Path(__file__).resolve().parent`). When `sulis-change start` runs inside
a change worktree (the normal dogfooding case), that file *is* the worktree
copy, so the spawned window execs `<worktree>/session_viewer.py`; the viewer
then resolves its own daemon binding from *its* location, and the daemon from
*its* location — so the whole spawn chain runs worktree code. This is fragile
(a half-finished worktree edit silently becomes the live machinery for an
unrelated change) and it is exactly the fork-the-running-code behaviour this
work exists to kill.

## Scope

- Resolve the **installed-plugin scripts directory** when building the spawned
  window's launch script, and use it for:
  1. the **viewer exec line** (`_terminal_launcher.py:303` → the `python3
     <scripts>/session_viewer.py …` the window runs); and
  2. the **origin-hook wiring** (`_terminal_launcher.py:350` → the
     `SULIS_SCRIPTS_DIR` export and the `core.hooksPath` GIT_CONFIG pointing at
     `<scripts>/hooks`).
- The resolver returns the scripts directory of the **newest installed plugin
  version** in the cache (`~/.claude/plugins/cache/sulis-ai-agents/sulis/<ver>/
  scripts`). Reuse the existing primitives — do not rebuild them (EP-03):
  `_prune_cache.default_cache_root()` / `_SULIS_SUBPATH` for the cache root, and
  `_version_pick.max_version()` for the numeric (non-lexical, #49-safe) version
  pick.
- **Escape hatch:** an explicit environment override lets a developer point the
  spawned machinery back at a chosen scripts directory when they are
  *intentionally* testing launcher/viewer/daemon changes from a worktree. When
  set and valid, the override wins over the cache pick. (Exact env-var name is a
  design-stage call.)
- **Graceful no-install fallback:** on a machine with no cached install (pure
  dev tree, fresh checkout with nothing installed), fall back to the launcher's
  own `Path(__file__).resolve().parent` — the current behaviour — rather than
  failing the spawn. A dev-only machine has no "installed plugin" to prefer, so
  its own tree is the honest answer.
- Confirm the same `__file__`-relative forking is not present elsewhere in the
  spawn chain that `sulis-change start` drives (best-effort sweep; fix in scope
  only if it's the same root cause in the same launcher path).

## Non-goals

- Changing **what** the spawned window runs (the viewer-attached-to-shared-
  session model from CH-01KTKB stays exactly as is) — only **which copy** of
  that code it runs.
- Changing how the viewer or daemon resolve their *own* sibling modules at
  runtime (`session_viewer.py:69`, `session_manager_daemon.py:67`). Pointing the
  exec'd viewer's path at the installed copy is sufficient: the viewer and
  daemon then self-locate from the installed copy by construction. Touching
  their internal resolution is out of scope.
- The version-skew daemon-restart guard (#102) — unchanged.
- Any change to the env-scrub preamble, the pre-prompt sidecar delivery, or the
  `SULIS_CHANGE_ID` binding hardening (#107).

## Acceptance

- **AC-1 — viewer runs from install.** A change started from inside a worktree
  spawns a window whose launch script execs `session_viewer.py` from the
  installed cache path, not the spawning worktree path.
- **AC-2 — hooks run from install.** The same launch script exports
  `SULIS_SCRIPTS_DIR` and sets `core.hooksPath` to the installed cache
  `scripts` / `scripts/hooks`, not the worktree's.
- **AC-3 — newest install wins.** With several versions cached, the resolver
  picks the numerically-newest (e.g. `0.126.0` over `0.98.0`), reusing
  `_version_pick` — never a lexical sort.
- **AC-4 — override wins.** With the dev-escape override set to a valid
  directory, the resolver returns it instead of the cache pick.
- **AC-5 — graceful fallback.** With no cached install and no override, the
  resolver returns the launcher's own directory and the spawn still succeeds
  (no crash, no empty path).
- **AC-6 — security preserved.** Every resolved path is still `shlex.quote`-d
  into the launch script exactly as today; the injection-safety property of the
  viewer exec line and hook exports is unchanged.

## Constraints

- **Stdlib only** (NFR-5, mirrors the launcher's existing constraint): the
  resolver imports only from the existing leaf helpers (`_prune_cache`,
  `_version_pick`) plus stdlib.
- **Reuse, don't rebuild** (EP-03): `default_cache_root()` and `max_version()`
  already exist and are unit-tested; the resolver composes them rather than
  re-deriving cache paths or version ordering.
- **Test-first** (EP-02): each acceptance criterion lands as a failing unit
  test before the resolver change. The launcher already has
  `tests/unit/test_terminal_launcher.py` and
  `test_terminal_launcher_runs_viewer.py` — extend those, don't fork a new
  suite.
- **No behavioural change on a fully-installed single-version machine** other
  than the path now being resolved explicitly rather than via `__file__` (on
  such a machine the two already coincide — the test must assert the explicit
  path equals the install).
- **Leave the file better** (EP-07): the two `Path(__file__).resolve().parent`
  call sites collapse to one named resolver; characterise current behaviour
  first.

## Verification Plan

- **How we'll know it's done:** unit tests drive the resolver and the generated
  launch-script body directly (the launcher is already structured for this —
  `_build_launch_script` is a pure function returning the script string, so a
  test can assert the exec line and the hook exports contain the installed path,
  not a worktree path). This is the green-but-broken guard: we assert the
  *resolved path in the emitted script*, not merely that the function ran.
- **Foundational checks:**
  - Resolver returns the newest cached `…/sulis/<ver>/scripts` given a fake
    cache under `tmp_path` (AC-3).
  - Resolver returns the override dir when the escape-hatch env var points at a
    valid directory (AC-4).
  - Resolver returns `Path(__file__).parent` when the fake cache is empty and no
    override is set (AC-5).
  - `_build_launch_script(...)` / `_build_viewer_exec_line(...)` emit the
    installed path in the `exec … session_viewer.py` line and in the
    `SULIS_SCRIPTS_DIR` / `GIT_CONFIG_VALUE_0` exports (AC-1, AC-2), with the
    path still `shlex.quote`-d (AC-6).
- **Integration / manual:** start a change from inside this very worktree and
  confirm the spawned window's `~/.sulis/changes/<id>/launch.sh` references the
  cache `session_viewer.py`, not the worktree's. (Recorded as the change's
  acceptance walk; this is the real-world repro that motivated the fix.)
- **Out of scope for verification:** the viewer's and daemon's own runtime
  self-location (unchanged); cross-platform terminal spawn behaviour (unchanged).

## Notes

- **Founder-owned call (none material).** This is internal build machinery with
  no user-visible surface; the intent is unambiguous. The two judgement calls —
  the resolution order and the exact escape-hatch env-var name — are
  engineering-internal and are settled at design time, not surfaced to the
  founder.
- The `exercises` design ref for any verification scenario is a synthetic
  placeholder at spec time; it resolves when the design stage emits the real
  Design entity.
