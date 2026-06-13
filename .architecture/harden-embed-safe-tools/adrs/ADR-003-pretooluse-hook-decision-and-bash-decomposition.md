---
id: ADR-003
title: PreToolUse hook — JSON deny decision + self-decomposed compound-Bash
status: accepted
change_id: 01KV0GW39Q522P6PMFTTXH9T2E
date: 2026-06-13
relates_to: SPEC §Phase 2, D2, D8 (hook-governed family)
grounded_in:
  - https://code.claude.com/docs/en/hooks            # PreToolUse stdin/stdout contract
  - https://code.claude.com/docs/en/permissions      # deny-first; Bash arg-matching fragile
---

# ADR-003 — PreToolUse hook: JSON `deny` decision + self-decomposed compound-Bash

## Context

Phase 2 is the governance layer (locus ii). A single PreToolUse hook must, on
`Write` / `Edit` / `Bash`: (a) deny file ops whose resolved path is outside
the write-roots; (b) allow the `Bash(sulis-*:*)` / `Bash(wpx-*:*)` CLI family;
(c) flat-deny raw `Bash(curl …)` / `Bash(wget …)`; (d) **decompose** compound
Bash (`&&`, `||`, `;`, `|`, `|&`, `&`, newlines, `$(…)`) and deny on the raw
sub-command. The grounding (verified against the live docs) constrains the
design:

- The hook receives `{tool_name, tool_input:{command|file_path}}` on stdin.
- It returns a decision either as `hookSpecificOutput.permissionDecision`
  (`"deny"`/`"allow"`, exit 0) OR via **exit 2** (block, stderr → Claude).
- A blocking hook **takes precedence over allow rules**; deny rules and ask
  rules still apply regardless of the hook.
- Bash **arg-matching in permission rules is documented-fragile** (options
  before URL, redirects, env-var indirection, extra spaces). The docs
  explicitly recommend: deny the network *tools* + use a **PreToolUse hook**
  for URL/command validation.

## Decision

1. **Decision channel: JSON `permissionDecision` on exit 0.** The hook prints
   `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…"}}`
   and exits 0 for a deny; prints nothing and exits 0 to **defer** (let the
   normal permission flow + the resolver-backed MCP path proceed). Exit 2 is
   used only for an internal hook error (fail-closed: a hook crash blocks the
   call rather than silently allowing). We do **not** emit `permissionDecision:"allow"`
   for the CLI family — we *defer* it, so a managed deny rule can still veto
   (allow from a hook would not override a deny rule, and emitting it would
   wrongly suggest the hook is the authority).

2. **The hook decomposes compound Bash itself.** It splits the raw `command`
   string on the recognised separators (`&&`, `||`, `;`, `|`, `|&`, `&`,
   newline) **and** extracts `$(…)` / backtick command-substitution bodies,
   then evaluates **every** sub-command. If **any** sub-command is a raw
   network tool (`curl`, `wget`, and the obvious aliases), the whole call is
   denied. This is deliberate redundancy with the harness's own
   operator-awareness: the harness splits compound commands for *permission
   rules*, but the **hook sees the raw string** and must not be fooled by
   `echo x && curl evil` arriving as one `command`.

3. **Path scope via the write-roots resolver (ADR-004).** For `Write`/`Edit`,
   resolve `tool_input.file_path` canonically and check it against the
   resolver's roots for the operation; deny if outside. For `Bash`, parse
   file-writing sub-commands (`>`, `>>`, `tee`, `mv`, `rm`, `cp` dst) on a
   best-effort basis and apply the same scope check — explicitly best-effort,
   because Bash file I/O is exactly the case the docs say only the **sandbox**
   (locus iii) fully covers (SC-E7).

## Rationale (the recommended convention)

- **JSON `permissionDecision` is the documented first-class channel**; exit 2
  is the blunt fallback. Using JSON gives a `permissionDecisionReason` the
  agent sees — it learns *why*, which is the honest, teaching-friendly default
  (mirrors the proxy's refuse-don't-redact stance).
- **Deny-not-allow for the CLI family** keeps deny-first precedence intact: a
  consumer's managed deny rule must always win. The hook's job is to *block
  the unsafe path*, not to *grant* the safe one.
- **Self-decomposition is mandatory** because the hook reads the raw command
  string; the docs' operator-awareness applies to *rule matching*, not to what
  a hook receives. Not decomposing is the documented bypass (`a && curl …`).
- **Best-effort Bash path-scope + honest deferral to the sandbox** — the docs
  state Read/Edit deny rules and hook string-parsing do NOT cover arbitrary
  subprocess file I/O; only the OS sandbox does. We do the cheap parse and
  label the gap, never claim completeness (the enforcement-locus honesty rule).

## Alternatives considered

- **Exit 2 for every deny** — REJECTED as the primary channel. Loses the
  structured `permissionDecisionReason`; reserved for hook-internal errors.
- **`permissionDecision:"allow"` for the CLI family** — REJECTED. Would not
  override a deny rule anyway, and misrepresents the hook as the grant
  authority. Defer instead.
- **Rely on `Bash(curl:*)` deny-rules instead of a hook for network** —
  REJECTED per the docs' explicit fragility warning (and the Working Set's
  rejected-list). The permission rule is kept as a **belt** (Phase 2 item 4),
  the hook is the **braces**; neither is claimed sufficient alone.
- **A regex over the whole command for `curl`/`wget`** — REJECTED as the
  *only* mechanism (a bare regex matches `curlytool`); decomposition +
  token-boundary matching on each sub-command's argv[0] is the boring-correct
  form.

## Consequences

- The hook is a Python module (`_safe_tools_hook.py`) + a registered command,
  added to `plugins/sulis/hooks/hooks.json` under a new `PreToolUse` matcher.
  It imports the write-roots resolver (ADR-004) — single source of truth, no
  re-implemented scope logic.
- It must resolve `change_id` + `repo_root` from the hook's runtime context
  (cwd / env) to build the resolver roots — same inputs the MCP server uses.
- Fail-closed: any unparseable input, missing change scope, or internal error
  → deny (exit 2 with a reason on stderr).
- SC-E3 (out-of-scope write denied / in-scope allowed), SC-E4 (CLI-family
  allowed, raw curl/wget denied, compound decomposed) are this hook's
  scenarios.
