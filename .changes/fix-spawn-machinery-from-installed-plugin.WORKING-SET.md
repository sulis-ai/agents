# Working Set — fix-spawn-machinery-from-installed-plugin

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
Spawned change sessions run viewer/daemon/hooks from the spawning change's worktree code instead of the installed plugin; make spawned machinery always run from the installed plugin.

## 2. Current best solution  (→ Design)
Root cause located: `_terminal_launcher.py` resolves `scripts_dir = Path(__file__).resolve().parent`
in TWO places (line 303 = viewer exec line; line 350 = origin-hook GIT hooksPath +
SULIS_SCRIPTS_DIR). When `sulis-change start` runs from a change worktree, `__file__` IS
the worktree copy, so the spawned window execs `<worktree>/session_viewer.py`; the viewer
then resolves its own daemon binding from its own `__file__.parent` (session_viewer.py:69
`_SCRIPTS = Path(__file__).resolve().parent`) and the daemon likewise (session_manager_daemon.py:67).
So pointing the viewer's PATH at the installed copy makes the whole chain (viewer → daemon →
hooks) run from installed.

Leading fix: add a resolver that returns the INSTALLED plugin scripts dir (cache pick) and
use it for the spawned exec line + hooks dir, instead of `__file__.parent`.
Reusable primitives already exist (Non-Negotiable #2 — extend, don't rebuild):
  - `_prune_cache.default_cache_root()` → ~/.claude/plugins/cache; `_SULIS_SUBPATH`.
  - `_version_pick.max_version()` → numeric SemVer pick (avoids the lexical-sort bug #49).
  - `_plugin_version.plugin_version()` → version from plugin.json.

## 3. Decisions  (→ Decision; status: ACCEPTED at design stage)
- **DD-1 — env var `SULIS_SPAWN_SCRIPTS_DIR` (NOT `SULIS_SCRIPTS_DIR`).** `SULIS_SCRIPTS_DIR`
  is already a launcher OUTPUT (line 352 export for the origin-hook); reusing it as a resolver
  INPUT is ambiguous (one name, two roles) + an inherited-value foot-gun. New intention-named
  var is unambiguous + greppable. ACCEPTED.
- **DD-2 — resolution order: override → newest cache install → `__file__.parent`.** Override is
  the deliberate dev escape hatch (wins over cache when intentionally testing worktree code);
  cache is the normal dogfooding answer; `__file__.parent` is the honest last-resort for a
  pure-dev machine with no install. ACCEPTED.
- **DD-3 — do NOT touch viewer/daemon self-location** (`session_viewer.py:69`,
  `session_manager_daemon.py:67`). Pointing the exec'd viewer's path at the install is
  sufficient — chain self-locates from install by construction. Spec non-goal. ACCEPTED.
- **DD-4 — one WP, not two.** Resolver + the two call-site redirects are atomic (redirect can't
  land without resolver; char-test gates both). Splitting manufactures a dependency edge for an
  indivisible change. ACCEPTED.

## 4. Open questions / unknowns  (all resolved at design stage)
- ~~Resolution order + dev escape hatch~~ → DD-1/DD-2.
- ~~Pure-dev machine with NO cache install~~ → graceful `__file__.parent` fallback (AC-5),
  pinned by `test_resolver_falls_back_to_module_dir_with_no_install_no_override`.
- ~~Same `__file__.parent` forking elsewhere in the spawn chain?~~ → Yes, in
  `session_viewer.py:69` / `session_manager_daemon.py:67`, but that is the *forward*
  self-location the fix LEVERAGES (not fixes): pointing the launcher's exec line at the install
  makes the chain self-locate from the install. Touching it is a spec non-goal (DD-3). No other
  launcher-path forking found.

## 5. Rejected so far  (→ Decision.rejected_alternatives)
- **Reuse `SULIS_SCRIPTS_DIR` as the override input** — ambiguous dual-role (already an output),
  latent inherited-value foot-gun (DD-1).
- **Cache-first resolution order** — would override a developer's explicit intent-to-test-from-
  worktree (DD-2).
- **`__file__`-first resolution order** — re-introduces the bug (DD-2).
- **Lexical / `sort -V` version pick** — lexical ranks `0.98.0` above `0.126.0` (#49); use
  `_version_pick.max_version` numeric pick (AC-3).
- **Split into resolver-WP + redirect-WP** — non-atomic; resolver-WP unused on its own (DD-4).
- **Editing viewer/daemon internal self-location** — out of scope, wider blast radius for no
  benefit (DD-3).

## 6. Working log  (append-only)
- 2026-06-13T16:18:57Z — Working Set created.
- 2026-06-13T16:25:29Z — Corrected a stale change binding inherited from a previous session (env var pointed at 01KV0JP9...).
- 2026-06-13T16:27:35Z — Recon done: root cause = _terminal_launcher.py scripts_dir=__file__.parent (lines 303,350); chain viewer->daemon->hooks inherits worktree path. Reusable cache-resolver primitives exist.
- 2026-06-13T16:29:21Z — Spec written (standard depth, not founder-facing): resolve installed-plugin scripts dir (cache pick via _prune_cache+_version_pick) for viewer exec line + origin-hook; env override escape hatch; graceful __file__ fallback on no-install. 6 ACs, all unit-testable on the pure _build_launch_script.
- 2026-06-13T16:36:15Z — Design+decompose done. Resolver _resolve_installed_scripts_dir() (override SULIS_SPAWN_SCRIPTS_DIR -> newest cache install via _prune_cache+_version_pick -> __file__.parent fallback) replaces both __file__.parent sites (303 viewer, 350 hook). DECIDED: DD-1 new env var SULIS_SPAWN_SCRIPTS_DIR not SULIS_SCRIPTS_DIR (latter is already a launcher OUTPUT; reuse=ambiguous); DD-2 order override>cache>fallback; DD-3 do NOT touch viewer/daemon self-location (spec non-goal); DD-4 one WP not two (resolver+redirects atomic, char-test gates both). Artifacts: .architecture/fix-spawn-machinery-from-installed-plugin/{DESIGN.md,work-packages/{INDEX.md,WP-001,DECOMPOSE_VALIDATION.md}}. INDEX lint PASS (canonical header). Decompose rubric PASS.
