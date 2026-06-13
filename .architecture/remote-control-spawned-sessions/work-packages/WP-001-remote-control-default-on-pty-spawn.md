---
wp: WP-001
change_id: 01KV0JP9J1HK5D5M27KZZGZAEK
title: Remote Control on by default in the interactive PTY spawn argv
kind: backend
source: feature
primitive: expand-create
group: expand
status: pending
dependsOn: []
estimated_token_cost: { input: ~14k, output: ~6k }
platform: claude-cli
touch-class: read-only
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_pty_remote_control.py
fixtures_created: []
---

# WP-001 — Remote Control on by default in the interactive PTY spawn argv

## Context

Maps to the SPEC's Scope/Acceptance (`.changes/feat-remote-control-spawned-sessions.SPEC.md`).
No TDD — this is an engineering-architect-light change by explicit brief: one
load-bearing seam, the design decisions pre-locked in the spec.

The single load-bearing target is the interactive PTY adapter the
session-manager daemon uses to spawn the **real interactive** `claude` the
founder attaches to:
`plugins/sulis/scripts/_session_manager/adapters/claude_pty.py` → `spawn_argv()`.
Recon confirmed the default change-start spawn path runs through this adapter
(terminal launcher → viewer → daemon → PTY adapter spawns interactive claude).

Claude Code's Remote Control (`claude --remote-control [name]`, verified against
`claude --help`, CLI v2.1.177 — "Start an interactive session with Remote
Control enabled (optionally named)") is **interactive-only**. Today it is off by
default and the founder enables it by hand in every freshly-spawned session.
This WP makes the spawned interactive session come up with Remote Control already
on, named after the change so it's identifiable in the founder's Remote Control
list.

**Non-goal — the headless chat adapter is out of scope.**
`_session_manager/adapters/claude.py` (`_BASE_ARGV`, `-p` / stream-json) is the
non-interactive print-mode io-model; Remote Control does not apply there and the
flag MUST NOT reach it. WP-001 leaves `claude.py` byte-for-byte unchanged; the
regression guard (Red item d) pins this.

**EXPAND-Create, not Wrap.** This widens the argv the adapter we own shapes for
the CLI it calls (the §2.4 Stripe-rule discriminator the adapter's docstring
already records). No new component, no wrapper over internal code — one flag
appended to one pure, testable argv builder, plus one env-knob constant mirroring
the existing `SULIS_TERMINAL_OS_WINDOW` override-knob convention.

## Contract

**Files modified:**

- `plugins/sulis/scripts/_session_manager/adapters/claude_pty.py`
  - Add a module-level env-knob constant + a small private helper, mirroring
    `_terminal_launcher.py`'s `_OS_WINDOW_FLAG` / `_OS_WINDOW_TRUTHY` /
    `_os_window_enabled()` shape but **default-ON** (opt-out) rather than the
    launcher's default-OFF (opt-in):
    ```python
    _REMOTE_CONTROL_FLAG = "SULIS_SESSION_REMOTE_CONTROL"
    _REMOTE_CONTROL_FALSEY = frozenset({"0", "false", "no", "off"})

    def _remote_control_enabled() -> bool:
        """Remote Control is ON by default; set SULIS_SESSION_REMOTE_CONTROL to a
        falsey value (0/false/no/off, case-insensitive) to opt a spawn out."""
        return (
            os.environ.get(_REMOTE_CONTROL_FLAG, "").strip().lower()
            not in _REMOTE_CONTROL_FALSEY
        )
    ```
    (An unset/empty var is NOT in the falsey set → enabled. This is the
    default-ON inversion of the launcher knob; the spec locks default-ON.)
  - Add a private helper that returns the `--remote-control [name]` argv
    fragment: when `spec.brief_change_id` is a valid change ULID, name the
    session after the change (`["--remote-control", <name>]`); otherwise return
    the bare `["--remote-control"]` (CLI auto-names with its hostname prefix).
    Reuse the same `(spec.brief_change_id or "").strip()` + `validate_change_ulid`
    guard pattern `_read_pre_prompt` / `_conversation_flags` already use — do not
    duplicate the validation logic, mirror the established seam.
  - In `spawn_argv()`, append the Remote Control fragment (when
    `_remote_control_enabled()`) to the argv it already builds. Order is not
    load-bearing for the CLI; append after the existing `_conversation_flags`
    and before the positional pre-prompt element, OR after — pick the boring
    placement that keeps the positional pre-prompt last (the pre-prompt is a
    positional arg; flags precede positionals). Keep `import os` (currently the
    module imports `pathlib.Path` only — add `import os`).

**Naming source (design decision, pre-locked by brief item 2).** The
`--remote-control <name>` argument is sourced from `spec.brief_change_id` (the
per-session change ULID the consumer already sets, this change's ADR-001 field on
`SessionSpec`). The PTY adapter's argv is passed **directly** to `Popen` (NO
`shell=True`, §2.12) — so the name is an `execv` literal token, never
shell-parsed; an uppercase/ULID value is safe here (the launcher's
`^[a-z][a-z0-9 \-]+$` entry-command whitelist does NOT apply to the directly-
spawned adapter argv). The handle/slug do not need lowercasing on this path.
When no resolvable change ref is present, fall back to the bare `--remote-control`.

**Files created:** none (the test file below is the only new file).

- `plugins/sulis/scripts/tests/unit/test_pty_remote_control.py` (new test module)

**Contract boundary (unchanged):** the `ProviderAdapter` Protocol signature is
untouched; `spawn_argv(spec) -> list[str]` stays pure (no subprocess, env read
only). Every frozen non-change caller (no `brief_change_id`) still gets a valid
interactive argv — now with bare `--remote-control` by default, removable via the
env knob.

