---
founder_facing: false
---
# Spec — Embed the safe tools into the agent's governed action-surface

**Change:** CH-522P6P · harden · grounded in spirals 01KW3BZNS… → 01KTZRTN0… → 01KTZTCSP2… → 01KV0G2GCK… → 01KV0KGGQQ…; decisions D1–D8 in the Working Set.

## Intent

Make the shipped L1 (safe-fetch) + L2 (scoped file-tools) **actually used and enforced**, via the harness, not prose. The model: a **CLI-majority action-surface + one governance hook + a small typed-MCP carve-out** (NOT a CLI→MCP migration). Every embedded rule is labelled by its **enforcement-locus** (model / harness / OS) and **threat-scope** (accidental-closed-now / adversarial-deferred), so nothing claims more safety than its locus delivers.

## Scope (phased; each item cites its locus)

**Phase 1 — the safe path exists + is ergonomic (locus ii, identity):**
1. A **Python stdio MCP server** (NOT npx) shipping with the plugin (`scripts/` + registered in `plugins/sulis/.mcp.json` via a `command` on the plugin's Python env), exposing: `safe_fetch(url, format)`, `safe_search(query)`, and the four scoped file ops — collapsed to avoid name-collision (one `scoped_file(op, …)` or four clearly-distinct tools; decide at design, default to the fewest that read clearly). Wraps the existing `_safe_fetch` + `_file_tools` libraries (no logic reimplementation).
2. Narrow the agent's `tools: "*"` to an explicit allowlist that includes the safe MCP tools.

**Phase 2 — the unsafe path is blocked (locus ii, governance):**
3. A **PreToolUse hook**: on `Write`/`Edit`/`Bash`, read `tool_input.file_path`/`command`, run the **write-roots resolver** (below) / `within_change_scope`, `deny` out-of-scope (hard-block, overrides allow). Allow the `Bash(sulis-*:*)`/`Bash(wpx-*:*)` CLI family; flat-`deny` raw `Bash(curl:*)`/`Bash(wget:*)`.
4. **Permission deny-rules**: deny `WebFetch` + raw network tools; allow the safe MCP tools.

**Phase 3 — the write-roots resolver (locus ii, single source of truth):**
5. One resolver computing the allowed write-roots, read by BOTH the file-tools scope check AND the sandbox config (no drift): change-scoped (`{worktree}`, `~/.sulis/changes/{THIS_ID}/`) + shared (the **resolved** brain dir via `brain_base_dir`; default in-worktree → no extra root) + runtime (daemon socket/log) + read-only (plugin cache, git-common-dir). Narrowest-root; canonical (`/private/…`) paths; never all of `~/.sulis/`; extra routes are reviewed config additions.

**Phase 4 — the OS backstop (locus iii):**
6. Document + provide the **sandbox-enable recipe** (`sandbox.enabled`, `allowedDomains` = the proxy egress host only, `denyRead` creds; consumer-managed `failIfUnavailable`/`allowUnsandboxedCommands:false`). This is the only layer that catches subprocess bypass.

**Phase 5 — graduate the criterion + the quality nudge:**
7. Write the **governed-action-surface standard** (the 2-axis criterion from D8 — substrate × governance; MCP iff typed-contract OR trust-boundary-identity AND no selection-bloat; default CLI; governance is a free-standing hook layer; honesty-labelling rule).
8. Prose (locus i) ONLY for quality — "prefer safe-fetch for clean/low-token output" in agent defs/skills.

## Non-goals

- **NOT a CLI→MCP migration.** ~55 `sulis-*`/`wpx-*` stay CLIs (incl. `gh`/`git push`). No 1:1 MCP-ification of the 21 `emit-*` (name-collision; if ever, one parameterised tool).
- **No claim that MCP-identity = enforcement.** It makes the safe path available + denyable; the sandbox is the adversarial backstop.
- **GAP-β deferred** — the TLS-aware safe-fetch-only egress proxy (deliberate exfil via a permitted broad domain). Out of scope; roadmap.
- No bespoke OS-sandbox build (Claude Code's ships); we enable + configure it.

## Acceptance / Verification Plan (scenarios — verifiable-now vs deferred-to-L3)

**Verifiable now:**
- **SC-E1 — safe tools are distinct MCP identities.** After load, `safe_fetch`/`safe_search` + the scoped-file tool(s) appear as callable MCP tools (observable in the tool list). *Test:* MCP server starts; tools enumerate.
- **SC-E2 — WebFetch is denied.** A permission deny-rule on `WebFetch` hard-blocks a `WebFetch` call. *Test:* automated against the permission config.
- **SC-E3 — the hook refuses an out-of-scope write.** The PreToolUse hook returns `deny` for a `Write`/`Edit` whose `file_path` resolves outside the write-roots (incl. the canonical `/tmp`→`/private/tmp` case + a sibling change's dir); ALLOWS an in-scope write. *Test:* automated hook-invocation.
- **SC-E4 — the hook governs the Bash CLI family.** Allows `Bash(sulis-emit-* …)`/`Bash(wpx-* …)`; flat-denies `Bash(curl …)`/`Bash(wget …)`; decomposes compound commands (`a && curl …`) and denies on the raw sub-command. *Test:* automated.
- **SC-E5 — write-roots resolver: one source, narrowest-root.** A write to the *resolved* brain dir (relocated-brain case) is allowed; a write to `~/.sulis/changes/{OTHER}/` is refused; the resolver output the file-tools use == the set the sandbox recipe consumes. *Test:* automated.
- **SC-E6 — honesty labels present.** The standard + each rule carries its enforcement-locus + threat-scope; a doc/test asserts no rule claims a locus it doesn't hold.

**Deferred-to-L3 / consumer-config (cannot be verified now — labelled, not faked):**
- **SC-E7 (deferred) — subprocess bypass.** A raw subprocess (`python -c 'urllib…'` / obfuscated curl) bypasses the hook — asserted to SUCCEED without the sandbox, naming the OS sandbox (locus iii) as the owner. With the sandbox enabled, blocked. *Test:* the bypass-succeeds half automated now; the sandbox-blocks half is a sandbox-enabled run (human-attested / CI-where-available).
- **SC-E8 (deferred) — real session inside the sandbox.** A real `claude --agent sulis` session completes a trivial change end-to-end inside the enabled sandbox with the resolver-computed allowlist (nothing legit blocked). *Test:* driven/attested.
- **SC-E9 (deferred) — operator-proof.** Unbypassable-by-operator needs consumer-applied managed settings; Sulis ships defaults + recipe only. Documented, not claimed.

## Constraints

- Python stdio MCP (uv/plugin env), not npx. Wrap existing libraries; no logic reimplementation.
- One write-roots resolver feeds L2 + L3 (no drift); canonical paths; narrowest-root.
- Distribution: MCP via plugin `.mcp.json`, hook via plugin `hooks/`, CLIs via `scripts/` — all version with the plugin. Note (A2): downstream consumers who don't load the plugin hook get only the MCP-identity half of governance.
- Test-first; `uv run pytest`; CP-01..05; the governed-action-surface standard is the durable home of the D8 criterion.

## Open before/within build
- **Q6 (cost):** measure the per-Bash-call screening-tax on hot-path CLIs; if large, a high-frequency CLI may earn MCP on cost grounds (the one cost-driven exception).
- MCP tool shape for the file ops (one parameterised vs four) — decide at design to avoid name-collision while staying readable.
