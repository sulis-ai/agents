# Work Packages — feat: remote-control-spawned-sessions (CH-HK5D5M)

> Sourced from `.changes/feat-remote-control-spawned-sessions.SPEC.md`
> (engineering-architect-light — no TDD by design; one load-bearing seam).
> Doctrine: `WORK_PACKAGE_STANDARD` + `WP_BACKEND_STANDARD`.

## Dependency Graph

```
WP-001 (remote-control default-on in PTY spawn argv)   [single atomic WP — no deps]
```

## Ready first (no unmet deps)

- **WP-001** — fully independent; start immediately.

## Orchestrator Config
max_parallel: 1

## Order

> Canonical header (`| ID | Title | Primitive | Status | Depends On | Blocks |`).
> `kind:` is carried in the WP file's frontmatter (backend), not as an INDEX
> column.

| ID | Title | Primitive | Status | Depends On | Blocks |
|----|-------|-----------|--------|------------|--------|
| WP-001 | Remote Control on by default in the interactive PTY spawn argv | expand-create | done | — | — |

## Notes

- **One atomic WP.** A single load-bearing seam (`claude_pty.py` `spawn_argv()`),
  one new env-knob constant mirroring `SULIS_TERMINAL_OS_WINDOW` (inverted to
  default-ON), one new test module. Fits one branch, one engineer, one commit —
  no split warranted (WP-02 one-branch / one-engineer tests both pass).
- **EXPAND-Create, not Wrap.** Widens the argv the adapter we own shapes for the
  CLI it calls (§2.4 Stripe-rule discriminator). No wrapper over internal code.
- **Non-goal pinned by a regression test.** The headless chat adapter
  (`claude.py`, `-p`/stream-json) must never carry `--remote-control`; WP-001's
  Red item (d) guards it.
- **Live round-trip is observed-done, once, on the founder machine** — CI stubs
  the real interactive `claude` (the WP-009 `--verbose` lesson), so "Remote
  Control actually on" is provable only against the real binary; the pure
  `spawn_argv` argv-shape assertions stand in for it in CI.
