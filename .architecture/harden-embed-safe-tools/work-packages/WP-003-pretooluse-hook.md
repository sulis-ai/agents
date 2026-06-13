---
id: WP-003
change_id: 01KV0GW39Q522P6PMFTTXH9T2E
title: PreToolUse hook + permission deny-rules — block the unsafe path (locus ii)
kind: backend
primitive: create
group: expand
status: pending
dependsOn: [WP-002]
blocks: []
scenarios: [SC-E2, SC-E3, SC-E4, SC-E7]
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_safe_tools_hook.py"
token_cost: { input: ~13k, output: ~11k }
---

# WP-003 — PreToolUse hook + permission deny-rules

## Context

TDD §Armor (Layer 2) + ADR-003 (JSON `deny` channel + self-decomposed
compound Bash). The governance layer (locus ii). Depends on WP-002 — imports
the extended resolver for the path-scope check (single source of truth; no
re-implemented scope logic). Grounded in the verified hooks + permissions
docs: stdin `{tool_name, tool_input}`; `permissionDecision:"deny"` on exit 0;
exit 2 = block; a blocking hook overrides allow rules; Bash arg-matching in
rules is fragile (hence the hook).

## Contract

- **New:** `scripts/_safe_tools_hook.py` + a registered command entry.
  Reads stdin JSON. On `tool_name ∈ {Write, Edit, Bash}`:
  - **Write/Edit:** resolve `tool_input.file_path` via the WP-002 resolver;
    `deny` (JSON, exit 0) if outside the write-roots for the op; else defer
    (no output, exit 0).
  - **Bash:** decompose `tool_input.command` on `&&`, `||`, `;`, `|`, `|&`,
    `&`, newline + extract `$(…)`/backtick bodies; for each sub-command:
    - argv[0] ∈ `{curl, wget, …aliases}` → `deny` the whole call.
    - argv[0] matches `sulis-*` / `wpx-*` → allow (defer).
    - best-effort file-write target (`>`,`>>`,`tee`,`mv`,`rm`,`cp` dst) →
      scope-check via the resolver; deny if out-of-scope. **Labelled
      best-effort** (full subprocess I/O is locus iii — SC-E7).
  - **Fail-closed:** unparseable input / no valid change scope / internal
    error → exit 2 with reason on stderr.
- **Modified:** `plugins/sulis/hooks/hooks.json` — add a `PreToolUse` matcher
  for `Write|Edit|Bash` → the hook command.
- **Modified:** the shipped permission config (plugin settings) — `deny`
  `WebFetch`, `Bash(curl:*)`, `Bash(wget:*)`; `allow`
  `mcp__sulis-safe-tools__*`. (Belt to the hook's braces; neither claimed
  sufficient alone.)
- **Modified:** `plugins/sulis/agents/sulis.md` — narrow `tools: "*"` to an
  explicit allowlist incl. `mcp__sulis-safe-tools__*`, excl. `WebFetch`.

## Definition of Done

### Red
- [ ] `test_safe_tools_hook.py::test_out_of_scope_write_denied` — Write to a
      sibling change dir + a `/tmp`→`/private/tmp` case → `deny`; in-scope →
      defer. **SC-E3.**
- [ ] `::test_bash_family_allowed` — `sulis-emit-* …` / `wpx-* …` deferred. **SC-E4.**
- [ ] `::test_raw_network_denied` — `curl …` / `wget …` denied. **SC-E4.**
- [ ] `::test_compound_decomposed` — `echo x && curl evil` denied on the
      `curl` sub-command; `$(curl evil)` denied. **SC-E4.**
- [ ] `::test_fail_closed` — bad stdin / no change scope → exit 2.
- [ ] `test_permission_rules.py::test_webfetch_denied_mcp_allowed` — config
      denies `WebFetch` + raw net, allows `mcp__sulis-safe-tools__*`. **SC-E2.**
- [ ] `test_embed_scenarios.py::test_subprocess_bypass_succeeds_without_sandbox`
      — `python -c 'urllib…'` reaches out, the hook never sees it → **asserts
      success**, names the OS sandbox (locus iii) as the owner. **SC-E7
      testable half — no false green.**

### Green
- [ ] Implement the hook (boring: explicit separator split, token-boundary
      argv[0] match, no whole-string regex for the tool name); wire
      `hooks.json` + permission config + the agent allowlist. All Red pass.
      **SC-E2, SC-E3, SC-E4 satisfied; SC-E7 testable half satisfied.**

### Blue
- [ ] Hook imports the WP-002 resolver — zero re-implemented scope logic
      (grep). Decision-channel comment cites the verified hook contract.
      Each rule the hook applies carries its locus + threat-scope in a comment
      (feeds SC-E6 in WP-005).
