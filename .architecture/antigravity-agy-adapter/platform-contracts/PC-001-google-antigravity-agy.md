---
id: PC-001
platform: Google Antigravity CLI (`agy`)
version-verified: 1.0.11 (recon) — flag surface re-confirmed unchanged on 1.0.12 at design (2026-06-25)
touch-class: write/exec (spawns an autonomous agent process in the worktree)
grounded-by: live binary introspection (READ-ONLY) — `agy --version`, `agy --help`, `agy models`
verified-on: 2026-06-25
auth: Google Sign-In (pre-authenticated; auth does NOT transfer at outage time)
---

# Platform Contract — Google Antigravity `agy` v1.0.11

This contract is grounded against the **real** installed binary, not documentation.
Every flag below was confirmed by running `agy --help` / `agy --version` on the
target machine; `agy models` was run read-only to confirm the binary is live and
authenticated. **No prompt-bearing or state-changing `agy` invocation was run**
(no `--prompt-interactive`, no `--print`, no `--dangerously-skip-permissions`) —
those execute an autonomous agent and are out of bounds for design-time grounding.

## 1. What the platform is

`agy` is Google Antigravity's agent CLI: an interactive coding agent (the
Antigravity analog of `claude`). It spawns an autonomous agent that can read and
write files and run commands inside the working directory. This is a **write/exec
third-party touch** — hard-gated at design (spec constraint), which this contract
discharges.

## 2. Invocation surface (verified flags, v1.0.11)

```
Usage of agy:
  --add-dir                       Add a directory to the workspace (repeatable)
  -c / --continue                 Continue the most recent conversation
  --conversation                  Resume a previous conversation by ID
  --dangerously-skip-permissions  Auto-approve all tool permission requests
  -i / --prompt-interactive       Run an initial prompt interactively and continue
  --log-file                      Override CLI log file path
  --model                         Model for the current CLI session
  -p / --print / --prompt         Run a single prompt non-interactively and print
  --print-timeout                 Timeout for print mode wait (default 5m0s)
  --sandbox                       Run in a sandbox with terminal restrictions
Subcommands: changelog, help, install, models, plugin(s), update
```

Notable absences (confirmed, load-bearing for the design):
- **No `--agent` flag.** Unlike `claude --agent sulis`, agy cannot load the Sulis
  agent/plugin+MCP stack as a launch flag. agy has its own `plugin` subcommand.
  → The agy session is seeded by the **portable-context brief as the opening
  prompt**, exactly the CH-GJ9KQR provider-agnostic model. (Out of scope to load
  a Sulis agent into agy.)
- **No `--remote-control`.** agy has no equivalent of Claude's Remote Control
  feature → that Claude-pty behaviour is **not mirrored** (ADR-002).
- **No `--session-id`.** agy assigns conversation ids itself; there is no flag to
  pin a Sulis-derived id pre-spawn. Resume is by the id agy assigns, via
  `--conversation <id>` (ADR-002).

## 3. Argument-passing form

`agy` accepts both `--flag value` (space-separated) and `--flag=value` forms
(standard Go `flag`/`pflag` parsing — confirmed by the `pflag`-style `-i`/`--prompt-interactive`
short/long aliasing in `--help`). The adapter uses the **space-separated
`--flag value`** form to mirror the Claude adapter's argv shape and the manager's
direct-execv spawn (no shell): each flag and its value are separate argv tokens.
The opening prompt is a **trailing positional** (`--prompt-interactive <prompt>`),
mirroring how the Claude adapter appends the brief as the final positional token.

## 4. The exact `spawn_argv` flag set (DECISION)

Base argv:

```
agy --prompt-interactive [--add-dir <cwd>] [--model <model>] [resume flags] <brief>
```

| Token | Present when | Rationale |
|---|---|---|
| `agy` | always | the binary. |
| `--prompt-interactive` | always | the interactive-pty io-model (mirrors `claude` interactive). The brief is its initial prompt. |
| `--add-dir <cwd>` | always | grants the agent the worktree as workspace. `cwd` is also the process launch dir (the manager `Popen(cwd=…)`), but agy's workspace is set by `--add-dir`, so it is passed explicitly. `cwd` is a non-flag-shaped, validated `SessionSpec` field (already shape-guarded in `__post_init__`). |
| `--model <model>` | only if a model is configured | optional; omitted by default so agy uses its own default model. A `SULIS_AGY_MODEL` env knob (see §6) supplies it when set. |
| `--conversation <id>` **or** `--continue` | resume (see ADR-002 §resume mapping) | resume support. |
| `<brief>` (trailing positional) | iff a valid brief sidecar resolves | the portable-context brief, read from the CH-GJ9KQR sidecar and passed as **one execv token** — never shell-parsed (the no-shell-parse property the Claude path secures). |

