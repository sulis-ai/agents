# Recon — Antigravity (agy) provider adapter (CH-M7WSQ4)

Goal: add an `agy` (Google Antigravity CLI) ProviderAdapter so Sulis can run an
agent session on Antigravity, seeded by the portable context shipped in
CH-GJ9KQR. Phase 1 of the Claude↔agy failover capability (Phase 2 = the failover
trigger, deferred).

## The seam the adapter must implement (plugins/sulis/scripts/_session_manager/adapter.py)
`ProviderAdapter` Protocol:
- `spawn_argv(spec) -> list[str]` — build the launch argv.
- `encode(command) -> bytes` — frame stdin (raw bytes / unused on the pty path).
- `decode(line) -> Event | None` — stdout → provider-neutral Event (unused on the
  pty path; the manager reads raw terminal bytes into scrollback).
- `capabilities = Capabilities(supports_resume: bool, ...)`.
- optional raw-failure → RecoveryClass mapping (the failover seam — Phase 2).
Template to mirror: `adapters/claude_pty.py` (InteractiveClaudePtyAdapter):
`_BASE_ARGV=("claude", …)`, `capabilities=Capabilities(supports_resume=True)`,
`spawn_argv` appends the pre_prompt brief as the trailing positional prompt;
`decode`/`encode` unused on the interactive-pty path.

## The real agy CLI (verified by running `agy --version`/`--help`; v1.0.11)
- `--prompt-interactive` / `-i` "<prompt>" — run an initial prompt INTERACTIVELY
  and continue the session → the interactive-PTY analog of how Sulis runs Claude.
  This is where our portable-context brief goes (mirrors claude_pty appending the
  pre_prompt). 
- `--print` / `-p` / `--prompt` — single prompt, non-interactive print (the
  headless analog of `claude -p`).
- `--continue` / `-c` — continue most recent conversation; `--conversation <ID>` —
  resume a conversation by id → agy SUPPORTS RESUME. capabilities.supports_resume=True;
  the resume handle maps to `--conversation <id>` / `--continue`.
- `--model`, `--add-dir <cwd>`, `--sandbox`, `--dangerously-skip-permissions`,
  `--print-timeout` (default 5m). Subcommands: models, plugin(s), install, update.
- NO `--agent` equivalent: agy can't load "the sulis agent"/plugin+MCP stack the
  way `claude --agent sulis` does (confirmed — agy has its own `plugin` subcommand,
  not a `--agent` flag). So the agy session is seeded by our portable-context BRIEF
  (the prompt), not a Claude-specific agent plugin — exactly the spec's design.

## Adapter design implication (for specify/design)
A new `adapters/agy_pty.py` `InteractiveAgyPtyAdapter` mirroring claude_pty:
`_BASE_ARGV=("agy","--prompt-interactive")` (+ `--add-dir <cwd>`, optional
`--model`), spawn_argv appends the portable-context brief as the prompt;
`capabilities=Capabilities(supports_resume=True)` with resume via `--conversation`;
decode/encode unused on the pty path. ~One new file, register it under provider
key "agy"/"antigravity". The portable-context brief (CH-GJ9KQR) feeds it unchanged.

## Platform-contract note (third-party platform touch)
agy is a third-party platform (Google Antigravity). Design must ground a Platform
Contract against agy's REAL behaviour (the flags above, verified by running the
installed binary v1.0.11; auth = Google Sign-In, pre-authenticated by the founder).

## Suggested next step
/sulis:specify the agy adapter (Phase 1): the interactive-pty adapter + capabilities
+ provider registration + the brief-as-prompt seeding; resume via --conversation.
