---
founder_facing: false
---
# Spec — Remote control on by default for spawned change sessions

**Change:** CH-HK5D5M · feat

## Intent

When a change session is spawned, the interactive `claude` process should start
with Claude Code's Remote Control feature already enabled, so the founder never
has to turn it on by hand each time. Remote Control lets the founder drive /
observe a running session from elsewhere (e.g. the Claude apps); today it is
off by default and must be enabled manually in every freshly-spawned session.

## Scope

- Add the `--remote-control` flag to the **interactive** spawned-session argv
  so Remote Control is on from the first turn.
- The single load-bearing target is the interactive PTY adapter that the
  session-manager daemon uses to spawn the real interactive `claude` the
  founder attaches to:
  `plugins/sulis/scripts/_session_manager/adapters/claude_pty.py` →
  `spawn_argv()`.
- Name the Remote Control session after the change so it's identifiable in the
  founder's Remote Control list (pass the change handle/slug as the optional
  `--remote-control <name>` argument), when a change is bound to the spec.
- Provide an env-var escape hatch (default ON) so Remote Control can be
  disabled for a spawn without a code change — matching the codebase's existing
  override-knob convention (e.g. the OS-window flag, the fake-claude argv seam).
  Working name: `SULIS_SESSION_REMOTE_CONTROL` (truthy default; set to a falsey
  value to opt out). Exact name finalised at design.

## Non-goals

- **Do NOT add the flag to the headless chat adapter**
  (`_session_manager/adapters/claude.py`, the `-p` / stream-json `_BASE_ARGV`).
  Remote Control is an *interactive*-session feature (per `claude --help` on
  v2.1.177: "Start an interactive session with Remote Control enabled"); the
  headless print-mode adapter is not interactive and must not carry it.
- No change to how the founder enables Remote Control in a non-spawned,
  hand-started session — that's outside this work.
- No new UI or cockpit surface for toggling Remote Control; the env-var escape
  hatch is the only control added.

## Acceptance

- A spawned interactive change session comes up with Remote Control already
  enabled — the founder does not enable it by hand.
- The spawned `claude` argv built by the interactive PTY adapter contains
  `--remote-control` (and, when a change is bound, the change-named argument)
  by default.
- Setting the opt-out env var to a falsey value produces an argv with NO
  `--remote-control` flag.
- The headless chat adapter's argv is unchanged — it never carries
  `--remote-control`.
- A unit test pins each of the above against `spawn_argv()` (the argv is built
  by a pure, testable function — no real `claude` spawn needed).

## Constraints

- Follow the existing adapter test-seam pattern: argv is shaped by `spawn_argv`
  and asserted directly in unit tests; do not require spawning the real binary.
- Honour the established override-knob convention for the opt-out (env var,
  default-on), per the convention-preference default.
- The `--remote-control` name argument must stay within shell-safe characters
  on the terminal-launcher path if that path also gains the flag; the launcher's
  entry-command whitelist is `^[a-z][a-z0-9 \-]+$` and the change handle/slug
  must conform (handles like `CH-HK5D5M` contain an uppercase prefix and would
  need lowercasing or routing through the adapter argv, which is not
  shell-parsed). Design decides the exact naming source so it stays safe.

## Verification Plan

- **How we'll know it's done:** a spawned interactive change session shows
  Remote Control enabled without any manual step, and the opt-out env var
  cleanly removes it.
- **Foundational checks (unit, deterministic):** assert `spawn_argv()` on the
  interactive PTY adapter includes `--remote-control` by default; assert it is
  absent when the opt-out env var is falsey; assert the headless chat adapter's
  argv never includes it. These are pure-function assertions on the argv, the
  same testing posture the existing adapters already use.
- **Observed check (manual, once):** spawn one real change session and confirm
  Remote Control is live from the first turn (the behaviour the unit tests
  stand in for, verified once against the real binary per the observed-done
  discipline).
- **Integration touch:** the Claude Code CLI is the third party here. The flag
  name and its interactive-only applicability were grounded against
  `claude --help` (v2.1.177) during recon; design re-confirms before wiring.
