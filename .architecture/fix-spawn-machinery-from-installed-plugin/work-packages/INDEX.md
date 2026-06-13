# Work Packages — fix-spawn-machinery-from-installed-plugin (CH-3FNT33)

> Change: `01KV0WE0CH3FNT3361WGPB2HBZ` · primitive: `fix` · branch:
> `change/fix-spawn-machinery-from-installed-plugin`. Design:
> [`../DESIGN.md`](../DESIGN.md). Spec:
> `.changes/fix-spawn-machinery-from-installed-plugin.SPEC.md`.

## Status

| ID | Title | Primitive | Status | Depends On | Blocks |
|----|-------|-----------|--------|------------|--------|
| WP-001 | Resolve the installed-plugin scripts dir for the spawned viewer exec line + origin hook | fix | done | — | — |

## Detail (extra columns — second table, non-canonical by design)

> The canonical table above is the one the run-all tooling parses (#60/#335).
> This second table carries the extra context without drifting the header.

| ID | Group | Verification artifact | Token est. |
|----|-------|-----------------------|------------|
| WP-001 | REINFORCE (+ REORGANISE-Refactor) | `test_terminal_launcher_runs_viewer.py` + `test_terminal_launcher.py` unit nodeids (see WP §Verification Plan) | ~15k |

## Build order

Single WP — no waves, no dependency graph. Build → verify (full launcher unit
suite green) → integrate.

```
WP-001  resolver + 2 call-site redirects (atomic; characterisation-test-gated)
        ── verify: pytest test_terminal_launcher.py test_terminal_launcher_runs_viewer.py ──
        ✅ change ready to verify
```

## Acceptance trace (SPEC AC → WP test)

| SPEC AC | Covered by (WP-001 test) |
|---|---|
| AC-1 — viewer runs from install | `test_viewer_exec_line_targets_installed_cache_scripts` |
| AC-2 — hooks run from install | `test_origin_hook_targets_installed_cache_scripts` |
| AC-3 — newest install wins (numeric) | `test_resolver_picks_numerically_newest_cached_install` |
| AC-4 — override wins | `test_resolver_honours_spawn_scripts_dir_override` |
| AC-5 — graceful fallback | `test_resolver_falls_back_to_module_dir_with_no_install_no_override` |
| AC-6 — security (shlex.quote) preserved | `test_resolved_path_still_shlex_quoted_in_script` |
| Constraint — no behavioural change on a single-version install | `test_explicit_scripts_dir_equals_install_on_single_version_machine` (characterisation) |
