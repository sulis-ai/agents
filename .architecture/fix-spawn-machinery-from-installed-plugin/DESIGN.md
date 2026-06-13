---
founder_facing: false
change_id: 01KV0WE0CH3FNT3361WGPB2HBZ
handle: CH-3FNT33
primitive: fix
sourced_from: ".changes/fix-spawn-machinery-from-installed-plugin.SPEC.md"
status: designed
journey-walk: "exempt — internal build machinery, no user round-trip"
---

# Design note — Spawn machinery resolves the installed-plugin scripts dir

> Lightweight design (contained `fix`; no full TDD warranted). One root cause,
> one resolver, two call-site redirects, one WP. The spec
> (`.changes/fix-spawn-machinery-from-installed-plugin.SPEC.md`) is authoritative
> for scope/ACs; this note records the design-stage decisions the spec deferred
> (resolution order, env-var name, the don't-touch-self-location boundary) and
> the Form/Armor/Proof shape of the fix.

## 1. Root cause (confirmed against current code)

`plugins/sulis/scripts/_terminal_launcher.py` decides where the spawned
window's sibling scripts live by self-locating from the **launcher's own file**:

- **Line 303** (`_build_launch_script`, default/viewer path):
  `scripts_dir = Path(__file__).resolve().parent` → fed to
  `_build_viewer_exec_line(...)` → the `exec env … python3 <scripts>/session_viewer.py
  --change-id … --worktree …` the spawned window runs.
- **Line 350** (`enable_origin_hook` block):
  `scripts_dir = Path(__file__).resolve().parent`; `hooks_dir = scripts_dir / "hooks"`
  → the `export SULIS_SCRIPTS_DIR=<scripts>` and the `GIT_CONFIG_VALUE_0=<scripts>/hooks`
  (`core.hooksPath`) the spawned session's git uses.

When `sulis-change start` runs from a change worktree, `__file__` **is** the
worktree copy, so both paths point at worktree code. The spawned chain then
self-locates forward from there: `session_viewer.py:69`
(`_SCRIPTS = Path(__file__).resolve().parent`) → `session_manager_daemon.py:67`
(same). So pointing the **viewer exec line's path** and the **hook scripts dir**
at the installed copy fixes the entire chain (viewer → daemon → hooks) **by
construction** — the viewer/daemon then self-locate from the installed copy.

## 2. The fix (Form)

Introduce one named resolver in `_terminal_launcher.py`:

```python
def _resolve_installed_scripts_dir() -> Path:
    """Scripts dir to bake into the spawned launch script (viewer exec + hooks).

    Resolution order:
      1. SULIS_SPAWN_SCRIPTS_DIR (dev escape hatch) — when set AND an existing
         dir, return it resolved.
      2. Newest cached install — default_cache_root()/sulis-ai-agents/sulis/
         <max_version>/scripts, when that dir exists (numeric version pick via
         _version_pick — never lexical, #49-safe).
      3. Fallback — Path(__file__).resolve().parent (today's behaviour), so a
         pure-dev machine with no install still spawns successfully.
    """
```

Both call sites (303, 350) call this resolver instead of
`Path(__file__).resolve().parent`. **The two `__file__.parent` sites collapse to
one named resolver** (EP-07 boy-scout). Every resolved path stays `shlex.quote`-d
into the launch script **exactly as today** — the resolver only changes *which*
path is quoted, not the quoting (AC-6 preserved by construction).

Composition (EP-03 — reuse, do not rebuild; all stdlib-only leaf modules, NFR-5):
- `_prune_cache.default_cache_root()` → `~/.claude/plugins/cache`;
  `_prune_cache._SULIS_SUBPATH` = `("sulis-ai-agents", "sulis")` for the cache root.
- `_version_pick.max_version(names)` → numeric newest-version pick over the
  cached version-dir names.

The launcher already does `sys.path.insert(0, str(Path(__file__).parent))` and
imports sibling leaf modules (`_change_session`, `_wpxlib`); the resolver imports
`_prune_cache` and `_version_pick` the same way. No new dependency, no non-stdlib
import (NFR-5 held).

## 3. Operational shape (Armor)

This is build machinery, not a network/service path — the Armor surface is
narrow and already satisfied:

- **Injection safety preserved (AC-6).** The resolved path continues through the
  existing `shlex.quote(str(scripts_dir))` / `shlex.quote(str(viewer))` /
  `shlex.quote(str(hooks_dir))` sites. The resolver returns a `Path`; quoting is
  unchanged. A cache/override path containing shell metacharacters is inert for
  the same reason a worktree path is today.
- **Graceful degradation (AC-5).** No install + no override must **never** crash
  or emit an empty path — the resolver falls back to `__file__.parent`. This is
  the offline/pure-dev guardrail (mirrors the degrade-gracefully convention used
  elsewhere in the change machinery, e.g. `sulis-change start`'s no-remote
  fallback).
- **Override validation.** `SULIS_SPAWN_SCRIPTS_DIR` is honoured **only when it
  points at an existing directory**; an unset or stale/invalid value falls
  through to the cache pick (it does not hard-fail the spawn). A set-but-missing
  override dir is treated as "no usable override" → cache pick, then fallback.

## 4. Verification shape (Proof)

All ACs are unit-testable against the **pure** `_build_launch_script` /
`_build_viewer_exec_line` and the resolver with a **fake cache under `tmp_path`**
— the launcher is already structured for this (`_build_launch_script` returns the
script string; `_build_viewer_exec_line` returns the exec line). This is the
green-but-broken guard: assert the **resolved path that appears in the emitted
script**, not merely that the function ran.

Extend the existing suites (Constraint — do not fork a new suite):
- `plugins/sulis/scripts/tests/unit/test_terminal_launcher_runs_viewer.py`
  (exec-line + scripts-dir assertions already live here).
- `plugins/sulis/scripts/tests/unit/test_terminal_launcher.py`
  (origin-hook export assertions already live here).

Characterise current behaviour first (EP-07): a test pinning that, on a
fully-installed single-version machine, the **explicitly-resolved** path **equals
the install** (Constraint — no behavioural change other than explicit resolution;
on such a machine the two coincide).

## 5. Design decisions (recorded)

### DD-1 — Escape-hatch env var: `SULIS_SPAWN_SCRIPTS_DIR` (NOT `SULIS_SCRIPTS_DIR`)

**Decision:** the dev-escape override is a **new** env var `SULIS_SPAWN_SCRIPTS_DIR`.

**Why:** `SULIS_SCRIPTS_DIR` is already an **output** of this launcher — line 352
`export SULIS_SCRIPTS_DIR=<scripts>` is written into the spawned launch script so
the origin-hook can locate `_origin_stamp`. Reusing the same name as an **input**
to the resolver would be ambiguous (one name, two roles: "where the hook finds
scripts" vs "where the resolver is told to look") and would risk an inherited
output value silently steering a later resolution. A distinct, intention-named
var (`SPAWN` = "what scripts dir to bake into the spawn") is unambiguous and
greppable. Rejected: reusing `SULIS_SCRIPTS_DIR` (ambiguous dual-role, latent
inherited-value foot-gun).

**Status:** accepted.

### DD-2 — Resolution order: override → cache → `__file__.parent`

**Decision:** explicit override first, newest cached install second, launcher's
own dir last.

**Why:** the override is the deliberate dev-testing escape hatch — when a
developer is *intentionally* exercising launcher/viewer/daemon changes from a
worktree, their explicit choice must win over the cache. The cache pick is the
**normal dogfooding answer** (a change started from a worktree should run the
installed plugin, not the worktree). `__file__.parent` is the **honest
last-resort** for a pure-dev machine with no install — there is no "installed
plugin" to prefer, so the launcher's own tree is the correct fallback rather than
a crash. Rejected: cache-first (would override a developer's explicit
intent-to-test); `__file__`-first (re-introduces the bug).

**Status:** accepted.

### DD-3 — Do NOT touch viewer/daemon self-location (scope boundary)

**Decision:** leave `session_viewer.py:69` and `session_manager_daemon.py:67`
(`Path(__file__).resolve().parent`) **unchanged**.

**Why:** pointing the exec'd viewer's path at the installed copy is **sufficient**
— the viewer and daemon then self-locate from the installed copy by construction.
Changing their internal resolution is explicitly out of scope per the spec
non-goals and would widen blast radius for no benefit. The fix is confined to the
launcher's two call sites.

**Status:** accepted (spec non-goal, restated here for the executor).

### DD-4 — One WP, not two

**Decision:** ship as a single WP.

**Why:** the resolver and the two call-site redirects are one atomic change — the
call-site redirect cannot land without the resolver, and the characterisation
test gates both. Splitting would create a WP that compiles but changes nothing
(resolver added, unused) and a second that depends entirely on it — bundling
nothing is satisfied by keeping the indivisible unit together. Touch surface is 3
path entries (1 script + 2 test files), well under the ≤15 MUST.

**Status:** accepted.

## 6. Out of scope (spec non-goals, restated)

- **What** the window runs (viewer-attached-to-shared-session model, CH-01KTKB
  ADR-003) — unchanged; only **which copy**.
- Viewer/daemon internal self-location (DD-3).
- Version-skew daemon-restart guard (#102); env-scrub preamble; pre-prompt
  sidecar delivery; `SULIS_CHANGE_ID` binding hardening (#107) — all unchanged.

## 7. NFRs surfaced

- **NFR-5 (stdlib-only) held.** Resolver composes existing stdlib-only leaf
  helpers (`_prune_cache`, `_version_pick`) + stdlib `os`/`pathlib` only.
- **NFR (no behavioural change on a fully-installed single-version machine)
  held by construction** and pinned by the characterisation test: explicit path
  == install on that machine.