## 5. Permission / sandbox posture (DECISION — the Armor gate)

**Do NOT blanket `--dangerously-skip-permissions`.** The spec is explicit: match
the guardrail posture the Claude session runs under, decided here.

Observed Claude-path posture: the Claude pty adapter *does* run
`--dangerously-skip-permissions` (its `_BASE_ARGV`), because a Sulis change
session runs unattended in an isolated git worktree under the launcher's default
entry command — the worktree IS the sandbox boundary.

**Decision for agy (Phase 1): default to agy's `--sandbox` mode; do NOT pass
`--dangerously-skip-permissions`.** Rationale:

1. **agy is a newer, less-exercised integration than the Claude path** — the
   conservative posture is correct until the failover capability (Phase 2) and
   real-session operation give us the evidence the Claude path has.
2. **agy ships a first-class `--sandbox` flag** (terminal restrictions) that the
   Claude CLI does not — using it is the boring, platform-native guardrail, not a
   bespoke one (CP-01).
3. **The auth precondition differs.** agy auth is Google Sign-In, pre-authenticated
   by the founder; an unattended auto-approve posture on a less-proven integration
   is a wider blast radius than the Claude path warrants in Phase 1.

A `SULIS_AGY_SKIP_PERMISSIONS` opt-in env knob (default-OFF / opt-in, mirroring the
launcher's `SULIS_TERMINAL_OS_WINDOW` polarity) lets an operator who has accepted
the risk drop `--sandbox` and pass `--dangerously-skip-permissions` — but the
**default is the guarded posture**. This is the inverse polarity of the Claude
adapter's default-ON Remote Control knob, deliberately: a permission-loosening knob
must be opt-in, never default-on.

## 6. Environment knobs (this adapter)

| Knob | Polarity | Effect |
|---|---|---|
| `SULIS_AGY_MODEL` | value | when set, appends `--model <value>`. Unset → agy default model. |
| `SULIS_AGY_SKIP_PERMISSIONS` | default-OFF / opt-in (truthy turns ON) | when truthy, drops `--sandbox` and adds `--dangerously-skip-permissions`. Default: guarded (`--sandbox`). |

## 7. Resume model

agy resume is conversation-id-based (`--conversation <id>`) or most-recent
(`--continue`). The id is agy-assigned (no pre-spawn pin like Claude's
`--session-id`). The adapter maps `SessionSpec.resume_ref` → `--conversation <ref>`
when set, else (no ref, but a continue is desired) the consumer can pass a sentinel
— Phase 1 maps a set `resume_ref` to `--conversation <ref>` and leaves `--continue`
as the documented most-recent fallback (ADR-002). `capabilities.supports_resume = True`.

## 8. Failure & recovery posture

`classify_failure` returns `None` (defer to the neutral classifier) in Phase 1 —
agy's raw failure/auth-expiry codes are not yet read. Provider-specific detection
(the failover seam) is **Phase 2**, exactly as the Claude pty adapter deferred its
own detection to WP-006. The pty io-model surfaces failures as raw terminal output,
not a structured error stream, so there is nothing to mis-detect in Phase 1.

## 9. What is NOT contracted (out of scope)

- The `--print`/`-p` headless mode (`--print-timeout` 5m default) — a possible later
  io-model, not Phase 1.
- The `plugin` subcommand / loading a Sulis agent into agy — by design, agy is
  seeded by the brief, not an agent plugin.
- The automatic Claude→agy failover trigger — Phase 2.

## 10. Re-grounding trigger

This contract is pinned to `agy` v1.0.x. It was grounded against v1.0.11 at recon and
the full flag surface in §2 was **re-confirmed byte-identical on v1.0.12** at design
time (the patch bump changed nothing in the invocation surface). If `agy --version`
reports a different **major/minor** (1.1.x, 2.x), re-run `agy --help` and reconcile
§2/§4/§5 before trusting the adapter in production; a patch bump (1.0.z) does not
require re-grounding on current evidence but the integration introspection test
(WP-001) guards it automatically.