## Definition of Done

### Red

New unit tests in `tests/unit/test_pty_remote_control.py`, following the existing
pure-argv adapter-test style (`test_claude_adapter.py::TestSpawnArgv`,
`test_terminal_launcher.py::test_os_window_*`). Each asserts directly against
`InteractiveClaudePtyAdapter().spawn_argv(spec)` — no real `claude` spawn:

- [ ] **(a) default-on:** with the opt-out env var unset, `--remote-control` is
      present in the argv for a plain spec
      (`SessionSpec(provider="claude", cwd="/w")`).
- [ ] **(b) change-named:** with a valid `brief_change_id` on the spec,
      `--remote-control` is present AND the next argv element is the
      change-derived name (assert
      `argv[argv.index("--remote-control") + 1]` equals the expected name and is
      not another flag). Use a real change-ULID-shaped value so
      `validate_change_ulid` passes.
- [ ] **(b2) bare when no change ref:** with no `brief_change_id` (and no
      `resume_ref`), `--remote-control` is present and is either the last element
      or immediately followed by a flag/positional that is NOT a name — i.e. the
      bare form, no name argument consumed.
- [ ] **(c) opt-out:** parametrised over falsey values (`"0"`, `"false"`,
      `"FALSE"`, `"no"`, `"off"`) via `monkeypatch.setenv`, assert
      `--remote-control` is ABSENT from the argv. Also assert truthy/empty values
      (`""` unset, `"1"`, `"true"`, `"yes"`, `"on"`) keep it PRESENT (mirrors
      `test_os_window_enabled_by_truthy_flag` / `_disabled_by_falsey_flag`).
- [ ] **(d) headless regression guard:** `ClaudeAdapter().spawn_argv(...)` (the
      headless chat adapter) NEVER contains `--remote-control`, with the env var
      unset AND set truthy. Pins the non-goal: the flag must not leak to the
      `-p`/stream-json adapter.

All fail before the implementation (the flag/constant don't exist yet).

### Green

- [ ] Add `import os`, the `_REMOTE_CONTROL_FLAG` / `_REMOTE_CONTROL_FALSEY`
      constants, `_remote_control_enabled()`, and the name-fragment helper to
      `claude_pty.py`.
- [ ] Wire the fragment into `spawn_argv()`. Reuse the existing
      `validate_change_ulid` + `(spec.brief_change_id or "").strip()` guard for
      the name source; do not re-implement ULID validation.
- [ ] Leave `claude.py` (`_BASE_ARGV`, `spawn_argv`) untouched.
- [ ] All Red tests green:
      `pytest plugins/sulis/scripts/tests/unit/test_pty_remote_control.py`.

### Blue

- [ ] Refactor for clarity only — no new behaviour. Confirm the env-knob helper
      and name-fragment helper read as boring mirrors of the launcher's
      `_os_window_enabled` convention; add a one-line docstring on each citing
      the default-ON inversion and the direct-Popen (no-shell) safety of the name
      token.
- [ ] Confirm no duplication of the change-ULID validation (assert via reuse of
      `validate_change_ulid`, the same import the module already carries).
- [ ] `claude_pty.py` docstring updated only if the new behaviour needs a line;
      keep it minimal.
- [ ] Existing adapter suites still green:
      `pytest plugins/sulis/scripts/tests/unit/test_pty_session.py
      plugins/sulis/scripts/tests/unit/test_claude_adapter.py`.

## Sequence

Sequence ID: WP-001

`dependsOn: []` — foundation WP; the change is a single atomic unit.
Blocks: none.

## Estimated Token Cost

input: ~14k / output: ~6k (one source file modified, one small test module
added; all context is local to the two adapter files + their existing test
patterns).

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

The change record's SPEC carries the design-time Verification Plan (variant
matrix + wiring check + observable outcome). This WP concretises it:

- **User-observable behaviour:** a spawned interactive change session shows
  Remote Control enabled from the first turn, named after the change; the opt-out
  env var cleanly removes it. (`founder_facing: false` — internal session
  behaviour; no visual contract, no scenario-coverage gate.)
- **Verification environment:** CI (`pytest`, local + branch-ci). The real
  interactive `claude` cannot run in CI (the WP-009 `--verbose` lesson recorded
  in `claude.py`); CI proves the argv shape against the pure `spawn_argv`.
- **Bootstrap-from-zero:** a fresh clone at the merge SHA runs
  `pytest plugins/sulis/scripts/tests/unit/test_pty_remote_control.py` green with
  no external dependency (pure-function argv assertions).
- **Per-integration verification strategy:** the Claude CLI is the only third
  party. Strategy = **pure-function argv assertion** (Shape 1 concrete) — the
  flag name + interactive-only applicability were grounded against
  `claude --help` v2.1.177 during recon; no real-binary spawn in CI. The live
  "Remote Control is actually on" round-trip is the **observed check (manual,
  once)** per the SPEC's observed-done discipline — deferred to a single real
  spawn on the founder machine, not a CI gate.
- **Per-kind verification adapter:** `kind: backend` → pytest nodeids in
  `tests/unit/test_pty_remote_control.py` (Shape 1 concrete, named in
  `verification:` frontmatter).
- **Infrastructure needs (deferred):** none — no vendor mock, no test account,
  no seed fixture. The manual one-time observed check needs only the founder's
  live machine.

**Platform touch:** `touch-class: read-only` — the only platform is the Claude
CLI we shell out to (read-only/launch, no write/deploy). No Platform Contract
gate (P-PLAT 10.01 fires only on write/deploy).

## Rollback

Revert the single commit. Pure additive code change to one argv builder plus one
new test file; no data migration, no config change, no schema change. Reverting
restores the pre-change argv (no `--remote-control`).
