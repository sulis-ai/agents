---
founder_facing: false
---

# Spec — Antigravity (`agy`) provider adapter

**Change:** CH-M7WSQ4 · create · builds on CH-GJ9KQR (portable agent context)

> Grounds on the recon (`.changes/create-antigravity-agy-adapter.RECON.md`): the
> `ProviderAdapter` seam + the real `agy` CLI (v1.0.11, verified by running the
> installed binary). Phase 1 of the Claude↔agy failover capability; Phase 2 (the
> automatic failover trigger) is a separate, deferred change.

## Intent

Add an `agy` (Google Antigravity CLI) provider adapter so Sulis can run an agent
session on Antigravity — seeded by the **portable, Sulis-owned context** shipped
in CH-GJ9KQR — instead of being able to run only on Claude. This makes
Antigravity a real, selectable execution target and lays the foundation for
automatic provider failover (deferred to Phase 2).

## Scope

1. **A new interactive `agy` PTY adapter** (`plugins/sulis/scripts/_session_manager/adapters/agy_pty.py`),
   mirroring `InteractiveClaudePtyAdapter`: `_BASE_ARGV = ("agy", "--prompt-interactive")`,
   `spawn_argv` appends the portable-context brief as the opening prompt and adds
   `--add-dir <cwd>` (and an optional `--model`); `encode`/`decode` unused on the
   interactive-pty path (the manager reads raw terminal bytes into scrollback,
   exactly as the Claude pty path).
2. **Resume support.** `Capabilities(supports_resume=True)`; the `SessionSpec`
   resume handle maps to agy's `--conversation <id>` (or `--continue` for the most
   recent), verified present in `agy --help`.
3. **Provider registration.** Register the adapter under a provider key (`"agy"`,
   alias `"antigravity"`) so the session manager can select it — additive to the
   existing Claude registration.
4. **Context seeding via the existing brief seam.** The CH-GJ9KQR portable-context
   brief (`~/.sulis/changes/{id}/pre_prompt.txt`) feeds the `agy` session
   **unchanged** — delivered as `agy`'s opening interactive prompt. No
   provider-specific context plumbing.

## Non-goals

- **The automatic failover trigger/policy** (switch Claude→agy on a
  connectivity/auth/rate-limit/outage signal, carrying context across) — that is
  **Phase 2**, a separate change. This change only makes agy a selectable target.
- **Running "the Sulis agent" / the plugin + MCP stack on agy.** `agy` has no
  `--agent` equivalent (it has its own `plugin` subcommand); the agent is seeded
  by our portable-context brief as the prompt, not by a Claude-specific agent
  plugin. This is by design (the CH-GJ9KQR provider-agnostic model).
- **Changing or risking the Claude path.** The adapter is purely additive; the
  Claude pty adapter and every existing session behaviour stay byte-for-byte
  unchanged.
- **The non-interactive `--print`/`-p` headless mode.** The interactive-pty mode
  is how Sulis runs an agent session; `--print` is a possible later mode, out of
  scope here.

## Acceptance

Observable, provider-independent behaviour:

- Sulis can **open an interactive agent session through the `agy` adapter**, and
  the agent receives the portable-context brief as its opening prompt (the same
  brief that seeds a Claude session).
- **Resume works:** a session opened via the adapter can be continued (mapped to
  `agy --conversation <id>` / `--continue`), and `capabilities.supports_resume`
  is `True`.
- The adapter **conforms to the `ProviderAdapter` Protocol** (`spawn_argv`,
  `encode`, `decode`, `capabilities`) and is selectable by provider key `"agy"`.
- The **Claude path is unaffected** — all existing session-manager tests stay
  green; no change to the Claude adapter or the shared seam.

## Constraints

- **Reuse, don't rebuild.** Mirror `adapters/claude_pty.py` and reuse the seam +
  the CH-GJ9KQR brief/`pre_prompt` injection. This is ~one new adapter file plus a
  registration, not new architecture.
- **Third-party platform touch (Platform Contract required at design).** `agy` is
  Google Antigravity's CLI (v1.0.11). The design pass MUST ground a Platform
  Contract against `agy`'s **real** behaviour — the flags verified at recon
  (`--prompt-interactive`, `--print`, `--continue`/`--conversation`, `--model`,
  `--add-dir`, `--sandbox`, `--dangerously-skip-permissions`, `--print-timeout`),
  auth = Google Sign-In. This is a write/exec touch → hard-gated at design.
- **`agy` must be pre-authenticated.** Agent-CLI auth does not transfer at the
  moment of an outage; the fallback is only viable if signed in ahead of time
  (the founder has installed + signed into `agy`).
- **Permission posture.** Do not blanket `--dangerously-skip-permissions`; respect
  the same guardrail posture the Claude session runs under (decide the exact
  flag set at design, grounded in the Platform Contract).

## Verification Plan

How we'll know it works — driven against the **real** `agy` binary (it's installed):

- **Adapter conformance:** the adapter implements the `ProviderAdapter` Protocol;
  `spawn_argv` produces the expected `agy --prompt-interactive <brief> --add-dir
  <cwd>` shape with the portable-context brief as the prompt (unit test).
- **Context seeding (driven):** open a session via the agy adapter and **observe**
  the portable-context brief arrives as agy's opening prompt (the brief-argv seam,
  the same check used for the Claude path).
- **Resume (driven):** a session continued via `--conversation`/`--continue`
  resumes the prior agy conversation; `supports_resume` honoured.
- **Claude path intact:** the full session-manager + adapter test suite stays
  green (no regression to the Claude path or the shared seam).

**Third-party platform touch:** YES — Google Antigravity (`agy`). A Platform
Contract grounded against the installed `agy` v1.0.11 is required at design time.

## Open questions for the design pass

- Exact `spawn_argv` flag set (model default; whether `--add-dir <cwd>` is the
  right workspace mechanism; the permission/sandbox flags) — grounded in the
  Platform Contract.
- How the `SessionSpec` resume handle maps to `--conversation <id>` vs
  `--continue` (id-based vs most-recent), and where agy stores its conversation id.
- Whether the interactive-pty `decode` truly stays unused (raw terminal view) for
  agy as it does for Claude, or whether any agy startup banner needs handling.
